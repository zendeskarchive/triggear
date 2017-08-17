import asyncio
from typing import List


class AsyncIterFromList:
    def __init__(self, tasks: List):
        self.not_done = tasks
        self.done = list()
    async def __aiter__(self):
        return self
    async def __anext__(self):
        if self.not_done:
            self.done.append(self.not_done.pop())
        if not self.done:
            assert not self.not_done
            raise StopAsyncIteration()
        return self.done.pop()
