import functools

import logging

import aiohttp.web
from aiohttp.web_response import Response
from typing import Any, Tuple


def handle_exceptions():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args: Tuple[Any]) -> Response:
            try:
                return await func(*args)
            except KeyError as missing_key:
                logging.warning(f"Error in {func}: {missing_key} key is missing")
                return aiohttp.web.Response(text=f'Error: {missing_key} is missing in request', status=400)
            except Exception as exc:
                logging.exception(f"Unknown error occurred in {func}: {exc}")
                return aiohttp.web.Response(text=f"Unknown error: {exc}", status=500)
        return wrapped
    return wrapper
