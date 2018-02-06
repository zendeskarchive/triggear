from enum import Enum
from typing import Dict, Optional


class JenkinsBuildState(Enum):
    SUCCESS = ('success', 'build succeeded')
    UNSTABLE = ('success', 'build unstable')
    FAILURE = ('failure', 'build failed')
    ABORTED = ('failure', 'build aborted')
    ERROR = ('error', 'build error')

    def __init__(self, state, description) -> None:
        self.state = state
        self.description = description

    @staticmethod
    def get_by_build_info(build_info: Optional[Dict]) -> 'JenkinsBuildState':
        if build_info is not None:
            result = build_info['result']
            if result == 'SUCCESS':
                return JenkinsBuildState.SUCCESS
            elif result == "UNSTABLE":
                return JenkinsBuildState.UNSTABLE
            elif result == "FAILURE":
                return JenkinsBuildState.FAILURE
            elif result == "ABORTED":
                return JenkinsBuildState.ABORTED
        return JenkinsBuildState.ERROR
