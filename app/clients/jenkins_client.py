import asyncio
import logging

import jenkins
import time
from urllib.error import HTTPError

from app.config.triggear_config import JenkinsInstanceConfig


class JenkinsClient:
    def __init__(self, instance_config: JenkinsInstanceConfig):
        self.config = instance_config
        self.__client = None

    @property
    def client(self) -> jenkins.Jenkins:
        if self.__client is None:
            self.setup_client()
        return self.__client

    @client.setter
    def client(self, client):
        self.__client = client

    def setup_client(self):
        self.__client = jenkins.Jenkins(url=self.config.url,
                                        username=self.config.username,
                                        password=self.config.token)

    async def get_jobs_next_build_number(self, job_name) -> int:
        return self.client.get_job_info(job_name)['nextBuildNumber']

    async def get_build_info(self, job_name, build_number):
        timeout = time.monotonic() + 30
        while time.monotonic() < timeout:
            try:
                return self.client.get_build_info(job_name, build_number)
            except jenkins.NotFoundException:
                logging.warning(f"Build number {build_number} was not yet found for job {job_name}."
                                f"Probably because of high load on Jenkins build is stuck in pre-run state and it is "
                                f"not available in history. We will retry for 30 sec for it to appear.")
                await asyncio.sleep(1)
        return None

    def build_jenkins_job(self, job_name, job_params):
        try:
            self.client.build_job(job_name, parameters=job_params)
        except HTTPError as http_error:
            logging.exception(f'Exception caught when building job {job_name} with params {job_params}')
            if http_error.code == 400 and http_error.msg == 'Nothing is submitted':
                logging.warning(f'Will retry building {job_name} with {{"": ""}} as params')
                # workaround for jenkins.Jenkins issue with calling parametrized jobs with no parameters
                self.client.build_job(job_name, parameters={'': ''})
                return
            raise

    async def get_job_url(self, job_name):
        return self.client.get_job_info(job_name).get('url')

    async def is_job_building(self, job_name, build_number):
        build_info = await self.get_build_info(job_name, build_number)
        if build_info is not None:
            return build_info['building']
        return None
