from typing import Dict

from app.mongo.registration_fields import RegistrationFields
from app.request_schemes.deregister_request_data import DeregisterRequestData


class DeregistrationQuery:
    def __init__(self,
                 jenkins_url: str,
                 job_name: str,
                 event_type: str,
                 caller: str) -> None:
        self.jenkins_url = jenkins_url
        self.job_name = job_name
        self.event_type = event_type
        self.caller = caller

    def get_deregistration_query(self) -> Dict[str, str]:
        return {
            RegistrationFields.JOB: self.job_name,
            RegistrationFields.JENKINS_URL: self.jenkins_url
        }

    @staticmethod
    def from_deregistration_request_data(data: Dict) -> 'DeregistrationQuery':
        return DeregistrationQuery(
            jenkins_url=data[DeregisterRequestData.jenkins_url],
            job_name=data[DeregisterRequestData.job_name],
            event_type=data[DeregisterRequestData.event_type],
            caller=data[DeregisterRequestData.caller]
        )
