import pytest
from asynctest import MagicMock, ANY, call
from pytest_mock import MockFixture

from app.github_handler import GithubHandler
from app.labels import Labels

pytestmark = pytest.mark.asyncio


async def test_no_valid_labels_found(gh_sut: GithubHandler,
                                     valid_synchronize_data: dict,
                                     mocker: MockFixture,
                                     mock_trigger_registered_jobs: MagicMock):
    pr_labels_mock = mocker.patch.object(gh_sut, 'get_pr_labels', return_value=['only', 'invalid', 'labels'])

    await gh_sut.handle_synchronize(valid_synchronize_data)

    pr_labels_mock.assert_called_once_with('test_pr_number', 'test_repo')
    mock_trigger_registered_jobs.assert_not_called()


async def test_triggear_sync(gh_sut: GithubHandler,
                             valid_synchronize_data: dict,
                             mocker: MockFixture,
                             mock_trigger_registered_jobs: MagicMock):
    pr_labels_mock = mocker.patch.object(gh_sut, 'get_pr_labels', return_value=[Labels.label_sync])

    await gh_sut.handle_synchronize(valid_synchronize_data)

    pr_labels_mock.assert_called_once_with('test_pr_number', 'test_repo')
    mock_trigger_registered_jobs.assert_not_called()


async def test_happy_path(gh_sut: GithubHandler,
                          valid_synchronize_data: dict,
                          mocker: MockFixture,
                          mock_trigger_registered_jobs: MagicMock):
    pr_labels_mock = mocker.patch.object(gh_sut, 'get_pr_labels',
                                         return_value=[Labels.label_sync, 'label_one', 'label_two'])

    await gh_sut.handle_synchronize(valid_synchronize_data)

    pr_labels_mock.assert_called_once_with('test_pr_number', 'test_repo')
    assert mock_trigger_registered_jobs.call_count == 2
    calls = [call(branch='test_branch',
                  collection=ANY,
                  query={'labels': 'label_one', 'repository': 'test_repo'},
                  sha='test_sha'),
             call(branch='test_branch',
                  collection=ANY,
                  query={'labels': 'label_two', 'repository': 'test_repo'},
                  sha='test_sha')]
    mock_trigger_registered_jobs.assert_has_calls(calls)
