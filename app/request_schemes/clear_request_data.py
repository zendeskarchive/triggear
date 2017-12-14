from typing import Dict


class ClearRequestData:
    event_type = 'eventType'
    job_name = 'jobName'

    @staticmethod
    def __get_all_mandatory_fields():
        return [ClearRequestData.event_type, ClearRequestData.job_name]

    @staticmethod
    def is_valid_clear_request_data(data: Dict):
        for field in ClearRequestData.__get_all_mandatory_fields():
            if field not in data.keys():
                return False
        return True
