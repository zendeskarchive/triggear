from typing import Dict
from collections import Counter


class StatusRequestData:
    repository = 'repository'
    sha = 'sha'
    state = 'state'
    description = 'description'
    url = 'url'
    context = 'context'

    @staticmethod
    def is_valid_status_data(data: Dict) -> bool:
        return Counter([StatusRequestData.repository,
                        StatusRequestData.sha,
                        StatusRequestData.state,
                        StatusRequestData.description,
                        StatusRequestData.url,
                        StatusRequestData.context]) == Counter(data.keys())
