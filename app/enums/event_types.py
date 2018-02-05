from enum import Enum
from typing import List

from app.data_objects.github_event import GithubEvent


class EventType(Enum):
    RELEASE = ('release', 'published', None, 'release')
    PR_LABELED = ('pull_request', 'labeled', None, 'labeled')
    ISSUE_COMMENT = ('issue_comment', 'created', None, None)
    PR_OPENED = ('pull_request', 'opened', None, 'opened')
    TAGGED = ('push', None, 'refs/tags/', 'tagged')
    PUSH = ('push', None, 'refs/heads/', 'push')
    SYNCHRONIZE = ('pull_request', 'synchronize', None, None)

    def __init__(self,
                 event_header: str,
                 action: str,
                 ref_prefix: str,
                 collection_name: str):
        self.event_header = event_header
        self.action = action
        self.ref_prefix = ref_prefix
        self.collection_name = collection_name

    def __eq__(self, other):
        if isinstance(other, GithubEvent):
            return self.action == other.action \
                   and self.event_header == other.event_header \
                   and other.ref.startswith(self.ref_prefix) if other.ref is not None else self.ref_prefix == other.ref
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
