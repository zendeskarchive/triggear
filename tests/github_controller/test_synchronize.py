import pytest
from asynctest import MagicMock, call
from pytest_mock import MockFixture

from app.controllers.github_controller import GithubController
from app.dto.hook_details import HookDetails
from app.enums.event_types import EventTypes
from app.enums.labels import Labels

pytestmark = pytest.mark.asyncio


async def test_no_valid_labels_found(gh_sut: GithubController,
                                     valid_synchronize_data: dict,
                                     mocker: MockFixture,
                                     mock_trigger_registered_jobs: MagicMock):
    pr_labels_mock = mocker.patch.object(gh_sut, 'get_pr_labels', return_value=['only', 'invalid', 'labels'])

    await gh_sut.handle_synchronize(valid_synchronize_data)

    pr_labels_mock.assert_called_once_with(pr_number='test_pr_number', repository='test_repo')
    mock_trigger_registered_jobs.assert_not_called()


async def test_triggear_sync(gh_sut: GithubController,
                             valid_synchronize_data: dict,
                             mocker: MockFixture,
                             mock_trigger_registered_jobs: MagicMock):
    pr_labels_mock = mocker.patch.object(gh_sut, 'get_pr_labels', return_value=[Labels.label_sync])

    await gh_sut.handle_synchronize(valid_synchronize_data)

    pr_labels_mock.assert_called_once_with(pr_number='test_pr_number', repository='test_repo')
    mock_trigger_registered_jobs.assert_not_called()


async def test_happy_path(gh_sut: GithubController,
                          valid_synchronize_data: dict,
                          mocker: MockFixture,
                          mock_trigger_registered_jobs: MagicMock):
    pr_labels_mock = mocker.patch.object(gh_sut, 'get_pr_labels',
                                         return_value=[Labels.label_sync, 'label_one', 'label_two'])

    await gh_sut.handle_synchronize(valid_synchronize_data)

    pr_labels_mock.assert_called_once_with(pr_number='test_pr_number', repository='test_repo')

    expected_hook_1 = HookDetails(event_type=EventTypes.labeled,
                                  repository='test_repo',
                                  branch='test_branch',
                                  sha='test_sha',
                                  labels='label_one')
    expected_hook_2 = HookDetails(event_type=EventTypes.labeled,
                                  repository='test_repo',
                                  branch='test_branch',
                                  sha='test_sha',
                                  labels='label_two')

    assert mock_trigger_registered_jobs.call_count == 2
    assert mock_trigger_registered_jobs.call_args_list[0] == call(expected_hook_1)
    assert mock_trigger_registered_jobs.call_args_list[1] == call(expected_hook_2)
