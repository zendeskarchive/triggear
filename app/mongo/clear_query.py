from typing import Dict

from app.mongo.registration_fields import RegistrationFields
from app.request_schemes.clear_request_data import ClearRequestData


class ClearQuery:
    def __init__(self,
                 jenkins_url: str,
                 job_name: str,
                 event_type: str):
        self.jenkins_url = jenkins_url
        self.job_name = job_name
        self.event_type = event_type

    def get_clear_query(self):
        return {
            RegistrationFields.JOB: self.job_name,
            RegistrationFields.JENKINS_URL: self.jenkins_url
        }

    @staticmethod
    def from_clear_request_data(data: Dict) -> 'ClearQuery':
        return ClearQuery(
            jenkins_url=data[ClearRequestData.jenkins_url],
            job_name=data[ClearRequestData.job_name],
            event_type=data[ClearRequestData.event_type]
        )
