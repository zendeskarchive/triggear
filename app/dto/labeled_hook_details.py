from typing import Dict

from app.dto.abstract_hook_details import AbstractHookDetails
from app.enums.event_types import EventTypes
from app.request_schemes.register_request_data import RegisterRequestData


class LabeledHookDetails(AbstractHookDetails):
    def __init__(self,
                 repository: str,
                 branch: str,
                 sha: str,
                 label: str):
        self.repository = repository
        self.branch = branch
        self.sha = sha
        self.label = label

    def get_query(self):
        return dict(repository=self.repository, label=self.label)

    def get_allowed_parameters(self) -> Dict[str, str]:
        return {
            RegisterRequestData.RequestedParams.branch: self.branch,
            RegisterRequestData.RequestedParams.sha: self.sha
        }

    def get_event_type(self) -> str:
        return EventTypes.labeled
