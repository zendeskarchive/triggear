import asyncio
import hmac
import logging
from typing import Dict, List, Set
from typing import Optional
from typing import Tuple

import aiohttp.web
import aiohttp.web_request
import motor.motor_asyncio
import yaml
from aiohttp.web_response import Response

from app.clients.async_client import AsyncClientException, AsyncClientNotFoundException
from app.clients.github_client import GithubClient
from app.clients.jenkins_client import JenkinsClient
from app.config.triggear_config import TriggearConfig
from app.dto.hook_details import HookDetails
from app.dto.hook_details_factory import HookDetailsFactory
from app.enums.event_types import EventTypes
from app.enums.labels import Labels
from app.enums.registration_fields import RegistrationFields
from app.exceptions.triggear_error import TriggearError
from app.request_schemes.register_request_data import RegisterRequestData
from app.utilities.constants import BRANCH_DELETED_SHA
from app.utilities.err_handling import handle_exceptions
from app.utilities.functions import any_starts_with, get_all_starting_with


class GithubController:
    def __init__(self,
                 github_client: GithubClient,
                 mongo_client: motor.motor_asyncio.AsyncIOMotorClient,
                 config: TriggearConfig):
        self.__github_client = github_client
        self.__mongo_client = mongo_client
        self.__jenkins_clients: Dict[str, JenkinsClient] = {}
        self.config = config

    def get_jenkins(self, url: str) -> JenkinsClient:
        client = self.__jenkins_clients.get(url)
        if client is None:
            logging.warning(f'Missing client for {url} - will create one')
            self.setup_jenkins_client(url)
        return self.__jenkins_clients.get(url)

    def setup_jenkins_client(self, url: str):
        if self.config.jenkins_instances.get(url) is None:
            logging.warning(f'Missing Jenkins {url} in current config. Will reload the config to check for new instances')
            try:
                new_config = TriggearConfig()
                if new_config.jenkins_instances.get(url) is None:
                    raise TriggearError(f'Jenkins {url} not defined in current config. Please add its definition to creds file')
                else:
                    self.config = new_config
            except (yaml.YAMLError, KeyError):
                logging.exception('Exception caught when trying to reconfigure for new Jenkins instance in GithubController.'
                                  'Please check validity of provided config. Sticking with old one for now.')
                raise
        self.__jenkins_clients[url] = JenkinsClient(self.config.jenkins_instances.get(url))

    async def validate_webhook_secret(self, req):
        header_signature = req.headers.get('X-Hub-Signature')

        if header_signature is None:
            return 401, 'Unauthorized'
        sha_name, signature = header_signature.split('=')
        if sha_name != 'sha1':
            return 501, "Only SHA1 auth supported"

        req_body = await req.read()
        mac = hmac.new(bytearray(self.config.triggear_token, 'utf-8'), msg=req_body, digestmod='sha1')
        if not hmac.compare_digest(str(mac.hexdigest()), str(signature)):
            return 401, 'Unauthorized'
        return 'AUTHORIZED'

    @staticmethod
    async def get_request_json(request: aiohttp.web_request.Request) -> Dict:
        return await request.json()

    @handle_exceptions()
    async def handle_hook(self, request: aiohttp.web_request.Request) -> Optional[Response]:
        validation = await self.validate_webhook_secret(request)
        if validation != 'AUTHORIZED':
            return aiohttp.web.Response(text=validation[1], status=validation[0])

        data = await self.get_request_json(request)
        logging.warning(f"Hook received")

        action = data.get('action')
        if action == EventTypes.labeled:
            await self.handle_labeled(data)
        elif action == EventTypes.synchronize:
            await self.handle_synchronize(data)
        elif action == EventTypes.comment:
            await self.handle_comment(data)
        elif await self.get_request_event_header(request) == EventTypes.pull_request:
            if action == EventTypes.pr_opened:
                await self.handle_pr_opened(data)
        elif await self.get_request_event_header(request) == EventTypes.push:
            if data['ref'].startswith('refs/heads/'):
                await self.handle_push(data)
            elif data['ref'].startswith('refs/tags/'):
                await self.handle_tagged(data)
        elif await self.get_request_event_header(request) == EventTypes.release:
            await self.handle_release(data)
        return aiohttp.web.Response(text='Hook ACK')

    @staticmethod
    async def get_request_event_header(request: aiohttp.web_request.Request) -> str:
        return request.headers.get('X-GitHub-Event')

    async def handle_release(self, data: Dict):
        hook_details: HookDetails = HookDetailsFactory.get_release_details(data)
        await self.trigger_registered_jobs(hook_details)

    async def handle_pr_opened(self, data: Dict):
        hook_details: HookDetails = HookDetailsFactory.get_pr_opened_details(data)
        await self.__github_client.set_sync_label(hook_details.repository, number=data['pull_request']['number'])
        await self.trigger_registered_jobs(hook_details)

    async def handle_tagged(self, data: dict):
        hook_details: HookDetails = HookDetailsFactory.get_tag_details(data)
        if hook_details.sha != BRANCH_DELETED_SHA:
            await self.trigger_registered_jobs(hook_details)
        else:
            logging.warning(f"Tag {hook_details.tag} was deleted as SHA was zeros only!")

    async def handle_labeled(self, data: dict):
        await self.trigger_registered_jobs(HookDetailsFactory.get_labeled_details(data))

    async def handle_synchronize(self, data: Dict):
        pr_labels = await self.__github_client.get_pr_labels(repo=data['pull_request']['head']['repo']['full_name'],
                                                             number=data['pull_request']['number'])
        try:
            await self.handle_pr_sync(data, pr_labels)
        finally:
            # we want to call labeled sync even is something went wrong in pr-sync handler
            await self.handle_labeled_sync(data, pr_labels)

    async def handle_pr_sync(self, data, pr_labels):
        if Labels.pr_sync in pr_labels:
            logging.warning(f'Sync hook on PR with {Labels.pr_sync} - handling like PR open')
            await self.handle_pr_opened(data)

    async def handle_labeled_sync(self, data, pr_labels):
        if Labels.label_sync in pr_labels and len(pr_labels) > 1:
            pr_labels.remove(Labels.label_sync)
            for label in pr_labels:
                # update data to have fields required from labeled hook
                # it's necessary for HookDetailsFactory in handle_labeled
                data.update({'label': {'name': label}})
                logging.warning(f'Sync hook on PR with {Labels.label_sync} - handling like PR labeled')
                await self.handle_labeled(data)

    async def handle_comment(self, data):
        comment_body = data['comment']['body']
        if comment_body == Labels.label_sync:
            await self.handle_labeled_sync_comment(data)
        elif comment_body == Labels.pr_sync:
            await self.handle_pr_sync_comment(data)

    async def handle_pr_sync_comment(self, data):
        head_branch, head_sha = await self.get_comment_branch_and_sha(data)
        await self.trigger_registered_jobs(HookDetailsFactory.get_pr_sync_details(data, head_branch, head_sha))

    async def get_comment_branch_and_sha(self, data: Dict) -> Tuple:
        repository_name = data['repository']['full_name']
        pr_number = data['issue']['number']
        head_branch = await self.__github_client.get_pr_branch(repository_name, pr_number)
        head_sha = await self.__github_client.get_latest_commit_sha(repository_name, pr_number)
        return head_branch, head_sha

    async def handle_labeled_sync_comment(self, data):
        head_branch, head_sha = await self.get_comment_branch_and_sha(data)
        for hook_details in HookDetailsFactory.get_labeled_sync_details(data, head_branch=head_branch, head_sha=head_sha):
            await self.trigger_registered_jobs(hook_details)

    async def handle_push(self, data):
        hook_details: HookDetails = HookDetailsFactory.get_push_details(data)
        if hook_details.sha != BRANCH_DELETED_SHA:
            await self.trigger_registered_jobs(hook_details)
        else:
            logging.warning(f"Branch {hook_details.branch} was deleted as SHA was zeros only!")

    async def trigger_registered_jobs(self, hook_details: HookDetails):
        collection = await self.get_collection_for_hook_type(hook_details.event_type)
        async for document in collection.find(hook_details.query):
            job_name = document[RegistrationFields.job]
            jenkins_url = document[RegistrationFields.jenkins_url]

            branch_restrictions = document.get(RegistrationFields.branch_restrictions)
            branch_restrictions = branch_restrictions if branch_restrictions is not None else []

            change_restrictions = document.get(RegistrationFields.change_restrictions)
            change_restrictions = change_restrictions if change_restrictions is not None else []

            file_restrictions = document.get(RegistrationFields.file_restrictions)
            file_restrictions = file_restrictions if file_restrictions is not None else []

            if not change_restrictions or any_starts_with(any_list=hook_details.changes, starts_with_list=change_restrictions):
                if not branch_restrictions or hook_details.branch in branch_restrictions:
                    if not file_restrictions or await self.are_files_in_repo(files=file_restrictions, hook=hook_details):
                        job_requested_params = document[RegistrationFields.requested_params]
                        try:
                            await self.get_jenkins(jenkins_url).get_jobs_next_build_number(job_name)  # Raises if job does not exist on Jenkins
                            asyncio.get_event_loop().create_task(self.trigger_registered_job(
                                jenkins_url=jenkins_url,
                                job_name=job_name,
                                job_requested_params=job_requested_params,
                                repository=document[RegistrationFields.repository],
                                sha=hook_details.sha,
                                pr_branch=hook_details.branch,
                                tag=hook_details.tag,
                                relevant_changes=get_all_starting_with(hook_details.changes, change_restrictions)
                            ))
                        except AsyncClientNotFoundException:
                            update_query = hook_details.query
                            update_query[RegistrationFields.job] = job_name
                            logging.exception(f"Job {jenkins_url}:{job_name} was not found on Jenkins anymore - "
                                              f"incrementing {RegistrationFields.missed_times} "
                                              f"for query {update_query}")
                            await collection.update_one(update_query, {'$inc': {RegistrationFields.missed_times: 1}})
                    else:
                        logging.warning(f"Job {jenkins_url}:{job_name} was registered with following file restrictions: "
                                        f"{file_restrictions}. Current hook was on {hook_details.branch}/{hook_details.sha}, "
                                        f"which appears not to have one of those files. That's why"
                                        f"Triggear will not build this job.")
                else:
                    logging.warning(f"Job {jenkins_url}:{job_name} was registered with following branch restrictions: "
                                    f"{branch_restrictions}. Current push was on {hook_details.branch} branch, "
                                    f"so Triggear will not build this job.")
            else:
                logging.warning(f"Job {jenkins_url}:{job_name} was registered with following change restrictions: "
                                f"{change_restrictions}. Current push had changes in {hook_details.changes}, "
                                f"so Triggear will not build this job.")

    async def are_files_in_repo(self, files: List[str], hook: HookDetails) -> bool:
        try:
            for file in files:
                await self.__github_client.get_file_content(repo=hook.repository, ref=hook.sha if hook.sha else hook.branch, path=file)
        except AsyncClientException as gh_exc:
            logging.exception(f"Exception when looking for file {file} in repo {hook.repository} at ref {hook.sha}/{hook.branch} (Exc: {gh_exc})")
            return False
        return True

    async def get_collection_for_hook_type(self, event_type: EventTypes):
        return self.__mongo_client.registered[event_type]

    async def trigger_registered_job(self,
                                     jenkins_url: str,
                                     job_name: str,
                                     job_requested_params: List[str],
                                     repository: str,
                                     sha: str,
                                     pr_branch: str,
                                     tag: str=None,
                                     relevant_changes: Set[str]=set()):
        job_params = await self.get_requested_parameters_values(job_requested_params, pr_branch, sha, tag, relevant_changes)
        next_build_number = await self.get_jenkins(jenkins_url).get_jobs_next_build_number(job_name)
        try:
            await self.get_jenkins(jenkins_url).build_jenkins_job(job_name, job_params)
            logging.warning(f"Scheduled build of: {jenkins_url}:{job_name} #{next_build_number}")
        except AsyncClientException as jenkins_exception:
            logging.exception(f"Job {jenkins_url}:{job_name} did not accept {job_params} as parameters but it requested them "
                              f"(Error: {jenkins_exception})")

            await self.__github_client.create_github_build_status(repository, sha, "error",
                                                                  await self.get_jenkins(jenkins_url).get_job_url(job_name),
                                                                  f"Job {jenkins_url}:{job_name} "
                                                                  f"did not accept requested parameters {job_params.keys()}",
                                                                  job_name)
            return

        build_info = await self.get_jenkins(jenkins_url).get_build_info_data(job_name, next_build_number)
        if build_info is not None:
            logging.warning(f"Creating pending status for {jenkins_url}:{job_name} in repo {repository} (branch {pr_branch}, sha {sha}")

            await self.__github_client.create_github_build_status(repository, sha, "pending", build_info['url'], "build in progress", job_name)

            while await self.get_jenkins(jenkins_url).is_job_building(job_name, next_build_number):
                await asyncio.sleep(1)

            build_info = await self.get_jenkins(jenkins_url).get_build_info_data(job_name, next_build_number)
            logging.warning(f"Build {jenkins_url}:{job_name} #{next_build_number} finished.")

            final_state = await self.get_final_build_state(build_info)
            final_description = await self.get_final_build_description(build_info)
            logging.warning(f"Creating build status for {jenkins_url}:{job_name} #{next_build_number} - verdict: {final_state}.")

            await self.__github_client.create_github_build_status(repository, sha, final_state, build_info['url'], final_description, job_name)
        else:
            logging.exception(f"Triggear was not able to find build number {next_build_number} for job {jenkins_url}:{job_name}. Task aborted.")
            await self.__github_client.create_github_build_status(repository, sha, "error",
                                                                  await self.get_jenkins(jenkins_url).get_job_url(job_name),
                                                                  f"Triggear cant find build {jenkins_url}:{job_name} #{next_build_number}",
                                                                  job_name)

    @staticmethod
    async def get_final_build_state(build_info):
        return "success" if build_info['result'] == "SUCCESS" \
            else "success" if build_info['result'] == "UNSTABLE" \
            else "failure" if build_info['result'] == "FAILURE" \
            else "failure" if build_info['result'] == "ABORTED" \
            else "error"

    @staticmethod
    async def get_final_build_description(build_info):
        return "build succeeded" if build_info['result'] == "SUCCESS" \
            else "build unstable" if build_info['result'] == "UNSTABLE" \
            else "build failed" if build_info['result'] == "FAILURE" \
            else "build aborted" if build_info['result'] == "ABORTED" \
            else "build error"

    @staticmethod
    async def get_requested_parameters_values(job_requested_params: List[str], pr_branch: str, sha: str, tag: str, changes: Set[str] = set()):
        job_params = None
        if job_requested_params:
            job_params = {}
            for param in job_requested_params:
                if param.startswith(RegisterRequestData.RequestedParams.branch):
                    param_key = await GithubController.__get_parsed_param_key(RegisterRequestData.RequestedParams.branch, param)
                    job_params[param_key] = pr_branch
                if param.startswith(RegisterRequestData.RequestedParams.sha):
                    param_key = await GithubController.__get_parsed_param_key(RegisterRequestData.RequestedParams.sha, param)
                    job_params[param_key] = sha
                if param.startswith(RegisterRequestData.RequestedParams.tag):
                    param_key = await GithubController.__get_parsed_param_key(RegisterRequestData.RequestedParams.tag, param)
                    job_params[param_key] = tag
                if param.startswith(RegisterRequestData.RequestedParams.changes):
                    param_key = await GithubController.__get_parsed_param_key(RegisterRequestData.RequestedParams.changes, param)
                    job_params[param_key] = ','.join(changes)
        return job_params if job_params != {} else None
