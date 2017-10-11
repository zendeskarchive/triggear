class RequestedParams:
    branch = 'branch'
    sha = 'sha'
    tag = 'tag'

    @staticmethod
    def get_allowed():
        return [RequestedParams.branch, RequestedParams.sha, RequestedParams.tag]
