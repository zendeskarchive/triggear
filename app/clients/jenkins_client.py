import asyncio
import base64
import logging
import time
from typing import List, Tuple, Dict, Union, Optional

from app.clients.async_client import AsyncClient, AsyncClientException, Payload


class JenkinsInstanceConfig:
    def __init__(self, url: str, username: str, token: str) -> None:
        self.username: str = username
        self.token: str = token
        self.url = url

    def get_auth_header(self) -> str:
        auth: bytes = f'{self.username}:{self.token}'.encode('utf-8')
        return 'Basic ' + base64.urlsafe_b64encode(auth).decode('utf8')


class JenkinsClient:
    def __init__(self, instance_config: JenkinsInstanceConfig) -> None:
        self.config: JenkinsInstanceConfig = instance_config
        self.__async_jenkins: Optional[AsyncClient] = None
        self.__crumb_header: Optional[str] = None
        self.__crumb_value: Optional[str] = None

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

    async def set_crumb_header(self) -> None:
        route = 'crumbIssuer/api/json'
        crumb_data = await self.get_async_jenkins().get(route=route)
        self.__crumb_header = crumb_data['crumbRequestField']
        self.__crumb_value = crumb_data['crumb']

    async def get_crumb_header(self) -> Optional[Dict[str, str]]:
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
                           job_path: str) -> Dict:
        job_folder, job_name = self.get_job_folder_and_name(job_path)
        route = f'{job_folder}job/{job_name}/api/json?depth=0'
        return await self.get_async_jenkins().get(route=route)

    async def get_jobs_next_build_number(self,
                                         job_path: str) -> int:
        job_info = await self.get_job_info(job_path)
        return int(job_info['nextBuildNumber'])

    async def get_build_info(self,
                             job_path: str,
                             build_number: int) -> Dict:
        job_folder, job_name = self.get_job_folder_and_name(job_path)
        route = f'{job_folder}job/{job_name}/{build_number}/api/json?depth=0'
        return await self.get_async_jenkins().get(route=route)

    async def get_job_url(self,
                          job_path: str) -> Optional[str]:
        job_info = await self.get_job_info(job_path)
        return job_info.get('url')

    async def get_build_info_data(self,
                                  job_path: str,
                                  build_number: int,
                                  timeout: float = 30.0) -> Optional[Dict]:
        timeout = time.monotonic() + timeout
        while time.monotonic() < timeout:
            try:
                build_info_data = await self.get_build_info(job_path=job_path,
                                                            build_number=build_number)
                return build_info_data
            except AsyncClientException as exception:
                if exception.status == 404:
                    logging.warning(f"Build number {build_number} was not yet found for job {job_path}."
                                    f"Probably because of high load on Jenkins build is stuck in pre-run state and it is "
                                    f"not available in history. We will retry for {timeout - time.monotonic()} sec more for it to appear.")
                    await asyncio.sleep(30)
                elif exception.status == 504:
                    logging.warning(f"Got timeout looking for #{build_number} in job {job_path}. Will retry.")
                    await asyncio.sleep(30)
                else:
                    logging.exception(f'Unexpected exception when looking for {job_path}#{build_number} info')
                    raise
        return None

    async def is_job_building(self,
                              job_path: str,
                              build_number: int) -> Optional[bool]:
        try:
            build_info = await self.get_build_info_data(job_path, build_number)
            if build_info is not None:
                return bool(build_info['building'])
        except AsyncClientException as client_exception:
            if client_exception.status != 504:
                raise
        return None

    async def build_jenkins_job(self,
                                job_path: str,
                                parameters: Union[None, Dict]) -> Dict:
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
                                 parameters: Optional[Dict]) -> Dict:
        folder_url, job_name = self.get_job_folder_and_name(job_path)
        route = f'{folder_url}job/{job_name}/buildWithParameters' if parameters else f'{folder_url}job/{job_name}/build'
        return await self.get_async_jenkins().post(route=route,
                                                   params=Payload(parameters),
                                                   headers=await self.get_crumb_header(),
                                                   content_type='text/plain')
