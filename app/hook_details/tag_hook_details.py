from typing import Dict

from app.enums.event_types import EventType
from app.hook_details.hook_details import HookDetails
from app.mongo.registration_cursor import RegistrationCursor
from app.request_schemes.register_request_data import RegisterRequestData


class TagHookDetails(HookDetails):
    def __repr__(self):
        return f"<PrOpenedHookDetails " \
               f"repository: {self.repository} " \
               f"tag: {self.tag} " \
               f"sha: {self.sha} " \
               f">"

    def __init__(self,
                 repository: str,
                 sha: str,
                 tag: str):
        self.repository = repository
        self.sha = sha
        self.tag = tag

    def get_query(self):
        return dict(repository=self.repository)

    def get_allowed_parameters(self) -> Dict[str, str]:
        return {
            RegisterRequestData.RequestedParams.tag: self.tag,
            RegisterRequestData.RequestedParams.sha: self.sha
        }

    def get_event_type(self) -> str:
        return EventType.pr_opened

    def get_ref(self) -> str:
        return self.sha

    def setup_final_param_values(self, registration_cursor: RegistrationCursor):
        pass
