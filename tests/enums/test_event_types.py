import pytest

from app.data_objects.github_event import GithubEvent
from app.enums.event_types import EventType

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestEventTypes:
    async def test__get_allowed_event_types__should_return_proper_5_events(self):
        assert EventType.get_allowed_registration_event_types() == {
            EventType.RELEASE,
            EventType.PR_LABELED,
            EventType.PR_OPENED,
            EventType.PUSH,
            EventType.TAGGED
        }

    @pytest.mark.parametrize("event_type, github_event", [
        (EventType.RELEASE, GithubEvent('published', 'release', None))
    ])
    async def test__eq_operator__should_return_true_for_proper_github_events(self, event_type: EventType, github_event: GithubEvent):
        assert event_type == github_event
