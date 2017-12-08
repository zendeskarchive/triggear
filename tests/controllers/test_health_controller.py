import pytest
import aiohttp.web
import aiohttp.web_request
from mockito import mock

from app.controllers.health_controller import HealthController

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestHealthController:
    async def test__when_invalid_token_is_provided__should_return_401_response(self):
        request = mock({'headers': {'Authorization': 'invalid'}}, spec=aiohttp.web_request.Request, strict=True)
        response: aiohttp.web.Response = await HealthController('api_token').handle_health_check(request)
        assert response.status == 401
        assert response.text == 'Unauthorized'

    async def test__when_token_is_valid__should_return_200_response(self):
        request = mock({'headers': {'Authorization': 'Token api_token'}, 'host': 'custom_host'}, spec=aiohttp.web_request.Request, strict=True)
        response: aiohttp.web.Response = await HealthController('api_token').handle_health_check(request)
        assert response.status == 200
        assert response.text == 'TriggearIsOk'
        assert response.reason == 'Host custom_host asked'
