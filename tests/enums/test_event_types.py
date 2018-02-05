import pytest

from app.data_objects.github_event import GithubEvent
from app.enums.event_types import EventType

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestEventTypes:
    async def test__get_allowed_event_types__should_return_proper_5_events(self):
        assert EventType.get_allowed_registration_event_types() == [
            EventType.PR_LABELED,
            EventType.TAGGED,
            EventType.PR_OPENED,
            EventType.PUSH,
            EventType.RELEASE
        ]

    @pytest.mark.parametrize("event_type, github_event", [
        (EventType.RELEASE, GithubEvent('release', 'published', None)),
        (EventType.PR_LABELED, GithubEvent('pull_request', 'labeled', None)),
        (EventType.ISSUE_COMMENT, GithubEvent('issue_comment', 'created', None)),
        (EventType.PR_OPENED, GithubEvent('pull_request', 'opened', None)),
        (EventType.TAGGED, GithubEvent('push', None, 'refs/tags/')),
        (EventType.PUSH, GithubEvent('push', None, 'refs/heads/'))
    ])
    async def test__eq_operator__should_return_true_for_proper_github_events(self, event_type: EventType, github_event: GithubEvent):
        assert event_type == github_event
