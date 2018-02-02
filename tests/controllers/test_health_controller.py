import pytest
import aiohttp.web
import aiohttp.web_request
from mockito import mock

from app.controllers.health_controller import HealthController

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestHealthController:
    async def test__handle_health_check__should_return_200_response(self):
        request = mock({'host': 'custom_host'}, spec=aiohttp.web_request.Request, strict=True)
        response: aiohttp.web.Response = await HealthController().handle_health_check(request)
        assert response.status == 200
        assert response.text == 'TriggearIsOk'
        assert response.reason == 'Host custom_host asked'
