from typing import List


class RequestedParams:
    branch = 'branch'
    sha = 'sha'
    tag = 'tag'

    @staticmethod
    def get_allowed() -> List[str]:
        return [RequestedParams.branch, RequestedParams.sha, RequestedParams.tag]
