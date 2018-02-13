from typing import List, Dict

import aiohttp.web
import aiohttp.web_request
import pytest
from aiohttp import ClientResponse
from mockito import mock, when, expect

from app.clients.async_client import AsyncClientNotFoundException
from app.clients.github_client import GithubClient
from app.clients.mongo_client import MongoClient
from app.controllers.pipeline_controller import PipelineController
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
from tests.async_mockito import async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestPipelineController:
    async def test__when_comment_request_data_is_invalid__should_return_400_response(self):
        pipeline_controller = PipelineController(mock(), mock())

        # given
        request = mock(spec=aiohttp.web_request.Request, strict=True)
        sample_data = {'sample': 'data'}
        when(request).json().thenReturn(async_value(sample_data))
        when(CommentRequestData).is_valid_comment_data(sample_data).thenReturn(False)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_comment(request)

        # then
        assert response.status == 400
        assert response.reason == 'Invalid comment request params!'

    async def test__when_comment_data_is_valid__should_send_it_to_proper_github_endpoint(self):
        proper_data = {'repository': 'repo', 'sha': '123abc', 'body': 'Comment body', 'jobName': 'job'}

        request = mock(spec=aiohttp.web_request.Request, strict=True)
        github_client = mock(spec=GithubClient)

        pipeline_controller = PipelineController(github_client, mock())

        # given
        when(request).json().thenReturn(async_value(proper_data))
        when(CommentRequestData).is_valid_comment_data(proper_data).thenReturn(True)
        expect(github_client).create_comment(repo='repo', sha='123abc', body="job\nComments: Comment body").thenReturn(async_value(None))

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_comment(request)

        # then
        assert response.status == 200
        assert response.text == 'Comment ACK'

    async def test__when_status_request_data_is_not_valid__should_return_400_response(self):
        pipeline_controller = PipelineController(mock(), mock())
        request = mock(spec=aiohttp.web_request.Request, strict=True)

        # given
        when(request).json().thenReturn(async_value({}))
        when(StatusRequestData).is_valid_status_data({}).thenReturn(False)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_status(request)

        # then
        assert response.status == 400
        assert response.reason == 'Invalid status request params!'

    async def test__when_status_data_is_ok__should_call_github_client_to_create_status(self):
        proper_data = {'repository': 'repo', 'sha': '123abc', 'state': 'State', 'description': 'Description', 'context': 'Context', 'url': 'pr_url'}

        request = mock(spec=aiohttp.web_request.Request, strict=True)
        github_client = mock(spec=GithubClient, strict=True)

        pipeline_controller = PipelineController(github_client, mock())

        # given
        when(request).json().thenReturn(async_value(proper_data))
        when(StatusRequestData).is_valid_status_data(proper_data).thenReturn(True)
        when(github_client).create_github_build_status(
            repo='repo',
            sha='123abc',
            state='State',
            description='Description',
            url='pr_url',
            context='Context'
        ).thenReturn(async_value(None))

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_status(request)

        # then
        assert response.status == 200
        assert response.text == 'Status ACK'

    async def test__when_github_entity_is_not_found__status_should_return_404_response_with_github_explanation(self):
        parameters = {'repository': 'repo', 'sha': 'null', 'state': 'State', 'description': 'Description', 'context': 'Context', 'url': 'pr_url'}
        request = mock(spec=aiohttp.web_request.Request, strict=True)
        github_exception_data = 'PR not found'

        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        pipeline_controller = PipelineController(github_client, mock())

        # given
        when(request).json().thenReturn(async_value(parameters))
        when(StatusRequestData).is_valid_status_data(parameters).thenReturn(True)
        when(github_client).create_github_build_status(
            repo='repo',
            sha='null',
            state='State',
            url='pr_url',
            description='Description',
            context='Context').thenRaise(AsyncClientNotFoundException(github_exception_data))

        # when
        with pytest.raises(AsyncClientNotFoundException):
            await pipeline_controller.handle_status(request)

    async def test__when_github_entity_is_not_found__comment_should_return_404_response_with_github_explanation(self):
        parameters = {'repository': 'repo', 'sha': 'null', 'body': 'Comment body', 'jobName': 'job'}
        request = mock(spec=aiohttp.web_request.Request, strict=True)
        github_exception_data = 'Commit not found'

        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        pipeline_controller = PipelineController(github_client, mock())

        # given
        when(request).json().thenReturn(async_value(parameters))
        when(CommentRequestData).is_valid_comment_data(parameters).thenReturn(True)
        when(github_client).create_comment(repo='repo', sha='null', body="job\nComments: Comment body")\
            .thenRaise(AsyncClientNotFoundException(github_exception_data))

        # when
        with pytest.raises(AsyncClientNotFoundException):
            await pipeline_controller.handle_comment(request)

    async def test__when_registration_data_is_not_valid__should_return_400_response(self):
        request = mock(spec=aiohttp.web_request.Request, strict=True)

        pipeline_controller = PipelineController(mock(), mock())

        # given
        when(request).json().thenReturn(async_value({}))
        when(RegisterRequestData).is_valid_register_request_data({}).thenReturn(False)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_register(request)

        # then
        assert response.status == 400
        assert response.reason == 'Invalid register request params!'

    async def test__when_data_is_valid__should_call_internal_add_registration__and_return_200_response(self):
        mock(RegistrationQuery)

        parameters = mock(strict=True)
        registration_query: RegistrationQuery = mock(spec=RegistrationQuery, strict=True)

        request = mock(spec=aiohttp.web_request.Request, strict=True)

        mongo_client: MongoClient = mock(spec=MongoClient, strict=True)
        pipeline_controller = PipelineController(mock(), mongo_client)

        # given
        when(request).json().thenReturn(async_value(parameters))
        when(RegisterRequestData).is_valid_register_request_data(parameters).thenReturn(True)
        when(RegistrationQuery).from_registration_request_data(parameters).thenReturn(registration_query)
        when(mongo_client).add_or_update_registration(registration_query).thenReturn(async_value(None))

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_register(request)

        # then
        assert response.status == 200
        assert response.reason == 'OK'

    async def test__when_event_type_is_missing__handle_missing_should_return_400(self):
        request = mock({'match_info': {}}, spec=aiohttp.web_request.Request, strict=True)

        pipeline_controller = PipelineController(mock(), mock())

        result: aiohttp.web.Response = await pipeline_controller.handle_missing(request)

        assert result.status == 400
        assert result.text == 'Invalid eventType requested'

    async def test__when_missing_endpoint_is_called__should_return_all_related_registrations_with_missing_times_more_then_0(self):
        request = mock({'match_info': {'eventType': 'push'}}, spec=aiohttp.web_request.Request, strict=True)

        mongo_client: MongoClient = mock(spec=MongoClient, strict=True)
        pipeline_controller = PipelineController(mock(), mongo_client)
        expect(mongo_client).get_missed_info('push').thenReturn(async_value(['url:push_job_1#7', 'url:push_job_2#13']))

        result: aiohttp.web.Response = await pipeline_controller.handle_missing(request)

        assert result.status == 200
        assert result.text == 'url:push_job_1#7,url:push_job_2#13'

    async def test__when_deregister_is_missing_parameters__should_return_400(self):
        request = mock(spec=aiohttp.web_request.Request, strict=True)

        pipeline_controller = PipelineController(mock(), mock())

        # given
        when(request).json().thenReturn(async_value({}))
        when(DeregisterRequestData).is_valid_deregister_request_data({}).thenReturn(False)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_deregister(request)

        # then
        assert response.status == 400
        assert response.reason == 'Invalid deregister request params!'

    async def test__when_deregister_request_is_valid__should_remove_registration_from_proper_collection__and_log_it_in_mongo(self):
        mock(DeregistrationQuery, strict=True)
        request = mock(spec=aiohttp.web_request.Request, strict=True)

        deregistration_query: DeregistrationQuery = mock(spec=DeregistrationQuery, strict=True)
        mongo_client: MongoClient = mock(spec=MongoClient, strict=True)
        pipeline_controller = PipelineController(mock(), mongo_client)

        # given
        data = {'eventType': 'push', 'jobName': 'job', 'caller': 'del_job#7', 'jenkins_url': 'url'}
        when(request).json().thenReturn(async_value(data))
        expect(DeregistrationQuery).from_deregistration_request_data(data).thenReturn(deregistration_query)
        expect(mongo_client).deregister(deregistration_query).thenReturn(async_value(None))

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_deregister(request)

        assert response.status == 200
        assert response.text == 'Deregistration of job for push succeeded'

    async def test__when_clear_is_missing_parameters__should_return_400(self):
        request = mock(spec=aiohttp.web_request.Request, strict=True)

        pipeline_controller = PipelineController(mock(), mock())

        # given
        when(request).json().thenReturn(async_value({}))
        when(ClearRequestData).is_valid_clear_request_data({}).thenReturn(False)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_clear(request)

        # then
        assert response.status == 400
        assert response.reason == 'Invalid clear request params!'

    async def test__when_clear_request_is_valid__should_set_missed_count_to_0(self):
        mock(ClearQuery, strict=True)
        mock(ClearRequestData, strict=True)

        request = mock(spec=aiohttp.web_request.Request, strict=True)
        clear_query = mock({'job_name': 'job'}, spec=ClearQuery, strict=True)
        mongo_client: MongoClient = mock(spec=MongoClient, strict=True)
        pipeline_controller = PipelineController(mock(), mongo_client)

        # given
        data = mock(strict=True)
        when(request).json().thenReturn(async_value(data))
        when(ClearRequestData).is_valid_clear_request_data(data).thenReturn(True)
        when(ClearQuery).from_clear_request_data(data).thenReturn(clear_query)
        expect(mongo_client).clear(clear_query).thenReturn(async_value(None))

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_clear(request)

        assert response.status == 200
        assert response.text == 'Clear of job missed counter succeeded'

    async def test__when_invalid_data_is_sent_to_deployment__400_response_should_be_returned(self):
        request = mock(spec=aiohttp.web_request.Request, strict=True)

        pipeline_controller = PipelineController(mock(), mock())

        # given
        when(request).json().thenReturn(async_value({}))
        when(DeploymentRequestData).is_valid_deployment_request_data({}).thenReturn(False)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_deployment(request)

        # then
        assert response.status == 400
        assert response.reason == 'Invalid deployment request payload!'

    async def test__when_deployment_data_is_valid__github_deployment_should_be_created(self):
        request = mock(spec=aiohttp.web_request.Request, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)

        pipeline_controller = PipelineController(mock(), mock())

        # given
        when(request).json().thenReturn(async_value({'repo': 'triggear',
                                                     'ref': '123321',
                                                     'environment': 'prod',
                                                     'description': 'something unique'}))
        when(pipeline_controller).get_github().thenReturn(github_client)

        # expect
        expect(github_client)\
            .create_deployment(repo='triggear', ref='123321', environment='prod', description='something unique')\
            .thenReturn(async_value(None))

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_deployment(request)

        # then
        assert response.status == 200
        assert response.text == 'Deployment ACK'

    async def test__when_invalid_data_is_sent_to_deployment_status__400_response_should_be_returned(self):
        request = mock(spec=aiohttp.web_request.Request, strict=True)

        pipeline_controller = PipelineController(mock(), mock())

        # given
        when(request).json().thenReturn(async_value({}))
        when(DeploymentStatusRequestData).is_valid_deployment_status_request_data({}).thenReturn(False)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_deployment_status(request)

        # then
        assert response.status == 400
        assert response.reason == 'Invalid deployment status request payload!'

    async def test__when_deployment_status_data_is_valid__and_matching_deployment_is_found__its_status_should_be_created(self):
        request = mock(spec=aiohttp.web_request.Request, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)

        pipeline_controller = PipelineController(mock(), mock())

        # given
        when(request).json().thenReturn(async_value({'repo': 'triggear',
                                                     'ref': '123321',
                                                     'environment': 'prod',
                                                     'description': 'something unique',
                                                     'targetUrl': 'http://app.futuresimple.com',
                                                     'state': 'pending'}))
        when(pipeline_controller).get_github().thenReturn(github_client)

        # expect
        expect(github_client).get_deployments(repo='triggear', ref='123321', environment='prod').thenReturn(async_value([
                {
                    'id': 123,
                    'ref': '123321',
                    'environment': 'prod',
                    'description': 'something unique'
                },
                {
                    'id': 321,
                    'ref': '321123',
                    'environment': 'staging',
                    'description': 'something other'
                }
            ]))
        expect(github_client).create_deployment_status(repo='triggear',
                                                       deployment_id=123,
                                                       state='pending',
                                                       target_url='http://app.futuresimple.com',
                                                       description='something unique')\
            .thenReturn(async_value(None))

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_deployment_status(request)

        # then
        assert response.status == 200
        assert response.text == 'Deployment status ACK'

    @pytest.mark.parametrize("deployments", [
        [
            {
                'id': 123,
                'ref': 'zxcasd',
                'environment': 'prod',
                'description': 'something unique'
            },
            {
                'id': 321,
                'ref': '321123',
                'environment': 'staging',
                'description': 'something other'
            }
        ],
        []
    ])
    async def test__when_deployment_status_data_is_valid__and_no_matching_deployment_is_found__no_status_should_be_created(self,
                                                                                                                           deployments: List[Dict]):
        request = mock(spec=aiohttp.web_request.Request, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)

        pipeline_controller = PipelineController(mock(), mock())

        # given
        when(request).json().thenReturn(async_value({'repo': 'triggear',
                                                     'ref': '123321',
                                                     'environment': 'prod',
                                                     'description': 'something unique',
                                                     'targetUrl': 'http://app.futuresimple.com',
                                                     'state': 'pending'}))
        when(pipeline_controller).get_github().thenReturn(github_client)

        # expect
        expect(github_client, times=2).get_deployments(repo='triggear', ref='123321', environment='prod')\
            .thenReturn(async_value(deployments))
        expect(github_client, times=0).create_deployment_status(any)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_deployment_status(request)

        # then
        assert response.status == 404
        assert response.reason == "Deployment matching {'environment': 'prod', 'ref': '123321', 'description': 'something unique'} not found"
