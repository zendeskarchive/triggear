import pytest

from app.enums.jenkins_build_state import JenkinsBuildState

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestJenkinsBuildState:
    async def test__final_state_returns_error__when_build_info_is_none(self):
        assert JenkinsBuildState.get_by_build_info(None) is JenkinsBuildState.ERROR

    async def test__final_state_returns_error__when_result_is_error(self):
        assert JenkinsBuildState.get_by_build_info({'result': ''}) is JenkinsBuildState.ERROR
        assert JenkinsBuildState.get_by_build_info({'result': 'error'}) is JenkinsBuildState.ERROR
        assert JenkinsBuildState.get_by_build_info({'result': 'ERROR'}) is JenkinsBuildState.ERROR

    async def test__final_state_returns_success__when_result_is_success(self):
        assert JenkinsBuildState.get_by_build_info({'result': 'SUCCESS'}) is JenkinsBuildState.SUCCESS

    async def test__final_state_returns_failure__when_result_is_failure(self):
        assert JenkinsBuildState.get_by_build_info({'result': 'FAILURE'}) is JenkinsBuildState.FAILURE

    async def test__final_state_returns_aborted__when_result_is_aborted(self):
        assert JenkinsBuildState.get_by_build_info({'result': 'ABORTED'}) is JenkinsBuildState.ABORTED

    async def test__final_state_returns_unstable__when_result_is_unstable(self):
        assert JenkinsBuildState.get_by_build_info({'result': 'UNSTABLE'}) is JenkinsBuildState.UNSTABLE
