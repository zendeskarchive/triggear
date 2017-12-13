import logging
from typing import List, Optional, Dict

import aiohttp.web
import aiohttp.web_request
import github
import motor.motor_asyncio

from app.enums.registration_fields import RegistrationFields
from app.request_schemes.comment_request_data import CommentRequestData
from app.request_schemes.register_request_data import RegisterRequestData
from app.request_schemes.status_request_data import StatusRequestData
from app.utilities.auth_validation import validate_auth_header
from app.utilities.err_handling import handle_exceptions


class PipelineController:
    def __init__(self,
                 github_client: github.Github,
                 mongo_client: motor.motor_asyncio.AsyncIOMotorClient,
                 api_token: str):
        self.__gh_client = github_client
        self.__mongo_client = mongo_client
        self.api_token = api_token

    async def add_registration_if_not_exists(self,
                                             event_type: str,
                                             repository: str,
                                             job_name: str,
                                             labels: List[str],
                                             requested_params: List[str],
                                             branch_restrictions: Optional[List[str]],
                                             change_restrictions: Optional[List[str]],
                                             file_restrictions: Optional[List[str]]):
        collection = self.__mongo_client.registered[event_type]
        job_registration = {
            RegistrationFields.repository: repository,
            RegistrationFields.job: job_name
        }
        found_doc = await collection.find_one(job_registration)
        job_registration[RegistrationFields.labels] = labels
        job_registration[RegistrationFields.requested_params] = requested_params
        job_registration[RegistrationFields.branch_restrictions] = branch_restrictions if branch_restrictions is not None else []
        job_registration[RegistrationFields.change_restrictions] = change_restrictions if change_restrictions is not None else []
        job_registration[RegistrationFields.file_restrictions] = file_restrictions if file_restrictions is not None else []
        if not found_doc:
            result = await collection.insert_one(job_registration)
            logging.info(f"Inserted document with ID {repr(result.inserted_id)}")
        else:
            result = await collection.replace_one(found_doc, job_registration)
            logging.info(f"Updated {repr(result.matched_count)} documents")

    @handle_exceptions()
    @validate_auth_header()
    async def handle_register(self, request: aiohttp.web_request.Request) -> aiohttp.web.Response:
        data: Dict = await request.json()
        logging.warning(f"Register REQ received: {data}")
        if not RegisterRequestData.is_valid_register_request_data(data):
            return aiohttp.web.Response(reason='Invalid register request params!', status=400)
        await self.add_registration_if_not_exists(
            event_type=data['eventType'],
            repository=data['repository'],
            job_name=data['jobName'],
            labels=data['labels'],
            requested_params=data['requested_params'],
            branch_restrictions=data.get('branch_restrictions'),
            change_restrictions=data.get('change_restrictions'),
            file_restrictions=data.get('file_restrictions')
        )
        return aiohttp.web.Response(text='Register ACK')

    @handle_exceptions()
    @validate_auth_header()
    async def handle_status(self, request: aiohttp.web_request.Request) -> aiohttp.web.Response:
        data = await request.json()
        if not StatusRequestData.is_valid_status_data(data):
            return aiohttp.web.Response(reason='Invalid status request params!', status=400)
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

    async def __create_or_update_status(self, repository, sha, state, description, url, context):
        self.__gh_client.get_repo(repository).get_commit(sha).create_status(
            state=state,
            description=description,
            target_url=url,
            context=context
        )

    @handle_exceptions()
    @validate_auth_header()
    async def handle_comment(self, request: aiohttp.web_request.Request):
        data = await request.json()
        if not CommentRequestData.is_valid_comment_data(data):
            return aiohttp.web.Response(reason='Invalid comment request params!', status=400)
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
