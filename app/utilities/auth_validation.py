import functools

import aiohttp.web


def validate_auth_header():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args):
            auth_header = args[1].headers.get('Authorization')
            expected_token = 'Token ' + args[0].api_token
            if auth_header == expected_token:
                return await func(*args)
            else:
                return aiohttp.web.Response(text=f"Unauthorized", status=401)
        return wrapped
    return wrapper
