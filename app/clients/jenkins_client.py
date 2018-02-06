import asyncio
import base64
import logging
import time
from typing import List, Tuple, Dict, Union

from aiohttp import ClientResponse

from app.clients.async_client import AsyncClient, AsyncClientException, Payload


class JenkinsInstanceConfig:
    def __init__(self, url, username, token) -> None:
        self.username: str = username
        self.token: str = token
        self.url = url

    def get_auth_header(self):
        auth = f'{self.username}:{self.token}'
        auth = auth.encode('utf-8')
        return 'Basic ' + base64.urlsafe_b64encode(auth).decode('utf8')


class JenkinsClient:
    def __init__(self, instance_config: JenkinsInstanceConfig) -> None:
        self.config: JenkinsInstanceConfig = instance_config
        self.__async_jenkins: AsyncClient = None
        self.__crumb_header: str = None
        self.__crumb_value: str = None

    def get_async_jenkins(self) -> AsyncClient:
        if self.__async_jenkins is None:
            self.__async_jenkins = AsyncClient(
                base_url=self.config.url,
                session_headers={
                    'Authorization': self.config.get_auth_header(),
                    'Content-Type': 'application/json'
                }
            )
        return self.__async_jenkins

    async def set_crumb_header(self):
        route = 'crumbIssuer/api/json'
        crumb_response = await self.get_async_jenkins().get(route=route)
        crumb_data = await crumb_response.json()
        self.__crumb_header = crumb_data['crumbRequestField']
        self.__crumb_value = crumb_data['crumb']

    async def get_crumb_header(self) -> Union[Dict[str, str], None]:
        if self.__crumb_header is not None and self.__crumb_value is not None:
            return {self.__crumb_header: self.__crumb_value}
        return None

    @staticmethod
    def get_job_folder_and_name(job_path: str) -> Tuple[str, str]:
        path_entries: List[str] = job_path.split('/')
        job_name = path_entries[-1]
        folder_url = (('job/' + '/job/'.join(path_entries[:-1]) + '/') if len(path_entries) > 1 else '')
        return folder_url, job_name

    async def get_job_info(self,
                           job_path: str) -> ClientResponse:
        job_folder, job_name = self.get_job_folder_and_name(job_path)
        route = f'{job_folder}job/{job_name}/api/json?depth=0'
        return await self.get_async_jenkins().get(route=route)

    async def get_jobs_next_build_number(self,
                                         job_path: str) -> int:
        job_info_response = await self.get_job_info(job_path)
        job_info = await job_info_response.json()
        return job_info['nextBuildNumber']

    async def get_build_info(self,
                             job_path: str,
                             build_number: int) -> ClientResponse:
        job_folder, job_name = self.get_job_folder_and_name(job_path)
        route = f'{job_folder}job/{job_name}/{build_number}/api/json?depth=0'
        return await self.get_async_jenkins().get(route=route)

    async def get_job_url(self,
                          job_path: str) -> str:
        job_info_response = await self.get_job_info(job_path)
        job_info = await job_info_response.json()
        return job_info.get('url')

    async def get_build_info_data(self,
                                  job_path: str,
                                  build_number: int,
                                  timeout: float=30.0) -> Union[Dict, None]:
        timeout = time.monotonic() + timeout
        while time.monotonic() < timeout:
            try:
                build_info_response = await self.get_build_info(job_path=job_path,
                                                                build_number=build_number)
                return await build_info_response.json()
            except AsyncClientException as exception:
                if exception.status == 404:
                    logging.warning(f"Build number {build_number} was not yet found for job {job_path}."
                                    f"Probably because of high load on Jenkins build is stuck in pre-run state and it is "
                                    f"not available in history. We will retry for {timeout - time.monotonic()} sec more for it to appear.")
                    await asyncio.sleep(1)
                else:
                    logging.exception(f'Unexpected exception when looking for {job_path}#{build_number} info')
                    raise
        return None

    async def is_job_building(self,
                              job_path: str,
                              build_number: int) -> Union[bool, None]:
        build_info = await self.get_build_info_data(job_path, build_number)
        if build_info is not None:
            return build_info['building']
        return None

    async def build_jenkins_job(self,
                                job_path: str,
                                parameters: Union[None, Dict]):
        try:
            return await self._build_jenkins_job(job_path, parameters=parameters)
        except AsyncClientException as exception:
            logging.exception(f'Exception caught when building job {job_path} with params {parameters}')
            if exception.status == 400 and 'Nothing is submitted' in exception.message:
                logging.exception(f'Will retry building {job_path} with {{"": ""}} as params')
                # workaround for Jenkins issue with calling parametrized jobs with no parameters
                return await self._build_jenkins_job(job_path, parameters={'': ''})
            elif exception.status == 403 and 'No valid crumb was included in the request' in exception.message:
                logging.exception(f'Will retry building {job_path} as crumb was missing/invalid. Crumb reset incoming')
                # workaround for Jenkins issue requiring crumb even if token authorization is valid - should be fixed in 2.96
                await self.set_crumb_header()
                return await self._build_jenkins_job(job_path, parameters=parameters)
            raise

    async def _build_jenkins_job(self,
                                 job_path: str,
                                 parameters: Union[None, Dict]):
        folder_url, job_name = self.get_job_folder_and_name(job_path)
        route = f'{folder_url}job/{job_name}/buildWithParameters' if parameters else f'{folder_url}job/{job_name}/build'
        return await self.get_async_jenkins().post(route=route,
                                                   params=Payload(parameters),
                                                   headers=await self.get_crumb_header())
