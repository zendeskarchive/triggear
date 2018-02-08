import pytest

from app.hook_details.tag_hook_details import TagHookDetails

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestTagHookDetails:
    async def test__repr(self):
        assert f"{TagHookDetails('repo', '123321', '1.0')}" \
               == "<TagHookDetails repository: repo, tag: 1.0, sha: 123321 >"
