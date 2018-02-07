from typing import Optional, List

import motor.motor_asyncio

from app.enums.event_types import EventType
from app.mongo.registration_fields import RegistrationFields


class RegistrationCursor:
    def __repr__(self) -> str:
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

    def __init__(self, event_type: EventType, cursor: motor.motor_asyncio.AsyncIOMotorCursor) -> None:
        self.event_type = event_type
        self.cursor = cursor

    @property
    def job_name(self) -> str:
        job_name: str = self.cursor[RegistrationFields.JOB]
        return job_name

    @property
    def repo(self) -> str:
        repo: str = self.cursor[RegistrationFields.REPO]
        return repo

    @property
    def jenkins_url(self) -> str:
        jenkins_url: str = self.cursor[RegistrationFields.JENKINS_URL]
        return jenkins_url

    @property
    def labels(self) -> Optional[List[str]]:
        labels: Optional[List[str]] = self.cursor.get(RegistrationFields.LABELS)
        return labels

    @property
    def requested_params(self) -> Optional[List[str]]:
        requested_params: Optional[List[str]] = self.cursor.get(RegistrationFields.REQUESTED_PARAMS)
        return requested_params

    @property
    def change_restrictions(self) -> Optional[List[str]]:
        change_restrictions: Optional[List[str]] = self.cursor.get(RegistrationFields.CHANGE_RESTRICTIONS)
        return change_restrictions

    @property
    def branch_restrictions(self) -> Optional[List[str]]:
        branch_restrictions: Optional[List[str]] = self.cursor.get(RegistrationFields.BRANCH_RESTRICTIONS)
        return branch_restrictions

    @property
    def file_restrictions(self) -> Optional[List[str]]:
        file_restrictions: Optional[List[str]] = self.cursor.get(RegistrationFields.FILE_RESTRICTIONS)
        return file_restrictions
