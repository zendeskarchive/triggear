import pytest
from asynctest import MagicMock, call, ANY
from pytest_mock import MockFixture

from app.github_handler import GithubHandler

pytestmark = pytest.mark.asyncio


async def test_run_test_no_params(gh_sut: GithubHandler,
                                  mocker: MockFixture,
                                  mock_trigger_unregistered_jobs: MagicMock):
    pr_labels_mock = mocker.patch.object(gh_sut, 'get_pr_branch',
                                         return_value='test_branch')
    hook_data = {'comment': {'body': 'Triggear run test'},
                 'repository': {'full_name': 'test_repo'},
                 'issue': {'number': 1}}

    await gh_sut.handle_comment(hook_data)

    pr_labels_mock.assert_called_once_with(1, 'test_repo')
    mock_trigger_unregistered_jobs.assert_called_once_with('test', 'test_branch', {}, 'test_repo', 1)


async def test_run_test_with_params(gh_sut: GithubHandler,
                                    mocker: MockFixture,
                                    mock_trigger_unregistered_jobs: MagicMock):
    pr_labels_mock = mocker.patch.object(gh_sut, 'get_pr_branch',
                                         return_value='test_branch')
    hook_data = {'comment': {'body': 'Triggear run test param1=value1 param2=value2'},
                 'repository': {'full_name': 'test_repo'},
                 'issue': {'number': 1}}

    await gh_sut.handle_comment(hook_data)

    pr_labels_mock.assert_called_once_with(1, 'test_repo')
    mock_trigger_unregistered_jobs.assert_called_once_with('test', 'test_branch',
                                                           {'param1': 'value1', 'param2': 'value2'}, 'test_repo', 1)


async def test_triggear_resync_labels(gh_sut: GithubHandler,
                                      mocker: MockFixture,
                                      mock_trigger_registered_jobs: MagicMock):
    pr_branch_mock = mocker.patch.object(gh_sut, 'get_pr_branch',
                                         return_value='test_branch')
    hook_data = {'comment': {'body': 'Triggear resync labels sha'},
                 'repository': {'full_name': 'test_repo'},
                 'issue': {'number': 1, 'labels': [{'name': 'label1'}, {'name': 'label2'}]}}

    await gh_sut.handle_comment(hook_data)

    pr_branch_mock.assert_called_once_with(1, 'test_repo')
    assert mock_trigger_registered_jobs.call_count == 2
    calls = [call(branch='test_branch',
                  collection=ANY,
                  query={'labels': 'label1', 'repository': 'test_repo'},
                  sha='sha'),
             call(branch='test_branch',
                  collection=ANY,
                  query={'labels': 'label2', 'repository': 'test_repo'},
                  sha='sha')]
    mock_trigger_registered_jobs.assert_has_calls(calls)


async def test_triggear_resync_commit(gh_sut: GithubHandler,
                                      mocker: MockFixture,
                                      mock_trigger_registered_jobs: MagicMock):
    pr_branch_mock = mocker.patch.object(gh_sut, 'get_pr_branch',
                                         return_value='test_branch')
    hook_data = {'comment': {'body': 'Triggear resync commit sha'},
                 'repository': {'full_name': 'test_repo'},
                 'issue': {'number': 1, 'labels': [{'name': 'label1'}, {'name': 'label2'}]}}

    await gh_sut.handle_comment(hook_data)

    pr_branch_mock.assert_called_once_with(1, 'test_repo')
    assert mock_trigger_registered_jobs.call_count == 1
    calls = [call(branch='test_branch',
                  collection=ANY,
                  query={'repository': 'test_repo'},
                  sha='sha')]
    mock_trigger_registered_jobs.assert_has_calls(calls)


async def test_triggear_resync_no_labels(gh_sut: GithubHandler,
                                         mocker: MockFixture,
                                         mock_trigger_registered_jobs: MagicMock):
    pr_labels_mock = mocker.patch.object(gh_sut, 'get_pr_branch',
                                         return_value='test_branch')
    hook_data = {'comment': {'body': 'Triggear resync labels sha'},
                 'repository': {'full_name': 'test_repo'},
                 'issue': {'number': 1, 'labels': []}}

    await gh_sut.handle_comment(hook_data)

    pr_labels_mock.assert_called_once_with(1, 'test_repo')
    mock_trigger_registered_jobs.assert_not_called()


async def test_not_relevant_comment(gh_sut: GithubHandler,
                                    mocker: MockFixture,
                                    mock_trigger_registered_jobs: MagicMock):
    pr_labels_mock = mocker.patch.object(gh_sut, 'get_pr_branch',
                                         return_value='test_branch')
    hook_data = {'comment': {'body': 'Triggear do something'},
                 'repository': {'full_name': 'test_repo'},
                 'issue': {'number': 1, 'labels': []}}

    await gh_sut.handle_comment(hook_data)

    pr_labels_mock.assert_not_called()
    mock_trigger_registered_jobs.assert_not_called()
