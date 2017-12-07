import asynctest
import github
import pytest
from pytest_mock import MockFixture

from app.controllers.github_controller import GithubController
from app.enums.labels import Labels

pytestmark = pytest.mark.asyncio


async def test_triggear_sync_label_found(gh_sut: GithubController,
                                         mocker: MockFixture):
    repo_labels_mock = mocker.patch.object(gh_sut, 'get_repo_labels', return_value=[Labels.pr_sync])
    with asynctest.patch.object(gh_sut, 'set_pr_sync_label') as set_label_mock:
        await gh_sut.set_sync_label('test_repo_1', 38)

        repo_labels_mock.assert_called_once_with('test_repo_1')
        set_label_mock.assert_called_once_with('test_repo_1', 38)


async def test_triggear_sync_label_should_survive_two_gh_exceptions_when_looking_for_pr(gh_sut: GithubController,
                                         mocker: MockFixture):
    repo_labels_mock = mocker.patch.object(gh_sut, 'get_repo_labels', return_value=[Labels.pr_sync])
    with asynctest.patch.object(gh_sut, 'set_pr_sync_label', side_effect=[github.GithubException(404, 'Not found'),
                                                                          github.GithubException(404, 'Not found'),
                                                                          None]) as set_label_mock:
        await gh_sut.set_sync_label('test_repo_1', 38)

        repo_labels_mock.assert_called_once_with('test_repo_1')
        assert set_label_mock.call_count == 3


async def test_triggear_sync_label_should_raise_timeout_error_when_pr_is_not_found_after_3_retries(gh_sut: GithubController,
                                         mocker: MockFixture):
    repo_labels_mock = mocker.patch.object(gh_sut, 'get_repo_labels', return_value=[Labels.pr_sync])
    with asynctest.patch.object(gh_sut, 'set_pr_sync_label', side_effect=[github.GithubException(404, 'Not found'),
                                                                          github.GithubException(404, 'Not found'),
                                                                          github.GithubException(404, 'Not found'),
                                                                          None]) as set_label_mock:
        with pytest.raises(TimeoutError):
            await gh_sut.set_sync_label('test_repo_1', 38)

            repo_labels_mock.assert_called_once_with('test_repo_1')
            assert set_label_mock.call_count == 3


async def test_triggear_sync_label_not_found(gh_sut: GithubController,
                                             mocker: MockFixture):
    repo_labels_mock = mocker.patch.object(gh_sut, 'get_repo_labels', return_value=['other', 'labels'])
    set_label_mock = mocker.patch.object(gh_sut, 'set_pr_sync_label')

    await gh_sut.set_sync_label('test_repo_1', 38)

    repo_labels_mock.assert_called_once_with('test_repo_1')
    set_label_mock.assert_not_called()
