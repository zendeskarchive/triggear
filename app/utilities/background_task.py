import asyncio
from typing import Coroutine, Callable


class BackgroundTask:
    @staticmethod
    async def run(coro: Coroutine, callback: Callable=None):
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, BackgroundTask.task_runner, coro, callback)

    @staticmethod
    def task_runner(coro: Coroutine, callback: Callable) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        fut = asyncio.ensure_future(coro)
        if callback is not None:
            fut.add_done_callback(callback)

        loop.run_until_complete(fut)
        loop.close()
