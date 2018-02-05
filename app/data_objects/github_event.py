from typing import Optional


class GithubEvent:
    def __init__(self, action: str, event_header: str, ref: Optional[str]):
        self.action = action
        self.event_header = event_header
        self.ref = ref
