import asyncio


_runtime_event = None
_source_change_requested = False
_dialog_refresh_requested = False


def initialize_runtime_events():
    global _runtime_event, _source_change_requested, _dialog_refresh_requested
    _runtime_event = asyncio.Event()
    _source_change_requested = False
    _dialog_refresh_requested = False


def initialize_source_change_event():
    # Backward-compatible alias for callers that still initialize the old event name.
    initialize_runtime_events()


def notify_source_change():
    global _source_change_requested
    _source_change_requested = True
    if _runtime_event is not None:
        _runtime_event.set()


def notify_dialog_refresh():
    global _dialog_refresh_requested
    _dialog_refresh_requested = True
    if _runtime_event is not None:
        _runtime_event.set()


async def wait_for_runtime_event(timeout: float):
    global _source_change_requested, _dialog_refresh_requested

    timed_out = False
    if _runtime_event is None:
        await asyncio.sleep(timeout)
        timed_out = True
    else:
        try:
            await asyncio.wait_for(_runtime_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            timed_out = True

    source_change = _source_change_requested
    dialog_refresh = _dialog_refresh_requested
    _source_change_requested = False
    _dialog_refresh_requested = False
    if _runtime_event is not None:
        _runtime_event.clear()

    return {
        "source_change": source_change,
        "dialog_refresh": dialog_refresh,
        "timed_out": timed_out,
    }


async def wait_for_source_change(timeout: float):
    event = await wait_for_runtime_event(timeout)
    return event["source_change"] or event["dialog_refresh"] or event["timed_out"]
