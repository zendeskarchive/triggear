import asyncio
from typing import Optional
from typing import Tuple


class BackgroundTask:
    async def run(self, coro, args, callback=None):
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, self.task_runner, coro, args, callback)

    @staticmethod
    def task_runner(coro, args: Tuple, callback: Optional) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        fut = asyncio.ensure_future(coro(*args))
        if callback is not None:
            fut.add_done_callback(callback)

        loop.run_until_complete(fut)
        loop.close()
