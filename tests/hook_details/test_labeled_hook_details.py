import pytest

from app.hook_details.labeled_hook_details import LabeledHookDetails

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestLabeledHookDetails:
    async def test__repr(self):
        assert f"{LabeledHookDetails('repo', 'master', '123321', 'custom')}" \
               == "<LabeledHookDetails repository: repo, branch: master, sha: 123321, label: custom >"
