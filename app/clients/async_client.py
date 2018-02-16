from typing import Dict, Union, Tuple, Optional, List

import aiohttp

PayloadType = Union[Optional[Dict[str, Union[Optional[str], Optional[bool], Optional[List]]]],
                    Optional[Tuple[Union[Optional[str], Optional[bool]], ...]]]


class AsyncClientException(Exception):
    def __init__(self,
                 message: str,
                 status: int) -> None:
        self.message = message
        self.status = status

    def __str__(self) -> str:
        return f"<AsyncClientException> message: {self.message}, status: {self.status}"


class AsyncClientNotFoundException(AsyncClientException):
    def __init__(self, message: str) -> None:
        super(AsyncClientNotFoundException, self).__init__(message, 404)


class Payload:
    def __init__(self, data: PayloadType) -> None:
        self.data: PayloadType = data

    @staticmethod
    def from_args(*args: Union[str, bool]) -> 'Payload':
        return Payload(args)

    @staticmethod
    def from_kwargs(**kwargs: Union[Optional[bool], Optional[str], Optional[List]]) -> 'Payload':
        return Payload(kwargs)


class AsyncClient:
    def __init__(self,
                 base_url: str,
                 session_headers: Dict[str, str]) -> None:
        self.base_url = base_url
        self.session_headers = session_headers
        self.__session: aiohttp.ClientSession = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if self.__session is None or self.__session.closed:
            self.__session = aiohttp.ClientSession(headers=self.session_headers)
        return self.__session

    def build_url(self, route: str) -> str:
        if route.startswith('/'):
            return f'{self.base_url}{route}'
        else:
            return f'{self.base_url}/{route}'

    async def post(self,
                   route: str,
                   payload: Optional[Payload]=None,
                   params: Optional[Payload]=None,
                   headers: Optional[Dict]=None,
                   content_type: str='application/json') -> Dict:
        async with self.session.post(self.build_url(route),
                                     json=payload.data if payload else None,
                                     headers=headers,
                                     params=params.data if params else None) as resp:
            valid_response: aiohttp.ClientResponse = await self.validate_response(resp)
            try:
                response_data: Dict = await valid_response.json(content_type=content_type)
                return response_data
            except aiohttp.ContentTypeError:
                return {}

    async def get(self,
                  route: str,
                  params: Optional[Payload]=None) -> Dict:
        async with self.session.get(self.build_url(route), params=params.data if params is not None else None) as resp:
            valid_response: aiohttp.ClientResponse = await self.validate_response(resp)
            response_data: Dict = await valid_response.json()
            return response_data

    @staticmethod
    async def validate_response(response: aiohttp.ClientResponse) -> aiohttp.ClientResponse:
        if response.status == 404:
            missing_response_text: str = await response.text()
            raise AsyncClientNotFoundException(f'<AC> not found: {response.status} - {missing_response_text}')
        if response.status >= 400:
            error_response_text: str = await response.text()
            raise AsyncClientException(f'<AC> request failed: {response.status} - {error_response_text}', response.status)
        else:
            return response
