import aiohttp.web
import aiohttp.web_request

from app.utilities.auth_validation import validate_auth_header
from app.utilities.err_handling import handle_exceptions


class HealthController:
    def __init__(self, api_token: str):
        self.api_token = api_token

    @handle_exceptions()
    @validate_auth_header()
    async def handle_health_check(self, request: aiohttp.web_request.Request):
        return aiohttp.web.Response(text='TriggearIsOk', reason=f'Host {request.host} asked')
