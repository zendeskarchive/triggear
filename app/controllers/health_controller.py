import aiohttp.web
import aiohttp.web_request


class HealthController:
    @staticmethod
    async def handle_health_check(request: aiohttp.web_request.Request) -> aiohttp.web.Response:
        return aiohttp.web.Response(text='TriggearIsOk', reason=f'Host {request.host} asked')
