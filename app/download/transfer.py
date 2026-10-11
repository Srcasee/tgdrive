import asyncio
import hashlib


async def tracked_stream(
    chunks,
    *,
    service,
    record_id,
    expected_bytes,
    verify=None,
    hash_content=False,
):
    """Track a streaming response independently of the HTTP routing layer."""
    transferred = 0
    digest = hashlib.sha256() if hash_content else None
    try:
        async for chunk in chunks:
            remaining = expected_bytes - transferred
            if remaining <= 0:
                break
            chunk = chunk[:remaining]
            if not chunk:
                continue
            transferred += len(chunk)
            if digest is not None:
                digest.update(chunk)
            yield chunk

        if transferred != expected_bytes:
            raise RuntimeError(
                f"Telegram source ended early: expected {expected_bytes} bytes, got {transferred}"
            )
        if digest is not None and verify is not None:
            verify(digest.hexdigest())
        if record_id is not None:
            service.complete(record_id, transferred)
    except asyncio.CancelledError:
        if record_id is not None:
            service.fail(record_id, transferred, "download cancelled by client")
        raise
    except Exception as exc:
        if record_id is not None:
            service.fail(record_id, transferred, str(exc))
        raise
    finally:
        close = getattr(chunks, "aclose", None)
        if close is not None:
            try:
                result = close()
                if hasattr(result, "__await__"):
                    await result
            except Exception as exc:
                print("[DOWNLOAD] stream close error", repr(exc), flush=True)
