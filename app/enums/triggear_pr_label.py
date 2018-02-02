from enum import Enum


class TriggearPrLabel(Enum):
    PR_SYNC = ('triggear-pr-sync', )
    LABEL_SYNC = ('triggear-label-sync', )

    def __init__(self, label_name: str) -> None:
        self.label_name = label_name

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.label_name == other
        elif isinstance(other, TriggearPrLabel):
            return self.label_name == other.label_name
        return False
