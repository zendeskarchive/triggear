from typing import Dict, Union, Any

from app.clients.github_client import GithubClient
from app.enums.event_types import EventType
from app.mongo.registration_cursor import RegistrationCursor


class HookDetails:
    def __repr__(self) -> str:
        raise NotImplementedError()

    def get_event_type(self) -> EventType:
        raise NotImplementedError()

    def get_allowed_parameters(self) -> Dict[str, str]:
        raise NotImplementedError()

    def get_query(self) -> Dict[str, Any]:
        raise NotImplementedError()

    def get_ref(self) -> str:
        raise NotImplementedError()

    def setup_final_param_values(self, registration_cursor: RegistrationCursor) -> None:
        raise NotImplementedError()

    async def should_trigger(self, cursor: RegistrationCursor, github_client: GithubClient) -> bool:
        raise NotImplementedError()
