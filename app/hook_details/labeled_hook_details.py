from typing import Dict

from app.enums.event_types import EventType
from app.hook_details.hook_details import HookDetails
from app.mongo.registration_cursor import RegistrationCursor
from app.request_schemes.register_request_data import RegisterRequestData


class LabeledHookDetails(HookDetails):
    def __repr__(self):
        return f"<LabeledHookDetails " \
               f"repository: {self.repository} " \
               f"branch: {self.branch} " \
               f"sha: {self.sha} " \
               f"label: {self.label} " \
               f">"

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
        return EventType.labeled

    def get_ref(self) -> str:
        return self.sha

    def setup_final_param_values(self, registration_cursor: RegistrationCursor):
        pass
