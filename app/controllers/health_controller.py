import aiohttp.web
import aiohttp.web_request

from app.clients.async_client import AsyncClientException


class HealthController:
    @staticmethod
    async def handle_health_check(request: aiohttp.web_request.Request):
        raise AsyncClientException('blah', 404)
        return aiohttp.web.Response(text='TriggearIsOk', reason=f'Host {request.host} asked')
