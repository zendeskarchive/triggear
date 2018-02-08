import pytest

from app.hook_details.push_hook_details import PushHookDetails

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestPushHookDetails:
    async def test__repr(self):
        assert f"{PushHookDetails('repo', 'master', '123321', {'README.md'})}" \
               == "<PushHookDetails repository: repo, branch: master, sha: 123321, changes: {'README.md'} >"
