import pytest
import aiohttp.web_request
import aiohttp.web
from mockito import mock, expect

from app.clients.async_client import AsyncClientNotFoundException
from app.controllers.github_controller import GithubController
from app.exceptions.triggear_timeout_error import TriggearTimeoutError
from app.middlewares.exceptions_middleware import exceptions
from tests.async_mockito import async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestExceptionsMiddleware:
    async def test__returns_value__if_no_known_exceptions_is_raised(self):
        github_controller: GithubController = mock(spec=GithubController, strict=True)
        request: aiohttp.web_request.Request = mock(spec=aiohttp.web_request.Request, strict=True)
        response: aiohttp.web.Response = mock(spec=aiohttp.web.Response, strict=True)

        expect(github_controller).handle_hook(request).thenReturn(async_value(response))
        assert response == await exceptions(request, github_controller.handle_hook)

    async def test__returns_504_value__if_timeout_error_is_raised(self):
        github_controller: GithubController = mock(spec=GithubController, strict=True)
        request: aiohttp.web_request.Request = mock(spec=aiohttp.web_request.Request, strict=True)

        expect(github_controller).handle_hook(request).thenRaise(TriggearTimeoutError('the reason'))
        response: aiohttp.web.Response = await exceptions(request, github_controller.handle_hook)
        assert response.status == 504
        assert response.text == 'the reason'
        assert response.reason == 'Timeout when accessing resources: the reason'

    async def test__returns_async_clients_response__if_async_client_exception_is_raised(self):
        github_controller: GithubController = mock(spec=GithubController, strict=True)
        request: aiohttp.web_request.Request = mock(spec=aiohttp.web_request.Request, strict=True)

        expect(github_controller).handle_hook(request).thenRaise(AsyncClientNotFoundException('the reason'))
        response: aiohttp.web.Response = await exceptions(request, github_controller.handle_hook)
        assert response.status == 404
        assert response.text == '<AsyncClientException> message: the reason, status: 404'
        assert response.reason == 'Not Found'
