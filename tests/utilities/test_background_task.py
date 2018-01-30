import asyncio

import pytest
from mockito import mock, expect

from app.utilities.background_task import BackgroundTask

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestBackgroundTask:
    async def test__when_coroutine_is_passed__should_be_passed_to_loop_executor(self):
        coro = mock()
        loop = mock(spec=asyncio.BaseEventLoop, strict=True)

        background_task = BackgroundTask()

        expect(asyncio).get_event_loop().thenReturn(loop)
        expect(loop, times=1).run_in_executor(None, background_task.task_runner, coro, None)

        await background_task.run(coro)

    async def test__when_coroutine_is_passed__and_callback_is_passed__should_be_both_passed_to_loop_executor(self):
        coro = mock()
        callback = mock()
        loop = mock(spec=asyncio.BaseEventLoop, strict=True)

        background_task = BackgroundTask()

        expect(asyncio, times=1, strict=True).get_event_loop().thenReturn(loop)
        expect(loop, times=1, strict=True).run_in_executor(None, background_task.task_runner, coro, callback)

        await background_task.run(coro, callback)

    async def test__task_runner__executes_coro_on_new_event_loop(self):
        coro = mock()
        callback = mock()
        future = mock()
        loop = mock(spec=asyncio.BaseEventLoop, strict=True)

        expect(asyncio, times=1, strict=True).new_event_loop().thenReturn(loop)
        expect(asyncio, times=1, strict=True).set_event_loop(loop)
        expect(asyncio, times=1, strict=True).ensure_future(coro).thenReturn(future)
        expect(future, times=1, strict=True).add_done_callback(callback)
        expect(loop, times=1, strict=True).run_until_complete(future)
        expect(loop, times=1, strict=True).close()

        BackgroundTask.task_runner(coro, callback)
