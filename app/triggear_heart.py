import asyncio
import logging
from typing import Optional, Dict, Union

from app.clients.async_client import AsyncClientNotFoundException, AsyncClientException
from app.clients.github_client import GithubClient
from app.clients.jenkinses_clients import JenkinsesClients
from app.clients.mongo_client import MongoClient
from app.enums.jenkins_build_state import JenkinsBuildState
from app.mongo.registration_fields import RegistrationFields
from app.hook_details.hook_details import HookDetails
from app.hook_details.hook_params_parser import HookParamsParser
from app.mongo.registration_cursor import RegistrationCursor


class TriggearHeart:
    def __init__(self,
                 mongo_client: MongoClient,
                 github_client: GithubClient,
                 jenkinses_clients: JenkinsesClients) -> None:
        self.__mongo_client: MongoClient = mongo_client
        self.__github_client: GithubClient = github_client
        self.__jenkinses_clients: JenkinsesClients = jenkinses_clients

    async def trigger_registered_jobs(self, hook_details: HookDetails) -> None:
        async for registration_cursor in self.__mongo_client.get_registered_jobs(hook_details):
            if await hook_details.should_trigger(registration_cursor, self.__github_client):
                try:
                    await self.__jenkinses_clients.get_jenkins(registration_cursor.jenkins_url)\
                        .get_job_info(registration_cursor.job_name)  # Raises if job does not exist on Jenkins
                    asyncio.get_event_loop().create_task(self.trigger_registered_job(hook_details, registration_cursor))
                except AsyncClientNotFoundException:
                    logging.exception(f"Job {registration_cursor.jenkins_url}:{registration_cursor.job_name} was not found on Jenkins anymore - "
                                      f"incrementing {RegistrationFields.MISSED_TIMES} for query {hook_details.get_query()}")
                    await self.__mongo_client.increment_missed_counter(hook_details, registration_cursor)

            else:
                logging.warning(f'Hook details {hook_details} will not be run due to unmet registration restrictions in {registration_cursor}')

    async def trigger_registered_job(self,
                                     hook_details: HookDetails,
                                     registration_cursor: RegistrationCursor) -> None:
        hook_details.setup_final_param_values(registration_cursor)
        job_params = HookParamsParser.get_requested_parameters_values(hook_details, registration_cursor)
        jenkins_client = self.__jenkinses_clients.get_jenkins(registration_cursor.jenkins_url)
        try:
            next_build_number = await jenkins_client.get_jobs_next_build_number(registration_cursor.job_name)
        except KeyError:
            # INFO: KeyError means that nextBuildNumber is not available - either plugin is not installed or it's a MultiBranch pipeline
            # In both cases we just want to run the job
            logging.warning(f"Running job that didn't have next build number: {registration_cursor.job_name}")
            await jenkins_client.build_jenkins_job(registration_cursor.job_name, job_params)
            return
        job_url: Optional[str] = await jenkins_client.get_job_url(registration_cursor.job_name)
        try:
            await jenkins_client.build_jenkins_job(registration_cursor.job_name, job_params)
            logging.warning(f"Scheduled build of: {registration_cursor.jenkins_url}:{registration_cursor.job_name} #{next_build_number}"
                            f"with params: {job_params}")
        except AsyncClientException:
            logging.exception(f"Job {registration_cursor.jenkins_url}:{registration_cursor.job_name} did "
                              f"not accept {job_params} as parameters but it requested them")

            await self.report_unaccepted_parameters_to_github(hook_details, registration_cursor, job_url, next_build_number, job_params)
            return

        build_info = await jenkins_client.get_build_info_data(registration_cursor.job_name, next_build_number, 3600)
        if build_info is not None:
            logging.warning(f"Creating pending status for {registration_cursor.jenkins_url}:{registration_cursor.job_name} "
                            f"in repo {registration_cursor.repo} (ref {hook_details.get_ref()})")

            await self.__github_client.create_github_build_status(repo=registration_cursor.repo,
                                                                  sha=hook_details.get_ref(),
                                                                  state="pending",
                                                                  url=build_info['url'],
                                                                  description="build in progress",
                                                                  context=registration_cursor.job_name)

            while await jenkins_client.is_job_building(registration_cursor.job_name, next_build_number):
                await asyncio.sleep(1)

            build_info = await jenkins_client.get_build_info_data(registration_cursor.job_name, next_build_number)
            logging.warning(f"Build {registration_cursor.jenkins_url}:{registration_cursor.job_name} #{next_build_number} finished.")

            final_build_state = JenkinsBuildState.get_by_build_info(build_info)
            logging.warning(f"Creating build status for {registration_cursor.jenkins_url}:{registration_cursor.job_name} #{next_build_number} - "
                            f"verdict: {final_build_state}.")

            if build_info is not None:
                await self.__github_client.create_github_build_status(repo=registration_cursor.repo,
                                                                      sha=hook_details.get_ref(),
                                                                      state=final_build_state.state,
                                                                      url=build_info['url'],
                                                                      description=final_build_state.description,
                                                                      context=registration_cursor.job_name)
            else:
                logging.warning(f'Could not create status for {registration_cursor.jenkins_url}:{registration_cursor.job_name} #{next_build_number} '
                                f'as build info was null')
        else:
            logging.exception(f"Triggear was not able to find build number {next_build_number} for job "
                              f"{registration_cursor.jenkins_url}:{registration_cursor.job_name}. Task aborted.")
            await self.report_not_found_build_to_github(hook_details, registration_cursor, job_url, next_build_number)

    async def report_not_found_build_to_github(self,
                                               hook_details: HookDetails,
                                               registration_cursor: RegistrationCursor,
                                               job_url: Optional[str],
                                               next_build_number: int) -> None:
        if job_url is not None:
            await self.__github_client.create_github_build_status(repo=registration_cursor.repo,
                                                                  sha=hook_details.get_ref(),
                                                                  state="error",
                                                                  url=job_url,
                                                                  description=f"Triggear cant find build {registration_cursor.jenkins_url}"
                                                                              f":{registration_cursor.job_name} #{next_build_number}",
                                                                  context=registration_cursor.job_name)
        else:
            logging.error(f'Could not report error for job {registration_cursor.jenkins_url}:{registration_cursor.job_name} #{next_build_number}'
                          f'as job URL is missing')

    async def report_unaccepted_parameters_to_github(self,
                                                     hook_details: HookDetails,
                                                     registration_cursor: RegistrationCursor,
                                                     job_url: Optional[str],
                                                     next_build_number: int,
                                                     job_params: Optional[Dict[str, str]]) -> None:
        if job_url is not None:
            await self.__github_client.create_github_build_status(
                repo=registration_cursor.repo,
                sha=hook_details.get_ref(),
                state="error",
                url=job_url,
                description=f"Job {registration_cursor.jenkins_url}:{registration_cursor.job_name} did not accept requested parameters "
                            f"{job_params.keys() if job_params is not None else None}",
                context=registration_cursor.job_name)
        else:
            logging.error(f'Could not report error for job {registration_cursor.jenkins_url}:{registration_cursor.job_name} #{next_build_number}'
                          f'as job URL is missing')
