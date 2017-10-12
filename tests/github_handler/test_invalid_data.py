import pytest
import asynctest

from app.github_handler import GithubHandler
from app.labels import Labels

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("hook_data, missing_key", [
    ({}, 'pull_request'),
    ({'pull_request': {}}, 'head'),
    ({'pull_request': {'head': {}}}, 'sha'),
    ({'pull_request': {'head': {'sha': '123123'}}}, 'ref'),
    ({'pull_request': {'head': {'sha': '123123', 'ref': 'branch'}}}, 'repo'),
    ({'pull_request': {'head': {'sha': '123123', 'ref': 'branch', 'repo': {}}}}, 'full_name'),
    ({'pull_request': {'head': {'sha': '123123', 'ref': 'branch', 'repo': {'full_name': 'repo'}}}}, 'label'),

])
async def test_handling_labeled(hook_data, missing_key, gh_sut: GithubHandler):
    with pytest.raises(KeyError) as exc_info:
        await gh_sut.handle_labeled(hook_data)
    assert missing_key in str(exc_info.value)


@pytest.mark.parametrize("hook_data, missing_key", [
    ({}, 'pull_request'),
    ({'pull_request': {}}, 'head'),
    ({'pull_request': {'head': {}}}, 'repo'),
    ({'pull_request': {'head': {'repo': {}}}}, 'full_name'),
    ({'pull_request': {'head': {'repo': {'full_name': 'test_repo'}}}}, 'number'),
    ({'pull_request': {'head': {'repo': {'full_name': 'test_repo'}}, 'number': 'test_pr_number'}}, 'sha'),
    ({'pull_request': {'head': {'repo': {'full_name': 'test_repo'}, 'sha': 'test_sha'},
                       'number': 'test_pr_number'}}, 'ref'),

])
async def test_handling_synchronize(hook_data, missing_key, gh_sut: GithubHandler):
    with pytest.raises(KeyError) as exc_info:
        await gh_sut.handle_synchronize(hook_data)
    assert missing_key in str(exc_info.value)


async def test_empty_hook_handle(gh_sut: GithubHandler, mocker):
    label = mocker.patch.object(gh_sut, 'handle_labeled')
    sync = mocker.patch.object(gh_sut, 'handle_synchronize')
    comment = mocker.patch.object(gh_sut, 'handle_comment')
    push = mocker.patch.object(gh_sut, 'handle_push')
    with asynctest.patch.object(gh_sut, 'get_request_json', return_value={}):
        with asynctest.patch.object(gh_sut, 'validate_webhook_secret', return_value='AUTHORIZED'):
            result = await gh_sut.handle_hook(asynctest.MagicMock())
            assert result.status == 200
            label.assert_not_called()
            sync.assert_not_called()
            comment.assert_not_called()
            push.assert_not_called()


@pytest.mark.parametrize("hook_data, missing_key", [
    ({}, 'comment'),
    ({'comment': {}}, 'body'),
    ({'comment': {'body': 'Triggear run job'}}, 'repository'),
    ({'comment': {'body': Labels.label_sync}}, 'repository'),
    ({'comment': {'body': 'Triggear run test'}, 'repository': {}}, 'full_name'),
    ({'comment': {'body': Labels.label_sync}, 'repository': {}}, 'full_name'),
    ({'comment': {'body': 'Triggear run test'}, 'repository': {'full_name': 'test_repo'}}, 'issue'),
    ({'comment': {'body': Labels.label_sync}, 'repository': {'full_name': 'test_repo'}}, 'issue'),
    ({'comment': {'body': 'Triggear run test'}, 'repository': {'full_name': 'test_repo'}, 'issue': {}}, 'number'),
    ({'comment': {'body': Labels.label_sync}, 'repository': {'full_name': 'test_repo'}, 'issue': {}}, 'number'),
    ({'comment': {'body': Labels.label_sync},
      'repository': {'full_name': 'test_repo'}, 'issue': {'number': 1}}, 'labels'),
    ({'comment': {'body': Labels.label_sync},
      'repository': {'full_name': 'test_repo'}, 'issue': {'number': 1, 'labels': [{}]}}, 'name'),

])
async def test_handling_synchronize(hook_data, missing_key, gh_sut: GithubHandler):
    with pytest.raises(KeyError) as exc_info:
        await gh_sut.handle_comment(hook_data)
    assert missing_key in str(exc_info.value)
