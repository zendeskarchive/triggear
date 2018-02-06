from typing import Dict, List, Any


class DeregisterRequestData:
    event_type = 'eventType'
    caller = 'caller'
    job_name = 'jobName'
    jenkins_url = 'jenkins_url'

    @staticmethod
    def __get_all_mandatory_fields() -> List[str]:
        return [DeregisterRequestData.event_type, DeregisterRequestData.caller, DeregisterRequestData.job_name, DeregisterRequestData.jenkins_url]

    @staticmethod
    def is_valid_deregister_request_data(data: Dict[str, Any]) -> bool:
        for field in DeregisterRequestData.__get_all_mandatory_fields():
            if field not in data.keys():
                return False
        return True
