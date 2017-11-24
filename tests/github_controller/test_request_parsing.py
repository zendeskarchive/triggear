import pytest

from app.controllers.github_controller import GithubController

pytestmark = pytest.mark.asyncio


async def test_get_req_json(gh_sut: GithubController, mock_request):
    assert await gh_sut.get_request_json(mock_request) == {'json': 'json'}


async def test_get_req_event_header(gh_sut: GithubController, mock_request):
    assert await gh_sut.get_request_event_header(mock_request) == 'event'
