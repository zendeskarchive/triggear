import asynctest
import pytest

from app.controllers.github_controller import GithubController

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("hook_data, hook_method", [
    ({'action': 'labeled'}, 'handle_labeled'),
    ({'action': 'created'}, 'handle_comment'),
    ({'action': 'synchronize'}, 'handle_synchronize'),
])
async def test_handling_action_hooks(gh_sut: GithubController, hook_data, hook_method):
    with asynctest.patch.object(gh_sut, 'get_request_json', return_value=hook_data):
        with asynctest.patch.object(gh_sut, 'validate_webhook_secret', return_value='AUTHORIZED'):
            with asynctest.patch.object(gh_sut, hook_method) as handle_method:
                result = await gh_sut.handle_hook(asynctest.MagicMock())
                assert result.status == 200
                handle_method.assert_called_once_with(hook_data)


async def test_handling_push(gh_sut: GithubController):
    with asynctest.patch.object(gh_sut, 'get_request_json',
                                return_value={'action': 'not_matched', 'ref': 'refs/heads/master'}):
        with asynctest.patch.object(gh_sut, 'validate_webhook_secret', return_value='AUTHORIZED'):
            with asynctest.patch.object(gh_sut, 'get_request_event_header', return_value='push'):
                with asynctest.patch.object(gh_sut, 'handle_push') as handle_mock:
                    result = await gh_sut.handle_hook(asynctest.MagicMock())
                    assert result.status == 200
                    handle_mock.assert_called_once_with({'action': 'not_matched', 'ref': 'refs/heads/master'})


async def test_handling_pr_opened(gh_sut: GithubController):
    with asynctest.patch.object(gh_sut, 'get_request_json',
                                return_value={'action': 'opened', 'ref': 'refs/heads/master'}):
        with asynctest.patch.object(gh_sut, 'validate_webhook_secret', return_value='AUTHORIZED'):
            with asynctest.patch.object(gh_sut, 'get_request_event_header', return_value='pull_request'):
                with asynctest.patch.object(gh_sut, 'handle_pr_opened') as handle_mock:
                    result = await gh_sut.handle_hook(asynctest.MagicMock())
                    assert result.status == 200
                    handle_mock.assert_called_once_with({'action': 'opened', 'ref': 'refs/heads/master'})


@pytest.mark.parametrize("hook_data, hook_method", [
    ({'action': 'labeled'}, 'handle_labeled'),
    ({'action': 'created'}, 'handle_comment'),
    ({'action': 'synchronize'}, 'handle_synchronize'),
])
async def test_handling_action_hooks(gh_sut: GithubController, hook_data, hook_method):
    with asynctest.patch.object(gh_sut, 'get_request_json', return_value=hook_data):
        with asynctest.patch.object(gh_sut, 'validate_webhook_secret', return_value='AUTHORIZED'):
            with asynctest.patch.object(gh_sut, hook_method, side_effect=Exception()) as handle_method:
                result = await gh_sut.handle_hook(asynctest.MagicMock())
                assert result.status == 500
                handle_method.assert_called_once_with(hook_data)
