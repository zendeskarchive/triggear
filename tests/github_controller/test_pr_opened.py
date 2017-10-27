import pytest
from pytest_mock import MockFixture

from app.controllers.github_controller import GithubController
from app.enums.labels import Labels

pytestmark = pytest.mark.asyncio


async def test_triggear_sync_label_found(gh_sut: GithubController,
                                         mocker: MockFixture):
    repo_labels_mock = mocker.patch.object(gh_sut, 'get_repo_labels', return_value=[Labels.pr_sync])
    set_label_mock = mocker.patch.object(gh_sut, 'set_pr_sync_label')

    await gh_sut.set_sync_label('test_repo_1', 38)

    repo_labels_mock.assert_called_once_with('test_repo_1')
    set_label_mock.assert_called_once_with('test_repo_1', 38)


async def test_triggear_sync_label_not_found(gh_sut: GithubController,
                                             mocker: MockFixture):
    repo_labels_mock = mocker.patch.object(gh_sut, 'get_repo_labels', return_value=['other', 'labels'])
    set_label_mock = mocker.patch.object(gh_sut, 'set_pr_sync_label')

    await gh_sut.set_sync_label('test_repo_1', 38)

    repo_labels_mock.assert_called_once_with('test_repo_1')
    set_label_mock.assert_not_called()
