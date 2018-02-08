import pytest

from app.hook_details.pr_opened_hook_details import PrOpenedHookDetails

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestPrOpenedHookDetails:
    async def test__repr(self):
        assert f"{PrOpenedHookDetails('repo', 'master', '123321')}" \
               == "<PrOpenedHookDetails repository: repo, branch: master, sha: 123321 >"
