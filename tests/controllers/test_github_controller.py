import asyncio

import os
import pytest
import motor.motor_asyncio
import aiohttp.web_request
import aiohttp.web
import time
from mockito import mock, when, expect, captor

import app.utilities.background_task
import app.config.triggear_config
import app.clients.jenkins_client
from app.clients.async_client import AsyncClientException, AsyncClient, AsyncClientNotFoundException
from app.clients.github_client import GithubClient
from app.controllers.github_controller import GithubController
from app.dto.hook_details import HookDetails
from app.dto.hook_details_factory import HookDetailsFactory
from app.enums.event_types import EventTypes
from app.exceptions.triggear_error import TriggearError
from tests.async_mockito import async_iter, async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestGithubController:
    async def test__when_job_does_not_exist__it_should_have_missed_times_field_incremented(self):
        hook_query = {'repository': 'repo'}
        job_name = 'non-existing-job'
        branch_name = 'branch'

        cursor = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCommandCursor,
            strict=True
        )
        collection = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCollection,
            strict=True
        )
        mongo_client: motor.motor_asyncio.AsyncIOMotorClient = mock(
            {'registered': {EventTypes.push: collection}},
            spec=motor.motor_asyncio.AsyncIOMotorClient,
            strict=True
        )
        hook_details = mock(
            {'event_type': EventTypes.push, 'query': hook_query, 'branch': branch_name},
            spec=HookDetails,
            strict=True
        )
        jenkins_client: app.clients.jenkins_client.JenkinsClient = mock(
            spec=app.clients.jenkins_client.JenkinsClient,
            strict=True
        )
        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mongo_client,
                                             config=mock())

        # given
        when(collection).find(hook_query).thenReturn(async_iter(cursor))
        when(cursor).__getitem__('job').thenReturn(job_name)
        when(cursor).__getitem__('requested_params').thenReturn(None)
        when(cursor).__getitem__('jenkins_url').thenReturn('url')
        when(cursor).get('branch_restrictions').thenReturn([])
        when(cursor).get('change_restrictions').thenReturn([])
        when(cursor).get('file_restrictions').thenReturn([])
        when(github_controller).get_jenkins('url').thenReturn(jenkins_client)
        when(jenkins_client).get_jobs_next_build_number(job_name).thenRaise(AsyncClientNotFoundException('not found', 404))
        expect(collection).update_one({'job': job_name, **hook_query}, {'$inc': {'missed_times': 1}}).thenReturn(async_value(any))

        # when
        await github_controller.trigger_registered_jobs(hook_details)

    async def test__when_header_signature_is_not_provided__should_return_401_from_validation(self):
        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mock(),
                                             config=mock())

        request = mock({'headers': {}}, spec=aiohttp.web_request.Request, strict=True)

        assert await github_controller.validate_webhook_secret(request) == (401, 'Unauthorized')

    async def test__when_auth_different_then_sha1_is_received__should_return_501(self):
        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mock(),
                                             config=mock())

        request = mock({'headers': {'X-Hub-Signature': 'different=token'}}, spec=aiohttp.web_request.Request, strict=True)

        assert await github_controller.validate_webhook_secret(request) == (501, "Only SHA1 auth supported")

    async def test__when_invalid_signature_is_sent__should_return_401_from_validation(self):
        triggear_config = mock({'triggear_token': 'api_token', 'rerun_time_limit': 1}, spec=app.config.triggear_config.TriggearConfig, strict=True)
        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mock(),
                                             config=triggear_config)

        request = mock({'headers': {'X-Hub-Signature': 'sha1=invalid_signature'}}, spec=aiohttp.web_request.Request, strict=True)

        # given
        when(request).read().thenReturn(async_value(b"valid_data"))

        # when
        assert await github_controller.validate_webhook_secret(request) == (401, 'Unauthorized')

    async def test__when_valid_signature_is_sent__should_return_authorized_from_validation(self):
        triggear_config = mock({'triggear_token': 'api_token', 'rerun_time_limit': 1}, spec=app.config.triggear_config.TriggearConfig, strict=True)
        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mock(),
                                             config=triggear_config)

        request = mock({'headers': {'X-Hub-Signature': 'sha1=95f4e9f69093927bc664b433f7255486b698537c'}},
                       spec=aiohttp.web_request.Request, strict=True)

        # given
        when(request).read().thenReturn(async_value(b"valid_data"))

        # when
        assert await github_controller.validate_webhook_secret(request) == 'AUTHORIZED'

    async def test__get_request_json__should_return_body_of_request_as_json(self):
        request = mock(spec=aiohttp.web_request.Request, strict=True)

        # given
        when(request).json().thenReturn(async_value({'key': 'value'}))

        # then
        assert await GithubController.get_request_json(request) == {'key': 'value'}

    async def test__when_validation_fails__should_return_its_values_as_request_status(self):
        github_controller = GithubController(mock(), mock(), mock())
        request = mock(spec=aiohttp.web_request.Request, strict=True)

        # given
        when(github_controller).validate_webhook_secret(request).thenReturn(async_value((401, 'Unauthorized')))

        # when
        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        # then
        assert response.status == 401
        assert response.text == 'Unauthorized'

    async def test__when_action_is_none__should_return_ack(self):
        github_controller = GithubController(mock(), mock(), mock())
        request = mock({'headers': {}}, spec=aiohttp.web_request.Request, strict=True)

        # given
        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(request).json().thenReturn(async_value({}))

        expect(github_controller, times=0).handle_labeled(any)
        expect(github_controller, times=0).handle_synchronize(any)
        expect(github_controller, times=0).handle_comment(any)
        expect(github_controller, times=0).handle_pr_opened(any)
        expect(github_controller, times=0).handle_push(any)
        expect(github_controller, times=0).handle_tagged(any)

        # when
        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        # then
        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_action_is_labeled__should_call_handle_labeled__and_return_200(self):
        github_controller = GithubController(mock(), mock(), mock())
        request = mock({'headers': {}}, spec=aiohttp.web_request.Request, strict=True)

        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(github_controller).get_request_json(request).thenReturn(async_value({'action': 'labeled'}))

        expect(github_controller, times=1).handle_labeled({'action': 'labeled'}).thenReturn(async_value(None))

        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_action_is_synchronized__should_call_handle_synchronized__and_return_200(self):
        github_controller = GithubController(mock(), mock(), mock())
        request = mock({'headers': {}}, spec=aiohttp.web_request.Request, strict=True)

        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(github_controller).get_request_json(request).thenReturn(async_value({'action': 'synchronize'}))

        expect(github_controller, times=1).handle_synchronize({'action': 'synchronize'}).thenReturn(async_value(None))

        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_action_is_created__should_call_handle_comment__and_return_200(self):
        github_controller = GithubController(mock(), mock(), mock())
        request = mock({'headers': {}}, spec=aiohttp.web_request.Request, strict=True)

        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(github_controller).get_request_json(request).thenReturn(async_value({'action': 'created'}))

        expect(github_controller, times=1).handle_comment({'action': 'created'}).thenReturn(async_value(None))

        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_event_header_is_pull_request__and_action_is_not_pr_opened__should_not_call_handle_pr_opened__and_return_200(self):
        github_controller = GithubController(mock(), mock(), mock())
        request = mock({'headers': {'X-GitHub-Event': 'pull_request'}}, spec=aiohttp.web_request.Request, strict=True)

        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(github_controller).get_request_json(request).thenReturn(async_value({'action': 'definitelly_not_opened'}))

        expect(github_controller, times=0).handle_pr_opened({'action': 'definitelly_not_opened'})

        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_event_header_is_pull_request__and_action_is_pr_opened__should_call_handle_pr_opened__and_return_200(self):
        github_controller = GithubController(mock(), mock(), mock())
        request = mock({'headers': {'X-GitHub-Event': 'pull_request'}}, spec=aiohttp.web_request.Request, strict=True)

        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(github_controller).get_request_json(request).thenReturn(async_value({'action': 'opened'}))

        expect(github_controller, times=1).handle_pr_opened({'action': 'opened'}).thenReturn(async_value(None))

        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_event_type_is_push__but_ref_does_not_match__neither_push_or_tagged_handle_should_be_called(self):
        github_controller = GithubController(mock(), mock(), mock())
        request = mock({'headers': {'X-GitHub-Event': 'push'}}, spec=aiohttp.web_request.Request, strict=True)

        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(github_controller).get_request_json(request).thenReturn(async_value({'ref': 'not_matching'}))

        expect(github_controller, times=0).handle_push({'ref': 'not_matching'})
        expect(github_controller, times=0).handle_tagged({'ref': 'not_matching'})

        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_event_type_is_push__and_ref_has_heads__should_call_handle_push(self):
        github_controller = GithubController(mock(), mock(), mock())
        request = mock({'headers': {'X-GitHub-Event': 'push'}}, spec=aiohttp.web_request.Request, strict=True)

        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(github_controller).get_request_json(request).thenReturn(async_value({'ref': 'refs/heads/master'}))

        expect(github_controller, times=1).handle_push({'ref': 'refs/heads/master'}).thenReturn(async_value(None))
        expect(github_controller, times=0).handle_tagged({'ref': 'refs/heads/master'})

        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_event_type_is_push__and_ref_has_tags__should_call_handle_tagged(self):
        github_controller = GithubController(mock(), mock(), mock())
        request = mock({'headers': {'X-GitHub-Event': 'push'}}, spec=aiohttp.web_request.Request, strict=True)

        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(github_controller).get_request_json(request).thenReturn(async_value({'ref': 'refs/tags/1.0'}))

        expect(github_controller, times=0).handle_push({'ref': 'refs/tags/1.0'})
        expect(github_controller, times=1).handle_tagged({'ref': 'refs/tags/1.0'}).thenReturn(async_value(None))

        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_handle_pr_opened_is_called__it_should_call_add_sync_label__and_trigger_registered_jobs(self):
        github_client = mock(spec=GithubClient, strict=True)
        github_controller = GithubController(github_client, mock(), mock())
        hook_data = {'repository': 'repo', 'pull_request': {'number': 25}}

        hook_details = mock({'repository': 'repo'}, spec=HookDetails, strict=True)

        # when
        when(github_client).set_sync_label('repo', number=25).thenReturn(async_value(None))
        when(HookDetailsFactory).get_pr_opened_details(hook_data).thenReturn(hook_details)
        when(github_controller).trigger_registered_jobs(hook_details).thenReturn(async_value(None))

        # then
        await github_controller.handle_pr_opened(hook_data)

    async def test__handle_tagged__passes_proper_hook_details_to_trigger_jobs(self):
        github_controller = GithubController(mock(), mock(), mock())
        hook_data = {'some': 'data'}
        hook_details = mock({'sha': '123321'}, spec=HookDetails, strict=True)

        # given
        when(HookDetailsFactory).get_tag_details(hook_data).thenReturn(hook_details)
        expect(github_controller, times=1).trigger_registered_jobs(hook_details).thenReturn(async_value(None))

        # then
        await github_controller.handle_tagged(hook_data)

    async def test__handle_labeled__passes_proper_hook_details_to_trigger_jobs(self):
        github_controller = GithubController(mock(), mock(), mock())
        hook_data = {'some': 'data'}
        hook_details = mock(spec=HookDetails, strict=True)

        # given
        when(HookDetailsFactory).get_labeled_details(hook_data).thenReturn(hook_details)
        expect(github_controller, times=1).trigger_registered_jobs(hook_details).thenReturn(async_value(None))

        # then
        await github_controller.handle_labeled(hook_data)

    async def test__handle_synchronize__should_get_pr_labels__and_call_pr_and_label_handlers(self):
        hook_data = {'pull_request': {'number': 12, 'head': {'repo': {'full_name': 'repo'}}}}
        pr_labels = ['label1', 'label2']
        github_client = mock(spec=GithubClient, strict=True)
        github_controller = GithubController(github_client, mock(), mock())

        # expect
        expect(github_client, times=1).get_pr_labels(repo='repo', number=12).thenReturn(async_value(pr_labels))
        expect(github_controller).handle_pr_sync(hook_data, pr_labels).thenReturn(async_value(None))
        expect(github_controller).handle_labeled_sync(hook_data, pr_labels).thenReturn(async_value(None))

        # when
        await github_controller.handle_synchronize(hook_data)

    async def test__handle_pr_sync__should_do_nothing__if_pr_sync_label_is_not_set(self):
        hook_data = {}
        github_controller = GithubController(mock(), mock(), mock())

        expect(github_controller, times=0).handle_pr_opened(hook_data)

        await github_controller.handle_pr_sync(hook_data, ['label', 'other_label'])

    async def test__handle_pr_sync__should_call_pr_opened_handle__if_pr_sync_label_is_set(self):
        hook_data = {}
        github_controller = GithubController(mock(), mock(), mock())

        expect(github_controller, times=1).handle_pr_opened(hook_data).thenReturn(async_value(None))

        await github_controller.handle_pr_sync(hook_data, ['label', 'triggear-pr-sync', 'other_label'])

    async def test__handle_synchronize__when_handle_pr_sync_raises_exception__handle_labeled_sync_should_be_called_anyway(self):
        hook_data = {'pull_request': {'number': 12, 'head': {'repo': {'full_name': 'repo'}}}}
        pr_labels = ['label1', 'label2']
        github_client = mock(spec=GithubClient, strict=True)
        github_controller = GithubController(github_client, mock(), mock())

        # expect
        expect(github_client, times=1).get_pr_labels(repo='repo', number=12).thenReturn(async_value(pr_labels))
        expect(github_controller, times=1).handle_pr_sync(hook_data, pr_labels).thenRaise(AsyncClientException('PR not found', 404))
        expect(github_controller, times=1).handle_labeled_sync(hook_data, pr_labels).thenReturn(async_value(None))

        # when
        with pytest.raises(AsyncClientException):
            await github_controller.handle_synchronize(hook_data)

    async def test__handle_synchronize__when_handle_pr_and_labeled_sync_raise_exceptions__it_should_be_raised_up(self):
        hook_data = {'pull_request': {'number': 12, 'head': {'repo': {'full_name': 'repo'}}}}
        pr_labels = ['label1', 'label2']
        github_client = mock(spec=GithubClient, strict=True)
        github_controller = GithubController(github_client, mock(), mock())

        # expect
        expect(github_client, times=1).get_pr_labels(repo='repo', number=12).thenReturn(async_value(pr_labels))
        expect(github_controller, times=1).handle_pr_sync(hook_data, pr_labels).thenRaise(AsyncClientException('PR not found', 404))
        expect(github_controller, times=1).handle_labeled_sync(hook_data, pr_labels).thenRaise(AsyncClientException('Something went wrong', 500))

        # when
        with pytest.raises(AsyncClientException) as exception:
            await github_controller.handle_synchronize(hook_data)
        assert exception.value.status == 500
        assert exception.value.message == 'Something went wrong'

    async def test__handle_labeled_sync__when_sync_label_is_not_in_labels__should_abort(self):
        github_controller = GithubController(mock(), mock(), mock())
        labels = mock(spec=list)
        labels_list = ['other_label']
        labels_iter = mock(spec=iter(labels_list))

        when(labels).__iter__().thenReturn(labels_iter)
        when(labels_iter).__next__().thenReturn(labels_list[0]).thenRaise(StopIteration())
        expect(labels, times=0).__len__()
        expect(labels, times=0).remove('triggear-label-sync')

        await github_controller.handle_labeled_sync(mock(), labels)

    async def test__handle_labeled_sync__when_sync_label_is_in_labels__but_its_the_only_label__should_abort(self):
        github_controller = GithubController(mock(), mock(), mock())
        labels = mock(spec=list)
        labels_list = ['triggear-label-sync']
        labels_iter = mock(spec=iter(labels_list))

        when(labels).__iter__().thenReturn(labels_iter)
        when(labels_iter).__next__().thenReturn(labels_list[0])
        expect(labels, times=1).__len__().thenReturn(1)
        expect(labels, times=0).remove('triggear-label-sync')

        await github_controller.handle_labeled_sync(mock(), labels)

    async def test__handle_labeled_sync__when_sync_label_is_present__should_call_handle_labeled_for_all_other_labels(self):
        github_controller = GithubController(mock(), mock(), mock())
        labels = ['triggear-label-sync', 'other-label', 'label']

        expect(github_controller).handle_labeled({'label': {'name': 'other-label'}}).thenReturn(async_value(None))
        expect(github_controller).handle_labeled({'label': {'name': 'label'}}).thenReturn(async_value(None))

        await github_controller.handle_labeled_sync({}, labels)

    async def test__when_comment_is_label_sync__should_call_handle_pr_sync(self):
        hook_data = {'comment': {'body': 'triggear-label-sync'}}
        github_controller = GithubController(mock(), mock(), mock())

        expect(github_controller, times=1).handle_labeled_sync_comment(hook_data).thenReturn(async_value(None))
        expect(github_controller, times=0).handle_pr_sync_comment(hook_data)

        await github_controller.handle_comment(hook_data)

    async def test__when_comment_is_pr_sync__should_call_handle_pr_sync(self):
        hook_data = {'comment': {'body': 'triggear-pr-sync'}}
        github_controller = GithubController(mock(), mock(), mock())

        expect(github_controller, times=0).handle_labeled_sync_comment(hook_data)
        expect(github_controller, times=1).handle_pr_sync_comment(hook_data).thenReturn(async_value(None))

        await github_controller.handle_comment(hook_data)

    async def test__handle_pr_sync_comment__should_build_hook_details__and_call_trigger_registered_jobs(self):
        github_controller = GithubController(mock(), mock(), mock())
        hook_data = mock()
        hook_details = mock(spec=HookDetails, strict=True)

        expect(github_controller).get_comment_branch_and_sha(hook_data).thenReturn(async_value(('branch', 'sha')))
        expect(HookDetailsFactory).get_pr_sync_details(hook_data, 'branch', 'sha').thenReturn(hook_details)
        expect(github_controller).trigger_registered_jobs(hook_details).thenReturn(async_value(None))

        await github_controller.handle_pr_sync_comment(hook_data)

    async def test__get_comment_branch_and_sha__should_return_branch_and_sha__by_parsing_hook_data(self):
        github_client = mock(spec=GithubClient, strict=True)
        github_controller = GithubController(github_client, mock(), mock())
        hook_data = {'repository': {'full_name': 'repo'}, 'issue': {'number': 23}}

        expect(github_client).get_pr_branch('repo', 23).thenReturn(async_value('master'))
        expect(github_client).get_latest_commit_sha('repo', 23).thenReturn(async_value('123asd'))

        branch, sha = await github_controller.get_comment_branch_and_sha(hook_data)

        assert 'master' == branch
        assert '123asd' == sha

    async def test__handle_labeled_sync_comment__should_trigger_registered_jobs__for_all_labeled_sync_details(self):
        github_controller = GithubController(mock(), mock(), mock())
        label_hook_details = mock(spec=HookDetails)
        other_label_hook_details = mock(spec=HookDetails)
        hook_data = mock()

        expect(github_controller, times=1)\
            .get_comment_branch_and_sha(hook_data)\
            .thenReturn(async_value(('staging', '321456')))
        expect(HookDetailsFactory, times=1)\
            .get_labeled_sync_details(hook_data, head_branch='staging', head_sha='321456')\
            .thenReturn([label_hook_details, other_label_hook_details])
        expect(github_controller, times=1)\
            .trigger_registered_jobs(label_hook_details)\
            .thenReturn(async_value(None))
        expect(github_controller, times=1)\
            .trigger_registered_jobs(other_label_hook_details)\
            .thenReturn(async_value(None))

        await github_controller.handle_labeled_sync_comment(hook_data)

    async def test__push_handle__should_not_trigger_jobs__if_sha_means_branch_deletion(self):
        github_controller = GithubController(mock(), mock(), mock())
        hook_data = mock()
        hook_details = mock({'sha': '0000000000000000000000000000000000000000', 'branch': 'master'}, spec=HookDetails, strict=True)

        expect(HookDetailsFactory).get_push_details(hook_data).thenReturn(hook_details)
        expect(github_controller, times=0).trigger_registered_jobs(hook_details)

        await github_controller.handle_push(hook_data)

    async def test__push_handle__should_trigger_jobs__if_sha_is_not_about_branch_deletion(self):
        github_controller = GithubController(mock(), mock(), mock())
        hook_data = mock()
        hook_details = mock({'sha': '1234567890qwertyuiopasdfghjklzxcvbnmnbvc', 'branch': 'master'}, spec=HookDetails, strict=True)

        expect(HookDetailsFactory).get_push_details(hook_data).thenReturn(hook_details)
        expect(github_controller, times=1).trigger_registered_jobs(hook_details).thenReturn(async_value(None))

        await github_controller.handle_push(hook_data)

    async def test__are_files_in_repo__should_return_false_on_any_missing_file(self):
        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        github_controller = GithubController(github_client, mock(), mock())

        hook_details = mock({'repository': 'repo', 'sha': '123qwe', 'branch': 'master'}, spec=HookDetails, strict=True)
        files = ['app/main.py', '.gitignore']

        expect(github_client).get_file_content(repo='repo', ref='123qwe', path='app/main.py').thenReturn(async_value(None))
        expect(github_client).get_file_content(repo='repo', ref='123qwe', path='.gitignore').thenRaise(AsyncClientException('File not found', 404))

        assert not await github_controller.are_files_in_repo(files, hook_details)

    async def test__are_files_in_repo__should_return_true_if_all_files_are_in_repo(self):
        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        github_controller = GithubController(github_client, mock(), mock())

        hook_details = mock({'repository': 'repo', 'sha': None, 'branch': 'master'}, spec=HookDetails, strict=True)
        files = ['app/main.py', '.gitignore']

        expect(github_client).get_file_content(repo='repo', ref='master', path='app/main.py').thenReturn(async_value(None))
        expect(github_client).get_file_content(repo='repo', ref='master', path='.gitignore').thenReturn(async_value(None))

        assert await github_controller.are_files_in_repo(files, hook_details)

    @pytest.mark.parametrize("build_info, expected_state", [
        ({'result': 'other'}, 'error'),
        ({'result': 'SUCCESS'}, 'success'),
        ({'result': 'FAILURE'}, 'failure'),
        ({'result': 'ABORTED'}, 'failure'),
        ({'result': 'UNSTABLE'}, 'success'),
    ])
    async def test__get_final_build_state__should_return_proper_states(self, build_info, expected_state):
        assert expected_state == await GithubController.get_final_build_state(build_info)

    @pytest.mark.parametrize("build_info, expected_description", [
        ({'result': 'other'}, 'build error'),
        ({'result': 'SUCCESS'}, 'build succeeded'),
        ({'result': 'FAILURE'}, 'build failed'),
        ({'result': 'ABORTED'}, 'build aborted'),
        ({'result': 'UNSTABLE'}, 'build unstable'),
    ])
    async def test__get_final_build_description__should_return_proper_description(self, build_info, expected_description):
        assert expected_description == await GithubController.get_final_build_description(build_info)

    @pytest.mark.parametrize("requested_parameters, expected_parameters", [
        ([], None),
        (['branch'], {'branch': 'master'}),
        (['sha'], {'sha': '123321'}),
        (['tag'], {'tag': '1.0'}),
        (['tag', 'sha'], {'tag': '1.0', 'sha': '123321'}),
        (['tag', 'sha', 'branch'], {'tag': '1.0', 'sha': '123321', 'branch': 'master'}),
        (['invalid'], None)
    ])
    async def test__get_requested_parameters_values__should_return_only_requested_parameters(self, requested_parameters, expected_parameters):
        assert expected_parameters == await GithubController.get_requested_parameters_values(requested_parameters,
                                                                                             'master',
                                                                                             '123321',
                                                                                             '1.0')

    @pytest.mark.parametrize("requested_parameters, expected_parameters", [
        ([], None),
        (['branch:customBranch'], {'customBranch': 'staging'}),
        (['sha:SHA'], {'SHA': '1q2w3e'}),
        (['tag:tAg'], {'tAg': '2.0'}),
        (['tag:Tag', 'sha:shA'], {'Tag': '2.0', 'shA': '1q2w3e'}),
        (['tag:custom', 'sha:very', 'branch:much'], {'custom': '2.0', 'very': '1q2w3e', 'much': 'staging'}),
        (['invalid'], None)
    ])
    async def test__get_requested_parameters_values__when_requested_params_are_prefix_based__should_return_proper_requested_params(
            self, requested_parameters, expected_parameters):
        assert expected_parameters == await GithubController.get_requested_parameters_values(requested_parameters,
                                                                                             'staging',
                                                                                             '1q2w3e',
                                                                                             '2.0')

    async def test__get_requested_parameters__should_return_files_joined_with_coma__when_changes_are_requested(self):
        result = await GithubController.get_requested_parameters_values(
            ['branch', 'changes'],
            'master',
            '123321',
            '1.0',
            changes={'README.md', '.gitignore'}
        )
        try:
            assert {'branch': 'master', 'changes': 'README.md,.gitignore'} == result
        except AssertionError:
            assert {'branch': 'master', 'changes': '.gitignore,README.md'} == result

    async def test__can_trigger_job_by_branch__when_job_was_not_run__should_add_it_to_mongo__and_return_true(self):
        collection = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCollection,
            strict=True
        )
        mongo_client: motor.motor_asyncio.AsyncIOMotorClient = mock(
            {'registered': {'last_run_in': collection}},
            spec=motor.motor_asyncio.AsyncIOMotorClient,
            strict=True
        )
        github_controller = GithubController(mock(), mongo_client, mock())
        mock(time)

        when(time).time().thenReturn(1)
        when(collection).find_one({'jenkins_url': 'url', "branch": 'master', "job": 'job'}).thenReturn(async_value(None))
        expect(collection).insert_one({'jenkins_url': 'url', 'branch': 'master', 'job': 'job', 'timestamp': 1}).thenReturn(async_value(None))

        assert await github_controller.can_trigger_job_by_branch('url', 'job', 'master')

    async def test__can_trigger_job_by_branch__when_job_was_run_long_ago__should_add_update_mongo__and_return_true(self):
        found_run = mock()
        collection = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCollection,
            strict=True
        )
        mongo_client: motor.motor_asyncio.AsyncIOMotorClient = mock(
            {'registered': {'last_run_in': collection}},
            spec=motor.motor_asyncio.AsyncIOMotorClient,
            strict=True
        )
        triggear_config = mock({'rerun_time_limit': 20, 'triggear_token': 'token'}, spec=app.config.triggear_config.TriggearConfig)
        github_controller = GithubController(mock(), mongo_client, triggear_config)
        mock(time)

        when(collection).find_one({'jenkins_url': 'url', "branch": 'master', "job": 'job'}).thenReturn(async_value(found_run))
        when(found_run).__getitem__('timestamp').thenReturn(3)
        when(time).time().thenReturn(23)
        expect(collection).replace_one(found_run, {'jenkins_url': 'url', 'branch': 'master', 'job': 'job', 'timestamp': 23})\
            .thenReturn(async_value(None))

        assert await github_controller.can_trigger_job_by_branch('url', 'job', 'master')

    async def test__can_trigger_job_by_branch__when_job_was_not_so_long_ago__should_return_false(self):
        found_run = mock()
        collection = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCollection,
            strict=True
        )
        mongo_client: motor.motor_asyncio.AsyncIOMotorClient = mock(
            {'registered': {'last_run_in': collection}},
            spec=motor.motor_asyncio.AsyncIOMotorClient,
            strict=True
        )
        triggear_config = mock({'rerun_time_limit': 20, 'triggear_token': 'token'}, spec=app.config.triggear_config.TriggearConfig)
        github_controller = GithubController(mock(), mongo_client, triggear_config)
        mock(time)

        when(collection).find_one({'jenkins_url': 'url', "branch": 'master', "job": 'job'}).thenReturn(async_value(found_run))
        when(found_run).__getitem__('timestamp').thenReturn(3)
        when(time).time().thenReturn(22)
        expect(collection, times=0)\
            .replace_one(found_run, {'jenkins_url': 'url', 'branch': 'master', 'job': 'job', 'timestamp': 23})\
            .thenReturn(async_value(None))

        assert not await github_controller.can_trigger_job_by_branch('url', 'job', 'master')

    async def test__trigger_registered_job__when_build_job_raises__error_status_should_be_created(self):
        jenkins_url = 'jenkins_url'
        requested_parameters = ['branch']
        branch = 'staging'
        sha = '123123'
        tag = '1.0'
        repository = 'repo'
        job_url = 'http://example.com'

        jenkins_client = mock(spec=app.clients.jenkins_client.JenkinsClient, strict=True)
        github_client = mock(spec=GithubClient, strict=True)
        github_controller = GithubController(github_client, mock(), mock())

        when(github_controller).get_jenkins(jenkins_url).thenReturn(jenkins_client)
        expect(github_controller)\
            .get_requested_parameters_values(requested_parameters, branch, sha, tag, set())\
            .thenReturn(async_value({'branch': branch}))
        expect(jenkins_client) \
            .get_jobs_next_build_number('job')\
            .thenReturn(async_value(321))
        when(jenkins_client)\
            .build_jenkins_job('job', {'branch': branch})\
            .thenRaise(AsyncClientException('Job did not accept parameters', 404))

        expect(jenkins_client)\
            .get_job_url('job')\
            .thenReturn(async_value(job_url))
        expect(github_client)\
            .create_github_build_status(repository, sha, 'error', job_url,
                                        "Job jenkins_url:job did not accept requested parameters dict_keys(['branch'])", 'job')\
            .thenReturn(async_value(None))

        await github_controller.trigger_registered_job(jenkins_url, 'job', requested_parameters, repository, sha, branch, tag)

    async def test__trigger_registered_job__when_build_info_is_none__proper_error_status_should_be_created(self):
        jenkins_url = 'jenkins_url'
        requested_parameters = ['branch']
        branch = 'staging'
        sha = '123123'
        repository = 'repo'
        job_url = 'http://example.com'
        job_name = 'job'

        jenkins_client = mock(spec=app.clients.jenkins_client.JenkinsClient, strict=True)
        github_client = mock(spec=GithubClient, strict=True)
        github_controller = GithubController(github_client, mock(), mock())

        mock(asyncio)

        when(github_controller).get_jenkins(jenkins_url).thenReturn(jenkins_client)
        expect(github_controller) \
            .get_requested_parameters_values(requested_parameters, branch, sha, None, set()) \
            .thenReturn(async_value({'branch': branch}))
        expect(jenkins_client) \
            .get_jobs_next_build_number(job_name) \
            .thenReturn(async_value(321))
        when(jenkins_client) \
            .build_jenkins_job(job_name, {'branch': branch})\
            .thenReturn(async_value(None))
        expect(jenkins_client, times=2) \
            .get_build_info_data(job_name, 321) \
            .thenReturn(async_value(None))
        expect(jenkins_client) \
            .get_job_url(job_name) \
            .thenReturn(async_value(job_url))

        expect(github_client) \
            .create_github_build_status(repository, sha, "error", job_url, 'Triggear cant find build jenkins_url:job #321', job_name) \
            .thenReturn(async_value(None))

        await github_controller.trigger_registered_job(jenkins_url, job_name, requested_parameters, repository, sha, branch)

    async def test__trigger_registered_job__when_build_info_is_not_none__proper_pending_and_final_status_should_be_created(self):
        jenkins_url = 'jenkins_url'
        requested_parameters = ['branch']
        branch = 'staging'
        sha = '123123'
        repository = 'repo'
        job_url = 'http://example.com'
        build_url = job_url + '/job/321'
        job_name = 'job'

        jenkins_client = mock(spec=app.clients.jenkins_client.JenkinsClient, strict=True)
        github_client = mock(spec=GithubClient, strict=True)
        github_controller = GithubController(github_client, mock(), mock())

        mock(asyncio)

        when(github_controller).get_jenkins(jenkins_url).thenReturn(jenkins_client)
        expect(github_controller)\
            .get_requested_parameters_values(requested_parameters, branch, sha, None, set())\
            .thenReturn(async_value({'branch': branch}))
        expect(jenkins_client) \
            .get_jobs_next_build_number(job_name)\
            .thenReturn(async_value(321))
        when(jenkins_client)\
            .build_jenkins_job(job_name, {'branch': branch})\
            .thenReturn(async_value(None))
        build_info = {'url': build_url}
        expect(jenkins_client, times=2)\
            .get_build_info_data(job_name, 321)\
            .thenReturn(async_value(build_info))\
            .thenReturn(async_value({**build_info, 'finished': 'yes'}))

        expect(github_client)\
            .create_github_build_status(repository, sha, "pending", build_url, "build in progress", job_name)\
            .thenReturn(async_value(None))

        when(asyncio)\
            .sleep(1)\
            .thenReturn(async_value(None))
        expect(jenkins_client, times=2)\
            .is_job_building(job_name, 321)\
            .thenReturn(async_value(True))\
            .thenReturn(async_value(False))

        expect(github_controller) \
            .get_final_build_state({**build_info, 'finished': 'yes'})\
            .thenReturn(async_value('success'))
        expect(github_controller) \
            .get_final_build_description({**build_info, 'finished': 'yes'})\
            .thenReturn(async_value('build succeeded'))

        expect(github_client)\
            .create_github_build_status(repository, sha, "success", build_url, "build succeeded", job_name)\
            .thenReturn(async_value(None))

        await github_controller.trigger_registered_job(jenkins_url, job_name, requested_parameters, repository, sha, branch)

    async def test__trigger_registered_jobs__when_job_exists__background_task_to_trigger_it_is_started(self):
        jenkins_url = 'jenkins_url'
        hook_query = {'repository': 'repo'}
        job_name = 'job'
        sha = '123789'
        branch_name = 'branch'

        cursor = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCommandCursor,
            strict=True
        )
        collection = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCollection,
            strict=True
        )
        mongo_client: motor.motor_asyncio.AsyncIOMotorClient = mock(
            {'registered': {EventTypes.push: collection}},
            spec=motor.motor_asyncio.AsyncIOMotorClient,
            strict=True
        )
        hook_details = mock(
            {'event_type': EventTypes.push, 'query': hook_query, 'branch': branch_name, 'sha': sha, 'tag': None, 'changes': {'.gitignore'}},
            spec=HookDetails,
            strict=True
        )
        jenkins_client = mock(spec=app.clients.jenkins_client.JenkinsClient, strict=True)

        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mongo_client,
                                             config=mock())

        # given
        when(github_controller).get_jenkins(jenkins_url).thenReturn(jenkins_client)
        when(collection).find(hook_query).thenReturn(async_iter(cursor))
        when(cursor).__getitem__('job').thenReturn(job_name)
        when(cursor).__getitem__('repository').thenReturn('repo')
        when(cursor).__getitem__('requested_params').thenReturn([])
        when(cursor).__getitem__('jenkins_url').thenReturn(jenkins_url)
        when(cursor).get('branch_restrictions').thenReturn([])
        when(cursor).get('change_restrictions').thenReturn([])
        when(cursor).get('file_restrictions').thenReturn([])
        when(jenkins_client).get_jobs_next_build_number(job_name).thenReturn(async_value(231))
        when(github_controller).can_trigger_job_by_branch(jenkins_url, job_name, branch_name).thenReturn(async_value(True))

        expect(github_controller).trigger_registered_job(jenkins_url, job_name, [], 'repo', sha, branch_name, None, set())

        # when
        await github_controller.trigger_registered_jobs(hook_details)

    async def test__when_changes_are_passed_to_trigger_registered_job__should_be_passed_to_build_job(self):
        jenkins_client = mock(spec=app.clients.jenkins_client.JenkinsClient, strict=True)
        github_client = mock(spec=GithubClient, strict=True)
        github_controller = GithubController(github_client, mock(), mock())

        # given
        when(github_controller).get_jenkins('jenkins_url').thenReturn(jenkins_client)
        when(jenkins_client).get_jobs_next_build_number('job').thenReturn(async_value(3))
        arg_captor = captor()
        expect(jenkins_client).build_jenkins_job('job', arg_captor).thenReturn(async_value(None))
        when(jenkins_client).get_build_info_data('job', 3).thenReturn(async_value(None))
        when(github_client)\
            .create_github_build_status('repo', '123321', 'error', 'url', 'Triggear cant find build jenkins_url:job #3', 'job')\
            .thenReturn(async_value(None))

        # expect
        expect(jenkins_client).get_job_url('job').thenReturn(async_value('url'))

        # when
        await github_controller.trigger_registered_job('jenkins_url', 'job', ['branch', 'changes'], 'repo', '123321', 'branch', '1.0',
                                                       {'README.md', '.gitignore'})

        assert isinstance(arg_captor.value, dict)
        assert arg_captor.value.get('branch') == 'branch'
        changes = arg_captor.value.get('changes').split(',')
        assert 'README.md' in changes
        assert '.gitignore' in changes

    async def test__trigger_registered_jobs__when_change_restrictions_are_not_met__background_task_to_trigger_it_is_not_started(self):
        jenkins_url = 'jenkins_url'
        hook_query = {'repository': 'repo'}
        job_name = 'job'
        sha = '123789'
        branch_name = 'branch'

        cursor = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCommandCursor,
            strict=True
        )
        collection = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCollection,
            strict=True
        )
        mongo_client: motor.motor_asyncio.AsyncIOMotorClient = mock(
            {'registered': {EventTypes.push: collection}},
            spec=motor.motor_asyncio.AsyncIOMotorClient,
            strict=True
        )
        hook_details = mock(
            {'event_type': EventTypes.push, 'query': hook_query, 'branch': branch_name, 'sha': sha, 'tag': None, 'changes': {'README.md'}},
            spec=HookDetails,
            strict=True
        )

        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mongo_client,
                                             config=mock())

        # given
        when(collection).find(hook_query).thenReturn(async_iter(cursor))
        when(cursor).__getitem__('job').thenReturn(job_name)
        when(cursor).__getitem__('jenkins_url').thenReturn(jenkins_url)
        when(cursor).get('branch_restrictions').thenReturn([])
        when(cursor).get('change_restrictions').thenReturn(['.gitignore'])
        when(cursor).get('file_restrictions').thenReturn([])
        expect(app.utilities.background_task, times=0).BackgroundTask()

        # when
        await github_controller.trigger_registered_jobs(hook_details)

    async def test__trigger_registered_jobs__when_branch_restrictions_are_not_met__background_task_to_trigger_it_is_not_started(self):
        hook_query = {'repository': 'repo'}
        job_name = 'job'
        sha = '123789'
        branch_name = 'branch'

        cursor = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCommandCursor,
            strict=True
        )
        collection = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCollection,
            strict=True
        )
        mongo_client: motor.motor_asyncio.AsyncIOMotorClient = mock(
            {'registered': {EventTypes.push: collection}},
            spec=motor.motor_asyncio.AsyncIOMotorClient,
            strict=True
        )
        hook_details = mock(
            {'event_type': EventTypes.push, 'query': hook_query, 'branch': branch_name, 'sha': sha, 'tag': None},
            spec=HookDetails,
            strict=True
        )

        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mongo_client,
                                             config=mock())

        # given
        when(collection).find(hook_query).thenReturn(async_iter(cursor))
        when(cursor).__getitem__('job').thenReturn(job_name)
        when(cursor).__getitem__('jenkins_url').thenReturn('jenkins_url')
        when(cursor).get('branch_restrictions').thenReturn(['master'])
        when(cursor).get('change_restrictions').thenReturn([])
        when(cursor).get('file_restrictions').thenReturn([])
        expect(app.utilities.background_task, times=0).BackgroundTask()

        # when
        await github_controller.trigger_registered_jobs(hook_details)

    async def test__trigger_registered_jobs__when_file_restrictions_are_not_met__background_task_to_trigger_it_is_not_started(self):
        hook_query = {'repository': 'repo'}
        job_name = 'job'
        sha = '123789'
        branch_name = 'branch'

        cursor = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCommandCursor,
            strict=True
        )
        collection = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCollection,
            strict=True
        )
        mongo_client: motor.motor_asyncio.AsyncIOMotorClient = mock(
            {'registered': {EventTypes.push: collection}},
            spec=motor.motor_asyncio.AsyncIOMotorClient,
            strict=True
        )
        hook_details = mock(
            {'event_type': EventTypes.push, 'query': hook_query, 'branch': branch_name, 'sha': sha, 'tag': None},
            spec=HookDetails,
            strict=True
        )

        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mongo_client,
                                             config=mock())

        # given
        when(collection).find(hook_query).thenReturn(async_iter(cursor))
        when(cursor).__getitem__('job').thenReturn(job_name)
        when(cursor).__getitem__('jenkins_url').thenReturn('jenkins_url')
        when(cursor).get('branch_restrictions').thenReturn([])
        when(cursor).get('change_restrictions').thenReturn([])
        when(cursor).get('file_restrictions').thenReturn(['README.md'])
        expect(github_controller).are_files_in_repo(files=['README.md'], hook=hook_details).thenReturn(async_value(False))
        expect(app.utilities.background_task, times=0).BackgroundTask()

        # when
        await github_controller.trigger_registered_jobs(hook_details)

    async def test__when_hook_has_changes__and_they_are_requested__but_not_in_restrictions__should_not_be_passed_to_job(self):
        jenkins_url = 'jenkins_url'
        hook_query = {'repository': 'repo'}
        job_name = 'job'
        sha = '123789'
        branch_name = 'branch'

        cursor = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCommandCursor,
            strict=True
        )
        collection = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCollection,
            strict=True
        )
        mongo_client: motor.motor_asyncio.AsyncIOMotorClient = mock(
            {'registered': {EventTypes.push: collection}},
            spec=motor.motor_asyncio.AsyncIOMotorClient,
            strict=True
        )
        hook_details = mock(
            {'event_type': EventTypes.push, 'query': hook_query, 'branch': branch_name, 'sha': sha, 'tag': None, 'changes': {'README.md'}},
            spec=HookDetails,
            strict=True
        )

        jenkins_client = mock(spec=app.clients.jenkins_client.JenkinsClient, strict=True)
        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mongo_client,
                                             config=mock())

        # given
        when(github_controller).get_jenkins(jenkins_url).thenReturn(jenkins_client)
        when(collection).find(hook_query).thenReturn(async_iter(cursor))
        when(cursor).__getitem__('job').thenReturn(job_name)
        when(cursor).__getitem__('jenkins_url').thenReturn(jenkins_url)
        when(cursor).__getitem__('repository').thenReturn('repo')
        when(cursor).__getitem__('requested_params').thenReturn([])
        when(cursor).get('branch_restrictions').thenReturn([])
        when(cursor).get('change_restrictions').thenReturn([])
        when(cursor).get('file_restrictions').thenReturn([])
        when(jenkins_client).get_jobs_next_build_number(job_name).thenReturn(async_value(231))
        when(github_controller).can_trigger_job_by_branch(jenkins_url, job_name, branch_name).thenReturn(async_value(True))

        expect(github_controller).trigger_registered_job(jenkins_url, job_name, [], 'repo', sha, branch_name, None, set())

        # when
        await github_controller.trigger_registered_jobs(hook_details)

    async def test__trigger_registered_jobs__when_only_some_changes_meets_change_restrictions__only_those_should_be_passed_to_job(self):
        jenkins_url = 'jenkins_url'
        hook_query = {'repository': 'repo'}
        job_name = 'job'
        sha = '123789'
        branch_name = 'branch'

        cursor = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCommandCursor,
            strict=True
        )
        collection = mock(
            spec=motor.motor_asyncio.AsyncIOMotorCollection,
            strict=True
        )
        mongo_client: motor.motor_asyncio.AsyncIOMotorClient = mock(
            {'registered': {EventTypes.push: collection}},
            spec=motor.motor_asyncio.AsyncIOMotorClient,
            strict=True
        )
        hook_details = mock(
            {'event_type': EventTypes.push,
             'query': hook_query,
             'branch': branch_name,
             'sha': sha,
             'tag': None,
             'changes': {'README.md', 'docs/README.md'}},
            spec=HookDetails,
            strict=True
        )

        jenkins_client = mock(spec=app.clients.jenkins_client.JenkinsClient, strict=True)
        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mongo_client,
                                             config=mock())

        # given
        when(github_controller).get_jenkins(jenkins_url).thenReturn(jenkins_client)
        when(collection).find(hook_query).thenReturn(async_iter(cursor))
        when(cursor).__getitem__('job').thenReturn(job_name)
        when(cursor).__getitem__('jenkins_url').thenReturn(jenkins_url)
        when(cursor).__getitem__('repository').thenReturn('repo')
        when(cursor).__getitem__('requested_params').thenReturn([])
        when(cursor).get('branch_restrictions').thenReturn([])
        when(cursor).get('change_restrictions').thenReturn(['docs'])
        when(cursor).get('file_restrictions').thenReturn([])
        when(jenkins_client).get_jobs_next_build_number(job_name).thenReturn(async_value(231))
        when(github_controller).can_trigger_job_by_branch(jenkins_url, job_name, branch_name).thenReturn(async_value(True))

        expect(github_controller).trigger_registered_job(jenkins_url, job_name, [], 'repo', sha, branch_name, None, {'docs/README.md'})

        # when
        await github_controller.trigger_registered_jobs(hook_details)
        await asyncio.sleep(.25)

    async def test__tag_handle__should_not_trigger_jobs__if_sha_means_branch_deletion(self):
        github_controller = GithubController(mock(), mock(), mock())
        hook_data = mock()
        hook_details = mock({'sha': '0000000000000000000000000000000000000000', 'branch': 'master', 'tag': '1.2.3'}, spec=HookDetails, strict=True)

        expect(HookDetailsFactory).get_tag_details(hook_data).thenReturn(hook_details)
        expect(github_controller, times=0).trigger_registered_jobs(hook_details)

        await github_controller.handle_tagged(hook_data)

    async def test__get_jenkins_client__should_setup_client__if_it_does_not_exist(self):
        instance = app.clients.jenkins_client.JenkinsInstanceConfig('jenkins_url', 'user', 'token')
        jenkins_instances = {'jenkins_url': instance}
        config: app.config.triggear_config.TriggearConfig = mock({'jenkins_instances': jenkins_instances,
                                                                  'rerun_time_limit': 2,
                                                                  'triggear_token': 'triggear_token'},
                                                                 spec=app.config.triggear_config.TriggearConfig,
                                                                 strict=True)
        github_controller = GithubController(mock(), mock(), config)

        tested_jenkins_client = github_controller.get_jenkins('jenkins_url')
        async_jenkins_client = tested_jenkins_client.get_async_jenkins()
        assert isinstance(async_jenkins_client, AsyncClient)
        assert async_jenkins_client.base_url == 'jenkins_url'

    async def test__when_jenkins_url_not_found_in_config__should_recreate_triggear_config__and_try_again(self):
        instance = app.clients.jenkins_client.JenkinsInstanceConfig('jenkins_url', 'user', 'token')
        jenkins_instances = {'jenkins_url': instance}
        config: app.config.triggear_config.TriggearConfig = mock({'jenkins_instances': jenkins_instances,
                                                                  'rerun_time_limit': 2,
                                                                  'triggear_token': 'triggear_token'},
                                                                 spec=app.config.triggear_config.TriggearConfig,
                                                                 strict=True)

        expect(os).getenv('CREDS_PATH').thenReturn('./tests/config/example_configs/creds.yaml')
        expect(os).getenv('CONFIG_PATH').thenReturn('./tests/config/example_configs/config.yaml')
        github_controller = GithubController(mock(), mock(), config)

        tested_jenkins_client = github_controller.get_jenkins("https://ci.triggear.com/")
        assert tested_jenkins_client.get_async_jenkins().base_url == "https://ci.triggear.com/"
        assert github_controller.config != config

    async def test__when_jenkins_url_not_found_in_config__and_reading_config_raises__should_keep_previous_config(self):
        instance = app.clients.jenkins_client.JenkinsInstanceConfig('jenkins_url', 'user', 'token')
        jenkins_instances = {'jenkins_url': instance}
        config: app.config.triggear_config.TriggearConfig = mock({'jenkins_instances': jenkins_instances,
                                                                  'rerun_time_limit': 2,
                                                                  'triggear_token': 'triggear_token'},
                                                                 spec=app.config.triggear_config.TriggearConfig,
                                                                 strict=True)

        expect(os).getenv('CREDS_PATH').thenReturn('./tests/config/example_configs/config.yaml')
        expect(app.clients.jenkins_client, times=0).JenkinsClient(any)
        github_controller = GithubController(mock(), mock(), config)

        with pytest.raises(KeyError):
            github_controller.get_jenkins("https://ci.triggear.com/")
        assert github_controller.config == config

    async def test__when_jenkins_url_not_found_in_config__and_config_did_not_change__should_raise_triggear_error(self):
        instance = app.clients.jenkins_client.JenkinsInstanceConfig('jenkins_url', 'user', 'token')
        jenkins_instances = {'jenkins_url': instance}
        config: app.config.triggear_config.TriggearConfig = mock({'jenkins_instances': jenkins_instances,
                                                                  'rerun_time_limit': 2,
                                                                  'triggear_token': 'triggear_token'},
                                                                 spec=app.config.triggear_config.TriggearConfig,
                                                                 strict=True)

        expect(os).getenv('CREDS_PATH').thenReturn('./tests/config/example_configs/creds.yaml')
        expect(os).getenv('CONFIG_PATH').thenReturn('./tests/config/example_configs/config.yaml')
        expect(app.clients.jenkins_client, times=0).JenkinsClient(any)
        github_controller = GithubController(mock(), mock(), config)

        with pytest.raises(TriggearError):
            github_controller.get_jenkins("https://ci.invalid.com/")
        assert github_controller.config == config
