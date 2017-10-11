import pytest
from asynctest import MagicMock
from pytest_mock import MockFixture

from app.github_handler import GithubHandler

pytestmark = pytest.mark.asyncio


async def test_triggear_sync_label_found(gh_sut: GithubHandler,
                                         mocker: MockFixture,
                                         mock_collection_with_branch_restriction: MagicMock):
    repo_labels_mock = mocker.patch.object(gh_sut, 'get_repo_labels', return_value=['triggear-sync'])
    set_label_mock = mocker.patch.object(gh_sut, 'add_triggear_sync_label_to_pr')

    await gh_sut.set_sync_label(mock_collection_with_branch_restriction, {'repository': 'test_repo_1'}, 38)

    repo_labels_mock.assert_called_once_with('test_repo_1')
    set_label_mock.assert_called_once_with('test_repo_1', 38)


async def test_triggear_sync_label_not_found(gh_sut: GithubHandler,
                                             mocker: MockFixture,
                                             mock_collection_with_branch_restriction: MagicMock):
    repo_labels_mock = mocker.patch.object(gh_sut, 'get_repo_labels', return_value=['other', 'labels'])
    set_label_mock = mocker.patch.object(gh_sut, 'add_triggear_sync_label_to_pr')

    await gh_sut.set_sync_label(mock_collection_with_branch_restriction, {'repository': 'test_repo_1'}, 38)

    repo_labels_mock.assert_called_once_with('test_repo_1')
    set_label_mock.assert_not_called()
