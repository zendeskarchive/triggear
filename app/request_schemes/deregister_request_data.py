from typing import Dict


class DeregisterRequestData:
    event_type = 'eventType'
    caller = 'caller'
    job_name = 'jobName'

    @staticmethod
    def __get_all_mandatory_fields():
        return [DeregisterRequestData.event_type, DeregisterRequestData.caller, DeregisterRequestData.job_name]

    @staticmethod
    def is_valid_deregister_request_data(data: Dict):
        for field in DeregisterRequestData.__get_all_mandatory_fields():
            if field not in data.keys():
                return False
        return True
