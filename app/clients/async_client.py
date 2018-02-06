from typing import Dict, Union, Tuple, Optional

from aiohttp import ClientSession, ClientResponse

PayloadType = Union[Dict[str, Union[bool, str]], Tuple[Union[str, bool], ...]]


class AsyncClientException(Exception):
    def __init__(self,
                 message: str,
                 status: int) -> None:
        self.message = message
        self.status = status

    def __str__(self) -> str:
        return f"<AsyncClientException> message: {self.message}, status: {self.status}"


class AsyncClientNotFoundException(AsyncClientException):
    pass


class Payload:
    def __init__(self, data: PayloadType) -> None:
        self.data: PayloadType = data

    @staticmethod
    def from_args(*args: Union[str, bool]) -> 'Payload':
        return Payload(args)

    @staticmethod
    def from_kwargs(**kwargs: Union[bool, str]) -> 'Payload':
        return Payload(kwargs)


class AsyncClient:
    def __init__(self,
                 base_url: str,
                 session_headers: Dict[str, str]) -> None:
        self.base_url = base_url
        self.session_headers = session_headers
        self.__session: ClientSession = None

    @property
    def session(self) -> ClientSession:
        if self.__session is None or self.__session.closed:
            self.__session = ClientSession(headers=self.session_headers)
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
                   headers: Dict=None) -> ClientResponse:
        async with self.session.post(self.build_url(route),
                                     json=payload.data if payload else None,
                                     headers=headers,
                                     params=params.data if params else None) as resp:
            return await self.validate_response(resp)

    async def get(self,
                  route: str,
                  params: Optional[Payload]=None) -> ClientResponse:
        async with self.session.get(self.build_url(route), params=params.data if params is not None else None) as resp:
            return await self.validate_response(resp)

    @staticmethod
    async def validate_response(response: ClientResponse) -> ClientResponse:
        if response.status == 404:
            missing_response_text: str = await response.text()
            raise AsyncClientNotFoundException(f'<AC> not found: {response.status} - {missing_response_text}', response.status)
        if response.status >= 400:
            error_response_text: str = await response.text()
            raise AsyncClientException(f'<AC> request failed: {response.status} - {error_response_text}', response.status)
        else:
            return response
