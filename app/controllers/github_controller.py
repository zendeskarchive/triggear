import asyncio
import hmac
import logging
import time
from typing import Dict

import aiohttp.web
import aiohttp.web_request
import github
import jenkins
import motor.motor_asyncio

from app.config.triggear_config import TriggearConfig
from app.dto.hook_details import HookDetails
from app.dto.hook_details_factory import HookDetailsFactory
from app.enums.event_types import EventTypes
from app.enums.labels import Labels
from app.utilities.background_task import BackgroundTask
from app.utilities.constants import LAST_RUN_IN, BRANCH_DELETED_SHA, TRIGGEAR_RUN_PREFIX
from app.utilities.err_handling import handle_exceptions
from app.utilities.functions import any_starts_with


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
            return 501, "Non SHA-1 auth non-implemented"

        req_body = await req.read()
        mac = hmac.new(bytearray(self.api_token, 'utf-8'), msg=req_body, digestmod='sha1')
        if not hmac.compare_digest(str(mac.hexdigest()), str(signature)):
            return 401, 'Unauthorized'
        return 'AUTHORIZED'

    @staticmethod
    async def get_request_json(request):
        return await request.json()

    @handle_exceptions()
    async def handle_hook(self, request: aiohttp.web_request.Request):
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
    async def get_request_event_header(request):
        return request.headers['X-GitHub-Event']

    async def handle_pr_opened(self, data: dict):
        hook_details: HookDetails = HookDetailsFactory.get_pr_opened_details(data)
        await self.set_sync_label(hook_details.repository, pr_number=data['pull_request']['number'])
        await self.trigger_registered_jobs(hook_details)

    async def set_sync_label(self, repository, pr_number):
        if Labels.pr_sync in self.get_repo_labels(repository):
            logging.warning(f'Setting "triggear-pr-sync" label on PR {pr_number} in repo {repository}')
            self.set_pr_sync_label(repository, pr_number)
            logging.warning('Label set')

    def set_pr_sync_label(self, repo, pr_number):
        self.__gh_client.get_repo(repo).get_issue(pr_number).set_labels(Labels.pr_sync)

    def get_repo_labels(self, repo: str):
        return [label.name for label in self.__gh_client.get_repo(repo).get_labels()]

    async def handle_tagged(self, data: dict):
        await self.trigger_registered_jobs(HookDetailsFactory.get_tag_details(data))

    async def handle_labeled(self, data: dict):
        await self.trigger_registered_jobs(HookDetailsFactory.get_labeled_details(data))

    async def handle_synchronize(self, data: Dict):
        pr_labels = self.get_pr_labels(repository=data['pull_request']['head']['repo']['full_name'],
                                       pr_number=data['pull_request']['number'])
        await self.handle_pr_sync(data, pr_labels)
        await self.handle_labeled_sync(data, pr_labels)

    async def handle_pr_sync(self, data, pr_labels):
        # noinspection PyBroadException
        try:
            if Labels.pr_sync in pr_labels:
                logging.warning(f'Sync hook on PR with {Labels.pr_sync} - handling like PR open')
                await self.handle_pr_opened(data)
        except Exception as pr_sync_exception:
            logging.exception(f'Unexpected exception while handling PR sync: {pr_sync_exception}')

    async def handle_labeled_sync(self, data, pr_labels):
        # noinspection PyBroadException
        try:
            if Labels.label_sync in pr_labels and len(pr_labels) > 1:
                pr_labels.remove(Labels.label_sync)
                for label in pr_labels:
                    # update data to have fields required from labeled hook - necessary for HookDetailsFactory in handle_labeled
                    data.update({'label': {'name': label}})
                    logging.warning(f'Sync hook on PR with {Labels.label_sync} - handling like PR open')
                    await self.handle_labeled(data)
        except Exception as label_sync_exception:
            logging.exception(f'Unexpected exception while handling PR sync: {label_sync_exception}')

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
        head_branch, head_sha = await self.__get_comment_branch_and_sha(data)
        await self.trigger_registered_jobs(HookDetailsFactory.get_pr_sync_details(data, head_branch, head_sha))

    async def __get_comment_branch_and_sha(self, data):
        repository_name = data['repository']['full_name']
        pr_number = data['issue']['number']
        head_branch = self.get_pr_branch(pr_number, repository_name)
        head_sha = self.get_latest_commit_sha(pr_number, repository_name)
        return head_branch, head_sha

    async def handle_labeled_sync_comment(self, data):
        head_branch, head_sha = await self.__get_comment_branch_and_sha(data)
        for hook_details in HookDetailsFactory.get_labeled_sync_details(data, head_branch=head_branch, head_sha=head_sha):
            self.trigger_registered_jobs(hook_details)

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

    def get_latest_commit_sha(self, pr_number, repository_name):
        return self.__gh_client.get_repo(repository_name).get_pull(pr_number).head.sha

    def get_pr_branch(self, pr_number, repository_name):
        return self.__gh_client.get_repo(repository_name).get_pull(pr_number).head.ref

    async def handle_push(self, data):
        hook_details: HookDetails = HookDetailsFactory.get_push_details(data)
        if hook_details.sha != BRANCH_DELETED_SHA:
            await self.trigger_registered_jobs(hook_details)
        else:
            logging.warning(f"Branch {hook_details.branch} was deleted as SHA was zeros only!")

    async def trigger_registered_jobs(self, hook_details: HookDetails):
        collection = await self.__get_collection_for_hook_type(hook_details.event_type)
        async for document in collection.find(hook_details.query):
            job_name = document['job']

            branch_restrictions = document.get('branch_restrictions')
            branch_restrictions = branch_restrictions if branch_restrictions is not None else []

            change_restrictions = document.get('change_restrictions')
            change_restrictions = change_restrictions if change_restrictions is not None else []

            if not change_restrictions or any_starts_with(any_list=hook_details.changes,
                                                          starts_with_list=change_restrictions):
                if branch_restrictions == [] or hook_details.branch in branch_restrictions:
                    job_requested_params = document['requested_params']
                    try:
                        self.get_jobs_next_build_number(job_name)  # Raises if job does not exist on Jenkins
                        if await self.can_trigger_job_by_branch(job_name, hook_details.branch):
                            await BackgroundTask().run(self.trigger_registered_job,
                                                       (
                                                           job_name,
                                                           job_requested_params,
                                                           document['repository'],
                                                           hook_details.sha,
                                                           hook_details.branch,
                                                           hook_details.tag
                                                       ),
                                                       callback=None)
                    except jenkins.NotFoundException as not_found_exception:
                        delete_query = hook_details.query
                        delete_query['job'] = job_name
                        logging.exception(f"Job {job_name} was not found on Jenkins anymore - deleting by query: "
                                          f"{hook_details.query}\n (Exception: {not_found_exception}")
                        await collection.delete_one(delete_query)
                else:
                    logging.warning(f"Job {job_name} was registered with following branch restrictions: "
                                    f"{branch_restrictions}. Current push was on {hook_details.branch} branch, "
                                    f"so Triggear will not build this job.")
            else:
                logging.warning(f"Job {job_name} was registered with following change restrictions: "
                                f"{change_restrictions}. Current push had changes in {hook_details.changes}, "
                                f"so Triggear will not build this job.")

    async def __get_collection_for_hook_type(self, event_type: EventTypes):
        return self.__mongo_client.registered[event_type]

    def get_jobs_next_build_number(self, job_name):
        return self.__jenkins_client.get_job_info(job_name)['nextBuildNumber']

    async def trigger_unregistered_job(self, job_name, pr_branch, job_params, repository, pr_number):
        if await self.can_trigger_job_by_branch(job_name, pr_branch):
            next_build_number = self.get_jobs_next_build_number(job_name)

            try:
                self.build_jenkins_job(job_name, job_params)
            except jenkins.JenkinsException as jexp:
                logging.exception(f"Job {job_name} did not accept {job_params} "
                                  f"as parameters but it was passed to it (Error: {jexp})")
                return

            while await self.is_job_building(job_name, next_build_number):
                await asyncio.sleep(1)
            build_info = await self.get_build_info(job_name, next_build_number)

            if build_info is not None:
                final_state = "success" if build_info['result'] == "SUCCESS" \
                    else "failure" if build_info['result'] == "FAILURE" \
                    else "error"
                final_description = "build succeeded" if build_info['result'] == "SUCCESS" \
                    else "build failed" if build_info['result'] == "FAILURE" \
                    else "build error"
                self.create_pr_comment(
                    pr_number,
                    repository,
                    body=f"Job {job_name} finished with status {final_state} - "
                         f"{final_description} ({build_info['url']})"
                )
            else:
                logging.exception(f"Triggear was not able to find build number {next_build_number} for job {job_name}."
                                  f"Task aborted.")
                return

    def create_pr_comment(self, pr_number, repository, body):
        self.__gh_client.get_repo(repository).get_issue(pr_number).create_comment(
            body=body
        )

    async def get_build_info(self, job_name, build_number):
        timeout = time.monotonic() + 30
        while time.monotonic() < timeout:
            try:
                return self.__jenkins_client.get_build_info(job_name, build_number)
            except jenkins.NotFoundException:
                logging.warning(f"Build number {build_number} was not yet found for job {job_name}."
                                f"Probably because of high load on Jenkins build is stuck in pre-run state and it is"
                                f"not available in history. We will retry for 30 sec for it to appear.")
                await asyncio.sleep(1)
        return None

    async def is_job_building(self, job_name, build_number):
        build_info = await self.get_build_info(job_name, build_number)
        if build_info is not None:
            return build_info['building']
        return None

    def build_jenkins_job(self, job_name, job_params):
        self.__jenkins_client.build_job(job_name, parameters=job_params)

    async def can_trigger_job_by_branch(self, job_name, branch):
        last_job_run_in_branch = {
            "branch": branch,
            "job": job_name
        }
        collection = self.__mongo_client.registered[LAST_RUN_IN]
        found_run = await collection.find_one(last_job_run_in_branch)
        last_job_run_in_branch['timestamp'] = int(time.time())
        if not found_run:
            result = await collection.insert_one(last_job_run_in_branch)
            logging.info(f"Inserted last run time document with ID {repr(result.inserted_id)}")
            logging.warning(f"Job {job_name} was never run in branch {branch}")
        else:
            if int(time.time()) - found_run['timestamp'] < self._rerun_time_limit:
                logging.warning(f"Job {job_name} was run in branch {branch} "
                                f"less then {self._rerun_time_limit} - won't be triggered")
                return False
            else:
                result = await collection.replace_one(found_run, last_job_run_in_branch)
                logging.warning(f"Job {job_name} was run in branch {branch} "
                                f"more then {self._rerun_time_limit} - time was updated and will be triggered")
                logging.info(f"Updated {repr(result.matched_count)} last run documents")
        return True

    async def trigger_registered_job(self, job_name, job_requested_params, repository, sha, pr_branch, tag=None):
        job_params = None
        if job_requested_params:
            job_params = {}
            if 'branch' in job_requested_params:
                job_params['branch'] = pr_branch
            if 'sha' in job_requested_params:
                job_params['sha'] = sha
            if 'tag' in job_requested_params:
                job_params['tag'] = tag
        next_build_number = self.get_jobs_next_build_number(job_name)
        try:
            self.build_jenkins_job(job_name, job_params)
            logging.warning(f"Scheduled build of: {job_name} #{next_build_number}")
        except jenkins.JenkinsException as jexp:
            logging.exception(f"Job {job_name} did not accept {job_params} "
                              f"as parameters but it requested them (Error: {jexp})")
            self.__gh_client.get_repo(repository).get_commit(sha).create_status(
                state="error",
                target_url=self.__jenkins_client.get_job_info(job_name).get('url'),
                description=f"Job {job_name} did not accept requested parameters {job_params.keys()}!",
                context=job_name)
            return

        build_info = await self.get_build_info(job_name, next_build_number)
        if build_info is not None:
            logging.warning(f"Creating pending status for {job_name} in repo {repository} "
                            f"(branch {pr_branch}, sha {sha}")
            self.__gh_client.get_repo(repository).get_commit(sha).create_status(
                state="pending",
                target_url=build_info['url'],
                description="build in progress",
                context=job_name)
            while await self.is_job_building(job_name, next_build_number):
                await asyncio.sleep(1)
            build_info = await self.get_build_info(job_name, next_build_number)
            logging.warning(f"Build {job_name} #{next_build_number} finished.")

            final_state = "success" if build_info['result'] == "SUCCESS" \
                else "failure" if build_info['result'] == "FAILURE" \
                else "error"
            final_description = "build succeeded" if build_info['result'] == "SUCCESS" \
                else "build failed" if build_info['result'] == "FAILURE" \
                else "build error"
            logging.warning(f"Creating build status for {job_name} #{next_build_number} - verdict: {final_state}.")
            self.__gh_client.get_repo(repository).get_commit(sha).create_status(
                state=final_state,
                target_url=build_info['url'],
                description=final_description,
                context=job_name)
        else:
            logging.exception(f"Triggear was not able to find build number {next_build_number} for job {job_name}."
                              f"Task aborted.")
            return
