from typing import Union, List

import aiohttp
import pytest
from mockito import expect, mock

from app.clients.async_client import AsyncClient, Payload, AsyncClientException
from tests.async_mockito import async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestAsyncClient:
    async def test__when_session__one_should_be_created__and_later_reused(self):
        session = mock({'closed': False}, spec=aiohttp.ClientSession, strict=True)
        async_client = AsyncClient('http://example.com', {'Authorization': 'token dummy'})

        expect(aiohttp, times=1).ClientSession(headers={'Authorization': 'token dummy'}).thenReturn(session)
        assert session == async_client.session
        assert session == async_client.session

    async def test__when_session_is_closed__should_be_recreated(self):
        session = mock({'closed': True}, spec=aiohttp.ClientSession, strict=True)
        async_client = AsyncClient('http://example.com', {'Authorization': 'token dummy'})

        expect(aiohttp, times=2).ClientSession(headers={'Authorization': 'token dummy'}).thenReturn(session)
        assert session == async_client.session
        assert session == async_client.session

    @pytest.mark.parametrize("route", [
        'subpage', '/subpage'
    ])
    async def test__build_url__should_properly_join_base_url__with_route(self, route: str):
        async_client = AsyncClient('http://example.com', {'Authorization': 'token dummy'})
        assert async_client.build_url(route) == 'http://example.com/subpage'

    async def test__post__should_be_executed_on_session__and_have_response_validated(self):
        async_client = AsyncClient('http://example.com', {'Authorization': 'token dummy'})
        response = mock(spec=aiohttp.ClientResponse, strict=True)
        session: aiohttp.ClientSession = mock({'closed': False}, spec=aiohttp.ClientSession, strict=True)
        payload = Payload.from_kwargs(some='param')

        expect(aiohttp, times=1).ClientSession(headers={'Authorization': 'token dummy'}).thenReturn(session)
        expect(response).__aenter__().thenReturn(async_value(response))
        expect(response).__aexit__(None, None, None).thenReturn(async_value(None))
        expect(session).post('http://example.com/subpage', json=payload.data).thenReturn(response)
        expect(async_client).validate_response(response).thenReturn(async_value(response))

        assert await async_client.post('subpage', payload) == response

    @pytest.mark.parametrize("params, params_data", [
        (Payload.from_args('label'), ('label',)),
        (None, None)
    ])
    async def test__get__should_be_executed_on_session__and_have_response_validated(self, params: Payload, params_data: Union[None, List[str]]):
        async_client = AsyncClient('http://example.com', {'Authorization': 'token dummy'})
        response = mock(spec=aiohttp.ClientResponse, strict=True)
        session: aiohttp.ClientSession = mock({'closed': False}, spec=aiohttp.ClientSession, strict=True)

        expect(aiohttp, times=1).ClientSession(headers={'Authorization': 'token dummy'}).thenReturn(session)
        expect(response).__aenter__().thenReturn(async_value(response))
        expect(response).__aexit__(None, None, None).thenReturn(async_value(None))
        expect(session).get('http://example.com/subpage', params=params_data).thenReturn(response)
        expect(async_client).validate_response(response).thenReturn(async_value(response))

        assert await async_client.get('subpage', params) == response

    @pytest.mark.parametrize("status", [400, 404, 500])
    async def test__validate_response__raises__for_statuses_higher_or_eq_to_400(self, status: int):
        response: aiohttp.ClientResponse = mock({'status': status}, spec=aiohttp.ClientResponse, strict=True)

        expect(response).text().thenReturn(async_value('exception info'))

        with pytest.raises(AsyncClientException) as exception:
            await AsyncClient.validate_response(response)
        assert exception.value.status == status
        assert exception.value.message == f'Call failed: {status} - exception info'

    @pytest.mark.parametrize("status", [200, 201, 304])
    async def test__validate_response__returns_response__for_statuses_lower_then_400(self, status: int):
        response: aiohttp.ClientResponse = mock({'status': status}, spec=aiohttp.ClientResponse, strict=True)
        expect(response, times=0).text()
        assert await AsyncClient.validate_response(response) == response
