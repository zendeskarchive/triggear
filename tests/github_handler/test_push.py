import pytest
from asynctest import MagicMock, ANY

from app.github_handler import GithubHandler

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("ref, parsed_ref", [
    ('refs/heads/test_branch', 'test_branch'),
    ('refs/tags/test_tag', 'refs/tags/test_tag'),
])
async def test_trigger_jobs_related_to_push(gh_sut: GithubHandler,
                                            mock_trigger_registered_jobs: MagicMock,
                                            ref,
                                            parsed_ref):
    hook_data = {'after': 'test_sha',
                 'ref': ref,
                 'repository': {'full_name': 'test_repo'}}

    await gh_sut.handle_push(hook_data)

    mock_trigger_registered_jobs.assert_called_once_with(branch=parsed_ref,
                                                         collection=ANY,
                                                         query={'repository': 'test_repo'},
                                                         sha='test_sha')


async def test_when_push_is_branch_delete_should_not_trigger_anything(gh_sut: GithubHandler,
                                                                      mock_trigger_registered_jobs: MagicMock):
    hook_data = {
        'after': '0000000000000000000000000000000000000000',
        'ref': 'refs/heads/test_branch',
        'repository': {'full_name': 'test_repo'}
    }

    await gh_sut.handle_push(hook_data)

    mock_trigger_registered_jobs.assert_not_called()
