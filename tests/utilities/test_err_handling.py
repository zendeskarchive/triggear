import github
import pytest
import aiohttp.web

from app.exceptions.triggear_timeout_error import TriggearTimeoutError
from app.utilities.err_handling import handle_exceptions

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestErrHandling:
    async def test__when_method_does_not_raise_error__should_return_its_return_value(self):
        @handle_exceptions()
        async def non_raising_coro():
            return True

        assert await non_raising_coro()

    async def test__when_method_raises_key_error__should_return_400_response_bad_request(self):
        @handle_exceptions()
        async def key_error_raising_coro():
            return {}['missing_key']

        response: aiohttp.web.Response = await key_error_raising_coro()

        assert response.status == 400
        assert response.reason == 'Bad Request'
        assert response.text == "Error: 'missing_key' is missing in request"

    async def test__when_method_raises_github_exception__should_return_its_status__and_data_as_reason(self):
        @handle_exceptions()
        async def github_exception_raising_coro():
            raise github.GithubException(404, {'message': 'Not found'})

        response: aiohttp.web.Response = await github_exception_raising_coro()

        assert response.status == 404
        assert response.reason == "{'message': 'Not found'}"

    async def test__when_any_other_exception_is_raised__should_let_it_pass(self):
        @handle_exceptions()
        async def exception_raising_coro():
            raise Exception('The reason')

        with pytest.raises(Exception) as exception:
            await exception_raising_coro()
        assert str(exception.value) == "The reason"

    async def test__when_method_raises_timeout_error__should_return_400_response_bad_request(self):
        @handle_exceptions()
        async def timeout_error_raising_coro():
            raise TriggearTimeoutError('github resource')

        response: aiohttp.web.Response = await timeout_error_raising_coro()

        assert response.status == 504
        assert response.reason == 'Timeout when accessing resources: github resource'
        assert response.text == 'github resource'
