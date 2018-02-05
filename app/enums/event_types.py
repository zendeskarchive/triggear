from enum import Enum
from typing import Set

from app.data_objects.github_event import GithubEvent


class EventType(Enum):
    # release = 'release'
    # comment = 'created'
    # synchronize = 'synchronize'
    # labeled = 'labeled'
    # tagged = 'tagged'
    # push = 'push'
    # pr_opened = 'opened'
    # pull_request = 'pull_request'

    RELEASE = ('published', 'release', None, )
    PR_LABELED = ('labeled', 'pull_request', None)
    ISSUE_COMMENT = ('created', 'issue_comment', None)
    PR_OPENED = ('opened', 'pull_request', None)
    TAGGED = (None, 'push', 'refs/tags/')
    PUSH = (None, 'push', 'refs/heads/')

    def __init__(self, action: str, event_header: str, ref_prefix: str):
        self.action = action
        self.event_header = event_header
        self.ref_prefix = ref_prefix

    def __eq__(self, other):
        if isinstance(other, GithubEvent):
            return self.action == other.action \
                   and self.event_header == other.event_header \
                   and other.ref.startswith(self.ref_prefix) if other.ref is not None else self.ref_prefix == other.ref
        return False

    @staticmethod
    def get_allowed_registration_event_types() -> Set['EventType']:
        return {EventType.labeled,
                EventType.tagged,
                EventType.pr_opened,
                EventType.push,
                EventType.RELEASE}
