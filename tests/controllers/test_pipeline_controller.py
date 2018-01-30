import datetime
from typing import List, Dict

import aiohttp.web
import aiohttp.web_request
import pytest
import motor.motor_asyncio
from aiohttp import ClientResponse
from mockito import mock, when, expect, captor
from pymongo.results import UpdateResult, InsertOneResult

from app.clients.async_client import AsyncClientException
from app.clients.github_client import GithubClient
from app.controllers.pipeline_controller import PipelineController
from app.enums.registration_fields import RegistrationFields
from app.request_schemes.clear_request_data import ClearRequestData
from app.request_schemes.comment_request_data import CommentRequestData
from app.request_schemes.deployment_request_data import DeploymentRequestData
from app.request_schemes.deployment_status_request_data import DeploymentStatusRequestData
from app.request_schemes.deregister_request_data import DeregisterRequestData
from app.request_schemes.register_request_data import RegisterRequestData
from app.request_schemes.status_request_data import StatusRequestData
from tests.async_mockito import async_value, async_iter

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestPipelineController:
    API_TOKEN = 'token'

    async def test__when_invalid_token_is_sent_to_comment__should_return_401_response(self):
        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        request = mock({'headers': {'Authorization': f'Invalid token'}}, spec=aiohttp.web_request.Request)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_comment(request)

        # then
        assert response.status == 401
        assert response.body == b'Unauthorized'

    async def test__when_invalid_token_is_sent_to_status__should_return_401_response(self):
        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        request = mock({'headers': {'Authorization': f'Invalid token'}}, spec=aiohttp.web_request.Request)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_status(request)

        # then
        assert response.status == 401
        assert response.body == b'Unauthorized'

    async def test__when_invalid_token_is_sent_to_register__should_return_401_response(self):
        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        request = mock({'headers': {'Authorization': f'Invalid token'}}, spec=aiohttp.web_request.Request)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_register(request)

        # then
        assert response.status == 401
        assert response.body == b'Unauthorized'

    async def test__when_comment_request_data_is_invalid__should_return_400_response(self):
        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request)
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

        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request)
        github_client = mock(spec=GithubClient)

        pipeline_controller = PipelineController(github_client, mock(), self.API_TOKEN)

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
        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)

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

        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)
        github_client = mock(spec=GithubClient, strict=True)

        pipeline_controller = PipelineController(github_client, mock(), self.API_TOKEN)

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
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)
        github_exception_data = 'PR not found'

        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        pipeline_controller = PipelineController(github_client, mock(), self.API_TOKEN)

        # given
        when(request).json().thenReturn(async_value(parameters))
        when(StatusRequestData).is_valid_status_data(parameters).thenReturn(True)
        when(github_client).create_github_build_status(
            repo='repo',
            sha='null',
            state='State',
            url='pr_url',
            description='Description',
            context='Context').thenRaise(AsyncClientException(github_exception_data, 404))

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_status(request)

        # then
        assert response.status == 404
        assert response.reason == '<AsyncClientException> message: PR not found, status: 404'

    async def test__when_github_entity_is_not_found__comment_should_return_404_response_with_github_explanation(self):
        parameters = {'repository': 'repo', 'sha': 'null', 'body': 'Comment body', 'jobName': 'job'}
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)
        github_exception_data = 'Commit not found'

        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        pipeline_controller = PipelineController(github_client, mock(), self.API_TOKEN)

        # given
        when(request).json().thenReturn(async_value(parameters))
        when(CommentRequestData).is_valid_comment_data(parameters).thenReturn(True)
        when(github_client).create_comment(repo='repo', sha='null', body="job\nComments: Comment body")\
            .thenRaise(AsyncClientException(github_exception_data, 404))

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_comment(request)

        # then
        assert response.status == 404
        assert response.reason == '<AsyncClientException> message: Commit not found, status: 404'

    async def test__when_registration_data_is_not_valid__should_return_400_response(self):
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)

        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        when(request).json().thenReturn(async_value({}))
        when(RegisterRequestData).is_valid_register_request_data({}).thenReturn(False)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_register(request)

        # then
        assert response.status == 400
        assert response.reason == 'Invalid register request params!'

    async def test__when_data_is_valid__should_call_internal_add_registration__and_return_200_response(self):
        parameters = {'jenkins_url': 'url', 'eventType': 'type', 'repository': 'repo',
                      'jobName': 'job', 'labels': ['label'], 'requested_params': ['branch']}
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)

        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        when(request).json().thenReturn(async_value(parameters))
        when(RegisterRequestData).is_valid_register_request_data(parameters).thenReturn(True)
        when(pipeline_controller).add_or_update_registration(
            jenkins_url='url',
            event_type='type',
            repository='repo',
            job_name='job',
            labels=['label'],
            requested_params=['branch'],
            branch_restrictions=None,
            change_restrictions=None,
            file_restrictions=None
        ).thenReturn(async_value(None))

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_register(request)

        # then
        assert response.status == 200
        assert response.reason == 'OK'

    async def test__when_registration_existed__should_be_replaced_with_current_version(self):
        update_result = mock(spec=UpdateResult)
        mongo_collection = mock(spec=motor.motor_asyncio.AsyncIOMotorCollection, strict=True)
        mongo_db = mock(spec=motor.motor_asyncio.AsyncIOMotorDatabase, strict=True)
        mongo_client = mock({'registered': {'pushed': mongo_db}}, spec=motor.motor_asyncio.AsyncIOMotorClient, strict=True)

        pipeline_controller = PipelineController(mock(), mongo_client, self.API_TOKEN)

        # given
        when(mongo_db).find_one({'jenkins_url': 'url', 'repository': 'repo', 'job': 'job'}).thenReturn(async_value(mongo_collection))
        when(mongo_db).replace_one(mongo_collection, {'jenkins_url': 'url',
                                                      'repository': 'repo',
                                                      'job': 'job',
                                                      'labels': ['label1', 'label2'],
                                                      'requested_params': ['branch', 'sha'],
                                                      'branch_restrictions': ['master'],
                                                      'change_restrictions': ['app/controllers'],
                                                      'file_restrictions': ['__init__.py']}).thenReturn(async_value(update_result))

        # when
        await pipeline_controller.add_or_update_registration(
            jenkins_url='url',
            event_type='pushed',
            repository='repo',
            job_name='job',
            labels=['label1', 'label2'],
            requested_params=['branch', 'sha'],
            branch_restrictions=['master'],
            change_restrictions=['app/controllers'],
            file_restrictions=['__init__.py']
        )

    async def test__when_registration_does_not_exist__should_be_added_to_mongo(self):
        update_result = mock(spec=InsertOneResult)
        mongo_db = mock(spec=motor.motor_asyncio.AsyncIOMotorDatabase, strict=True)
        mongo_client = mock({'registered': {'pushed': mongo_db}}, spec=motor.motor_asyncio.AsyncIOMotorClient, strict=True)

        pipeline_controller = PipelineController(mock(), mongo_client, self.API_TOKEN)

        # given
        when(mongo_db).find_one({'jenkins_url': 'url', 'repository': 'repo', 'job': 'job'}).thenReturn(async_value(None))
        when(mongo_db).insert_one({'repository': 'repo',
                                   'jenkins_url': 'url',
                                   'job': 'job',
                                   'labels': ['label1', 'label2'],
                                   'requested_params': ['branch', 'sha'],
                                   'branch_restrictions': ['master'],
                                   'change_restrictions': ['app/controllers'],
                                   'file_restrictions': ['__init__.py']}).thenReturn(async_value(update_result))

        # when
        await pipeline_controller.add_or_update_registration(
            jenkins_url='url',
            event_type='pushed',
            repository='repo',
            job_name='job',
            labels=['label1', 'label2'],
            requested_params=['branch', 'sha'],
            branch_restrictions=['master'],
            change_restrictions=['app/controllers'],
            file_restrictions=['__init__.py']
        )

    async def test__when_optionals_are_none__should_be_replaced_with_empty_lists(self):
        update_result = mock(spec=InsertOneResult)
        mongo_db = mock(spec=motor.motor_asyncio.AsyncIOMotorDatabase, strict=True)
        mongo_client = mock({'registered': {'pushed': mongo_db}}, spec=motor.motor_asyncio.AsyncIOMotorClient, strict=True)

        pipeline_controller = PipelineController(mock(), mongo_client, self.API_TOKEN)

        # given
        when(mongo_db).find_one({'jenkins_url': 'url', 'repository': 'repo', 'job': 'job'}).thenReturn(async_value(None))
        when(mongo_db).insert_one({'repository': 'repo',
                                   'jenkins_url': 'url',
                                   'job': 'job',
                                   'labels': ['label1', 'label2'],
                                   'requested_params': ['branch', 'sha'],
                                   'branch_restrictions': [],
                                   'change_restrictions': [],
                                   'file_restrictions': []}).thenReturn(async_value(update_result))

        # when
        await pipeline_controller.add_or_update_registration(
            jenkins_url='url',
            event_type='pushed',
            repository='repo',
            job_name='job',
            labels=['label1', 'label2'],
            requested_params=['branch', 'sha'],
            branch_restrictions=None,
            change_restrictions=None,
            file_restrictions=None
        )

    async def test__when_invalid_token_is_sent_to_missing__should_return_401_response(self):
        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        request = mock({'headers': {'Authorization': f'Invalid token'}}, spec=aiohttp.web_request.Request)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_missing(request)

        # then
        assert response.status == 401
        assert response.body == b'Unauthorized'

    async def test__when_event_type_is_missing__handle_missing_should_return_400(self):
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'},
                        'match_info': {}}, spec=aiohttp.web_request.Request, strict=True)

        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        result: aiohttp.web.Response = await pipeline_controller.handle_missing(request)

        assert result.status == 400
        assert result.text == 'Invalid eventType requested'

    async def test__when_missing_endpoint_is_called__should_return_all_related_registrations_with_missing_times_more_then_0(self):
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'},
                        'match_info': {'eventType': 'push'}}, spec=aiohttp.web_request.Request, strict=True)

        cursor: motor.motor_asyncio.AsyncIOMotorCommandCursor = async_iter(
            {RegistrationFields.jenkins_url: 'url', RegistrationFields.job: 'push_job_1', RegistrationFields.missed_times: 7},
            {RegistrationFields.jenkins_url: 'url', RegistrationFields.job: 'push_job_2', RegistrationFields.missed_times: 13}
        )
        labeled_collection: motor.motor_asyncio.AsyncIOMotorCollection = mock(spec=motor.motor_asyncio.AsyncIOMotorCollection, strict=True)
        push_collection: motor.motor_asyncio.AsyncIOMotorCollection = mock(spec=motor.motor_asyncio.AsyncIOMotorCollection, strict=True)
        mongo_client: motor.motor_asyncio.AsyncIOMotorClient = mock({'registered': {'labeled': labeled_collection, 'push': push_collection}},
                                                                    spec=motor.motor_asyncio.AsyncIOMotorClient, strict=True)

        pipeline_controller = PipelineController(mock(), mongo_client, self.API_TOKEN)

        expect(push_collection).find({RegistrationFields.missed_times: {'$gt': 0}}).thenReturn(cursor)
        expect(labeled_collection, times=0).find({RegistrationFields.missed_times: {'$gt': 0}})

        result: aiohttp.web.Response = await pipeline_controller.handle_missing(request)

        assert result.status == 200
        try:
            assert result.text == 'url:push_job_1#7,url:push_job_2#13'
        except AssertionError:
            assert result.text == 'url:push_job_2#13,url:push_job_1#7'

    async def test__when_deregister_got_wrong_token__should_return_401(self):
        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        request = mock({'headers': {'Authorization': f'Invalid token'}}, spec=aiohttp.web_request.Request)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_deregister(request)

        # then
        assert response.status == 401
        assert response.body == b'Unauthorized'

    async def test__when_deregister_is_missing_parameters__should_return_400(self):
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)

        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        when(request).json().thenReturn(async_value({}))
        when(DeregisterRequestData).is_valid_deregister_request_data({}).thenReturn(False)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_deregister(request)

        # then
        assert response.status == 400
        assert response.reason == 'Invalid deregister request params!'

    async def test__when_deregister_request_is_valid__should_remove_registration_from_proper_collection__and_log_it_in_mongo(self):
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)

        deregister_log_collection: motor.motor_asyncio.AsyncIOMotorCollection = mock(spec=motor.motor_asyncio.AsyncIOMotorCollection, strict=True)
        labeled_collection: motor.motor_asyncio.AsyncIOMotorCollection = mock(spec=motor.motor_asyncio.AsyncIOMotorCollection, strict=True)
        push_collection: motor.motor_asyncio.AsyncIOMotorCollection = mock(spec=motor.motor_asyncio.AsyncIOMotorCollection, strict=True)
        mongo_client: motor.motor_asyncio.AsyncIOMotorClient = mock({'registered': {'labeled': labeled_collection,
                                                                                    'push': push_collection},
                                                                     'deregistered': {'log': deregister_log_collection}},
                                                                    spec=motor.motor_asyncio.AsyncIOMotorClient, strict=True)

        pipeline_controller = PipelineController(mock(), mongo_client, self.API_TOKEN)

        # given
        when(request).json().thenReturn(async_value({'eventType': 'push', 'jobName': 'job', 'caller': 'del_job#7', 'jenkins_url': 'url'}))
        expect(push_collection).delete_one({RegistrationFields.job: 'job', RegistrationFields.jenkins_url: 'url'})
        expect(labeled_collection, times=0).delete_one({RegistrationFields.job: 'jobName', RegistrationFields.jenkins_url: 'url'})

        arg_captor = captor()
        expect(deregister_log_collection).insert_one(arg_captor)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_deregister(request)

        assert 'job' == arg_captor.value.get('job')
        assert 'del_job#7' == arg_captor.value.get('caller')
        assert 'url' == arg_captor.value.get('jenkins_url')

        assert 'push' == arg_captor.value.get('eventType')
        assert isinstance(arg_captor.value.get('timestamp'), datetime.datetime)

        assert response.status == 200
        assert response.text == 'Deregistration of job for push succeeded'

    async def test__when_clear_got_wrong_token__should_return_401(self):
        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        request = mock({'headers': {'Authorization': f'Invalid token'}}, spec=aiohttp.web_request.Request)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_clear(request)

        # then
        assert response.status == 401
        assert response.body == b'Unauthorized'

    async def test__when_clear_is_missing_parameters__should_return_400(self):
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)

        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        when(request).json().thenReturn(async_value({}))
        when(ClearRequestData).is_valid_clear_request_data({}).thenReturn(False)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_clear(request)

        # then
        assert response.status == 400
        assert response.reason == 'Invalid clear request params!'

    async def test__when_clear_request_is_valid__should_set_missed_count_to_0(self):
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)

        labeled_collection: motor.motor_asyncio.AsyncIOMotorCollection = mock(spec=motor.motor_asyncio.AsyncIOMotorCollection, strict=True)
        push_collection: motor.motor_asyncio.AsyncIOMotorCollection = mock(spec=motor.motor_asyncio.AsyncIOMotorCollection, strict=True)
        mongo_client: motor.motor_asyncio.AsyncIOMotorClient = mock({'registered': {'labeled': labeled_collection,
                                                                                    'push': push_collection}},
                                                                    spec=motor.motor_asyncio.AsyncIOMotorClient, strict=True)

        pipeline_controller = PipelineController(mock(), mongo_client, self.API_TOKEN)

        # given
        when(request).json().thenReturn(async_value({'eventType': 'push', 'jobName': 'job', 'caller': 'del_job#7', 'jenkins_url': 'url'}))
        expect(push_collection).update_one({RegistrationFields.job: 'job', RegistrationFields.jenkins_url: 'url'}, {'$set': {'missed_times': 0}})
        expect(labeled_collection, times=0).update_one({RegistrationFields.job: 'jobName', RegistrationFields.jenkins_url: 'url'},
                                                       {'$set': {'missed_count': 0}})

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_clear(request)

        assert response.status == 200
        assert response.text == 'Clear of job missed counter succeeded'

    async def test__when_invalid_token_is_sent_to_deployment__should_return_401_response(self):
        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        request = mock({'headers': {'Authorization': f'Invalid token'}}, spec=aiohttp.web_request.Request)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_deployment(request)

        # then
        assert response.status == 401
        assert response.body == b'Unauthorized'

    async def test__when_invalid_data_is_sent_to_deployment__400_response_should_be_returned(self):
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)

        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        when(request).json().thenReturn(async_value({}))
        when(DeploymentRequestData).is_valid_deployment_request_data({}).thenReturn(False)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_deployment(request)

        # then
        assert response.status == 400
        assert response.reason == 'Invalid deployment request payload!'

    async def test__when_deployment_data_is_valid__github_deployment_should_be_created(self):
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)

        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

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

    async def test__when_invalid_token_is_sent_to_deployment_status__should_return_401_response(self):
        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        request = mock({'headers': {'Authorization': f'Invalid token'}}, spec=aiohttp.web_request.Request)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_deployment_status(request)

        # then
        assert response.status == 401
        assert response.body == b'Unauthorized'

    async def test__when_invalid_data_is_sent_to_deployment_status__400_response_should_be_returned(self):
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)

        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        when(request).json().thenReturn(async_value({}))
        when(DeploymentStatusRequestData).is_valid_deployment_status_request_data({}).thenReturn(False)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_deployment_status(request)

        # then
        assert response.status == 400
        assert response.reason == 'Invalid deployment status request payload!'

    async def test__when_deployment_status_data_is_valid__and_matching_deployment_is_found__its_status_should_be_created(self):
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)
        get_deployments_response = mock(spec=ClientResponse, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)

        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        when(request).json().thenReturn(async_value({'repo': 'triggear',
                                                     'ref': '123321',
                                                     'environment': 'prod',
                                                     'description': 'something unique',
                                                     'targetUrl': 'http://app.futuresimple.com',
                                                     'state': 'pending'}))
        when(pipeline_controller).get_github().thenReturn(github_client)

        # expect
        expect(github_client).get_deployments(repo='triggear', ref='123321', environment='prod').thenReturn(async_value(get_deployments_response))
        expect(get_deployments_response).json()\
            .thenReturn(async_value([
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
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)
        get_deployments_response = mock(spec=ClientResponse, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)

        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

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
            .thenReturn(async_value(get_deployments_response))
        expect(get_deployments_response).json()\
            .thenReturn(async_value(deployments))
        expect(github_client, times=0).create_deployment_status(any)

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_deployment_status(request)

        # then
        assert response.status == 404
        assert response.reason == "Deployment matching {'environment': 'prod', 'ref': '123321', 'description': 'something unique'} not found"
