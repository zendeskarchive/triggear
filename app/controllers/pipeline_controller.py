import logging
from typing import Dict, List

import aiohttp.web
import aiohttp.web_request

from app.clients.github_client import GithubClient
from app.clients.mongo_client import MongoClient
from app.enums.event_types import EventType
from app.mongo.clear_query import ClearQuery
from app.mongo.deregistration_query import DeregistrationQuery
from app.mongo.registration_query import RegistrationQuery
from app.request_schemes.clear_request_data import ClearRequestData
from app.request_schemes.comment_request_data import CommentRequestData
from app.request_schemes.deployment_request_data import DeploymentRequestData
from app.request_schemes.deployment_status_request_data import DeploymentStatusRequestData
from app.request_schemes.deregister_request_data import DeregisterRequestData
from app.request_schemes.register_request_data import RegisterRequestData
from app.request_schemes.status_request_data import StatusRequestData


class PipelineController:
    def __init__(self,
                 github_client: GithubClient,
                 mongo_client: MongoClient) -> None:
        self.__gh_client: GithubClient = github_client
        self.__mongo_client: MongoClient = mongo_client

    def get_github(self) -> GithubClient:
        return self.__gh_client

    async def handle_register(self, request: aiohttp.web_request.Request) -> aiohttp.web.Response:
        data: Dict = await request.json()
        logging.warning(f"Register REQ received: {data}")
        if not RegisterRequestData.is_valid_register_request_data(data):
            return aiohttp.web.Response(reason='Invalid register request params!', status=400)
        await self.__mongo_client.add_or_update_registration(RegistrationQuery.from_registration_request_data(data))
        return aiohttp.web.Response(text='Register ACK')

    async def handle_missing(self, request: aiohttp.web_request.Request) -> aiohttp.web.Response:
        event_type = request.match_info.get('eventType')
        logging.warning(f"Missing REQ received for: {event_type}")
        if event_type not in EventType.get_allowed_registration_event_types():
            return aiohttp.web.Response(status=400, text='Invalid eventType requested')
        return aiohttp.web.Response(text=','.join(await self.__mongo_client.get_missed_info(event_type)))

    async def handle_deregister(self, request: aiohttp.web_request.Request) -> aiohttp.web.Response:
        data: Dict = await request.json()
        logging.warning(f"Deregister REQ received: {data}")
        if not DeregisterRequestData.is_valid_deregister_request_data(data):
            return aiohttp.web.Response(reason='Invalid deregister request params!', status=400)
        await self.__mongo_client.deregister(DeregistrationQuery.from_deregistration_request_data(data))
        return aiohttp.web.Response(text=f'Deregistration of {data[DeregisterRequestData.job_name]} '
                                         f'for {data[DeregisterRequestData.event_type]} succeeded')

    async def handle_clear(self, request: aiohttp.web_request.Request) -> aiohttp.web.Response:
        data: Dict = await request.json()
        logging.warning(f"Clear REQ received: {data}")
        if not ClearRequestData.is_valid_clear_request_data(data):
            return aiohttp.web.Response(reason='Invalid clear request params!', status=400)
        clear_query = ClearQuery.from_clear_request_data(data)
        await self.__mongo_client.clear(clear_query)
        return aiohttp.web.Response(text=f'Clear of {clear_query.job_name} missed counter succeeded')

    async def handle_status(self, request: aiohttp.web_request.Request) -> aiohttp.web.Response:
        data = await request.json()
        if not StatusRequestData.is_valid_status_data(data):
            return aiohttp.web.Response(reason='Invalid status request params!', status=400)
        logging.warning(f"Status REQ received: {data}")
        await self.get_github().create_github_build_status(
            repo=data['repository'],
            sha=data['sha'],
            state=data['state'],
            description=data['description'],
            url=data['url'],
            context=data['context']
        )
        return aiohttp.web.Response(text='Status ACK')

    async def handle_comment(self, request: aiohttp.web_request.Request) -> aiohttp.web.Response:
        data = await request.json()
        if not CommentRequestData.is_valid_comment_data(data):
            return aiohttp.web.Response(reason='Invalid comment request params!', status=400)
        logging.warning(f"Comment REQ received: {data}")
        await self.get_github().create_comment(
            repo=data['repository'],
            sha=data['sha'],
            body=data['jobName'] + "\nComments: " + data['body'],
        )
        return aiohttp.web.Response(text='Comment ACK')

    async def handle_deployment(self, request: aiohttp.web_request.Request) -> aiohttp.web.Response:
        data: Dict = await request.json()
        logging.warning(f'Deployment request received: {data}')
        if not DeploymentRequestData.is_valid_deployment_request_data(data):
            return aiohttp.web.Response(reason='Invalid deployment request payload!', status=400)
        await self.get_github().create_deployment(repo=data[DeploymentRequestData.repo],
                                                  ref=data[DeploymentRequestData.ref],
                                                  environment=data[DeploymentRequestData.environment],
                                                  description=data[DeploymentRequestData.description])
        return aiohttp.web.Response(text='Deployment ACK')

    async def handle_deployment_status(self, request: aiohttp.web_request.Request) -> aiohttp.web.Response:
        data: Dict = await request.json()
        logging.warning(f'Deployment status request received: {data}')
        if not DeploymentStatusRequestData.is_valid_deployment_status_request_data(data):
            return aiohttp.web.Response(reason='Invalid deployment status request payload!', status=400)
        deployments: List = await self.get_github().get_deployments(repo=data[DeploymentRequestData.repo],
                                                                    ref=data[DeploymentRequestData.ref],
                                                                    environment=data[DeploymentRequestData.environment])

        deployment_matcher = {
            'environment': data[DeploymentRequestData.environment],
            'ref': data[DeploymentRequestData.ref],
            'description': data[DeploymentRequestData.description]
        }
        for deployment in deployments:
            match = {k: deployment[k] for k in deployment_matcher.keys()}
            if match == deployment_matcher:
                await self.get_github().create_deployment_status(repo=data[DeploymentRequestData.repo],
                                                                 deployment_id=deployment['id'],
                                                                 state=data[DeploymentStatusRequestData.state],
                                                                 target_url=data[DeploymentStatusRequestData.target_url],
                                                                 description=data[DeploymentStatusRequestData.description])
                return aiohttp.web.Response(text='Deployment status ACK')
        logging.error(f'Deployment matching {deployment_matcher} not found')
        return aiohttp.web.Response(reason=f'Deployment matching {deployment_matcher} not found', status=404)
