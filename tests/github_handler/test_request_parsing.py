import pytest

from app.github_handler import GithubHandler

pytestmark = pytest.mark.asyncio


async def test_get_req_json(gh_sut: GithubHandler, mock_request):
    assert await gh_sut.get_request_json(mock_request) == 'json'


async def test_get_req_event_header(gh_sut: GithubHandler, mock_request):
    assert await gh_sut.get_request_event_header(mock_request) == 'event'
