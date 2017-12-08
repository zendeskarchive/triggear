from typing import Dict

import pytest

from app.request_schemes.comment_request_data import CommentRequestData

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestCommentRequestData:
    @pytest.mark.parametrize("comment_data, expected_result", [
        ({'repository': '', 'sha': '', 'body': '', 'jobName': ''}, True),
        ({'repository': '', 'sha': '', 'body': '', 'jobName': '', 'other': ''}, False),
        ({'repository': '', 'body': '', 'jobName': ''}, False),
        ({}, False),
    ])
    async def test__is_valid_comment_data(self, comment_data: Dict[str, str], expected_result: bool):
        assert CommentRequestData.is_valid_comment_data(comment_data) == expected_result
