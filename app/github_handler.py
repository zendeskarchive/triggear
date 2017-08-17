import hmac
import logging
import time

import asyncio
import jenkins
import github
import motor.motor_asyncio

import aiohttp.web
import aiohttp.web_request

from app.background_task import BackgroundTask
from app.err_handling import handle_exceptions
from app.event_types import EventTypes


class GithubHandler:
    def __init__(self,
                 github_client: github.Github,
                 mongo_client: motor.motor_asyncio.AsyncIOMotorClient,
                 jenkins_client: jenkins.Jenkins,
                 rerun_time_limit,
                 api_token):
        self.__gh_client = github_client
        self.__mongo_client = mongo_client
        self.__jenkins_client = jenkins_client
        self._rerun_time_limit = rerun_time_limit
        self.__last_run_in = 'last_run_in'
        self.api_token = api_token

    @staticmethod
    async def get_request_json(request):
        return await request.json()

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
        elif await self.get_request_event_header(request) == EventTypes.push:
            if data['ref'].startswith('refs/heads/'):
                await self.handle_push(data)
            elif data['ref'].startswith('refs/tags/'):
                await self.handle_tagged(data)
        return aiohttp.web.Response(text='Hook ACK')

    @staticmethod
    async def get_request_event_header(request):
        return request.headers['X-GitHub-Event']

    async def handle_tagged(self, data: dict):
        collection = self.__mongo_client.registered[EventTypes.tagged]
        tag = data['ref'][10:]
        repo = data['repository']['full_name']
        branch = data['base_ref'][11:]
        sha = data['after']
        registration_query = {
            "repository": repo,
        }
        logging.warning(f"Hook details: labeled for query {registration_query}")
        await self.trigger_registered_jobs(
            collection=collection,
            query=registration_query,
            sha=sha,
            branch=branch,
            tag=tag
        )

    async def handle_labeled(self, data: dict):
        collection = self.__mongo_client.registered[EventTypes.labeled]
        commit_sha = data['pull_request']['head']['sha']
        pr_branch = data['pull_request']['head']['ref']
        registration_query = {
            "repository": data['pull_request']['head']['repo']['full_name'],
            "labels": data['label']['name']
        }
        logging.warning(f"Hook details: labeled for query {registration_query}")
        await self.trigger_registered_jobs(
            collection=collection,
            query=registration_query,
            sha=commit_sha,
            branch=pr_branch
        )

    async def handle_synchronize(self, data):
        collection = self.__mongo_client.registered[EventTypes.labeled]
        repository = data['pull_request']['head']['repo']['full_name']
        pr_number = data['pull_request']['number']
        commit_sha = data['pull_request']['head']['sha']
        pr_branch = data['pull_request']['head']['ref']
        pr_labels = self.get_pr_labels(pr_number, repository)
        logging.warning(f"Hook details: synchronize for repository {repository} and branch {pr_branch}")
        if 'triggear-sync' in pr_labels and len(pr_labels) > 1:
            pr_labels.remove('triggear-sync')
            for label in pr_labels:
                registration_query = {
                    "repository": repository,
                    "labels": label
                }
                await self.trigger_registered_jobs(
                    collection=collection,
                    query=registration_query,
                    sha=commit_sha,
                    branch=pr_branch
                )

    def get_pr_labels(self, pr_number, repository):
        return [label.name for label in self.__gh_client.get_repo(repository).get_issue(pr_number).labels]

    async def handle_comment(self, data):
        if data['comment']['body'].startswith('Triggear run '):
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
        elif data['comment']['body'].startswith('Triggear resync '):
            commit_sha = data['comment']['body'].split()[2]
            collection = self.__mongo_client.registered[EventTypes.labeled]
            repository_name = data['repository']['full_name']
            pr_number = data['issue']['number']
            pr_labels = [label['name'] for label in data['issue']['labels']]
            pr_branch = self.get_pr_branch(pr_number, repository_name)
            for label in pr_labels:
                registration_query = {
                    "repository": repository_name,
                    "labels": label
                }
                logging.warning(f"Hook details: resync comment for repository {repository_name} and branch {pr_branch}")
                await self.trigger_registered_jobs(
                    collection=collection,
                    query=registration_query,
                    sha=commit_sha,
                    branch=pr_branch
                )
        else:
            return

    def get_pr_branch(self, pr_number, repository_name):
        return self.__gh_client.get_repo(repository_name).get_pull(pr_number).head.ref

    async def handle_push(self, data):
        collection = self.__mongo_client.registered[EventTypes.push]
        commit_sha = data['after']
        branch = data['ref'][11:] if data['ref'].startswith('refs/heads/') else data['ref']
        registration_query = {
            "repository": data['repository']['full_name']
        }
        logging.warning(f"Hook details: push for query {registration_query} and branch {branch}")
        await self.trigger_registered_jobs(
            collection=collection,
            query=registration_query,
            sha=commit_sha,
            branch=branch
        )

    async def trigger_registered_jobs(self, collection, query, sha, branch, tag=None):
        async for document in collection.find(query):
            job_name = document['job']
            job_requested_params = document['requested_params']
            try:
                next_build_number = self.get_jobs_next_build_number(job_name)
                if await self.can_trigger_job_by_branch(job_name, branch):
                    await BackgroundTask().run(self.trigger_registered_job,
                                               (
                                                   job_name,
                                                   job_requested_params,
                                                   next_build_number,
                                                   document['repository'],
                                                   sha,
                                                   branch,
                                                   tag
                                               ),
                                               callback=None)
            except jenkins.NotFoundException as e:
                delete_query = query
                delete_query['job'] = job_name
                logging.error(f"Job {job_name} was not found on Jenkins anymore - deleting by query: {query}\n"
                              f"(Exception: {str(e)}")
                await collection.delete_one(delete_query)

    def get_jobs_next_build_number(self, job_name):
        return self.__jenkins_client.get_job_info(job_name)['nextBuildNumber']

    async def trigger_unregistered_job(self, job_name, pr_branch, job_params, repository, pr_number):
        if await self.can_trigger_job_by_branch(job_name, pr_branch):
            next_build_number = self.get_jobs_next_build_number(job_name)

            try:
                self.build_jenkins_job(job_name, job_params)
            except jenkins.JenkinsException as jexp:
                logging.error(f"Job {job_name} did not accept {job_params} "
                              f"as parameters but it was passed to it (Error: {jexp})")
                return

            while await self.is_job_building(job_name, next_build_number):
                await asyncio.sleep(1)
            job_info = await self.get_job_info(job_name, next_build_number)

            final_state = "success" if job_info['result'] == "SUCCESS" \
                else "failure" if job_info['result'] == "FAILURE" \
                else "error"
            final_description = "build succeeded" if job_info['result'] == "SUCCESS" \
                else "build failed" if job_info['result'] == "FAILURE" \
                else "build error"
            self.create_pr_comment(
                pr_number,
                repository,
                body=f"Job {job_name} finished with status {final_state} - {final_description} ({job_info['url']})"
            )

    def create_pr_comment(self, pr_number, repository, body):
        self.__gh_client.get_repo(repository).get_issue(pr_number).create_comment(
            body=body
        )

    async def get_job_info(self, job_name, build_number):
        return self.__jenkins_client.get_build_info(job_name, build_number)

    async def is_job_building(self, job_name, build_number):
        return self.__jenkins_client.get_build_info(job_name, build_number)['building']

    def build_jenkins_job(self, job_name, job_params):
        self.__jenkins_client.build_job(job_name, parameters=job_params)

    async def can_trigger_job_by_branch(self, job_name, branch):
        last_job_run_in_branch = {
            "branch": branch,
            "job": job_name
        }
        collection = self.__mongo_client.registered[self.__last_run_in]
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

    async def trigger_registered_job(self,
                                     job_name,
                                     job_requested_params,
                                     next_build_number,
                                     repository,
                                     sha,
                                     pr_branch,
                                     tag=None):
        logging.warning(f"Scheduling build of: {job_name} #{next_build_number}")

        job_params = None
        if job_requested_params:
            job_params = {}
            if 'branch' in job_requested_params:
                job_params['branch'] = pr_branch
            if 'sha' in job_requested_params:
                job_params['sha'] = sha
            if 'tag' in job_requested_params:
                job_params['tag'] = tag

        try:
            self.build_jenkins_job(job_name, job_params)
        except jenkins.JenkinsException as jexp:
            logging.error(f"Job {job_name} did not accept {job_params} "
                          f"as parameters but it requested them (Error: {jexp})")
            self.__gh_client.get_repo(repository).get_commit(sha).create_status(
                state="error",
                target_url=self.__jenkins_client.get_job_info(job_name).get('url'),
                description=f"job did not accept requested parameters {job_params.keys()}!",
                context=job_name)
            return

        job_info = await self.get_job_info(job_name, next_build_number)
        self.__gh_client.get_repo(repository).get_commit(sha).create_status(
            state="pending",
            target_url=job_info['url'],
            description="build in progress",
            context=job_name)
        while await self.is_job_building(job_name, next_build_number):
            await asyncio.sleep(1)
        job_info = await self.get_job_info(job_name, next_build_number)

        final_state = "success" if job_info['result'] == "SUCCESS" \
            else "failure" if job_info['result'] == "FAILURE" \
            else "error"
        final_description = "build succeeded" if job_info['result'] == "SUCCESS" \
            else "build failed" if job_info['result'] == "FAILURE" \
            else "build error"
        self.__gh_client.get_repo(repository).get_commit(sha).create_status(
            state=final_state,
            target_url=job_info['url'],
            description=final_description,
            context=job_name)
