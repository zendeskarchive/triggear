from typing import Dict

import aiohttp


class AsyncClientException(Exception):
    def __init__(self, message: str, status: int):
        self.message = message
        self.status = status

    def __str__(self):
        return f"<AsyncClientException> message: {self.message}, status: {self.status}"


class AsyncClientNotFoundException(AsyncClientException):
    pass


class Payload:
    def __init__(self, data):
        self.data = data

    @staticmethod
    def from_args(*args):
        return Payload(args)

    @staticmethod
    def from_kwargs(**kwargs):
        return Payload(kwargs)


class AsyncClient:
    def __init__(self, base_url: str, session_headers: Dict[str, str]):
        self.base_url = base_url
        self.session_headers = session_headers
        self.__session = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if self.__session is None or self.__session.closed:
            self.__session = aiohttp.ClientSession(headers=self.session_headers)
        return self.__session

    def build_url(self, route: str):
        if route.startswith('/'):
            return f'{self.base_url}{route}'
        else:
            return f'{self.base_url}/{route}'

    async def post(self,
                   route: str,
                   payload: Payload=None,
                   params: Payload=None,
                   headers: Dict=None) -> aiohttp.client_reqrep.ClientResponse:
        async with self.session.post(self.build_url(route),
                                     json=payload.data if payload else None,
                                     headers=headers,
                                     params=params.data if params else None) as resp:
            return await self.validate_response(resp)

    async def get(self,
                  route: str,
                  params: Payload=None) -> aiohttp.client_reqrep.ClientResponse:
        async with self.session.get(self.build_url(route), params=params.data if params is not None else None) as resp:
            return await self.validate_response(resp)

    @staticmethod
    async def validate_response(response: aiohttp.client_reqrep.ClientResponse) -> aiohttp.client_reqrep.ClientResponse:
        if response.status == 404:
            response_text: str = await response.text()
            raise AsyncClientNotFoundException(f'<AC> not found: {response.status} - {response_text}', response.status)
        if response.status >= 400:
            response_text: str = await response.text()
            raise AsyncClientException(f'<AC> request failed: {response.status} - {response_text}', response.status)
        else:
            return response