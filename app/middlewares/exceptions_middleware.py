import logging
from typing import Callable, Awaitable

import aiohttp.web_request
from aiohttp import web

from app.clients.async_client import AsyncClientException
from app.exceptions.triggear_timeout_error import TriggearTimeoutError

RequestHandlerType = Callable[[aiohttp.web_request.Request], Awaitable[aiohttp.web.Response]]


@web.middleware
async def exceptions(request: aiohttp.web_request.Request, handler: RequestHandlerType) -> aiohttp.web.Response:
    try:
        return await handler(request)
    except TriggearTimeoutError as timeout_error:
        logging.exception(f'Timeout error raised')
        return aiohttp.web.Response(text=str(timeout_error), reason=f'Timeout when accessing resources: {str(timeout_error)}', status=504)
    except AsyncClientException as client_exception:
        logging.exception(f'Async client raised exception')
        return aiohttp.web.Response(text=str(client_exception), status=client_exception.status)
