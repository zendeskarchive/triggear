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
