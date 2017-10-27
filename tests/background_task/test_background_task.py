import asyncio
from asyncio.selector_events import BaseSelectorEventLoop
from unittest.mock import Mock

import pytest
from pytest_mock import MockFixture

from app.utilities.background_task import BackgroundTask

pytestmark = pytest.mark.asyncio

async def test_coro_no_args(empty_coro: Mock, background_task: BackgroundTask):
    await background_task.run(empty_coro, ())
    await asyncio.sleep(0.1)

    empty_coro.assert_called_once_with()

async def test_coro_with_args(empty_coro: Mock, background_task: BackgroundTask):
    await background_task.run(empty_coro, (12,))
    await asyncio.sleep(0.1)

    empty_coro.assert_called_once_with(12)

async def test_loop_is_opened_and_closed(mocker: MockFixture, empty_coro: Mock, background_task: BackgroundTask):
    mocker.spy(asyncio, 'new_event_loop')
    mocker.spy(BaseSelectorEventLoop, 'close')

    await background_task.run(empty_coro, ())
    await asyncio.sleep(0.1)

    assert asyncio.new_event_loop.call_count == 1
    assert BaseSelectorEventLoop.close.call_count == 1

async def test_success_callback_is_called(empty_coro: Mock, callback: Mock, background_task: BackgroundTask):
    await background_task.run(empty_coro, (), callback=callback)
    await asyncio.sleep(0.1)

    callback.assert_called_once()
    assert 'result=((), {})' in str(callback.call_args)


async def test_exception_callback_is_called(exception_coro: Mock, callback: Mock, background_task: BackgroundTask):
    await background_task.run(exception_coro, (), callback=callback)
    await asyncio.sleep(0.1)

    callback.assert_called_once()
    assert 'Exception()' in str(callback.call_args)

