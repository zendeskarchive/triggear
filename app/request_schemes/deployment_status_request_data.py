from typing import Dict, List


class DeploymentStatusRequestData:
    repo = 'repo'
    ref = 'ref'
    environment = 'environment'
    description = 'description'
    state = 'state'
    target_url = 'targetUrl'

    class DeploymentState:
        success = 'success'
        error = 'error'
        failure = 'failure'
        pending = 'pending'

    @staticmethod
    def __get_all_mandatory_fields() -> List[str]:
        return [DeploymentStatusRequestData.repo,
                DeploymentStatusRequestData.ref,
                DeploymentStatusRequestData.environment,
                DeploymentStatusRequestData.description,
                DeploymentStatusRequestData.state,
                DeploymentStatusRequestData.target_url]

    @staticmethod
    def __get_allowed_deployment_states() -> List[str]:
        return [DeploymentStatusRequestData.DeploymentState.success,
                DeploymentStatusRequestData.DeploymentState.error,
                DeploymentStatusRequestData.DeploymentState.failure,
                DeploymentStatusRequestData.DeploymentState.pending]

    @staticmethod
    def is_valid_deployment_status_request_data(data: Dict) -> bool:
        for field in DeploymentStatusRequestData.__get_all_mandatory_fields():
            if field not in data.keys():
                return False
        if data.get(DeploymentStatusRequestData.state) not in DeploymentStatusRequestData.__get_allowed_deployment_states():
            return False
        return True
