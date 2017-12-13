import github
import aiohttp.web
import aiohttp.web_request
import github.Repository
import github.Commit
import pytest
import motor.motor_asyncio
from mockito import mock, when
from pymongo.results import UpdateResult, InsertOneResult

from app.controllers.pipeline_controller import PipelineController
from app.request_schemes.comment_request_data import CommentRequestData
from app.request_schemes.register_request_data import RegisterRequestData
from app.request_schemes.status_request_data import StatusRequestData
from tests.async_mockito import async_value

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
        github_client = mock(spec=github.Github)
        github_repository = mock(spec=github.Repository)
        github_commit = mock(spec=github.Commit)

        pipeline_controller = PipelineController(github_client, mock(), self.API_TOKEN)

        # given
        when(request).json().thenReturn(async_value(proper_data))
        when(CommentRequestData).is_valid_comment_data(proper_data).thenReturn(True)
        when(github_client).get_repo('repo').thenReturn(github_repository)
        when(github_repository).get_commit('123abc').thenReturn(github_commit)
        when(github_commit).create_comment(body='job\nComments: Comment body')

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
        github_client = mock(spec=github.Github, strict=True)
        github_repository = mock(spec=github.Repository, strict=True)
        github_commit = mock(spec=github.Commit, strict=True)

        pipeline_controller = PipelineController(github_client, mock(), self.API_TOKEN)

        # given
        when(request).json().thenReturn(async_value(proper_data))
        when(StatusRequestData).is_valid_status_data(proper_data).thenReturn(True)
        when(github_client).get_repo('repo').thenReturn(github_repository)
        when(github_repository).get_commit('123abc').thenReturn(github_commit)
        when(github_commit).create_status(state='State', description='Description', target_url='pr_url', context='Context')

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_status(request)

        # then
        assert response.status == 200
        assert response.text == 'Status ACK'

    async def test__when_github_entity_is_not_found__status_should_return_404_response_with_github_explanation(self):
        parameters = {'repository': 'repo', 'sha': 'null', 'state': 'State', 'description': 'Description', 'context': 'Context', 'url': 'pr_url'}
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)
        github_client = mock(spec=github.Github, strict=True)
        github_repository = mock(spec=github.Repository, strict=True)

        pipeline_controller = PipelineController(github_client, mock(), self.API_TOKEN)

        # given
        when(request).json().thenReturn(async_value(parameters))
        when(StatusRequestData).is_valid_status_data(parameters).thenReturn(True)
        when(github_client).get_repo('repo').thenReturn(github_repository)
        github_exception_data = {'message': 'Not Found', 'documentation_url': 'https://developer.github.com/v3/'}
        when(github_repository).get_commit('null').thenRaise(github.GithubException(404, github_exception_data))

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_status(request)

        # then
        assert response.status == 404
        assert response.reason == str(github_exception_data)

    async def test__when_github_entity_is_not_found__comment_should_return_404_response_with_github_explanation(self):
        parameters = {'repository': 'repo', 'sha': 'null', 'body': 'Comment body', 'jobName': 'job'}
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)
        github_client = mock(spec=github.Github, strict=True)
        github_repository = mock(spec=github.Repository, strict=True)

        pipeline_controller = PipelineController(github_client, mock(), self.API_TOKEN)

        # given
        when(request).json().thenReturn(async_value(parameters))
        when(CommentRequestData).is_valid_comment_data(parameters).thenReturn(True)
        when(github_client).get_repo('repo').thenReturn(github_repository)
        github_exception_data = {'message': 'Not Found', 'documentation_url': 'https://developer.github.com/v3/'}
        when(github_repository).get_commit('null').thenRaise(github.GithubException(404, github_exception_data))

        # when
        response: aiohttp.web.Response = await pipeline_controller.handle_comment(request)

        # then
        assert response.status == 404
        assert response.reason == str(github_exception_data)

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
        parameters = {'eventType': 'type', 'repository': 'repo', 'jobName': 'job', 'labels': ['label'], 'requested_params': ['branch']}
        request = mock({'headers': {'Authorization': f'Token {self.API_TOKEN}'}}, spec=aiohttp.web_request.Request, strict=True)

        pipeline_controller = PipelineController(mock(), mock(), self.API_TOKEN)

        # given
        when(request).json().thenReturn(async_value(parameters))
        when(RegisterRequestData).is_valid_register_request_data(parameters).thenReturn(True)
        when(pipeline_controller).add_registration_if_not_exists(
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
        when(mongo_db).find_one({'repository': 'repo', 'job': 'job'}).thenReturn(async_value(mongo_collection))
        when(mongo_db).replace_one(mongo_collection, {'repository': 'repo',
                                                      'job': 'job',
                                                      'labels': ['label1', 'label2'],
                                                      'requested_params': ['branch', 'sha'],
                                                      'branch_restrictions': ['master'],
                                                      'change_restrictions': ['app/controllers'],
                                                      'file_restrictions': ['__init__.py']}).thenReturn(async_value(update_result))

        # when
        await pipeline_controller.add_registration_if_not_exists(
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
        when(mongo_db).find_one({'repository': 'repo', 'job': 'job'}).thenReturn(async_value(None))
        when(mongo_db).insert_one({'repository': 'repo',
                                   'job': 'job',
                                   'labels': ['label1', 'label2'],
                                   'requested_params': ['branch', 'sha'],
                                   'branch_restrictions': ['master'],
                                   'change_restrictions': ['app/controllers'],
                                   'file_restrictions': ['__init__.py']}).thenReturn(async_value(update_result))

        # when
        await pipeline_controller.add_registration_if_not_exists(
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
        when(mongo_db).find_one({'repository': 'repo', 'job': 'job'}).thenReturn(async_value(None))
        when(mongo_db).insert_one({'repository': 'repo',
                                   'job': 'job',
                                   'labels': ['label1', 'label2'],
                                   'requested_params': ['branch', 'sha'],
                                   'branch_restrictions': [],
                                   'change_restrictions': [],
                                   'file_restrictions': []}).thenReturn(async_value(update_result))

        # when
        await pipeline_controller.add_registration_if_not_exists(
            event_type='pushed',
            repository='repo',
            job_name='job',
            labels=['label1', 'label2'],
            requested_params=['branch', 'sha'],
            branch_restrictions=None,
            change_restrictions=None,
            file_restrictions=None
        )
