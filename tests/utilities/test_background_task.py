from asyncio.selector_events import BaseSelectorEventLoop

import pytest
from asynctest import Mock, asyncio
from mockito import when

from app.utilities.background_task import BackgroundTask

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestBackgroundTask:
    @staticmethod
    async def empty_coro(*args, **kwargs):
        return args, kwargs

    @staticmethod
    def exception_coro(*args, **kwargs):
        raise Exception()

    @staticmethod
    def callback():
        pass

    async def test__when_coroutine_with_no_arguments_is_passed__should_be_run_with_no_args(self):
        empty_coro = Mock(wraps=self.empty_coro)

        # when
        await BackgroundTask().run(empty_coro, ())
        await asyncio.sleep(0.1)

        # then
        empty_coro.assert_called_once_with()

    async def test__when_coroutine_with_args_is_passed__should_be_run_with_all_of_them(self):
        empty_coro = Mock(wraps=self.empty_coro)

        # when
        await BackgroundTask().run(empty_coro, (1, 2))
        await asyncio.sleep(0.1)

        # then
        empty_coro.assert_called_once_with(1, 2)

    async def test__when_task_is_ran__should_open_and_close_event_loop(self):
        empty_coro = Mock(wraps=self.empty_coro)

        # given
        when(asyncio).new_event_loop()
        when(BaseSelectorEventLoop).close()

        # when
        await BackgroundTask().run(empty_coro, (1, 2))
        await asyncio.sleep(0.1)

    async def test__when_callback_is_passed__it_is_called_when_coro_is_done(self):
        callback = Mock(wraps=self.callback)

        # when
        await BackgroundTask().run(self.empty_coro, (1, 2), callback=callback)
        await asyncio.sleep(0.2)

        callback.assert_called_once()
