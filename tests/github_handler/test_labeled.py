import pytest
from asynctest import MagicMock, ANY

from app.github_handler import GithubHandler

pytestmark = pytest.mark.asyncio


async def test_handling_label_happy_path(gh_sut: GithubHandler,
                                         valid_labeled_data: dict,
                                         mock_trigger_registered_jobs: MagicMock):
    await gh_sut.handle_labeled(valid_labeled_data)

    mock_trigger_registered_jobs.assert_called_once_with(
        branch='test_branch',
        collection=ANY,
        query={'labels': 'test_label', 'repository': 'test_repo'},
        sha='test_sha')
