import asyncio
from asyncio.selector_events import BaseSelectorEventLoop

import pytest
from mockito import mock, expect

from app.utilities.background_task import BackgroundTask
from tests.async_mockito import async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestBackgroundTask:
    async def test__when_coroutine_with_no_arguments_is_passed__should_be_run_with_no_args(self):
        test_background_task = mock()

        # when
        expect(test_background_task, times=1).empty_coro().thenReturn(async_value(None))
        await BackgroundTask().run(test_background_task.empty_coro, ())

    async def test__when_coroutine_with_args_is_passed__should_be_run_with_all_of_them(self):
        test_background_task = mock()

        # when
        expect(test_background_task, times=1).empty_coro(1, 2).thenReturn(async_value(None))
        await BackgroundTask().run(test_background_task.empty_coro, (1, 2))

    async def test__when_task_is_ran__should_open_and_close_event_loop(self):
        test_background_task = mock()
        loop = mock()

        # given
        expect(test_background_task, times=2).empty_coro(1, 2)
        expect(asyncio).new_event_loop().thenReturn(loop)
        expect(asyncio).set_event_loop(loop)
        expect(asyncio).ensure_future(test_background_task.empty_coro(1, 2))
        expect(BaseSelectorEventLoop).close()

        # when
        await BackgroundTask().run(test_background_task.empty_coro, (1, 2))

    async def test__when_callback_is_passed__it_is_called_when_coro_is_done(self):
        test_background_task = mock()

        # when
        expect(test_background_task, times=1).empty_coro(1, 2).thenReturn(async_value(None))
        expect(test_background_task, times=1).callback(any).thenReturn(None)
        await BackgroundTask().run(test_background_task.empty_coro, (1, 2), callback=test_background_task.callback)
        await asyncio.sleep(0.2)

    async def test__when_callback_is_passed__and_coro_raises__callback_is_called_anyway(self):
        async def exception_coro():
            raise Exception()

        test_background_task = mock()

        # when
        expect(test_background_task, times=1).exception_coro(1, 2).thenReturn(exception_coro())
        expect(test_background_task, times=1).callback(any).thenReturn(None)
        await BackgroundTask().run(test_background_task.exception_coro, (1, 2), callback=test_background_task.callback)
        await asyncio.sleep(0.2)

