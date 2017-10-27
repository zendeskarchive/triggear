import pytest
from asynctest import MagicMock

from app.controllers.github_controller import GithubController
from app.dto.hook_details import HookDetails
from app.enums.event_types import EventTypes

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("ref, parsed_ref", [
    ('refs/heads/test_branch', 'test_branch'),
    ('refs/tags/test_tag', 'refs/tags/test_tag'),
])
async def test_trigger_jobs_related_to_push(gh_sut: GithubController,
                                            mock_trigger_registered_jobs: MagicMock,
                                            ref,
                                            parsed_ref):
    hook_data = {'after': 'test_sha',
                 'ref': ref,
                 'repository': {'full_name': 'test_repo'},
                 'commits': [{'added': ['c'], 'removed': ['b'], 'modified': ['a']}]}
    expected_hook_details = HookDetails(event_type=EventTypes.push,
                                        repository='test_repo',
                                        branch=parsed_ref,
                                        sha='test_sha')
    expected_hook_details.changes = {'a', 'b', 'c'}

    await gh_sut.handle_push(hook_data)

    mock_trigger_registered_jobs.assert_called_once_with(expected_hook_details)


async def test_when_push_is_branch_delete_should_not_trigger_anything(gh_sut: GithubController,
                                                                      mock_trigger_registered_jobs: MagicMock):
    hook_data = {
        'after': '0000000000000000000000000000000000000000',
        'ref': 'refs/heads/test_branch',
        'repository': {'full_name': 'test_repo'},
        'commits': []
    }

    await gh_sut.handle_push(hook_data)

    mock_trigger_registered_jobs.assert_not_called()
