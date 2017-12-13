from typing import Dict

import pytest

from app.request_schemes.status_request_data import StatusRequestData

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestStatusRequestData:
    @pytest.mark.parametrize("status_data, expected_result", [
        ({'repository': '', 'sha': '', 'state': '', 'description': '', 'url': '', 'context': ''}, True),
        ({'repository': '', 'sha': '', 'state': '', 'description': '', 'url': '', 'context': '', 'other': ''}, False),
        ({'repository': '', 'sha': '', 'state': '', 'description': ''}, False),
        ({}, False),
    ])
    async def test__is_valid_comment_data(self, status_data: Dict[str, str], expected_result: bool):
        assert StatusRequestData.is_valid_status_data(status_data) == expected_result
