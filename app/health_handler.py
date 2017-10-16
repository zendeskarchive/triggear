import aiohttp.web_request
import aiohttp.web

from app.auth_validation import validate_auth_header
from app.err_handling import handle_exceptions


class HealthHandler:
    def __init__(self, api_token: str):
        self.api_token = api_token

    @handle_exceptions()
    @validate_auth_header()
    async def handle_health_check(self, request: aiohttp.web_request.Request):
        return aiohttp.web.Response(text='TriggearIsOk', reason=f'Host {request.host} asked')
