import asyncio
import hashlib
import logging
import time

logger = logging.getLogger(__name__)


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
    started_at = time.monotonic()
    digest = hashlib.sha256() if hash_content else None
    logger.debug("download_stream_opened", extra={"download_id": record_id, "expected_bytes": expected_bytes, "hash_content": hash_content})
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
        logger.info("download_stream_verified", extra={"download_id": record_id, "bytes_transferred": transferred, "duration_seconds": time.monotonic() - started_at, "sha256_checked": digest is not None and verify is not None})
    except asyncio.CancelledError:
        logger.info("download_stream_cancelled", extra={"download_id": record_id, "bytes_transferred": transferred, "duration_seconds": time.monotonic() - started_at})
        if record_id is not None:
            service.fail(record_id, transferred, "download cancelled by client")
        raise
    except GeneratorExit:
        logger.info("download_stream_closed_early", extra={"download_id": record_id, "bytes_transferred": transferred})
        if record_id is not None:
            service.fail(record_id, transferred, "download stream closed before completion")
        raise
    except Exception as exc:
        logger.exception("download_stream_failed", extra={"download_id": record_id, "bytes_transferred": transferred, "duration_seconds": time.monotonic() - started_at})
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
                logger.warning("download_upstream_close_failed", extra={"download_id": record_id, "error": repr(exc)})
