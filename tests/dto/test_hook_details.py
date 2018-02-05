import pytest

from app.enums.event_types import EventType
from app.hook_details.hook_details import HookDetails

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestHookDetails:
    async def test__hook_details__should_be_comparable(self):
        hook_details = HookDetails(event_type=EventType.push,
                                   repository='repo',
                                   branch='master',
                                   sha='sha',
                                   anything='other')

        different_hook_details = HookDetails(event_type=EventType.push,
                                             repository='repo',
                                             branch='master',
                                             sha='sha',
                                             anything='different')

        same_hook_details = HookDetails(event_type=EventType.push,
                                        repository='repo',
                                        branch='master',
                                        sha='sha',
                                        anything='other')

        assert hook_details != different_hook_details
        assert hook_details == same_hook_details
        assert not hook_details == different_hook_details
        assert not hook_details != same_hook_details

    async def test__hook_details__should_provide_proper_description(self):
        hook_details = HookDetails(event_type=EventType.push,
                                   repository='repo',
                                   branch='master',
                                   sha='sha',
                                   anything='other')

        assert str(hook_details) == "HookDetails(eventType: push, " \
                                    "repo: repo, branch: master, " \
                                    "sha: sha, tag: None, changes: set(), " \
                                    "query: {'repository': 'repo', 'anything': 'other'}, " \
                                    "release_target: None, is_prerelease: None)"

    async def test__hook_details__should_provide_proper_field_getters_and_setters(self):
        hook_details = HookDetails(event_type=EventType.push,
                                   repository='repo',
                                   branch='master',
                                   sha='sha',
                                   anything='other')

        assert hook_details.event_type == 'push'
        assert hook_details.repository == 'repo'
        assert hook_details.branch == 'master'
        assert hook_details.sha == 'sha'
        assert hook_details.query == {'anything': 'other', 'repository': 'repo'}

        assert hook_details.tag is None
        assert hook_details.changes == set()

        hook_details.tag = '1.0'
        hook_details.changes = ['README.md', '.gitignore', '.gitignore']

        assert hook_details.tag == '1.0'
        assert hook_details.changes == {'README.md', '.gitignore'}
