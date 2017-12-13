import functools

import logging

import aiohttp.web
from aiohttp.web_response import Response
from typing import Any, Tuple

from github import GithubException

from app.controllers.github_controller import TriggearTimeoutError


def handle_exceptions():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args: Tuple[Any]) -> Response:
            try:
                return await func(*args)
            except KeyError as missing_key:
                logging.warning(f"Error in {func}: {missing_key} key is missing")
                return aiohttp.web.Response(text=f'Error: {missing_key} is missing in request', status=400)
            except TriggearTimeoutError as timeout_error:
                logging.exception(f'Timeout error raised')
                return aiohttp.web.Response(text=str(timeout_error), reason=f'Timeout when accessing resources: {str(timeout_error)}', status=504)
            except GithubException as github_exception:
                logging.exception(f'Github client raised exception')
                return aiohttp.web.Response(reason=str(github_exception.data), status=github_exception.status)
        return wrapped
    return wrapper
