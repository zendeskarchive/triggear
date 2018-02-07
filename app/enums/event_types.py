from enum import Enum
from typing import List, Optional, Union

from app.data_objects.github_event import GithubEvent
from app.exceptions.triggear_error import TriggearError


class CollectionNames:
    RELEASE = 'release'
    LABELED = 'labeled'
    OPENED = 'opened'
    TAGGED = 'tagged'
    PUSH = 'push'


class EventType(Enum):
    RELEASE = ('release', 'published', None, CollectionNames.RELEASE)
    PR_LABELED = ('pull_request', 'labeled', None, CollectionNames.LABELED)
    ISSUE_COMMENT = ('issue_comment', 'created', None, None)
    PR_OPENED = ('pull_request', 'opened', None, CollectionNames.OPENED)
    TAGGED = ('push', None, 'refs/tags/', CollectionNames.TAGGED)
    PUSH = ('push', None, 'refs/heads/', CollectionNames.PUSH)
    SYNCHRONIZE = ('pull_request', 'synchronize', None, None)

    def __init__(self,
                 event_header: str,
                 action: str,
                 ref_prefix: str,
                 collection_name: str) -> None:
        self.event_header = event_header
        self.action = action
        self.ref_prefix = ref_prefix
        self.collection_name = collection_name

    def __eq__(self, other: object) -> bool:
        if isinstance(other, GithubEvent):
            result = self.action == other.action \
                   and self.event_header == other.event_header \
                   and (other.ref.startswith(self.ref_prefix) if other.ref is not None else self.ref_prefix == other.ref)
            return result
        elif isinstance(other, EventType):
            return self.action == other.action \
                   and self.event_header == other.event_header \
                   and self.ref_prefix == other.ref_prefix
        elif isinstance(other, str):
            return self.collection_name == other
        return False

    @staticmethod
    def get_allowed_registration_event_types() -> List['EventType']:
        return [EventType.PR_LABELED,
                EventType.TAGGED,
                EventType.PR_OPENED,
                EventType.PUSH,
                EventType.RELEASE]

    @staticmethod
    def get_by_collection_name(name: str) -> 'EventType':
        if name == CollectionNames.PUSH:
            return EventType.PUSH
        elif name == CollectionNames.OPENED:
            return EventType.PR_OPENED
        elif name == CollectionNames.TAGGED:
            return EventType.TAGGED
        elif name == CollectionNames.LABELED:
            return EventType.PR_LABELED
        elif name == CollectionNames.RELEASE:
            return EventType.RELEASE
        raise TriggearError(f'Unsupported event type: {name}')
