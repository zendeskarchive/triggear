from typing import List

import pytest

from app.enums.event_types import EventType
from app.hook_details.hook_details_factory import HookDetailsFactory
from app.hook_details.labeled_hook_details import LabeledHookDetails
from app.hook_details.pr_opened_hook_details import PrOpenedHookDetails
from app.hook_details.push_hook_details import PushHookDetails
from app.hook_details.release_hook_details import ReleaseHookDetails
from app.hook_details.tag_hook_details import TagHookDetails

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestHookDetailsFactory:
    async def test__when_pr_opened_hook_is_provided__should_return_proper_hook_details(self):
        hook_data = {'repository': {'full_name': 'repo'}, 'pull_request': {'head': {'ref': 'master', 'sha': '123abc'}}}

        hook_details = HookDetailsFactory.get_pr_opened_details(hook_data)
        assert isinstance(hook_details, PrOpenedHookDetails)
        assert EventType.PR_OPENED == hook_details.get_event_type()
        assert 'master' == hook_details.branch
        assert '123abc' == hook_details.sha
        assert 'repo' == hook_details.repository

    async def test__when_tag_hook_is_provided__should_return_proper_hook_details(self):
        hook_data = {'repository': {'full_name': 'repo'}, 'after': '123qwe', 'ref': 'refs/tags/2.0'}
        hook_details = HookDetailsFactory.get_tag_details(hook_data)
        assert isinstance(hook_details, TagHookDetails)
        assert hook_details.get_event_type() == EventType.TAGGED
        assert hook_details.repository == 'repo'
        assert hook_details.tag == '2.0'
        assert hook_details.sha == '123qwe'

    async def test__when_push_hook_is_provided__should_return_proper_hook_details(self):
        hook_data = {'repository': {'full_name': 'repo'}, 'ref': 'refs/heads/staging', 'after': '321123',
                     'commits': [
                         {
                             'added': ['.gitignore'],
                             'removed': ['app/controllers/github_controller.py'],
                             'modified': []
                         },
                         {
                             'added': [],
                             'removed': [],
                             'modified': ['app/controllers/github_controller.py', '.gitignore']
                         },
                     ]}
        hook_details = HookDetailsFactory.get_push_details(hook_data)
        assert isinstance(hook_details, PushHookDetails)
        assert hook_details.get_event_type() == EventType.PUSH
        assert hook_details.repository == 'repo'
        assert hook_details.branch == 'staging'
        assert hook_details.sha == '321123'
        assert hook_details.changes == {'.gitignore', 'app/controllers/github_controller.py'}

    async def test__when_ref_in_push_hook_does_not_start_with_refs_heads__should_be_placed_in_hook_details_as_whole(self):
        hook_data_with_different_ref_format = {'repository': {'full_name': 'repo'}, 'ref': 'staging', 'after': '321123', 'commits': []}
        hook_details = HookDetailsFactory.get_push_details(hook_data_with_different_ref_format)
        assert hook_details.branch == 'staging'

    async def test__when_labels_hook_is_provided__should_return_proper_hook_details(self):
        hook_data = {'pull_request': {'head': {'repo': {'full_name': 'repo'}, 'ref': 'sandbox', 'sha': '321321'}}, 'label': {'name': 'triggear'}}
        hook_details = HookDetailsFactory.get_labeled_details(hook_data)
        assert isinstance(hook_details, LabeledHookDetails)
        assert hook_details.get_event_type() == EventType.PR_LABELED
        assert hook_details.repository == 'repo'
        assert hook_details.branch == 'sandbox'
        assert hook_details.sha == '321321'
        assert hook_details.label == 'triggear'

    async def test__when_labeled_sync_hook_is_provided__should_return_proper_hook_details_list(self):
        hook_data = {'repository': {'full_name': 'repo'}, 'issue': {'labels': [{'name': 'first_label'}, {'name': 'second_label'}]}}
        hook_details: List[LabeledHookDetails] = HookDetailsFactory.get_labeled_sync_details(hook_data, 'master', '123456')
        assert len(hook_details) == 2
        first_hook_details = hook_details[0]
        assert isinstance(first_hook_details, LabeledHookDetails)
        assert first_hook_details.get_event_type() == EventType.PR_LABELED
        assert first_hook_details.repository == 'repo'
        assert first_hook_details.branch == 'master'
        assert first_hook_details.sha == '123456'
        assert first_hook_details.label == 'first_label'
        second_hook_details = hook_details[1]
        assert isinstance(second_hook_details, LabeledHookDetails)
        assert second_hook_details.get_event_type() == EventType.PR_LABELED
        assert second_hook_details.repository == 'repo'
        assert second_hook_details.branch == 'master'
        assert second_hook_details.sha == '123456'
        assert second_hook_details.label == 'second_label'

    async def test__when_pr_sync_hook_is_provided__should_return_proper_hook_details(self):
        hook_data = {'repository': {'full_name': 'repo'}}
        hook_details = HookDetailsFactory.get_pr_sync_details(hook_data, 'master', '123456')
        assert isinstance(hook_details, PrOpenedHookDetails)
        assert hook_details.get_event_type() == EventType.PR_OPENED
        assert hook_details.repository == 'repo'
        assert hook_details.branch == 'master'
        assert hook_details.sha == '123456'

    async def test__when_release_hook_is_provided__should_return_proper_hook_details(self):
        hook_data = {
            "release": {
                "tag_name": "theTag",
                "target_commitish": "123321",
                "prerelease": True
            },
            "repository": {
                "full_name": "repo",
            }
        }
        hook_details = HookDetailsFactory.get_release_details(hook_data)
        assert isinstance(hook_details, ReleaseHookDetails)
        assert hook_details.repository == 'repo'
        assert hook_details.tag == 'theTag'
        assert hook_details.release_target == '123321'
        assert hook_details.is_prerelease
