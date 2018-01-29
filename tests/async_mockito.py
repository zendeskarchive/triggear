async def async_value(value):
    """
    Gives an object which can be used in .thenReturn for methods that are coroutines
    :param value: what should be returned after coroutine is awaited
    :return: coroutine that can be awaited
    """
    return value


# noinspection PyPep8Naming
class async_iter:
    """
    Object that can be used in async for. Specify it in .thenReturn as needed.
    """
    def __init__(self, *items: any):
        self.not_done = list(items)
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