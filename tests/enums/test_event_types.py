import pytest

from app.enums.event_types import EventTypes

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestEventTypes:
    async def test__get_allowed_event_types__should_return_proper_4_events(self):
        event_types = EventTypes.get_allowed_registration_event_types()
        assert 5 == len(event_types)
        assert 'opened' in event_types
        assert 'push' in event_types
        assert 'labeled' in event_types
        assert 'tagged' in event_types
        assert 'release' in event_types
