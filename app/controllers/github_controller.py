import asyncio
import hmac
import logging
import time
from typing import Dict, List, Set
from typing import Optional
from typing import Tuple

import aiohttp.web
import aiohttp.web_request
import github
import jenkins
import motor.motor_asyncio
from aiohttp.web_response import Response
from urllib.error import HTTPError

from app.config.triggear_config import TriggearConfig
from app.dto.hook_details import HookDetails
from app.dto.hook_details_factory import HookDetailsFactory
from app.enums.event_types import EventTypes
from app.enums.labels import Labels
from app.enums.registration_fields import RegistrationFields
from app.exceptions.triggear_timeout_error import TriggearTimeoutError
from app.request_schemes.register_request_data import RegisterRequestData
from app.utilities.background_task import BackgroundTask
from app.utilities.constants import LAST_RUN_IN, BRANCH_DELETED_SHA, TRIGGEAR_RUN_PREFIX
from app.utilities.err_handling import handle_exceptions
from app.utilities.functions import any_starts_with, get_all_starting_with


class GithubController:
    def __init__(self,
                 github_client: github.Github,
                 mongo_client: motor.motor_asyncio.AsyncIOMotorClient,
                 jenkins_client: jenkins.Jenkins,
                 config: TriggearConfig):
        self.__gh_client = github_client
        self.__mongo_client = mongo_client
        self.__jenkins_client = jenkins_client
        self._rerun_time_limit: int = config.rerun_time_limit
        self.api_token: str = config.triggear_token

    async def validate_webhook_secret(self, req):
        header_signature = req.headers.get('X-Hub-Signature')

        if header_signature is None:
            return 401, 'Unauthorized'
        sha_name, signature = header_signature.split('=')
        if sha_name != 'sha1':
            return 501, "Only SHA1 auth supported"

        req_body = await req.read()
        mac = hmac.new(bytearray(self.api_token, 'utf-8'), msg=req_body, digestmod='sha1')
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
        return aiohttp.web.Response(text='Hook ACK')

    @staticmethod
    async def get_request_event_header(request: aiohttp.web_request.Request) -> str:
        return request.headers.get('X-GitHub-Event')

    async def handle_pr_opened(self, data: dict):
        hook_details: HookDetails = HookDetailsFactory.get_pr_opened_details(data)
        await self.set_sync_label(hook_details.repository, pr_number=data['pull_request']['number'])
        await self.trigger_registered_jobs(hook_details)

    async def set_sync_label(self, repository, pr_number):
        if Labels.pr_sync in self.get_repo_labels(repository):
            logging.warning(f'Setting "triggear-pr-sync" label on PR {pr_number} in repo {repository}')
            await self.set_pr_sync_label_with_retry(repository, pr_number)
            logging.warning('Label set')

    async def set_pr_sync_label_with_retry(self, repo, pr_number):
        retries = 3
        while retries:
            try:
                self.__gh_client.get_repo(repo).get_issue(pr_number).add_to_labels(Labels.pr_sync)
                return
            except github.GithubException as gh_exception:
                logging.exception(f'Exception when trying to set label on PR. Exception: {gh_exception}')
                retries -= 1
                await asyncio.sleep(1)
        raise TriggearTimeoutError(f'Failed to set label on PR #{pr_number} in repo {repo} after 3 retries')

    def get_repo_labels(self, repo: str):
        return [label.name for label in self.__gh_client.get_repo(repo).get_labels()]

    async def handle_tagged(self, data: dict):
        await self.trigger_registered_jobs(HookDetailsFactory.get_tag_details(data))

    async def handle_labeled(self, data: dict):
        await self.trigger_registered_jobs(HookDetailsFactory.get_labeled_details(data))

    async def handle_synchronize(self, data: Dict):
        pr_labels = self.get_pr_labels(repository=data['pull_request']['head']['repo']['full_name'],
                                       pr_number=data['pull_request']['number'])
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

    def get_pr_labels(self, repository, pr_number):
        return [label.name for label in self.__gh_client.get_repo(repository).get_issue(pr_number).labels]

    async def handle_comment(self, data):
        comment_body = data['comment']['body']
        if comment_body.startswith(TRIGGEAR_RUN_PREFIX):
            await self.handle_run_comment(data)
        else:
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
        head_branch = self.get_pr_branch(pr_number, repository_name)
        head_sha = self.get_latest_commit_sha(pr_number, repository_name)
        return head_branch, head_sha

    async def handle_labeled_sync_comment(self, data):
        head_branch, head_sha = await self.get_comment_branch_and_sha(data)
        for hook_details in HookDetailsFactory.get_labeled_sync_details(data, head_branch=head_branch, head_sha=head_sha):
            await self.trigger_registered_jobs(hook_details)

    async def handle_run_comment(self, data):
        comment_body_parts = data['comment']['body'].split()[2:]
        job_name = comment_body_parts[0]
        repository_name = data['repository']['full_name']
        pr_number = data['issue']['number']
        pr_branch = self.get_pr_branch(pr_number, repository_name)
        job_params = comment_body_parts[1:] if len(comment_body_parts) > 1 else {}
        job_params = {param_name: param_value for param_name, param_value
                      in [item.split('=') for item in job_params]}
        logging.warning(f"Hook details: single run comment for repository {repository_name} and branch {pr_branch}")
        await self.trigger_unregistered_job(job_name, pr_branch, job_params, repository_name, pr_number)

    def get_latest_commit_sha(self, pr_number: int, repository_name: str) -> str:
        return self.__gh_client.get_repo(repository_name).get_pull(pr_number).head.sha

    def get_pr_branch(self, pr_number: int, repository_name: str) -> str:
        return self.__gh_client.get_repo(repository_name).get_pull(pr_number).head.ref

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
                            self.get_jobs_next_build_number(job_name)  # Raises if job does not exist on Jenkins
                            if await self.can_trigger_job_by_branch(job_name, hook_details.branch):
                                await BackgroundTask().run(self.trigger_registered_job,
                                                           (
                                                               job_name,
                                                               job_requested_params,
                                                               document[RegistrationFields.repository],
                                                               hook_details.sha,
                                                               hook_details.branch,
                                                               hook_details.tag,
                                                               get_all_starting_with(hook_details.changes, change_restrictions)
                                                           ),
                                                           callback=None)
                        except jenkins.NotFoundException:
                            update_query = hook_details.query
                            update_query[RegistrationFields.job] = job_name
                            logging.exception(f"Job {job_name} was not found on Jenkins anymore - incrementing {RegistrationFields.missed_times} "
                                              f"for query {update_query}")
                            await collection.update_one(update_query, {'$inc': {RegistrationFields.missed_times: 1}})
                    else:
                        logging.warning(f"Job {job_name} was registered with following file restrictions: "
                                        f"{file_restrictions}. Current hook was on {hook_details.branch}/{hook_details.sha}, "
                                        f"which appears not to have one of those files. That's why"
                                        f"Triggear will not build this job.")
                else:
                    logging.warning(f"Job {job_name} was registered with following branch restrictions: "
                                    f"{branch_restrictions}. Current push was on {hook_details.branch} branch, "
                                    f"so Triggear will not build this job.")
            else:
                logging.warning(f"Job {job_name} was registered with following change restrictions: "
                                f"{change_restrictions}. Current push had changes in {hook_details.changes}, "
                                f"so Triggear will not build this job.")

    async def are_files_in_repo(self, files: List[str], hook: HookDetails) -> bool:
        try:
            for file in files:
                self.__gh_client.get_repo(hook.repository).get_file_contents(path=file, ref=hook.sha if hook.sha else hook.branch)
        except github.GithubException as gh_exc:
            logging.exception(f"Exception when looking for file {file} in repo {hook.repository} at ref {hook.sha}/{hook.branch} (Exc: {gh_exc})")
            return False
        return True

    async def get_collection_for_hook_type(self, event_type: EventTypes):
        return self.__mongo_client.registered[event_type]

    def get_jobs_next_build_number(self, job_name) -> int:
        return self.__jenkins_client.get_job_info(job_name)['nextBuildNumber']

    async def trigger_unregistered_job(self, job_name, pr_branch, job_params, repository, pr_number):
        if await self.can_trigger_job_by_branch(job_name, pr_branch):
            next_build_number = self.get_jobs_next_build_number(job_name)

            try:
                self.build_jenkins_job(job_name, job_params)
            except jenkins.JenkinsException as jenkins_exception:
                logging.exception(f"Job {job_name} did not accept {job_params} as parameters but it was passed to it (Error: {jenkins_exception})")
                return

            while await self.is_job_building(job_name, next_build_number):
                await asyncio.sleep(1)
            build_info = await self.get_build_info(job_name, next_build_number)

            if build_info is not None:
                final_state = await self.get_final_build_state(build_info)
                final_description = await self.get_final_build_description(build_info)
                self.create_pr_comment(pr_number, repository,
                                       body=f"Job {job_name} finished with status {final_state} - {final_description} ({build_info['url']})")
            else:
                logging.exception(f"Triggear was not able to find build number {next_build_number} for job {job_name}. Task aborted.")

    def create_pr_comment(self, pr_number, repository, body):
        self.__gh_client.get_repo(repository).get_issue(pr_number).create_comment(body=body)

    async def get_build_info(self, job_name, build_number):
        timeout = time.monotonic() + 30
        while time.monotonic() < timeout:
            try:
                return self.__jenkins_client.get_build_info(job_name, build_number)
            except jenkins.NotFoundException:
                logging.warning(f"Build number {build_number} was not yet found for job {job_name}."
                                f"Probably because of high load on Jenkins build is stuck in pre-run state and it is "
                                f"not available in history. We will retry for 30 sec for it to appear.")
                await asyncio.sleep(1)
        return None

    async def is_job_building(self, job_name, build_number):
        build_info = await self.get_build_info(job_name, build_number)
        if build_info is not None:
            return build_info['building']
        return None

    def build_jenkins_job(self, job_name, job_params):
        try:
            self.__jenkins_client.build_job(job_name, parameters=job_params)
        except HTTPError as http_error:
            if http_error.code == 400 and http_error.msg == 'Nothing is submitted':
                # workaround for jenkins.Jenkins issue with calling parametrized jobs with no parameters
                self.__jenkins_client.build_job(job_name, parameters={'': ''})
                return
            raise

    async def can_trigger_job_by_branch(self, job_name, branch):
        last_job_run_in_branch = {"branch": branch, "job": job_name}
        collection = self.__mongo_client.registered[LAST_RUN_IN]
        found_run = await collection.find_one(last_job_run_in_branch)
        last_job_run_in_branch['timestamp'] = int(time.time())
        if not found_run:
            await collection.insert_one(last_job_run_in_branch)
            logging.warning(f"Job {job_name} was never run in branch {branch}")
        else:
            if int(time.time()) - found_run['timestamp'] < self._rerun_time_limit:
                logging.warning(f"Job {job_name} was run in branch {branch} less then {self._rerun_time_limit} - won't be triggered")
                return False
            else:
                await collection.replace_one(found_run, last_job_run_in_branch)
                logging.warning(f"Job {job_name} for branch {branch} ran more then {self._rerun_time_limit} ago. Will be run, last run time updated.")
        return True

    async def trigger_registered_job(self,
                                     job_name: str,
                                     job_requested_params: List[str],
                                     repository: str,
                                     sha: str,
                                     pr_branch: str,
                                     tag: str=None,
                                     relevant_changes: Set[str]=set()):
        job_params = await self.get_requested_parameters_values(job_requested_params, pr_branch, sha, tag, relevant_changes)
        next_build_number = self.get_jobs_next_build_number(job_name)
        try:
            self.build_jenkins_job(job_name, job_params)
            logging.warning(f"Scheduled build of: {job_name} #{next_build_number}")
        except jenkins.JenkinsException as jenkins_exception:
            logging.exception(f"Job {job_name} did not accept {job_params} as parameters but it requested them (Error: {jenkins_exception})")

            await self.create_github_build_status(repository, sha, "error",
                                                  await self.get_job_url(job_name),
                                                  f"Job {job_name} did not accept requested parameters {job_params.keys()}!",
                                                  job_name)
            return

        build_info = await self.get_build_info(job_name, next_build_number)
        if build_info is not None:
            logging.warning(f"Creating pending status for {job_name} in repo {repository} (branch {pr_branch}, sha {sha}")

            await self.create_github_build_status(repository, sha, "pending", build_info['url'], "build in progress", job_name)

            while await self.is_job_building(job_name, next_build_number):
                await asyncio.sleep(1)

            build_info = await self.get_build_info(job_name, next_build_number)
            logging.warning(f"Build {job_name} #{next_build_number} finished.")

            final_state = await self.get_final_build_state(build_info)
            final_description = await self.get_final_build_description(build_info)
            logging.warning(f"Creating build status for {job_name} #{next_build_number} - verdict: {final_state}.")

            await self.create_github_build_status(repository, sha, final_state, build_info['url'], final_description, job_name)
        else:
            logging.exception(f"Triggear was not able to find build number {next_build_number} for job {job_name}. Task aborted.")

            await self.create_github_build_status(repository, sha, "error",
                                                  await self.get_job_url(job_name),
                                                  f"Triggear cant find build {job_name} #{next_build_number}",
                                                  job_name)

    async def get_job_url(self, job_name):
        return self.__jenkins_client.get_job_info(job_name).get('url')

    async def create_github_build_status(self, repository, sha, state, url, description, context):
        self.__gh_client.get_repo(repository).get_commit(sha).create_status(state=state,
                                                                            target_url=url,
                                                                            description=description,
                                                                            context=context)

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

    @staticmethod
    async def __get_parsed_param_key(prefix, param):
        return prefix if param == prefix else param.split(':', 1)[1]
