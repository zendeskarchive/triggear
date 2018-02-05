from typing import Dict

from app.enums.event_types import EventType
from app.mongo.registration_cursor import RegistrationCursor


class HookDetails:
    def __repr__(self):
        raise NotImplementedError()

    def get_event_type(self) -> EventType:
        raise NotImplementedError()

    def get_allowed_parameters(self) -> Dict[str, str]:
        raise NotImplementedError()

    def get_query(self):
        raise NotImplementedError()

    def get_ref(self) -> str:
        raise NotImplementedError()

    def setup_final_param_values(self, registration_cursor: RegistrationCursor):
        raise NotImplementedError()
