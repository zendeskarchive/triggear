import asyncio
from typing import List

import github
import jenkins
import pytest
import motor.motor_asyncio
import aiohttp.web_request
import aiohttp.web
import github.Repository
import github.Issue
import github.Label
import github.PullRequest
import github.PullRequestPart
import github.Commit
import time
from github import GithubException
from mockito import mock, when, expect

from app.config.triggear_config import TriggearConfig
from app.controllers.github_controller import GithubController
from app.dto.hook_details import HookDetails
from app.dto.hook_details_factory import HookDetailsFactory
from app.enums.event_types import EventTypes
from app.exceptions.triggear_timeout_error import TriggearTimeoutError
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

        jenkins_client = mock(
            spec=jenkins.Jenkins,
            strict=True
        )
        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mongo_client,
                                             jenkins_client=jenkins_client,
                                             config=mock())

        # given
        when(collection).find(hook_query).thenReturn(async_iter(cursor))
        when(cursor).__getitem__('job').thenReturn(job_name)
        when(cursor).__getitem__('requested_params').thenReturn(None)
        when(cursor).get('branch_restrictions').thenReturn([])
        when(cursor).get('change_restrictions').thenReturn([])
        when(cursor).get('file_restrictions').thenReturn([])
        when(jenkins_client).get_job_info(job_name).thenRaise(jenkins.NotFoundException())
        when(collection).update_one({'job': job_name, **hook_query}, {'$inc': {'missed_times': 1}}).thenReturn(async_value(any))

        # when
        await github_controller.trigger_registered_jobs(hook_details)

    async def test__when_header_signature_is_not_provided__should_return_401_from_validation(self):
        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mock(),
                                             jenkins_client=mock(),
                                             config=mock())

        request = mock({'headers': {}}, spec=aiohttp.web_request.Request, strict=True)

        assert await github_controller.validate_webhook_secret(request) == (401, 'Unauthorized')

    async def test__when_auth_different_then_sha1_is_received__should_return_501(self):
        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mock(),
                                             jenkins_client=mock(),
                                             config=mock())

        request = mock({'headers': {'X-Hub-Signature': 'different=token'}}, spec=aiohttp.web_request.Request, strict=True)

        assert await github_controller.validate_webhook_secret(request) == (501, "Only SHA1 auth supported")

    async def test__when_invalid_signature_is_sent__should_return_401_from_validation(self):
        triggear_config = mock({'triggear_token': 'api_token', 'rerun_time_limit': 1}, spec=TriggearConfig, strict=True)
        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mock(),
                                             jenkins_client=mock(),
                                             config=triggear_config)

        request = mock({'headers': {'X-Hub-Signature': 'sha1=invalid_signature'}}, spec=aiohttp.web_request.Request, strict=True)

        # given
        when(request).read().thenReturn(async_value(b"valid_data"))

        # when
        assert await github_controller.validate_webhook_secret(request) == (401, 'Unauthorized')

    async def test__when_valid_signature_is_sent__should_return_authorized_from_validation(self):
        triggear_config = mock({'triggear_token': 'api_token', 'rerun_time_limit': 1}, spec=TriggearConfig, strict=True)
        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mock(),
                                             jenkins_client=mock(),
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
        github_controller = GithubController(mock(), mock(), mock(), mock())
        request = mock(spec=aiohttp.web_request.Request, strict=True)

        # given
        when(github_controller).validate_webhook_secret(request).thenReturn(async_value((401, 'Unauthorized')))

        # when
        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        # then
        assert response.status == 401
        assert response.text == 'Unauthorized'

    async def test__when_action_is_none__should_return_ack(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
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
        github_controller = GithubController(mock(), mock(), mock(), mock())
        request = mock({'headers': {}}, spec=aiohttp.web_request.Request, strict=True)

        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(github_controller).get_request_json(request).thenReturn(async_value({'action': 'labeled'}))

        expect(github_controller, times=1).handle_labeled({'action': 'labeled'}).thenReturn(async_value(None))

        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_action_is_synchornized__should_call_handle_synchronized__and_return_200(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        request = mock({'headers': {}}, spec=aiohttp.web_request.Request, strict=True)

        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(github_controller).get_request_json(request).thenReturn(async_value({'action': 'synchronize'}))

        expect(github_controller, times=1).handle_synchronize({'action': 'synchronize'}).thenReturn(async_value(None))

        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_action_is_created__should_call_handle_comment__and_return_200(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        request = mock({'headers': {}}, spec=aiohttp.web_request.Request, strict=True)

        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(github_controller).get_request_json(request).thenReturn(async_value({'action': 'created'}))

        expect(github_controller, times=1).handle_comment({'action': 'created'}).thenReturn(async_value(None))

        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_event_header_is_pull_request__and_action_is_not_pr_opened__should_not_call_handle_pr_opened__and_return_200(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        request = mock({'headers': {'X-GitHub-Event': 'pull_request'}}, spec=aiohttp.web_request.Request, strict=True)

        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(github_controller).get_request_json(request).thenReturn(async_value({'action': 'definitelly_not_opened'}))

        expect(github_controller, times=0).handle_pr_opened({'action': 'definitelly_not_opened'})

        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_event_header_is_pull_request__and_action_is_pr_opened__should_call_handle_pr_opened__and_return_200(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        request = mock({'headers': {'X-GitHub-Event': 'pull_request'}}, spec=aiohttp.web_request.Request, strict=True)

        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(github_controller).get_request_json(request).thenReturn(async_value({'action': 'opened'}))

        expect(github_controller, times=1).handle_pr_opened({'action': 'opened'}).thenReturn(async_value(None))

        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_event_type_is_push__but_ref_does_not_match__neither_push_or_tagged_handle_should_be_called(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        request = mock({'headers': {'X-GitHub-Event': 'push'}}, spec=aiohttp.web_request.Request, strict=True)

        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(github_controller).get_request_json(request).thenReturn(async_value({'ref': 'not_matching'}))

        expect(github_controller, times=0).handle_push({'ref': 'not_matching'})
        expect(github_controller, times=0).handle_tagged({'ref': 'not_matching'})

        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_event_type_is_push__and_ref_has_heads__should_call_handle_push(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        request = mock({'headers': {'X-GitHub-Event': 'push'}}, spec=aiohttp.web_request.Request, strict=True)

        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(github_controller).get_request_json(request).thenReturn(async_value({'ref': 'refs/heads/master'}))

        expect(github_controller, times=1).handle_push({'ref': 'refs/heads/master'}).thenReturn(async_value(None))
        expect(github_controller, times=0).handle_tagged({'ref': 'refs/heads/master'})

        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_event_type_is_push__and_ref_has_tags__should_call_handle_tagged(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        request = mock({'headers': {'X-GitHub-Event': 'push'}}, spec=aiohttp.web_request.Request, strict=True)

        when(github_controller).validate_webhook_secret(request).thenReturn(async_value('AUTHORIZED'))
        when(github_controller).get_request_json(request).thenReturn(async_value({'ref': 'refs/tags/1.0'}))

        expect(github_controller, times=0).handle_push({'ref': 'refs/tags/1.0'})
        expect(github_controller, times=1).handle_tagged({'ref': 'refs/tags/1.0'}).thenReturn(async_value(None))

        response: aiohttp.web.Response = await github_controller.handle_hook(request)

        assert 200 == response.status
        assert 'Hook ACK' == response.text

    async def test__when_handle_pr_opened_is_called__it_should_call_add_sync_label__and_trigger_registered_jobs(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        hook_data = {'repository': 'repo', 'pull_request': {'number': 25}}

        hook_details = mock({'repository': 'repo'}, spec=HookDetails, strict=True)

        # when
        when(github_controller).set_sync_label('repo', pr_number=25).thenReturn(async_value(None))
        when(HookDetailsFactory).get_pr_opened_details(hook_data).thenReturn(hook_details)
        when(github_controller).trigger_registered_jobs(hook_details).thenReturn(async_value(None))

        # then
        await github_controller.handle_pr_opened(hook_data)

    async def test__when_repo_does_not_have_pr_sync_label__it_should_not_be_set(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())

        # when
        when(github_controller).get_repo_labels('repo').thenReturn(['label', 'other-label'])
        expect(github_controller, times=0).set_pr_sync_label_with_retry('repo', 25)

        # then
        await github_controller.set_sync_label('repo', 25)

    async def test__when_repo_has_pr_sync_label__it_should_be_set(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())

        # when
        when(github_controller).get_repo_labels('repo').thenReturn(['label', 'triggear-pr-sync', 'other-label'])
        expect(github_controller, times=1).set_pr_sync_label_with_retry('repo', 25).thenReturn(async_value(None))

        # then
        await github_controller.set_sync_label('repo', 25)

    async def test__when_setting_pr_sync_label__if_github_raises_more_then_3_times__timeout_error_should_be_raised(self):
        github_client: github.Github = mock(spec=github.Github, strict=True)
        github_controller = GithubController(github_client, mock(), mock(), mock())
        github_repository: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        mock(spec=asyncio)

        # when
        when(github_client).get_repo('repo')\
            .thenRaise(github.GithubException(404, 'repo not found'))\
            .thenRaise(github.GithubException(404, 'repo not found'))\
            .thenReturn(github_repository)
        when(github_repository).get_issue(43)\
            .thenRaise(github.GithubException(404, 'repo not found'))
        when(asyncio).sleep(1)\
            .thenReturn(async_value(None))\
            .thenReturn(async_value(None))\
            .thenReturn(async_value(None))

        # then
        with pytest.raises(TriggearTimeoutError) as timeout_error:
            await github_controller.set_pr_sync_label_with_retry('repo', 43)
        assert str(timeout_error.value) == 'Failed to set label on PR #43 in repo repo after 3 retries'

    async def test__when_setting_pr_sync_label__if_github_returns_proper_objects__pr_sync_label_should_be_set(self):
        github_client: github.Github = mock(spec=github.Github, strict=True)
        github_controller = GithubController(github_client, mock(), mock(), mock())
        github_repository: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        github_issue: github.Issue.Issue = mock(spec=github.Issue.Issue, strict=True)

        # given
        when(github_client).get_repo('repo')\
            .thenReturn(github_repository)
        when(github_repository).get_issue(43)\
            .thenReturn(github_issue)
        expect(github_issue, times=1)\
            .add_to_labels('triggear-pr-sync')

        # when
        result = await github_controller.set_pr_sync_label_with_retry('repo', 43)

        # then
        assert result is None

    async def test__when_get_repo_labels_is_called__only_label_names_are_returned(self):
        github_client: github.Github = mock(spec=github.Github, strict=True)
        github_controller = GithubController(github_client, mock(), mock(), mock())
        github_repository: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        label: github.Label.Label = mock({'name': 'label'}, spec=github.Label.Label, strict=True)
        other_label: github.Label.Label = mock({'name': 'other_label'}, spec=github.Label.Label, strict=True)

        # given
        when(github_client).get_repo('repo')\
            .thenReturn(github_repository)
        when(github_repository).get_labels()\
            .thenReturn([label, other_label])

        # when
        result: List[str] = github_controller.get_repo_labels('repo')

        # then
        assert result == ['label', 'other_label']

    async def test__handle_tagged__passes_proper_hook_details_to_trigger_jobs(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        hook_data = {'some': 'data'}
        hook_details = mock(spec=HookDetails, strict=True)

        # given
        when(HookDetailsFactory).get_tag_details(hook_data).thenReturn(hook_details)
        expect(github_controller, times=1).trigger_registered_jobs(hook_details).thenReturn(async_value(None))

        # then
        await github_controller.handle_tagged(hook_data)

    async def test__handle_labeled__passes_proper_hook_details_to_trigger_jobs(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
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
        github_controller = GithubController(mock(), mock(), mock(), mock())

        # expect
        expect(github_controller, times=1).get_pr_labels(repository='repo', pr_number=12).thenReturn(pr_labels)
        expect(github_controller).handle_pr_sync(hook_data, pr_labels).thenReturn(async_value(None))
        expect(github_controller).handle_labeled_sync(hook_data, pr_labels).thenReturn(async_value(None))

        # when
        await github_controller.handle_synchronize(hook_data)

    async def test__handle_pr_sync__should_do_nothing__if_pr_sync_label_is_not_set(self):
        hook_data = {}
        github_controller = GithubController(mock(), mock(), mock(), mock())

        expect(github_controller, times=0).handle_pr_opened(hook_data)

        await github_controller.handle_pr_sync(hook_data, ['label', 'other_label'])

    async def test__handle_pr_sync__should_call_pr_opened_handle__if_pr_sync_label_is_set(self):
        hook_data = {}
        github_controller = GithubController(mock(), mock(), mock(), mock())

        expect(github_controller, times=1).handle_pr_opened(hook_data).thenReturn(async_value(None))

        await github_controller.handle_pr_sync(hook_data, ['label', 'triggear-pr-sync', 'other_label'])

    async def test__handle_synchronize__when_handle_pr_sync_raises_exception__handle_labeled_sync_should_be_called_anyway(self):
        hook_data = {'pull_request': {'number': 12, 'head': {'repo': {'full_name': 'repo'}}}}
        pr_labels = ['label1', 'label2']
        github_controller = GithubController(mock(), mock(), mock(), mock())

        # expect
        expect(github_controller, times=1).get_pr_labels(repository='repo', pr_number=12).thenReturn(pr_labels)
        expect(github_controller, times=1).handle_pr_sync(hook_data, pr_labels).thenRaise(GithubException(404, 'PR not found'))
        expect(github_controller, times=1).handle_labeled_sync(hook_data, pr_labels).thenReturn(async_value(None))

        # when
        with pytest.raises(GithubException):
            await github_controller.handle_synchronize(hook_data)

    async def test__handle_synchronize__when_handle_pr_and_labeled_sync_raise_exceptions__it_should_be_raised_up(self):
        hook_data = {'pull_request': {'number': 12, 'head': {'repo': {'full_name': 'repo'}}}}
        pr_labels = ['label1', 'label2']
        github_controller = GithubController(mock(), mock(), mock(), mock())

        # expect
        expect(github_controller, times=1).get_pr_labels(repository='repo', pr_number=12).thenReturn(pr_labels)
        expect(github_controller, times=1).handle_pr_sync(hook_data, pr_labels).thenRaise(GithubException(404, 'PR not found'))
        expect(github_controller, times=1).handle_labeled_sync(hook_data, pr_labels).thenRaise(jenkins.JenkinsException())

        # when
        with pytest.raises(jenkins.JenkinsException):
            await github_controller.handle_synchronize(hook_data)

    async def test__handle_labeled_sync__when_sync_label_is_not_in_labels__should_abort(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        labels = mock(spec=list)
        labels_list = ['other_label']
        labels_iter = mock(spec=iter(labels_list))

        when(labels).__iter__().thenReturn(labels_iter)
        when(labels_iter).__next__().thenReturn(labels_list[0]).thenRaise(StopIteration())
        expect(labels, times=0).__len__()
        expect(labels, times=0).remove('triggear-label-sync')

        await github_controller.handle_labeled_sync(mock(), labels)

    async def test__handle_labeled_sync__when_sync_label_is_in_labels__but_its_the_only_label__should_abort(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        labels = mock(spec=list)
        labels_list = ['triggear-label-sync']
        labels_iter = mock(spec=iter(labels_list))

        when(labels).__iter__().thenReturn(labels_iter)
        when(labels_iter).__next__().thenReturn(labels_list[0])
        expect(labels, times=1).__len__().thenReturn(1)
        expect(labels, times=0).remove('triggear-label-sync')

        await github_controller.handle_labeled_sync(mock(), labels)

    async def test__handle_labeled_sync__when_sync_label_is_present__should_call_handle_labeled_for_all_other_labels(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        labels = ['triggear-label-sync', 'other-label', 'label']

        expect(github_controller).handle_labeled({'label': {'name': 'other-label'}}).thenReturn(async_value(None))
        expect(github_controller).handle_labeled({'label': {'name': 'label'}}).thenReturn(async_value(None))

        await github_controller.handle_labeled_sync({}, labels)

    async def test__get_pr_labels__should_return_only_label_names(self):
        github_client: github.Github = mock(spec=github.Github, strict=True)
        github_controller = GithubController(github_client, mock(), mock(), mock())
        github_repository: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        label: github.Label.Label = mock({'name': 'label'}, spec=github.Label.Label, strict=True)
        other_label: github.Label.Label = mock({'name': 'other_label'}, spec=github.Label.Label, strict=True)
        github_issue: github.Issue.Issue = mock({'labels': [label, other_label]}, spec=github.Issue.Issue, strict=True)

        when(github_client).get_repo('repo')\
            .thenReturn(github_repository)
        when(github_repository).get_issue(25)\
            .thenReturn(github_issue)

        labels: List[str] = github_controller.get_pr_labels('repo', 25)

        assert ['label', 'other_label'] == labels

    async def test__when_comment_starts_with_triggear_run_prefix__handle_run_comment_should_be_called(self):
        hook_data = {'comment': {'body': 'Triggear run job'}}
        github_controller = GithubController(mock(), mock(), mock(), mock())

        expect(github_controller, times=1).handle_run_comment(hook_data).thenReturn(async_value(None))
        expect(github_controller, times=0).handle_labeled_sync_comment(hook_data)
        expect(github_controller, times=0).handle_pr_sync_comment(hook_data)

        await github_controller.handle_comment(hook_data)

    async def test__when_comment_is_label_sync__should_call_handle_pr_sync(self):
        hook_data = {'comment': {'body': 'triggear-label-sync'}}
        github_controller = GithubController(mock(), mock(), mock(), mock())

        expect(github_controller, times=0).handle_run_comment(hook_data)
        expect(github_controller, times=1).handle_labeled_sync_comment(hook_data).thenReturn(async_value(None))
        expect(github_controller, times=0).handle_pr_sync_comment(hook_data)

        await github_controller.handle_comment(hook_data)

    async def test__when_comment_is_pr_sync__should_call_handle_pr_sync(self):
        hook_data = {'comment': {'body': 'triggear-pr-sync'}}
        github_controller = GithubController(mock(), mock(), mock(), mock())

        expect(github_controller, times=0).handle_run_comment(hook_data)
        expect(github_controller, times=0).handle_labeled_sync_comment(hook_data)
        expect(github_controller, times=1).handle_pr_sync_comment(hook_data).thenReturn(async_value(None))

        await github_controller.handle_comment(hook_data)

    async def test__handle_pr_sync_comment__should_build_hook_details__and_call_trigger_registered_jobs(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        hook_data = mock()
        hook_details = mock(spec=HookDetails, strict=True)

        expect(github_controller).get_comment_branch_and_sha(hook_data).thenReturn(async_value(('branch', 'sha')))
        expect(HookDetailsFactory).get_pr_sync_details(hook_data, 'branch', 'sha').thenReturn(hook_details)
        expect(github_controller).trigger_registered_jobs(hook_details).thenReturn(async_value(None))

        await github_controller.handle_pr_sync_comment(hook_data)

    async def test__get_comment_branch_and_sha__should_return_branch_and_sha__by_parsing_hook_data(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        hook_data = {'repository': {'full_name': 'repo'}, 'issue': {'number': 23}}

        expect(github_controller).get_pr_branch(23, 'repo').thenReturn('master')
        expect(github_controller).get_latest_commit_sha(23, 'repo').thenReturn('123asd')

        branch, sha = await github_controller.get_comment_branch_and_sha(hook_data)

        assert 'master' == branch
        assert '123asd' == sha

    async def test__handle_labeled_sync_comment__should_trigger_registered_jobs__for_all_labeled_sync_details(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
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

    async def test__handle_run_comment__should_run_job_with_no_params__when_no_parameters_are_passed(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        hook_data = {'comment': {'body': 'Triggear run job_name'},
                     'repository': {'full_name': 'repo'},
                     'issue': {'number': 35}}

        expect(github_controller).get_pr_branch(35, 'repo').thenReturn('trunk')
        expect(github_controller, times=1).trigger_unregistered_job('job_name', 'trunk', {}, 'repo', 35).thenReturn(async_value(None))

        await github_controller.handle_run_comment(hook_data)

    async def test__handle_run_comment__should_run_job_with_proper_params__when_parameters_are_passed(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        hook_data = {'comment': {'body': 'Triggear run job_name param=1 other_param=value'},
                     'repository': {'full_name': 'repo'},
                     'issue': {'number': 35}}

        expect(github_controller)\
            .get_pr_branch(35, 'repo')\
            .thenReturn('trunk')
        expect(github_controller, times=1)\
            .trigger_unregistered_job('job_name', 'trunk', {'param': '1', 'other_param': 'value'}, 'repo', 35)\
            .thenReturn(async_value(None))

        await github_controller.handle_run_comment(hook_data)

    async def test__get_latest_commit_sha__should_call_proper_github_entities(self):
        github_client: github.Github = mock(spec=github.Github, strict=True)
        github_repo: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        github_head: github.PullRequestPart.PullRequestPart = mock({'sha': '123zxc'}, spec=github.PullRequestPart, strict=True)
        github_pull_request: github.PullRequest.PullRequest = mock({'head': github_head}, spec=github.PullRequest.PullRequest, strict=True)
        github_controller = GithubController(github_client, mock(), mock(), mock())

        expect(github_client).get_repo('triggear').thenReturn(github_repo)
        expect(github_repo).get_pull(32).thenReturn(github_pull_request)

        sha: str = github_controller.get_latest_commit_sha(32, 'triggear')

        assert '123zxc' == sha

    async def test__get_pr_branch__should_call_proper_github_entities(self):
        github_client: github.Github = mock(spec=github.Github, strict=True)
        github_repo: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        github_head: github.PullRequestPart.PullRequestPart = mock({'ref': '123zxc'}, spec=github.PullRequestPart, strict=True)
        github_pull_request: github.PullRequest.PullRequest = mock({'head': github_head}, spec=github.PullRequest.PullRequest, strict=True)
        github_controller = GithubController(github_client, mock(), mock(), mock())

        expect(github_client).get_repo('triggear').thenReturn(github_repo)
        expect(github_repo).get_pull(32).thenReturn(github_pull_request)

        sha: str = github_controller.get_pr_branch(32, 'triggear')

        assert '123zxc' == sha

    async def test__push_handle__should_not_trigger_jobs__if_sha_means_branch_deletion(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        hook_data = mock()
        hook_details = mock({'sha': '0000000000000000000000000000000000000000', 'branch': 'master'}, spec=HookDetails, strict=True)

        expect(HookDetailsFactory).get_push_details(hook_data).thenReturn(hook_details)
        expect(github_controller, times=0).trigger_registered_jobs(hook_details)

        await github_controller.handle_push(hook_data)

    async def test__push_handle__should_trigger_jobs__if_sha_is_not_about_branch_deletion(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        hook_data = mock()
        hook_details = mock({'sha': '1234567890qwertyuiopasdfghjklzxcvbnmnbvc', 'branch': 'master'}, spec=HookDetails, strict=True)

        expect(HookDetailsFactory).get_push_details(hook_data).thenReturn(hook_details)
        expect(github_controller, times=1).trigger_registered_jobs(hook_details).thenReturn(async_value(None))

        await github_controller.handle_push(hook_data)

    async def test__are_files_in_repo__should_return_false_on_any_missing_file(self):
        github_client: github.Github = mock(spec=github.Github, strict=True)
        github_repo: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        github_controller = GithubController(github_client, mock(), mock(), mock())

        hook_details = mock({'repository': 'repo', 'sha': '123qwe', 'branch': 'master'}, spec=HookDetails, strict=True)
        files = ['app/main.py', '.gitignore']

        expect(github_client).get_repo('repo').thenReturn(github_repo)
        expect(github_repo).get_file_contents(path='app/main.py', ref='123qwe').thenReturn(None)
        expect(github_repo).get_file_contents(path='.gitignore', ref='123qwe').thenRaise(GithubException(404, 'File not found'))

        assert not await github_controller.are_files_in_repo(files, hook_details)

    async def test__are_files_in_repo__should_return_true_if_all_files_are_in_repo(self):
        github_client: github.Github = mock(spec=github.Github, strict=True)
        github_repo: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        github_controller = GithubController(github_client, mock(), mock(), mock())

        hook_details = mock({'repository': 'repo', 'sha': None, 'branch': 'master'}, spec=HookDetails, strict=True)
        files = ['app/main.py', '.gitignore']

        expect(github_client).get_repo('repo').thenReturn(github_repo)
        expect(github_repo).get_file_contents(path='app/main.py', ref='master').thenReturn(None)
        expect(github_repo).get_file_contents(path='.gitignore', ref='master').thenReturn(None)

        assert await github_controller.are_files_in_repo(files, hook_details)

    async def test__create_pr_comment__calls_proper_github_entities(self):
        github_client: github.Github = mock(spec=github.Github, strict=True)
        github_repo: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        github_issue: github.Issue.Issue = mock(spec=github.Issue.Issue, strict=True)
        github_controller = GithubController(github_client, mock(), mock(), mock())

        expect(github_client).get_repo('triggear').thenReturn(github_repo)
        expect(github_repo).get_issue(23).thenReturn(github_issue)
        expect(github_issue).create_comment(body='Comment to send')

        github_controller.create_pr_comment(23, 'triggear', 'Comment to send')

    async def test__get_build_info__returns_none__in_case_of_timeout(self):
        jenkins_client = mock(spec=jenkins.Jenkins, strict=True)
        github_controller = GithubController(mock(), mock(), jenkins_client, mock())
        mock(time)
        mock(asyncio)

        when(time).monotonic()\
            .thenReturn(0)\
            .thenReturn(15)\
            .thenReturn(31)
        when(asyncio).sleep(1).thenReturn(async_value(None))
        expect(jenkins_client).get_build_info('job', 23).thenRaise(jenkins.NotFoundException())

        assert await github_controller.get_build_info('job', 23) is None

    async def test__get_build_info__returns_build_info__in_case_of_no_timeout(self):
        jenkins_client = mock(spec=jenkins.Jenkins, strict=True)
        github_controller = GithubController(mock(), mock(), jenkins_client, mock())
        mock(time)
        mock(asyncio)

        when(time).monotonic()\
            .thenReturn(0)\
            .thenReturn(15)
        expect(jenkins_client).get_build_info('job', 23).thenReturn({'some': 'values'})

        assert {'some': 'values'} == await github_controller.get_build_info('job', 23)

    async def test__is_job_building__returns_none__when_build_info_is_none(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())

        expect(github_controller).get_build_info('job', 12).thenReturn(async_value(None))

        assert await github_controller.is_job_building('job', 12) is None

    async def test__is_job_building__returns_status__when_build_info_is_valid(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())

        expect(github_controller).get_build_info('job', 12).thenReturn(async_value({'building': True}))

        assert await github_controller.is_job_building('job', 12)

    async def test__build_jenkins_job__calls_jenkins_properly(self):
        jenkins_client: jenkins.Jenkins = mock(spec=jenkins.Jenkins, strict=True)
        github_controller = GithubController(mock(), mock(), jenkins_client, mock())

        expect(jenkins_client).build_job('job', parameters={'param': 'value'})

        github_controller.build_jenkins_job('job', {'param': 'value'})

    async def test__create_github_build_status__calls_github_client_properly(self):
        github_client: github.Github = mock(spec=github.Github, strict=True)
        github_repo: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        github_commit: github.Commit.Commit = mock(spec=github.Commit.Commit, strict=True)
        github_controller = GithubController(github_client, mock(), mock(), mock())

        expect(github_client).get_repo('repo').thenReturn(github_repo)
        expect(github_repo).get_commit('123456').thenReturn(github_commit)
        expect(github_commit).create_status(state='pending',
                                            target_url='http://example.com',
                                            description='whatever you need',
                                            context='job')

        await github_controller.create_github_build_status('repo', '123456', 'pending', 'http://example.com', 'whatever you need', 'job')

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

    async def test__get_requested_parameters__should_return_files_joined_with_coma__when_changes_are_requested(self):
        assert {'branch': 'master', 'changes': 'README.md,.gitignore'} == await GithubController.get_requested_parameters_values(
            ['branch', 'changes'],
            'master',
            '123321',
            '1.0',
            changes=['README.md', '.gitignore']
        )

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
        github_controller = GithubController(mock(), mongo_client, mock(), mock())
        mock(time)

        when(time).time().thenReturn(1)
        when(collection).find_one({"branch": 'master', "job": 'job'}).thenReturn(async_value(None))
        expect(collection).insert_one({'branch': 'master', 'job': 'job', 'timestamp': 1}).thenReturn(async_value(None))

        assert await github_controller.can_trigger_job_by_branch('job', 'master')

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
        triggear_config = mock({'rerun_time_limit': 20, 'triggear_token': 'token'}, spec=TriggearConfig)
        github_controller = GithubController(mock(), mongo_client, mock(), triggear_config)
        mock(time)

        when(collection).find_one({"branch": 'master', "job": 'job'}).thenReturn(async_value(found_run))
        when(found_run).__getitem__('timestamp').thenReturn(3)
        when(time).time().thenReturn(23)
        expect(collection).replace_one(found_run, {'branch': 'master', 'job': 'job', 'timestamp': 23}).thenReturn(async_value(None))

        assert await github_controller.can_trigger_job_by_branch('job', 'master')

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
        triggear_config = mock({'rerun_time_limit': 20, 'triggear_token': 'token'}, spec=TriggearConfig)
        github_controller = GithubController(mock(), mongo_client, mock(), triggear_config)
        mock(time)

        when(collection).find_one({"branch": 'master', "job": 'job'}).thenReturn(async_value(found_run))
        when(found_run).__getitem__('timestamp').thenReturn(3)
        when(time).time().thenReturn(22)
        expect(collection, times=0).replace_one(found_run, {'branch': 'master', 'job': 'job', 'timestamp': 23}).thenReturn(async_value(None))

        assert not await github_controller.can_trigger_job_by_branch('job', 'master')

    async def test__trigger_unregistered_job__should_not_build__when_cannot_be_run_on_branch(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())

        when(github_controller).can_trigger_job_by_branch('job', 'staging').thenReturn(async_value(False))
        expect(github_controller, times=0).get_jobs_next_build_number('job')
        expect(github_controller, times=0).build_jenkins_job('job', {'branch': 'staging'})

        assert await github_controller.trigger_unregistered_job('job', 'staging', {'branch': 'staging'}, 'triggear', 21) is None

    async def test__trigger_unregistered_job__should_return__when_build_job_raises_exception(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())

        when(github_controller).can_trigger_job_by_branch('job', 'staging').thenReturn(async_value(True))
        expect(github_controller, times=1).get_jobs_next_build_number('job').thenReturn(2)
        expect(github_controller, times=1).build_jenkins_job('job', {'branch': 'staging'}).thenRaise(jenkins.JenkinsException())
        expect(github_controller, times=0).is_job_building('job', 2).thenRaise(jenkins.JenkinsException())

        assert await github_controller.trigger_unregistered_job('job', 'staging', {'branch': 'staging'}, 'triggear', 21) is None

    async def test__trigger_unregistered_job__should_not_create_comment__when_build_info_is_none(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        mock(asyncio)

        when(github_controller).can_trigger_job_by_branch('job', 'staging').thenReturn(async_value(True))
        expect(github_controller, times=1).get_jobs_next_build_number('job').thenReturn(2)
        expect(github_controller, times=1).build_jenkins_job('job', {'branch': 'staging'})
        expect(github_controller, times=2).is_job_building('job', 2).thenReturn(async_value(True)).thenReturn(async_value(False))
        expect(asyncio).sleep(1).thenReturn(async_value(None))
        expect(github_controller).get_build_info('job', 2).thenReturn(async_value(None))
        expect(github_controller, times=0).get_final_build_state(None).thenReturn(async_value(None))

        assert await github_controller.trigger_unregistered_job('job', 'staging', {'branch': 'staging'}, 'triggear', 21) is None

    async def test__trigger_unregistered_job__should_create_comment__when_build_info_is_not_none(self):
        github_controller = GithubController(mock(), mock(), mock(), mock())
        mock(asyncio)
        build_info = {'url': 'http://jenkins.com'}

        when(github_controller).can_trigger_job_by_branch('job', 'staging').thenReturn(async_value(True))
        expect(github_controller, times=1).get_jobs_next_build_number('job').thenReturn(2)
        expect(github_controller, times=1).build_jenkins_job('job', {'branch': 'staging'})
        expect(github_controller, times=2).is_job_building('job', 2).thenReturn(async_value(True)).thenReturn(async_value(False))
        expect(asyncio).sleep(1).thenReturn(async_value(None))
        expect(github_controller).get_build_info('job', 2).thenReturn(async_value(build_info))
        expect(github_controller, times=1).get_final_build_state(build_info).thenReturn(async_value('success'))
        expect(github_controller, times=1).get_final_build_description(build_info).thenReturn(async_value('build succeeded'))
        expect(github_controller, times=1).create_pr_comment(21, 'triggear',
                                                             body='Job job finished with status success - build succeeded (http://jenkins.com)')

        assert await github_controller.trigger_unregistered_job('job', 'staging', {'branch': 'staging'}, 'triggear', 21) is None

    async def test__trigger_registered_job__when_build_job_raises__error_status_should_be_created(self):
        requested_parameters = ['branch']
        branch = 'staging'
        sha = '123123'
        tag = '1.0'
        repository = 'repo'
        job_url = 'http://example.com'

        github_controller = GithubController(mock(), mock(), mock(), mock())

        expect(github_controller)\
            .get_requested_parameters_values(requested_parameters, branch, sha, tag)\
            .thenReturn(async_value({'branch': branch}))
        expect(github_controller) \
            .get_jobs_next_build_number('job')\
            .thenReturn(321)
        when(github_controller)\
            .build_jenkins_job('job', {'branch': branch})\
            .thenRaise(jenkins.JenkinsException())

        expect(github_controller)\
            .get_job_url('job')\
            .thenReturn(async_value(job_url))
        expect(github_controller)\
            .create_github_build_status(repository, sha, 'error', job_url,
                                        "Job job did not accept requested parameters dict_keys(['branch'])!", 'job')\
            .thenReturn(async_value(None))

        await github_controller.trigger_registered_job('job', requested_parameters, repository, sha, branch, tag)

    async def test__trigger_registered_job__when_build_info_is_none__proper_error_status_should_be_created(self):
            requested_parameters = ['branch']
            branch = 'staging'
            sha = '123123'
            repository = 'repo'
            job_url = 'http://example.com'
            job_name = 'job'

            github_controller = GithubController(mock(), mock(), mock(), mock())

            mock(asyncio)

            expect(github_controller) \
                .get_requested_parameters_values(requested_parameters, branch, sha, None) \
                .thenReturn(async_value({'branch': branch}))
            expect(github_controller) \
                .get_jobs_next_build_number(job_name) \
                .thenReturn(321)
            when(github_controller) \
                .build_jenkins_job(job_name, {'branch': branch})
            expect(github_controller, times=2) \
                .get_build_info(job_name, 321) \
                .thenReturn(async_value(None))

            expect(github_controller) \
                .get_job_url(job_name) \
                .thenReturn(async_value(job_url))
            expect(github_controller) \
                .create_github_build_status(repository, sha, "error", job_url, 'Triggear cant find build job #321', job_name) \
                .thenReturn(async_value(None))

            await github_controller.trigger_registered_job(job_name, requested_parameters, repository, sha, branch)

    async def test__trigger_registered_job__when_build_info_is_not_none__proper_pending_and_final_status_should_be_created(self):
        requested_parameters = ['branch']
        branch = 'staging'
        sha = '123123'
        repository = 'repo'
        job_url = 'http://example.com'
        build_url = job_url + '/job/321'
        job_name = 'job'

        github_controller = GithubController(mock(), mock(), mock(), mock())

        mock(asyncio)

        expect(github_controller)\
            .get_requested_parameters_values(requested_parameters, branch, sha, None)\
            .thenReturn(async_value({'branch': branch}))
        expect(github_controller) \
            .get_jobs_next_build_number(job_name)\
            .thenReturn(321)
        when(github_controller)\
            .build_jenkins_job(job_name, {'branch': branch})
        build_info = {'url': build_url}
        expect(github_controller, times=2)\
            .get_build_info(job_name, 321)\
            .thenReturn(async_value(build_info))\
            .thenReturn(async_value({**build_info, 'finished': 'yes'}))

        expect(github_controller)\
            .create_github_build_status(repository, sha, "pending", build_url, "build in progress", job_name)\
            .thenReturn(async_value(None))

        when(asyncio)\
            .sleep(1)\
            .thenReturn(async_value(None))
        expect(github_controller, times=2)\
            .is_job_building(job_name, 321)\
            .thenReturn(async_value(True))\
            .thenReturn(async_value(False))

        expect(github_controller) \
            .get_final_build_state({**build_info, 'finished': 'yes'})\
            .thenReturn(async_value('success'))
        expect(github_controller) \
            .get_final_build_description({**build_info, 'finished': 'yes'})\
            .thenReturn(async_value('build succeeded'))

        expect(github_controller)\
            .create_github_build_status(repository, sha, "success", build_url, "build succeeded", job_name)\
            .thenReturn(async_value(None))

        await github_controller.trigger_registered_job(job_name, requested_parameters, repository, sha, branch)

    @pytest.mark.parametrize("job_info, expected_url", [
        ({'url': 'http://example.com'}, 'http://example.com'),
        ({}, None),
    ])
    async def test__get_job_url__properly_calls_jenkins_client(self, job_info, expected_url):
        jenkins_client: jenkins.Jenkins = mock(spec=jenkins.Jenkins, strict=True)
        github_controller = GithubController(mock(), mock(), jenkins_client, mock())

        expect(jenkins_client).get_job_info('job').thenReturn(job_info)

        assert expected_url == await github_controller.get_job_url('job')

    async def test__trigger_registered_jobs__when_job_exists__background_task_to_trigger_it_is_started(self):
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
                                             jenkins_client=mock(),
                                             config=mock())

        # given
        when(collection).find(hook_query).thenReturn(async_iter(cursor))
        when(cursor).__getitem__('job').thenReturn(job_name)
        when(cursor).__getitem__('repository').thenReturn('repo')
        when(cursor).__getitem__('requested_params').thenReturn([])
        when(cursor).get('branch_restrictions').thenReturn([])
        when(cursor).get('change_restrictions').thenReturn([])
        when(cursor).get('file_restrictions').thenReturn([])
        when(github_controller).get_jobs_next_build_number(job_name).thenReturn(231)
        when(github_controller).can_trigger_job_by_branch(job_name, branch_name).thenReturn(async_value(True))

        expect(github_controller).trigger_registered_job(job_name, [], 'repo', sha, branch_name, None)

        # when
        await github_controller.trigger_registered_jobs(hook_details)

    async def test__trigger_registered_jobs__when_change_restrictions_are_not_met__background_task_to_trigger_it_is_not_started(self):
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
            {'event_type': EventTypes.push, 'query': hook_query, 'branch': branch_name, 'sha': sha, 'tag': None, 'changes': ['README.md']},
            spec=HookDetails,
            strict=True
        )

        github_controller = GithubController(github_client=mock(),
                                             mongo_client=mongo_client,
                                             jenkins_client=mock(),
                                             config=mock())

        # given
        when(collection).find(hook_query).thenReturn(async_iter(cursor))
        when(cursor).__getitem__('job').thenReturn(job_name)
        when(cursor).get('branch_restrictions').thenReturn([])
        when(cursor).get('change_restrictions').thenReturn(['.gitignore'])
        when(cursor).get('file_restrictions').thenReturn([])
        expect(github_controller, times=0).get_jobs_next_build_number(job_name).thenReturn(231)

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
                                             jenkins_client=mock(),
                                             config=mock())

        # given
        when(collection).find(hook_query).thenReturn(async_iter(cursor))
        when(cursor).__getitem__('job').thenReturn(job_name)
        when(cursor).get('branch_restrictions').thenReturn(['master'])
        when(cursor).get('change_restrictions').thenReturn([])
        when(cursor).get('file_restrictions').thenReturn([])
        expect(github_controller, times=0).get_jobs_next_build_number(job_name).thenReturn(231)

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
                                             jenkins_client=mock(),
                                             config=mock())

        # given
        when(collection).find(hook_query).thenReturn(async_iter(cursor))
        when(cursor).__getitem__('job').thenReturn(job_name)
        when(cursor).get('branch_restrictions').thenReturn([])
        when(cursor).get('change_restrictions').thenReturn([])
        when(cursor).get('file_restrictions').thenReturn(['README.md'])
        expect(github_controller).are_files_in_repo(files=['README.md'], hook=hook_details).thenReturn(async_value(False))
        expect(github_controller, times=0).get_jobs_next_build_number(job_name).thenReturn(231)

        # when
        await github_controller.trigger_registered_jobs(hook_details)
