import pytest

from app.enums.event_types import EventType
from app.hook_details.hook_details import HookDetails
from app.hook_details.hook_details_factory import HookDetailsFactory

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestHookDetailsFactory:
    async def test__when_pr_opened_hook_is_provided__should_return_proper_hook_details(self):
        hook_data = {'repository': {'full_name': 'repo'}, 'pull_request': {'head': {'ref': 'master', 'sha': '123abc'}}}
        expected_hook_details = HookDetails(EventType.pr_opened,
                                            repository='repo',
                                            branch='master',
                                            sha='123abc')

        assert HookDetailsFactory.get_pr_opened_details(hook_data) == expected_hook_details

    async def test__when_tag_hook_is_provided__should_return_proper_hook_details(self):
        hook_data = {'repository': {'full_name': 'repo'}, 'after': '123qwe', 'ref': 'refs/tags/2.0'}
        expected_hook_details = HookDetails(EventType.tagged,
                                            repository='repo',
                                            branch='',
                                            sha='123qwe')
        expected_hook_details.tag = '2.0'

        assert HookDetailsFactory.get_tag_details(hook_data) == expected_hook_details

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
        expected_hook_details = HookDetails(EventType.push,
                                            repository='repo',
                                            branch='staging',
                                            sha='321123')
        expected_hook_details.changes = ['.gitignore', 'app/controllers/github_controller.py']

        assert HookDetailsFactory.get_push_details(hook_data) == expected_hook_details

    async def test__when_ref_in_push_hook_does_not_start_with_refs_heads__should_be_placed_in_hook_details_as_whole(self):
        hook_data_with_different_ref_format = {'repository': {'full_name': 'repo'}, 'ref': 'staging', 'after': '321123', 'commits': []}
        expected_hook_details = HookDetails(EventType.push,
                                            repository='repo',
                                            branch='staging',
                                            sha='321123')
        assert HookDetailsFactory.get_push_details(hook_data_with_different_ref_format) == expected_hook_details

    async def test__when_labels_hook_is_provided__should_return_proper_hook_details(self):
        hook_data = {'pull_request': {'head': {'repo': {'full_name': 'repo'}, 'ref': 'sandbox', 'sha': '321321'}}, 'label': {'name': 'triggear'}}
        expected_hook_details = HookDetails(EventType.labeled,
                                            repository='repo',
                                            branch='sandbox',
                                            sha='321321',
                                            labels='triggear')

        assert HookDetailsFactory.get_labeled_details(hook_data) == expected_hook_details

    async def test__when_labeled_sync_hook_is_provided__should_return_proper_hook_details_list(self):
        hook_data = {'repository': {'full_name': 'repo'}, 'issue': {'labels': [{'name': 'first_label'}, {'name': 'second_label'}]}}
        expected_hook_details = [
            HookDetails(EventType.labeled,
                        repository='repo',
                        branch='master',
                        sha='123456',
                        labels='first_label'),

            HookDetails(EventType.labeled,
                        repository='repo',
                        branch='master',
                        sha='123456',
                        labels='second_label')
        ]
        assert HookDetailsFactory.get_labeled_sync_details(hook_data, 'master', '123456') == expected_hook_details

    async def test__when_pr_sync_hook_is_provided__should_return_proper_hook_details(self):
        hook_data = {'repository': {'full_name': 'repo'}}
        expected_hook_details = HookDetails(EventType.pr_opened,
                                            repository='repo',
                                            branch='master',
                                            sha='123456')
        assert HookDetailsFactory.get_pr_sync_details(hook_data, 'master', '123456') == expected_hook_details

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
        expected_hook_details = HookDetails(EventType.release,
                                            repository='repo',
                                            branch='',
                                            sha='')
        expected_hook_details.tag = 'theTag'
        expected_hook_details.release_target = '123321'
        expected_hook_details.is_prerelease = True
        assert HookDetailsFactory.get_release_details(hook_data) == expected_hook_details
