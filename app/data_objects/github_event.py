from typing import Optional


class GithubEvent:
    def __repr__(self) -> str:
        return f"<GithubEvent " \
               f"event_header: {self.event_header}, " \
               f"action: {self.action}, " \
               f"ref: {self.ref}, >"

    def __init__(self,
                 event_header: str,
                 action: Optional[str],
                 ref: Optional[str]) -> None:
        self.event_header = event_header
        self.action = action
        self.ref = ref
