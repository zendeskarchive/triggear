import logging

import aiohttp.web
import aiohttp.web_request

from app.auth_validation import validate_auth_header
from app.err_handling import handle_exceptions
from app.requested_params import RequestedParams


class PipelineHandler:
    def __init__(self, github_client, mongo_client, api_token):
        self.__gh_client = github_client
        self.__mongo_client = mongo_client
        self.api_token = api_token

    async def add_registration_if_not_exists(self,
                                             event_type,
                                             repository,
                                             job_name,
                                             labels,
                                             requested_params,
                                             branch_restrictions):
        collection = self.__mongo_client.registered[event_type]
        job_registration = {
            "repository": repository,
            "job": job_name
        }
        found_doc = await collection.find_one(job_registration)
        job_registration['labels'] = labels
        job_registration['requested_params'] = requested_params
        job_registration['branch_restrictions'] = branch_restrictions if branch_restrictions is not None else []
        if not found_doc:
            result = await collection.insert_one(job_registration)
            logging.info(f"Inserted document with ID {repr(result.inserted_id)}")
        else:
            result = await collection.replace_one(found_doc, job_registration)
            logging.info(f"Updated {repr(result.matched_count)} documents")

    @handle_exceptions()
    @validate_auth_header()
    async def handle_register(self, request: aiohttp.web_request.Request):
        data = await request.json()
        logging.warning(f"Register REQ received: {data}")
        if not self.are_params_valid(data):
            return aiohttp.web.Response(reason='Invalid requested params!', status=400)
        await self.add_registration_if_not_exists(
            event_type=data['eventType'],
            repository=data['repository'],
            job_name=data['jobName'],
            labels=data['labels'],
            requested_params=data['requested_params'],
            branch_restrictions=data.get('branch_restrictions')
        )
        return aiohttp.web.Response(text='Register ACK')

    @staticmethod
    def are_params_valid(data: dict):
        allowed_params = RequestedParams.get_allowed()
        for param in data['requested_params']:
            if param not in allowed_params:
                return False
        return True

    async def __create_or_update_status(self, repository, sha, state, description, url, context):
        self.__gh_client.get_repo(repository).get_commit(sha).create_status(
            state=state,
            description=description,
            target_url=url,
            context=context
        )

    @handle_exceptions()
    @validate_auth_header()
    async def handle_status(self, request: aiohttp.web_request.Request):
        data = await request.json()
        logging.warning(f"Status REQ received: {data}")
        await self.__create_or_update_status(
            repository=data['repository'],
            sha=data['sha'],
            state=data['state'],
            description=data['description'],
            url=data['url'],
            context=data['context']
        )
        return aiohttp.web.Response(text='Status ACK')

    @handle_exceptions()
    @validate_auth_header()
    async def handle_comment(self, request: aiohttp.web_request.Request):
        data = await request.json()
        logging.warning(f"Comment REQ received: {data}")
        await self.__create_comment(
            repository=data['repository'],
            sha=data['sha'],
            body=data['body'],
            job_name=data['jobName']
        )
        return aiohttp.web.Response(text='Comment ACK')

    async def __create_comment(self, repository, sha, body, job_name):
        body = job_name + "\nComments: " + body
        self.__gh_client.get_repo(repository).get_commit(sha).create_comment(body=body)
