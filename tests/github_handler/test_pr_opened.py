import pytest
from asynctest import MagicMock
from pytest_mock import MockFixture

from app.github_handler import GithubHandler

pytestmark = pytest.mark.asyncio


async def test_triggear_sync_label_found(gh_sut: GithubHandler,
                                         valid_pr_opened_data: dict,
                                         mocker: MockFixture,
                                         mock_trigger_registered_jobs: MagicMock):
    repo_labels_mock = mocker.patch.object(gh_sut, 'get_repo_labels', return_value=['triggear-sync'])
    set_label_mock = mocker.patch.object(gh_sut, 'add_triggear_sync_label_to_pr')

    await gh_sut.handle_pr_opened(valid_pr_opened_data)

    repo_labels_mock.assert_called_once_with('test_repo')
    set_label_mock.assert_called_once_with('test_repo', 38)
    mock_trigger_registered_jobs.assert_called_once()


async def test_triggear_sync_label_not_found(gh_sut: GithubHandler,
                                             valid_pr_opened_data: dict,
                                             mocker: MockFixture,
                                             mock_trigger_registered_jobs: MagicMock):
    repo_labels_mock = mocker.patch.object(gh_sut, 'get_repo_labels', return_value=['other', 'labels'])
    set_label_mock = mocker.patch.object(gh_sut, 'add_triggear_sync_label_to_pr')

    await gh_sut.handle_pr_opened(valid_pr_opened_data)

    repo_labels_mock.assert_called_once_with('test_repo')
    set_label_mock.assert_not_called()
    mock_trigger_registered_jobs.assert_called_once()
