import pytest

from app.hook_details.release_hook_details import ReleaseHookDetails

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestReleaseHookDetails:
    async def test__repr(self):
        assert f"{ReleaseHookDetails('repo', '1.0', '123321', False)}" \
               == "<ReleaseHookDetails repository: repo, tag: 1.0, release_target: 123321, is_prerelease: False >"
