from typing import Dict, List


class DeploymentRequestData:
    repo = 'repo'
    ref = 'ref'
    environment = 'environment'
    description = 'description'

    @staticmethod
    def __get_all_mandatory_fields() -> List[str]:
        return [DeploymentRequestData.repo, DeploymentRequestData.ref, DeploymentRequestData.environment, DeploymentRequestData.description]

    @staticmethod
    def is_valid_deployment_request_data(data: Dict) -> bool:
        for field in DeploymentRequestData.__get_all_mandatory_fields():
            if field not in data.keys():
                return False
        return True
