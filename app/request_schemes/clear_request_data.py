from typing import Dict, List


class ClearRequestData:
    event_type = 'eventType'
    job_name = 'jobName'
    jenkins_url = 'jenkins_url'

    @staticmethod
    def __get_all_mandatory_fields() -> List[str]:
        return [ClearRequestData.event_type, ClearRequestData.job_name, ClearRequestData.jenkins_url]

    @staticmethod
    def is_valid_clear_request_data(data: Dict) -> bool:
        for field in ClearRequestData.__get_all_mandatory_fields():
            if field not in data.keys():
                return False
        return True
