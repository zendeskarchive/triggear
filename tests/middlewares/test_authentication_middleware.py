import pytest
import aiohttp.web_request
import aiohttp.web
from mockito import mock, expect, when

from app.config.triggear_config import TriggearConfig
from app.controllers.github_controller import GithubController
from app.middlewares.authentication_middleware import AuthenticationMiddleware
from tests.async_mockito import async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestAuthenticationMiddleware:
    async def test_github__when_header_signature_is_not_provided__should_return_401_from_validation(self):
        triggear_config: TriggearConfig = mock({'triggear_token': 'abc'}, spec=TriggearConfig, strict=True)
        github_controller: GithubController = mock(spec=GithubController, strict=True)

        request = mock({'path': '/github', 'headers': {}}, spec=aiohttp.web_request.Request)

        expect(github_controller, times=0).handle_hook(request)

        response: aiohttp.web.Response = await AuthenticationMiddleware(triggear_config).authentication(request, github_controller.handle_hook)
        assert response.status == 401
        assert response.text == 'Unauthorized'

    async def test_github__when_header_signature_is_invalid__should_return_401_from_validation(self):
        triggear_config: TriggearConfig = mock({'triggear_token': 'abc'}, spec=TriggearConfig, strict=True)
        github_controller: GithubController = mock(spec=GithubController, strict=True)

        request = mock({'path': '/github', 'headers': {'X-Hub-Signature': 'sha1=abc'}}, spec=aiohttp.web_request.Request)

        when(request).read().thenReturn(async_value(None))
        expect(github_controller, times=0).handle_hook(request)

        response: aiohttp.web.Response = await AuthenticationMiddleware(triggear_config).authentication(request, github_controller.handle_hook)
        assert response.status == 401
        assert response.text == 'Unauthorized'

    async def test_github__when_header_signature_is_provided__but_auth_is_not_sha1__should_return_501_from_validation(self):
        triggear_config: TriggearConfig = mock(spec=TriggearConfig, strict=True)
        github_controller: GithubController = mock(spec=GithubController, strict=True)

        request = mock({'path': '/github', 'headers': {'X-Hub-Signature': 'different=abc'}}, spec=aiohttp.web_request.Request, strict=True)

        expect(github_controller, times=0).handle_hook(request)

        response: aiohttp.web.Response = await AuthenticationMiddleware(triggear_config).authentication(request, github_controller.handle_hook)
        assert response.status == 501
        assert response.text == 'Unsupported authentication method'

    async def test__github__when_valid_signature_is_sent__should_return_value_from_handler(self):
        triggear_config: TriggearConfig = mock({'triggear_token': 'api_token'}, spec=TriggearConfig, strict=True)
        github_controller: GithubController = mock(spec=GithubController, strict=True)

        request = mock({'path': '/github', 'headers': {'X-Hub-Signature': 'sha1=95f4e9f69093927bc664b433f7255486b698537c'}},
                       spec=aiohttp.web_request.Request, strict=True)
        response = mock(spec=aiohttp.web.Response, strict=True)

        when(request).read().thenReturn(async_value(b"valid_data"))
        expect(github_controller).handle_hook(request).thenReturn(async_value(response))

        actual_response: aiohttp.web.Response = await AuthenticationMiddleware(triggear_config).authentication(request, github_controller.handle_hook)
        assert response == actual_response

    @pytest.mark.parametrize("endpoint", [
        '/register',
        '/status',
        '/comment',
        '/missing',
        '/deregister',
        '/clear',
        '/deployment',
        '/deployment_status'
    ])
    async def test__token_authorized_endpoints__when_invalid_token_is_sent__should_return_401(self, endpoint: str):
        triggear_config: TriggearConfig = mock({'triggear_token': 'api_token'}, spec=TriggearConfig, strict=True)
        controller = mock(strict=True)

        request = mock({'path': endpoint, 'headers': {'Authorization': 'Token invalid'}},
                       spec=aiohttp.web_request.Request, strict=True)

        expect(controller, times=0).handler(request)

        response: aiohttp.web.Response = await AuthenticationMiddleware(triggear_config).authentication(request, controller.handler)
        assert response.status == 401
        assert response.text == 'Unauthorized'

    @pytest.mark.parametrize("endpoint", [
        '/register',
        '/status',
        '/comment',
        '/missing',
        '/deregister',
        '/clear',
        '/deployment',
        '/deployment_status'
    ])
    async def test__token_authorized_endpoints__when_valid_token_is_sent__should_return_handler_response(self, endpoint: str):
        triggear_config: TriggearConfig = mock({'triggear_token': 'api_token'}, spec=TriggearConfig, strict=True)
        controller = mock(strict=True)

        request = mock({'path': endpoint, 'headers': {'Authorization': 'Token api_token'}},
                       spec=aiohttp.web_request.Request, strict=True)
        response = mock(spec=aiohttp.web.Response, strict=True)

        expect(controller, times=1).handler(request).thenReturn(async_value(response))

        actual_response: aiohttp.web.Response = await AuthenticationMiddleware(triggear_config).authentication(request, controller.handler)
        assert response == actual_response

    @pytest.mark.parametrize("auth_header", [
        {'Authorization': 'Token api_token'},
        {'Authorization': 'Token invalid'}
    ])
    async def test__open_endpoint__should_return_handler_result__no_matter_whether_auth_was_used(self, auth_header: str):
        triggear_config: TriggearConfig = mock({'triggear_token': 'api_token'}, spec=TriggearConfig, strict=True)
        controller = mock(strict=True)

        request = mock({'path': '/health', 'headers': auth_header, 'remote': 'localhost'},
                       spec=aiohttp.web_request.Request, strict=True)
        response = mock(spec=aiohttp.web.Response, strict=True)

        expect(controller, times=1).handler(request).thenReturn(async_value(response))

        actual_response: aiohttp.web.Response = await AuthenticationMiddleware(triggear_config).authentication(request, controller.handler)
        assert response == actual_response
