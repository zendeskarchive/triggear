import pytest
from mockito import mock

from app.hook_details.hook_details import HookDetails

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestHookDetails:
    async def test__hook_details__is_pure_interface(self):
        with pytest.raises(NotImplementedError):
            f"{HookDetails()}"
        with pytest.raises(NotImplementedError):
            HookDetails().get_allowed_parameters()
        with pytest.raises(NotImplementedError):
            HookDetails().get_query()
        with pytest.raises(NotImplementedError):
            HookDetails().get_ref()
        with pytest.raises(NotImplementedError):
            HookDetails().setup_final_param_values(mock())
        with pytest.raises(NotImplementedError):
            await HookDetails().should_trigger(mock(), mock())
        with pytest.raises(NotImplementedError):
            HookDetails().get_event_type()
