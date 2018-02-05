from typing import Optional


class GithubEvent:
    def __init__(self, event_header: str, action: Optional[str], ref: Optional[str]):
        self.event_header = event_header
        self.action = action
        self.ref = ref
