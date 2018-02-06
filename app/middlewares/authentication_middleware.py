import hmac
import logging
from enum import Enum, auto
from typing import Callable, Awaitable, Dict

import aiohttp.web_request
from aiohttp import web
from pip.utils import cached_property

from app.config.triggear_config import TriggearConfig
from app.routes import Routes


RequestHandlerType = Callable[[aiohttp.web_request.Request], Awaitable[aiohttp.web.Response]]


class AuthenticationPolicy(Enum):
    GITHUB = auto()
    TOKEN = auto()
    NONE = auto()


class AuthenticationResult(Enum):
    AUTHENTICATED = auto()
    UNAUTHORIZED = auto()
    NOT_IMPLEMENTED = auto()


authentication_policies = {
    Routes.HEALTH.route_id: AuthenticationPolicy.NONE,
    Routes.GITHUB.route_id: AuthenticationPolicy.GITHUB,
    Routes.REGISTER.route_id: AuthenticationPolicy.TOKEN,
    Routes.STATUS.route_id: AuthenticationPolicy.TOKEN,
    Routes.COMMENT.route_id: AuthenticationPolicy.TOKEN,
    Routes.MISSING.route_id: AuthenticationPolicy.TOKEN,
    Routes.DEREGISTER.route_id: AuthenticationPolicy.TOKEN,
    Routes.CLEAR.route_id: AuthenticationPolicy.TOKEN,
    Routes.DEPLOYMENT.route_id: AuthenticationPolicy.TOKEN,
    Routes.DEPLOYMENT_STATUS.route_id: AuthenticationPolicy.TOKEN
}


class AuthenticationMiddleware:
    GITHUB_SIGNATURE_HEADER = 'X-Hub-Signature'

    def __init__(self, config: TriggearConfig) -> None:
        self.config = config

    @cached_property
    def expected_token(self) -> str:
        return 'Token ' + self.config.triggear_token

    @cached_property
    def policy_handlers(self) -> Dict[AuthenticationPolicy, Callable[[aiohttp.web_request.Request], Awaitable]]:
        return {
            AuthenticationPolicy.TOKEN: self.token_handler,
            AuthenticationPolicy.GITHUB: self.github_handler,
            AuthenticationPolicy.NONE: self.none_handler
        }

    async def token_handler(self, request: aiohttp.web_request.Request) -> AuthenticationResult:
        auth_header = request.headers.get('Authorization')
        if auth_header == self.expected_token:
            return AuthenticationResult.AUTHENTICATED
        else:
            return AuthenticationResult.UNAUTHORIZED

    async def github_handler(self, request: aiohttp.web_request.Request) -> AuthenticationResult:
        header_signature = request.headers.get(self.GITHUB_SIGNATURE_HEADER)

        if header_signature is None:
            return AuthenticationResult.UNAUTHORIZED
        sha_name, signature = header_signature.split('=')
        if sha_name != 'sha1':
            return AuthenticationResult.NOT_IMPLEMENTED

        req_body = await request.read()
        mac = hmac.new(bytearray(self.config.triggear_token, 'utf-8'), msg=req_body, digestmod='sha1')
        if not hmac.compare_digest(str(mac.hexdigest()), str(signature)):
            return AuthenticationResult.UNAUTHORIZED
        return AuthenticationResult.AUTHENTICATED

    @staticmethod
    async def none_handler(request: aiohttp.web_request.Request) -> AuthenticationResult:
        logging.warning(f'{request.remote} has requested open endpoint')
        return AuthenticationResult.AUTHENTICATED

    @web.middleware
    async def authentication(self, request: aiohttp.web_request.Request, handler: RequestHandlerType) -> aiohttp.web.Response:
        route_id = request.path.split('/')[1]
        authentication_result: AuthenticationResult = await self.policy_handlers[authentication_policies[route_id]](request)
        if authentication_result == AuthenticationResult.UNAUTHORIZED:
            return aiohttp.web.Response(text='Unauthorized', status=401)
        elif authentication_result == AuthenticationResult.NOT_IMPLEMENTED:
            return aiohttp.web.Response(text='Unsupported authentication method', status=501)
        else:
            return await handler(request)
