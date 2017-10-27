import pytest
from asynctest import MagicMock

from app.controllers.github_controller import GithubController
from app.dto.hook_details import HookDetails
from app.enums.event_types import EventTypes

pytestmark = pytest.mark.asyncio


async def test_handling_label_happy_path(gh_sut: GithubController,
                                         valid_labeled_data: dict,
                                         mock_trigger_registered_jobs: MagicMock):
    await gh_sut.handle_labeled(valid_labeled_data)

    mock_trigger_registered_jobs.assert_called_once_with(HookDetails(event_type=EventTypes.labeled,
                                                                     repository='test_repo',
                                                                     branch='test_branch',
                                                                     sha='test_sha',
                                                                     labels='test_label'))
