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
    on_digest=None,
    hash_content=False,
):
    """Track bytes and optionally record a SHA-256 digest for a complete body.

    The digest callback records/promotes the observed digest; it does not compare
    against a previously trusted expected digest. Since this is streaming, the
    callback runs after the body bytes have already been yielded to the client.
    """
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
        if digest is not None and on_digest is not None:
            on_digest(digest.hexdigest())
        if record_id is not None:
            service.complete(record_id, transferred)
        logger.info("download_stream_completed", extra={"download_id": record_id, "bytes_transferred": transferred, "duration_seconds": time.monotonic() - started_at, "sha256_recorded": digest is not None and on_digest is not None})
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
