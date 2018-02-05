from typing import Optional, List

from motor import MotorCursor

from app.enums.registration_fields import RegistrationFields


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

    def __init__(self, event_type: str, cursor: MotorCursor):
        self.event_type = event_type
        self.cursor = cursor

    @property
    def job_name(self) -> str:
        return self.cursor[RegistrationFields.job]

    @property
    def repo(self) -> str:
        return self.cursor[RegistrationFields.repository]

    @property
    def jenkins_url(self) -> str:
        return self.cursor[RegistrationFields.repository]

    @property
    def labels(self) -> Optional[List[str]]:
        return self.cursor.get(RegistrationFields.labels)

    @property
    def requested_params(self) -> Optional[List[str]]:
        return self.cursor.get(RegistrationFields.requested_params)

    @property
    def change_restrictions(self) -> Optional[List[str]]:
        return self.cursor.get(RegistrationFields.change_restrictions)

    @property
    def branch_restrictions(self) -> Optional[List[str]]:
        return self.cursor.get(RegistrationFields.branch_restrictions)

    @property
    def file_restrictions(self) -> Optional[List[str]]:
        return self.cursor.get(RegistrationFields.file_restrictions)