import asyncio
import logging

import pytest
import aiohttp.web_request
import aiohttp.web
from mockito import mock, when, expect, captor

from app.clients.github_client import GithubClient
from app.controllers.github_controller import GithubController
from app.data_objects.github_event import GithubEvent
from app.hook_details.hook_details import HookDetails
from app.hook_details.hook_details_factory import HookDetailsFactory
from app.hook_details.labeled_hook_details import LabeledHookDetails
from app.hook_details.pr_opened_hook_details import PrOpenedHookDetails
from app.hook_details.push_hook_details import PushHookDetails
from app.hook_details.release_hook_details import ReleaseHookDetails
from app.hook_details.tag_hook_details import TagHookDetails
from app.triggear_heart import TriggearHeart
from tests.async_mockito import async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestGithubController:
    async def test__when_github_event_matches_no_handler__should_return_no_task(self):
        github_controller = GithubController(mock(), mock(), mock())

        expect(github_controller, times=0).handle_labeled(any)
        expect(github_controller, times=0).handle_synchronize(any)
        expect(github_controller, times=0).handle_comment(any)
        expect(github_controller, times=0).handle_pr_opened(any)
        expect(github_controller, times=0).handle_push(any)
        expect(github_controller, times=0).handle_tagged(any)
        expect(github_controller, times=0).handle_release(any)

        assert github_controller.get_event_handler_task({}, GithubEvent('pull_request', 'closed', None)) is None

    async def test__when_github_event__matches_labeled__should_return_proper_handler(self):
        github_controller = GithubController(mock(), mock(), mock())

        expect(github_controller, times=1).handle_labeled({}).thenReturn('mock')

        assert 'mock' == github_controller.get_event_handler_task({}, GithubEvent('pull_request', 'labeled', None))

    async def test__when_github_event__matches_synchronize__should_return_proper_handler(self):
        github_controller = GithubController(mock(), mock(), mock())

        expect(github_controller, times=1).handle_synchronize({}).thenReturn('mock')

        assert 'mock' == github_controller.get_event_handler_task({}, GithubEvent('pull_request', 'synchronize', None))

    async def test__when_github_event__matches_comment__should_return_proper_handler(self):
        github_controller = GithubController(mock(), mock(), mock())

        expect(github_controller, times=1).handle_comment({}).thenReturn('mock')

        assert 'mock' == github_controller.get_event_handler_task({}, GithubEvent('issue_comment', 'created', None))

    async def test__when_github_event__matches_pr_opened__should_return_proper_handler(self):
        github_controller = GithubController(mock(), mock(), mock())

        expect(github_controller, times=1).handle_pr_opened({}).thenReturn('mock')

        assert 'mock' == github_controller.get_event_handler_task({}, GithubEvent('pull_request', 'opened', None))

    async def test__when_github_event__matches_push__should_return_proper_handler(self):
        github_controller = GithubController(mock(), mock(), mock())

        assert github_controller.get_event_handler_task({}, GithubEvent('push', None, 'refs/heads/master')) is None

    async def test__when_github_event__matches_tagged__should_return_proper_handler(self):
        github_controller = GithubController(mock(), mock(), mock())

        expect(github_controller, times=1).handle_tagged({}).thenReturn('mock')

        assert 'mock' == github_controller.get_event_handler_task({}, GithubEvent('push', None, 'refs/tags/1.0'))

    async def test__when_github_event__matches_release__should_return_proper_handler(self):
        github_controller = GithubController(mock(), mock(), mock())

        assert github_controller.get_event_handler_task({}, GithubEvent('release', 'published', None)) is None

    async def test__when_event_handle_is_not_none__should_be_scheduled_as_task(self):
        mock(asyncio, strict=True)

        github_controller = GithubController(mock(), mock(), mock())
        request: aiohttp.web_request.Request = mock({'headers': {'X-GitHub-Event': 'push'}}, spec=aiohttp.web_request.Request, strict=True)
        event_handler = mock(strict=True)
        event_loop = mock(strict=True)

        github_event_captor = captor()

        when(request).json().thenReturn(async_value({'action': 'action', 'ref': '123321'}))
        when(github_controller).get_event_handler_task({'action': 'action', 'ref': '123321'}, github_event_captor).thenReturn(event_handler)

        expect(asyncio).get_event_loop().thenReturn(event_loop)
        expect(event_loop).create_task(event_handler)

        await github_controller.handle_hook(request)

        github_event: GithubEvent = github_event_captor.value
        assert isinstance(github_event, GithubEvent)
        assert github_event.event_header == 'push'
        assert github_event.action == 'action'
        assert github_event.ref == '123321'

    async def test__when_event_handle_none__nothing_should_be_scheduled_on_event_loop(self):
        mock(asyncio, strict=True)

        github_controller = GithubController(mock(), mock(), mock())
        request: aiohttp.web_request.Request = mock({'headers': {'X-GitHub-Event': 'push'}}, spec=aiohttp.web_request.Request, strict=True)
        event_loop = mock(strict=True)

        github_event_captor = captor()

        when(request).json().thenReturn(async_value({'action': 'action', 'ref': '123321'}))
        when(github_controller).get_event_handler_task({'action': 'action', 'ref': '123321'}, github_event_captor).thenReturn(None)

        expect(asyncio, times=0).get_event_loop().thenReturn(event_loop)

        await github_controller.handle_hook(request)

        github_event: GithubEvent = github_event_captor.value
        assert isinstance(github_event, GithubEvent)
        assert github_event.event_header == 'push'
        assert github_event.action == 'action'
        assert github_event.ref == '123321'

    async def test__handle_release_calls_triggear_heart(self):
        mock(HookDetailsFactory)

        data = mock(strict=True)
        hook_details: ReleaseHookDetails = mock(spec=ReleaseHookDetails, strict=True)
        triggear_heart: TriggearHeart = mock(spec=TriggearHeart, strict=True)
        github_controller = GithubController(mock(), mock(), triggear_heart)

        expect(HookDetailsFactory).get_release_details(data).thenReturn(hook_details)
        expect(triggear_heart).trigger_registered_jobs(hook_details).thenReturn(async_value(None))

        await github_controller.handle_release(data)

    async def test__handle_pr_opened_should_set_sync_label__and_call_triggear_heart(self):
        mock(HookDetailsFactory)

        data = {'pull_request': {'number': 34}}
        hook_details: PrOpenedHookDetails = mock({'repository': 'triggear'}, spec=PrOpenedHookDetails, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        triggear_heart: TriggearHeart = mock(spec=TriggearHeart, strict=True)
        github_controller = GithubController(mock(), github_client, triggear_heart)

        expect(HookDetailsFactory).get_pr_opened_details(data).thenReturn(hook_details)
        expect(github_client).set_sync_label(repo='triggear', number=34).thenReturn(async_value(None))
        expect(triggear_heart).trigger_registered_jobs(hook_details).thenReturn(async_value(None))

        await github_controller.handle_pr_opened(data)

    async def test__handle_tagged_calls_triggear_heart__when_sha_is_not_deletion(self):
        mock(HookDetailsFactory)

        data = mock(strict=True)
        hook_details: TagHookDetails = mock({'sha': '123321'}, spec=TagHookDetails, strict=True)
        triggear_heart: TriggearHeart = mock(spec=TriggearHeart, strict=True)
        github_controller = GithubController(mock(), mock(), triggear_heart)

        expect(HookDetailsFactory).get_tag_details(data).thenReturn(hook_details)
        expect(triggear_heart).trigger_registered_jobs(hook_details).thenReturn(async_value(None))

        await github_controller.handle_tagged(data)

    async def test__handle_tagged_does_not_call_triggear_heart__when_sha_is_deletion(self):
        mock(HookDetailsFactory)
        mock(logging)

        data = mock(strict=True)
        hook_details: TagHookDetails = mock({'tag': '1.0', 'sha': '0000000000000000000000000000000000000000'}, spec=TagHookDetails, strict=True)
        triggear_heart: TriggearHeart = mock(spec=TriggearHeart, strict=True)
        github_controller = GithubController(mock(), mock(), triggear_heart)

        expect(HookDetailsFactory).get_tag_details(data).thenReturn(hook_details)
        expect(triggear_heart, times=0).trigger_registered_jobs(hook_details).thenReturn(async_value(None))
        expect(logging).warning('Tag 1.0 was deleted as SHA was zeros only!')

        await github_controller.handle_tagged(data)

    async def test__handle_labeled_calls_triggear_heart(self):
        mock(HookDetailsFactory)

        data = mock(strict=True)
        hook_details: LabeledHookDetails = mock(spec=LabeledHookDetails, strict=True)
        triggear_heart: TriggearHeart = mock(spec=TriggearHeart, strict=True)
        github_controller = GithubController(mock(), mock(), triggear_heart)

        expect(HookDetailsFactory).get_labeled_details(data).thenReturn(hook_details)
        expect(triggear_heart).trigger_registered_jobs(hook_details).thenReturn(async_value(None))

        await github_controller.handle_labeled(data)

    async def test__handle_push_calls_triggear_heart__when_sha_is_not_deletion(self):
        mock(HookDetailsFactory)

        data = mock(strict=True)
        hook_details: PushHookDetails = mock({'sha': '123321'}, spec=PushHookDetails, strict=True)
        triggear_heart: TriggearHeart = mock(spec=TriggearHeart, strict=True)
        github_controller = GithubController(mock(), mock(), triggear_heart)

        expect(HookDetailsFactory).get_push_details(data).thenReturn(hook_details)
        expect(triggear_heart).trigger_registered_jobs(hook_details).thenReturn(async_value(None))

        await github_controller.handle_push(data)

    async def test__handle_push_does_not_call_triggear_heart__when_sha_is_deletion(self):
        mock(HookDetailsFactory)
        mock(logging)

        data = mock(strict=True)
        hook_details: PushHookDetails = mock({'branch': 'master', 'sha': '0000000000000000000000000000000000000000'},
                                             spec=PushHookDetails, strict=True)
        triggear_heart: TriggearHeart = mock(spec=TriggearHeart, strict=True)
        github_controller = GithubController(mock(), mock(), triggear_heart)

        expect(HookDetailsFactory).get_push_details(data).thenReturn(hook_details)
        expect(triggear_heart, times=0).trigger_registered_jobs(hook_details).thenReturn(async_value(None))
        expect(logging).warning('Branch master was deleted as SHA was zeros only!')

        await github_controller.handle_push(data)

    async def test__handle_pr_sync_calls_triggear_heart(self):
        mock(HookDetailsFactory)

        data = mock(strict=True)
        hook_details: PrOpenedHookDetails = mock(spec=PrOpenedHookDetails, strict=True)
        triggear_heart: TriggearHeart = mock(spec=TriggearHeart, strict=True)
        github_controller = GithubController(mock(), mock(), triggear_heart)

        expect(HookDetailsFactory).get_pr_sync_details(data, 'master', '123321').thenReturn(hook_details)
        expect(triggear_heart).trigger_registered_jobs(hook_details).thenReturn(async_value(None))

        await github_controller.handle_pr_sync_comment(data, 'master', '123321')

    async def test__handle_synchronize__calls_labeled_and_pr_sync_in_asyncio_gather(self):
        mock(asyncio, strict=True)

        pr_sync_handle_coro = mock(strict=True)
        labeled_sync_handle_coro = mock(strict=True)
        data = {'pull_request': {'head': {'repo': {'full_name': 'triggear'}}, 'number': 23}}
        pr_labels = ['some', 'labels']
        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        triggear_heart: TriggearHeart = mock(spec=TriggearHeart, strict=True)
        github_controller = GithubController(mock(), github_client, triggear_heart)

        expect(github_client).get_pr_labels(repo='triggear', number=23).thenReturn(async_value(pr_labels))
        expect(github_controller).handle_pr_sync(data, pr_labels).thenReturn(pr_sync_handle_coro)
        expect(github_controller).handle_labeled_sync(data, pr_labels).thenReturn(labeled_sync_handle_coro)
        expect(asyncio).gather(pr_sync_handle_coro, labeled_sync_handle_coro)

        await github_controller.handle_synchronize(data)

    async def test__handle_pr_sync__calls_handle_pr_opened__when_triggear_pr_sync_label_is_set(self):
        data = mock(strict=True)
        pr_labels = ['triggear-pr-sync', 'other-label']
        triggear_heart: TriggearHeart = mock(spec=TriggearHeart, strict=True)
        github_controller = GithubController(mock(), mock(), triggear_heart)

        expect(github_controller).handle_pr_opened(data).thenReturn(async_value(None))

        await github_controller.handle_pr_sync(data, pr_labels)

    async def test__handle_pr_sync__does_not_call_handle_pr_opened__when_triggear_pr_sync_label_is_not_set(self):
        data = mock(strict=True)
        pr_labels = ['dummy-label', 'other-label']
        triggear_heart: TriggearHeart = mock(spec=TriggearHeart, strict=True)
        github_controller = GithubController(mock(), mock(), triggear_heart)

        expect(github_controller, times=0).handle_pr_opened(data).thenReturn(async_value(None))

        await github_controller.handle_pr_sync(data, pr_labels)

    async def test__when_issue_comment_is_pr_sync__should_call_pr_sync__and_not_labeled_sync(self):
        data = {'comment': {'body': 'triggear-pr-sync'}}

        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        triggear_heart: TriggearHeart = mock(spec=TriggearHeart, strict=True)
        github_controller = GithubController(mock(), github_client, triggear_heart)

        expect(github_client).get_pr_comment_branch_and_sha(data).thenReturn(async_value(('master', '123321')))
        expect(github_controller).handle_pr_sync_comment(data, 'master', '123321').thenReturn(async_value(None))
        expect(github_controller, times=0).handle_labeled_sync_comment(data, 'master', '123321')

        await github_controller.handle_comment(data)

    async def test__when_issue_comment_is_label_sync__should_call_label_sync__and_not_pr_sync(self):
        data = {'comment': {'body': 'triggear-label-sync'}}

        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        triggear_heart: TriggearHeart = mock(spec=TriggearHeart, strict=True)
        github_controller = GithubController(mock(), github_client, triggear_heart)

        expect(github_client).get_pr_comment_branch_and_sha(data).thenReturn(async_value(('master', '123321')))
        expect(github_controller, times=0).handle_pr_sync_comment(data, 'master', '123321')
        expect(github_controller).handle_labeled_sync_comment(data, 'master', '123321').thenReturn(async_value(None))

        await github_controller.handle_comment(data)

    async def test__handle_labeled_sync_comment__should_trigger_jobs_for_all_returned_hook_details(self):
        mock(HookDetailsFactory)

        branch = 'staging'
        sha = '321123'
        data = mock(strict=True)

        first_hook_details = mock(spec=HookDetails, strict=True)
        second_hook_details = mock(spec=HookDetails, strict=True)
        triggear_heart: TriggearHeart = mock(spec=TriggearHeart, strict=True)
        github_controller = GithubController(mock(), mock(), triggear_heart)

        expect(HookDetailsFactory).get_labeled_sync_details(data, head_branch=branch, head_sha=sha)\
            .thenReturn([first_hook_details, second_hook_details])
        expect(triggear_heart).trigger_registered_jobs(first_hook_details).thenReturn(async_value(None))
        expect(triggear_heart).trigger_registered_jobs(second_hook_details).thenReturn(async_value(None))

        await github_controller.handle_labeled_sync_comment(data, branch, sha)

    async def test__handle_labeled_sync__calls_handle_labeled__for_every_label(self):
        data = {}
        triggear_heart: TriggearHeart = mock(spec=TriggearHeart, strict=True)
        github_controller = GithubController(mock(), mock(), triggear_heart)

        expect(github_controller, times=1).handle_labeled({'label': {'name': 'other-label'}}).thenReturn(async_value(None))
        expect(github_controller, times=1).handle_labeled({'label': {'name': 'dummy-label'}}).thenReturn(async_value(None))

        await github_controller.handle_labeled_sync(data, ['triggear-label-sync', 'other-label', 'dummy-label'])
