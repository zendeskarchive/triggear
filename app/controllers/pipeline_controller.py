import logging
from datetime import datetime
from typing import List, Optional, Dict

import aiohttp.web
import aiohttp.web_request
import motor.motor_asyncio

from app.clients.github_client import GithubClient
from app.enums.event_types import EventTypes
from app.enums.registration_fields import RegistrationFields
from app.request_schemes.clear_request_data import ClearRequestData
from app.request_schemes.comment_request_data import CommentRequestData
from app.request_schemes.deregister_request_data import DeregisterRequestData
from app.request_schemes.register_request_data import RegisterRequestData
from app.request_schemes.status_request_data import StatusRequestData
from app.utilities.auth_validation import validate_auth_header
from app.utilities.err_handling import handle_exceptions


class PipelineController:
    def __init__(self,
                 github_client: GithubClient,
                 mongo_client: motor.motor_asyncio.AsyncIOMotorClient,
                 api_token: str):
        self.__gh_client = github_client
        self.__mongo_client = mongo_client
        self.api_token = api_token

    async def add_or_update_registration(self,
                                         jenkins_url: str,
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
            RegistrationFields.jenkins_url: jenkins_url,
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
        await self.add_or_update_registration(
            jenkins_url=data['jenkins_url'],
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
        await self.__gh_client.create_github_build_status(
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
        if not CommentRequestData.is_valid_comment_data(data):
            return aiohttp.web.Response(reason='Invalid comment request params!', status=400)
        logging.warning(f"Comment REQ received: {data}")
        await self.__gh_client.create_comment(
            repo=data['repository'],
            sha=data['sha'],
            body=data['jobName'] + "\nComments: " + data['body'],
        )
        return aiohttp.web.Response(text='Comment ACK')

    @handle_exceptions()
    @validate_auth_header()
    async def handle_missing(self, request: aiohttp.web_request.Request) -> aiohttp.web.Response:
        event_type = request.match_info.get('eventType')
        if event_type not in EventTypes.get_allowed_registration_event_types():
            return aiohttp.web.Response(status=400, text='Invalid eventType requested')
        logging.warning(f"Missing REQ received for: {event_type}")
        collection: motor.motor_asyncio.AsyncIOMotorCollection = self.__mongo_client.registered[event_type]
        cursor: motor.motor_asyncio.AsyncIOMotorCommandCursor = collection.find({RegistrationFields.missed_times: {'$gt': 0}})

        missed_registered_jobs = []
        async for document in cursor:
            missed_registered_jobs.append(f'{document[RegistrationFields.jenkins_url]}:{document[RegistrationFields.job]}'
                                          f'#{document[RegistrationFields.missed_times]}')

        return aiohttp.web.Response(text=','.join(missed_registered_jobs))

    @handle_exceptions()
    @validate_auth_header()
    async def handle_deregister(self, request: aiohttp.web_request.Request) -> aiohttp.web.Response:
        data: Dict = await request.json()
        logging.warning(f"Deregister REQ received: {data}")
        if not DeregisterRequestData.is_valid_deregister_request_data(data):
            return aiohttp.web.Response(reason='Invalid deregister request params!', status=400)
        collection = self.__mongo_client.registered[data[RegisterRequestData.event_type]]
        collection.delete_one({RegistrationFields.job: data[DeregisterRequestData.job_name],
                               RegistrationFields.jenkins_url: data[DeregisterRequestData.jenkins_url]})

        self.__mongo_client.deregistered['log'].insert_one({'job': data[DeregisterRequestData.job_name],
                                                            'caller': data[DeregisterRequestData.caller],
                                                            'eventType': data[DeregisterRequestData.event_type],
                                                            'jenkins_url': data[DeregisterRequestData.jenkins_url],
                                                            'timestamp': datetime.now()})
        return aiohttp.web.Response(text=f'Deregistration of {data[DeregisterRequestData.job_name]} '
                                         f'for {data[DeregisterRequestData.event_type]} succeeded')

    @handle_exceptions()
    @validate_auth_header()
    async def handle_clear(self, request: aiohttp.web_request.Request) -> aiohttp.web.Response:
        data: Dict = await request.json()
        logging.warning(f"Clear REQ received: {data}")
        if not ClearRequestData.is_valid_clear_request_data(data):
            return aiohttp.web.Response(reason='Invalid clear request params!', status=400)
        collection = self.__mongo_client.registered[data[RegisterRequestData.event_type]]
        collection.update_one({RegistrationFields.job: data[DeregisterRequestData.job_name],
                               RegistrationFields.jenkins_url: data[DeregisterRequestData.jenkins_url]},
                              {'$set': {RegistrationFields.missed_times: 0}})

        return aiohttp.web.Response(text=f'Clear of {data[DeregisterRequestData.job_name]} missed counter succeeded')
