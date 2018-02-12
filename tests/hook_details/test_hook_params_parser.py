import pytest
from mockito import mock, expect

from app.hook_details.hook_details import HookDetails
from app.hook_details.hook_params_parser import HookParamsParser
from app.mongo.registration_cursor import RegistrationCursor

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestHookParamsParser:
    async def test__params_are_none__when_no_params_were_requested(self):
        hook_details: HookDetails = mock(spec=HookDetails, strict=True)
        registration_cursor: RegistrationCursor = mock({'requested_params': []}, spec=RegistrationCursor, strict=True)

        assert HookParamsParser.get_requested_parameters_values(hook_details, registration_cursor) is None

    async def test__when_requested_params_dont_match_allowed_params__result_is_none(self):
        hook_details: HookDetails = mock(spec=HookDetails, strict=True)
        registration_cursor: RegistrationCursor = mock({'requested_params': ['branch']}, spec=RegistrationCursor, strict=True)

        expect(hook_details).get_allowed_parameters().thenReturn({'sha': '123321', 'tag': '1.0'})
        assert HookParamsParser.get_requested_parameters_values(hook_details, registration_cursor) is None

    async def test__when_requested_param_match_allowed_params__result_is_params_dict_with_values(self):
        hook_details: HookDetails = mock(spec=HookDetails, strict=True)
        registration_cursor: RegistrationCursor = mock({'requested_params': ['tag', 'is_prerelease', 'invalid']},
                                                       spec=RegistrationCursor, strict=True)

        expect(hook_details).get_allowed_parameters().thenReturn({'release_target': '123321', 'is_prerelease': True, 'tag': '1.0'})
        assert HookParamsParser.get_requested_parameters_values(hook_details, registration_cursor) == {'tag': '1.0', 'is_prerelease': True}

    async def test__when_requested_prefixed_param_match_allowed_params__result_is_params_dict_with_values(self):
        hook_details: HookDetails = mock(spec=HookDetails, strict=True)
        registration_cursor: RegistrationCursor = mock({'requested_params': ['release_target:commitish', 'is_prerelease:is_it', 'invalid']},
                                                       spec=RegistrationCursor, strict=True)

        expect(hook_details).get_allowed_parameters().thenReturn({'release_target': '123321', 'is_prerelease': True, 'tag': '1.0'})
        assert HookParamsParser.get_requested_parameters_values(hook_details, registration_cursor) == {'commitish': '123321', 'is_it': True}
