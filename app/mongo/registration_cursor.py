from typing import Optional, List

import motor.motor_asyncio

from app.enums.event_types import EventType
from app.mongo.registration_fields import RegistrationFields


class RegistrationCursor:
    def __repr__(self):
        return f"<RegistrationCursor" \
               f"event_type {self.event_type} " \
               f"job_name {self.job_name} " \
               f"repo {self.repo} " \
               f"jenkins_url {self.jenkins_url} " \
               f"labels {self.labels} " \
               f"requested_params {self.requested_params} " \
               f"change_restrictions {self.change_restrictions} " \
               f"branch_restrictions {self.branch_restrictions} " \
               f"file_restrictions {self.file_restrictions} " \
               f">"

    def __init__(self, event_type: EventType, cursor: motor.motor_asyncio.AsyncIOMotorCursor):
        self.event_type = event_type
        self.cursor = cursor

    @property
    def job_name(self) -> str:
        return self.cursor[RegistrationFields.JOB]

    @property
    def repo(self) -> str:
        return self.cursor[RegistrationFields.REPO]

    @property
    def jenkins_url(self) -> str:
        return self.cursor[RegistrationFields.REPO]

    @property
    def labels(self) -> Optional[List[str]]:
        return self.cursor.get(RegistrationFields.LABELS)

    @property
    def requested_params(self) -> Optional[List[str]]:
        return self.cursor.get(RegistrationFields.REQUESTED_PARAMS)

    @property
    def change_restrictions(self) -> Optional[List[str]]:
        return self.cursor.get(RegistrationFields.CHANGE_RESTRICTIONS)

    @property
    def branch_restrictions(self) -> Optional[List[str]]:
        return self.cursor.get(RegistrationFields.BRANCH_RESTRICTIONS)

    @property
    def file_restrictions(self) -> Optional[List[str]]:
        return self.cursor.get(RegistrationFields.FILE_RESTRICTIONS)
