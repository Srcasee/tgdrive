import asyncio


_source_change_event = None


def initialize_source_change_event():
    global _source_change_event
    _source_change_event = asyncio.Event()


def notify_source_change():
    if _source_change_event is not None:
        _source_change_event.set()


async def wait_for_source_change(timeout: float):
    if _source_change_event is None:
        await asyncio.sleep(timeout)
        return False

    try:
        await asyncio.wait_for(_source_change_event.wait(), timeout=timeout)
        return True
    except asyncio.TimeoutError:
        return False
    finally:
        _source_change_event.clear()
