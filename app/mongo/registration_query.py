from typing import Dict, List, Optional

from app.mongo.registration_fields import RegistrationFields
from app.request_schemes.deregister_request_data import DeregisterRequestData
from app.request_schemes.register_request_data import RegisterRequestData


class RegistrationQuery:
    def __init__(self,
                 event_type: str,
                 jenkins_url: str,
                 job_name: str,
                 repository: Optional[str]=None,
                 labels: Optional[List[str]]=None,
                 requested_params: Optional[List[str]]=None,
                 branch_restrictions: Optional[List[str]]=None,
                 change_restrictions: Optional[List[str]]=None,
                 file_restrictions: Optional[List[str]]=None):
        self.event_type: str = event_type
        self.jenkins_url: str = jenkins_url
        self.job_name: str = job_name
        self.repository: str = repository
        self.labels: List[str] = labels
        self.requested_params: List[str] = requested_params
        self.branch_restrictions: List[str] = branch_restrictions
        self.change_restrictions: List[str] = change_restrictions
        self.file_restrictions: List[str] = file_restrictions

    def get_registration_query(self):
        return {
            RegistrationFields.JENKINS_URL: self.jenkins_url,
            RegistrationFields.REPO: self.repository,
            RegistrationFields.JOB: self.job_name
        }

    def get_deregistration_query(self):
        return {
            RegistrationFields.JOB: self.job_name,
            RegistrationFields.JENKINS_URL: self.jenkins_url
        }

    def get_full_document(self) -> Dict[str, str]:
        return dict({
            RegistrationFields.LABELS: self.labels,
            RegistrationFields.REQUESTED_PARAMS: self.requested_params,
            RegistrationFields.BRANCH_RESTRICTIONS: self.branch_restrictions,
            RegistrationFields.CHANGE_RESTRICTIONS: self.change_restrictions,
            RegistrationFields.FILE_RESTRICTIONS: self.file_restrictions
        }, **self.get_registration_query())

    @staticmethod
    def from_registration_request_data(data: Dict):
        branch_restrictions = data.get(RegisterRequestData.branch_restrictions)
        change_restrictions = data.get(RegisterRequestData.change_restrictions)
        file_restrictions = data.get(RegisterRequestData.file_restrictions)
        return RegistrationQuery(
            jenkins_url=data[RegisterRequestData.jenkins_url],
            event_type=data[RegisterRequestData.event_type],
            repository=data[RegisterRequestData.repository],
            job_name=data[RegisterRequestData.job_name],
            labels=data[RegisterRequestData.labels],
            requested_params=data[RegisterRequestData.requested_params],
            branch_restrictions=branch_restrictions if branch_restrictions is not None else [],
            change_restrictions=change_restrictions if change_restrictions is not None else [],
            file_restrictions=file_restrictions if file_restrictions is not None else []
        )

    @staticmethod
    def from_deregistration_request_data(data: Dict):
        return RegistrationQuery(
            jenkins_url=data[data[DeregisterRequestData.job_name]],
            job_name=data[DeregisterRequestData.job_name],
            event_type=data[DeregisterRequestData.event_type]
        )
