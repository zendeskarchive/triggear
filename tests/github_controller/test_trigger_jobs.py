import time

import jenkins
import pytest
from asynctest import MagicMock, call, patch
from pytest_mock import MockFixture

from app.controllers.github_controller import GithubController
from app.dto.hook_details import HookDetails
from app.enums.event_types import EventTypes

pytestmark = pytest.mark.asyncio


async def test_trigger_empty_register_collection(gh_sut: GithubController,
                                                 mock_empty_collection,
                                                 mock_trigger_registered_job: MagicMock):
    # noinspection PyUnresolvedReferences
    with patch.object(gh_sut, '_GithubController__get_collection_for_hook_type',
                      return_value=mock_empty_collection) as get_collection_method:
        hook_details = HookDetails(event_type=EventTypes.push,
                                   repository='test_repo',
                                   branch='test_branch',
                                   sha='test_sha')
        await gh_sut.trigger_registered_jobs(hook_details)
        mock_trigger_registered_job.assert_not_called()
        get_collection_method.assert_called_once_with(EventTypes.push)


async def test_cannot_trigger_registered_job_by_branch(gh_sut: GithubController,
                                                       mock_two_elem_collection: MagicMock,
                                                       mock_trigger_registered_job: MagicMock,
                                                       mock_cannot_trigger_job_by_branch: MagicMock):
    # noinspection PyUnresolvedReferences
    with patch.object(gh_sut, '_GithubController__get_collection_for_hook_type',
                      return_value=mock_two_elem_collection) as get_collection_method:
        hook_details = HookDetails(event_type=EventTypes.push,
                                   repository='test_repo',
                                   branch='test_branch',
                                   sha='test_sha')
        await gh_sut.trigger_registered_jobs(hook_details)
        assert mock_cannot_trigger_job_by_branch.call_count == 2
        calls = [call('test_job_2', 'test_branch'),
                 call('test_job_1', 'test_branch')]
        mock_cannot_trigger_job_by_branch.assert_has_calls(calls)
        mock_trigger_registered_job.assert_not_called()
        get_collection_method.assert_called_once_with(EventTypes.push)


async def test_can_trigger_two_jobs(gh_sut: GithubController,
                                    mock_two_elem_collection: MagicMock,
                                    mock_trigger_registered_job: MagicMock,
                                    mock_can_trigger_job_by_branch: MagicMock,
                                    mocker: MockFixture):
    mock_get_next_build = mocker.patch.object(gh_sut, 'get_jobs_next_build_number', return_value=2)

    # noinspection PyUnresolvedReferences
    with patch.object(gh_sut, '_GithubController__get_collection_for_hook_type',
                      return_value=mock_two_elem_collection) as get_collection_method:
        hook_details = HookDetails(event_type=EventTypes.push,
                                   repository='test_repo_1',
                                   branch='test_branch',
                                   sha='test_sha')

        await gh_sut.trigger_registered_jobs(hook_details)
        time.sleep(0.1)

        assert mock_get_next_build.call_count == 2
        assert mock_can_trigger_job_by_branch.call_count == 2
        calls = [call('test_job_2', 'test_branch'),
                 call('test_job_1', 'test_branch')]
        mock_can_trigger_job_by_branch.assert_has_calls(calls)
        assert mock_trigger_registered_job.call_count == 2
        calls = [call('test_job_1',
                      [],
                      'test_repo_1',
                      'test_sha',
                      'test_branch',
                      None),
                 call('test_job_2',
                      ['branch'],
                      'test_repo_2',
                      'test_sha',
                      'test_branch',
                      None)]
        mock_trigger_registered_job.assert_has_calls(calls, any_order=True)
        get_collection_method.assert_called_once_with(EventTypes.push)


async def test_one_of_jobs_not_found(gh_sut: GithubController,
                                     mock_two_elem_collection: MagicMock,
                                     mock_trigger_registered_job: MagicMock,
                                     mock_can_trigger_job_by_branch: MagicMock,
                                     mocker: MockFixture):
    mock_get_next_build = mocker.patch.object(gh_sut, 'get_jobs_next_build_number',
                                              side_effect=[3, jenkins.NotFoundException])

    # noinspection PyUnresolvedReferences
    with patch.object(gh_sut, '_GithubController__get_collection_for_hook_type',
                      return_value=mock_two_elem_collection) as get_collection_method:
        hook_details = HookDetails(event_type=EventTypes.push,
                                   repository='test_repo_1',
                                   branch='test_branch',
                                   sha='test_sha')
        await gh_sut.trigger_registered_jobs(hook_details)
        time.sleep(0.3)

        assert mock_get_next_build.call_count == 2
        mock_can_trigger_job_by_branch.assert_called_once_with('test_job_2', 'test_branch')
        mock_trigger_registered_job.assert_called_once_with('test_job_2',
                                                            ['branch'],
                                                            'test_repo_2',
                                                            'test_sha',
                                                            'test_branch',
                                                            None)
        get_collection_method.assert_called_once_with(EventTypes.push)


async def test_unregistered_job_cant_be_called(gh_sut: GithubController,
                                               mocker: MockFixture,
                                               mock_cannot_trigger_job_by_branch: MagicMock):
    mock_get_next_build: MagicMock = mocker.patch.object(gh_sut, 'get_jobs_next_build_number')
    mock_build_job: MagicMock = mocker.patch.object(gh_sut, 'build_jenkins_job')

    await gh_sut.trigger_unregistered_job(job_name='test_job',
                                          pr_branch='test_branch',
                                          job_params={'param': 'value'},
                                          repository='test_repo',
                                          pr_number=1)
    mock_cannot_trigger_job_by_branch.assert_called_once()
    mock_get_next_build.assert_not_called()
    mock_build_job.assert_not_called()


async def test_job_do_not_accept_requested_params(gh_sut: GithubController,
                                                  mocker: MockFixture,
                                                  mock_can_trigger_job_by_branch: MagicMock):
    mock_get_next_build: MagicMock = mocker.patch.object(gh_sut, 'get_jobs_next_build_number')
    mock_build_job: MagicMock = mocker.patch.object(gh_sut, 'build_jenkins_job', side_effect=jenkins.JenkinsException)
    mock_is_job_building: MagicMock = mocker.patch.object(gh_sut, 'is_job_building')

    await gh_sut.trigger_unregistered_job(job_name='test_job',
                                          pr_branch='test_branch',
                                          job_params={'param': 'value'},
                                          repository='test_repo',
                                          pr_number=1)
    mock_can_trigger_job_by_branch.assert_called_once()
    mock_get_next_build.assert_called_once_with('test_job')
    mock_build_job.assert_called_once_with('test_job', {'param': 'value'})
    mock_is_job_building.assert_not_called()


@pytest.mark.parametrize("job_result, expected_state, expected_description", [
    ('SUCCESS', 'success', 'build succeeded'),
    ('FAILURE', 'failure', 'build failed'),
    ('ERROR', 'error', 'build error'),
    ('INVALID', 'error', 'build error'),

])
async def test_unregistered_job_was_run(gh_sut: GithubController,
                                        mocker: MockFixture,
                                        mock_can_trigger_job_by_branch: MagicMock,
                                        mock_is_job_building: MagicMock,
                                        job_result,
                                        expected_state,
                                        expected_description):
    mock_get_next_build: MagicMock = mocker.patch.object(gh_sut, 'get_jobs_next_build_number', return_value=1)
    mock_build_job: MagicMock = mocker.patch.object(gh_sut, 'build_jenkins_job')
    mock_create_pr_comment: MagicMock = mocker.patch.object(gh_sut, 'create_pr_comment')

    # noinspection PyUnresolvedReferences
    with patch.object(gh_sut, 'get_build_info',
                      return_value={'result': job_result, 'url': 'test_url'}) as mock_get_build_info:
        await gh_sut.trigger_unregistered_job(job_name='test_job',
                                              pr_branch='test_branch',
                                              job_params={'param': 'value'},
                                              repository='test_repo',
                                              pr_number=1)

        mock_can_trigger_job_by_branch.assert_called_once()
        mock_get_next_build.assert_called_once_with('test_job')
        mock_build_job.assert_called_once_with('test_job', {'param': 'value'})
        assert mock_is_job_building.call_count == 2
        calls = [call('test_job', 1),
                 call('test_job', 1)]
        mock_is_job_building.assert_has_calls(calls)
        mock_get_build_info.assert_called_once_with('test_job', 1)
        mock_create_pr_comment.assert_called_once_with(
            1, 'test_repo',
            body=f"Job test_job finished with status {expected_state} - {expected_description} (test_url)"
        )


# noinspection PyUnresolvedReferences
async def test_trigger_registered_job(gh_sut: GithubController,
                                      mocker: MockFixture):
    mock_get_next_build: MagicMock = mocker.patch.object(gh_sut, 'get_jobs_next_build_number', return_value=1)
    with patch.object(gh_sut, 'build_jenkins_job') as mock_build_jenkins_job:
        with patch.object(gh_sut, 'is_job_building', return_value=False) as mock_is_job_building:
            await gh_sut.trigger_registered_job('job_name',
                                                ['branch', 'sha'],
                                                'test_repo',
                                                'test_sha',
                                                'test_branch')
            mock_is_job_building.assert_called_once()
            mock_get_next_build.assert_called_once()
            mock_build_jenkins_job.assert_called_once()


# noinspection PyUnresolvedReferences
async def test_trigger_registered_job_build_not_found(gh_sut: GithubController,
                                                      mocker: MockFixture):
    mock_get_next_build: MagicMock = mocker.patch.object(gh_sut, 'get_jobs_next_build_number', return_value=1)
    with patch.object(gh_sut, 'build_jenkins_job') as mock_build_jenkins_job:
        with patch.object(gh_sut, 'get_build_info', return_value=None) as mock_get_build_info:
            with patch.object(gh_sut, 'is_job_building', return_value=None) as mock_is_job_building:
                await gh_sut.trigger_registered_job('job_name',
                                                    ['branch', 'sha'],
                                                    'test_repo',
                                                    'test_sha',
                                                    'test_branch')
                mock_is_job_building.assert_not_called()
                mock_get_build_info.assert_called_once()
                mock_get_next_build.assert_called_once()
                mock_build_jenkins_job.assert_called_once()


async def test_push_hook_does_not_meet_branch_restriction(gh_sut: GithubController,
                                                          mock_collection_with_branch_restriction: MagicMock,
                                                          mock_trigger_registered_job: MagicMock,
                                                          mock_can_trigger_job_by_branch: MagicMock):
    # noinspection PyUnresolvedReferences
    with patch.object(gh_sut, '_GithubController__get_collection_for_hook_type',
                      return_value=mock_collection_with_branch_restriction) as get_collection_method:
        hook_details = HookDetails(event_type=EventTypes.push,
                                   repository='test_repo_1',
                                   branch='test_branch',
                                   sha='test_sha')
        await gh_sut.trigger_registered_jobs(hook_details)
        time.sleep(0.3)

        mock_can_trigger_job_by_branch.assert_not_called()
        mock_trigger_registered_job.assert_not_called()
        get_collection_method.assert_called_once_with(EventTypes.push)


async def test_push_hook_meets_branch_restriction(gh_sut: GithubController,
                                                  mock_collection_with_branch_restriction: MagicMock,
                                                  mock_trigger_registered_job: MagicMock,
                                                  mock_can_trigger_job_by_branch: MagicMock):
    # noinspection PyUnresolvedReferences
    with patch.object(gh_sut, '_GithubController__get_collection_for_hook_type',
                      return_value=mock_collection_with_branch_restriction) as get_collection_method:
        hook_details = HookDetails(event_type=EventTypes.push,
                                   repository='test_repo_1',
                                   branch='master',
                                   sha='test_sha')
        await gh_sut.trigger_registered_jobs(hook_details)
        time.sleep(0.3)

        mock_can_trigger_job_by_branch.assert_called_once_with('test_job_1', 'master')
        mock_trigger_registered_job.assert_called_once_with('test_job_1',
                                                            [],
                                                            'test_repo_1',
                                                            'test_sha',
                                                            'master',
                                                            None)
        get_collection_method.assert_called_once_with(EventTypes.push)


async def test_push_hook_does_not_meet_change_restriction(gh_sut: GithubController,
                                                          mock_collection_with_change_restriction: MagicMock,
                                                          mock_trigger_registered_job: MagicMock,
                                                          mock_can_trigger_job_by_branch: MagicMock):
    # noinspection PyUnresolvedReferences
    with patch.object(gh_sut, '_GithubController__get_collection_for_hook_type',
                      return_value=mock_collection_with_change_restriction) as get_collection_method:
        hook_details = HookDetails(event_type=EventTypes.push,
                                   repository='test_repo',
                                   branch='master',
                                   sha='test_sha')
        hook_details.changes = {'different_file', 'different/dir'}

        await gh_sut.trigger_registered_jobs(hook_details)
        time.sleep(0.3)

        mock_can_trigger_job_by_branch.assert_not_called()
        mock_trigger_registered_job.assert_not_called()
        get_collection_method.assert_called_once_with(EventTypes.push)


@pytest.mark.parametrize("changes", [
    'some_file',
    'another/directory',
])
async def test_push_hook_meets_change_restriction(gh_sut: GithubController,
                                                  mock_collection_with_change_restriction: MagicMock,
                                                  mock_trigger_registered_job: MagicMock,
                                                  mock_can_trigger_job_by_branch: MagicMock,
                                                  changes: str):
    # noinspection PyUnresolvedReferences
    with patch.object(gh_sut, '_GithubController__get_collection_for_hook_type',
                      return_value=mock_collection_with_change_restriction) as get_collection_method:
        hook_details = HookDetails(event_type=EventTypes.push,
                                   repository='test_repo',
                                   branch='master',
                                   sha='test_sha')
        hook_details.changes = {changes, 'different/dir', 'different_file'}
        await gh_sut.trigger_registered_jobs(hook_details)
        time.sleep(0.3)

        mock_can_trigger_job_by_branch.assert_called_once_with('test_job_1', 'master')
        mock_trigger_registered_job.assert_called_once_with('test_job_1',
                                                            [],
                                                            'test_repo_1',
                                                            'test_sha',
                                                            'master',
                                                            None)
        get_collection_method.assert_called_once_with(EventTypes.push)
