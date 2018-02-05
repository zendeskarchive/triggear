from typing import Dict, Set

from app.enums.event_types import EventType
from app.hook_details.hook_details import HookDetails
from app.mongo.registration_cursor import RegistrationCursor
from app.request_schemes.register_request_data import RegisterRequestData
from app.utilities.functions import get_all_starting_with


class PushHookDetails(HookDetails):
    def __repr__(self):
        return f"<PrOpenedHookDetails " \
               f"repository: {self.repository} " \
               f"branch: {self.branch} " \
               f"sha: {self.sha} " \
               f"changes: {self.changes} " \
               f">"

    def __init__(self,
                 repository: str,
                 branch: str,
                 sha: str,
                 changes: Set[str]):
        self.repository = repository
        self.branch = branch
        self.sha = sha
        self.changes = changes

    def get_allowed_parameters(self) -> Dict[str, str]:
        return {
            RegisterRequestData.RequestedParams.branch: self.branch,
            RegisterRequestData.RequestedParams.sha: self.sha,
            RegisterRequestData.RequestedParams.changes: self.changes
        }

    def get_query(self):
        return dict(repository=self.repository)

    def get_event_type(self) -> str:
        return EventType.pr_opened

    def get_ref(self) -> str:
        return self.sha

    def setup_final_param_values(self, registration_cursor: RegistrationCursor):
        self.changes = get_all_starting_with(self.changes, registration_cursor.change_restrictions)
