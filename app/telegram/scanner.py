import asyncio
import os

from ingestion.recognizer import TelegramMessageRecognizer
from ingestion.service import IngestionService
from repositories.resources import ResourceRepository
from repositories.sources import SourceRepository
from repositories.telegram_files import TelegramFileRepository


# Resource scanning interval. Dialog discovery is not periodic; it is only
# performed during Telegram account setup/manual admin refresh.
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "300"))

source_repository = SourceRepository()
file_repository = TelegramFileRepository()
resource_repository = ResourceRepository()
ingestion_service = IngestionService(source_repository, file_repository, resource_repository)
recognizer = TelegramMessageRecognizer()


async def scan_dialogs(client, account_id):
    """Scan enabled Telegram sources.

    Dialog discovery is intentionally not part of the recurring scanner loop.
    The previous implementation called iter_dialogs() periodically only to find
    enabled sources, which made Telegram dialog state reconciliation implicit.
    Dialog discovery should be triggered explicitly during account setup or by
    an admin action.
    """
    count = 0
    source_rows = source_repository.list_enabled_for_account(account_id)
    for source in source_rows:
        try:
            dialog = await client.get_entity(source["telegram_chat_id"])
        except Exception:
            continue
        count += await _scan_source(client, account_id, dialog, source)
    return count


async def _scan_source(client, account_id, dialog, source):
    full_sync = ingestion_service.begin_source_scan(source, account_id, dialog.id)
    last_message_id = source["last_message_id"] or 0
    current_max_message_id = last_message_id
    count = 0
    print("[SCAN] dialog:", getattr(dialog, "title", dialog.id), "id:", dialog.id, flush=True)
    try:
        message_kwargs = {} if full_sync else {"min_id": last_message_id}
        async for message in client.iter_messages(dialog, **message_kwargs):
            observation = recognizer.recognize(
                message, chat_id=dialog.id, account_id=account_id
            )
            if observation is None:
                continue
            current_max_message_id = max(current_max_message_id, message.id)
            # Scanning is metadata-only. Content hashing is deliberately deferred
            # until a user requests delivery, so indexing never downloads payloads.
            ingestion_service.ingest(observation)
            count += 1

        ingestion_service.finish_source_scan(
            source, account_id, dialog.id, current_max_message_id
        )
        return count
    except asyncio.CancelledError:
        ingestion_service.fail_source_scan(source, account_id, dialog.id)
        raise
    except Exception:
        ingestion_service.fail_source_scan(source, account_id, dialog.id)
        raise


async def discover_dialogs(client):
    """Return only Telegram Channel dialogs for admin display.

    This is manual discovery only. Non-Channel dialogs are intentionally
    excluded from the management view.
    """
    dialogs = []
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if getattr(entity, "__class__", None).__name__ != "Channel":
            continue
        dialogs.append(dialog)
    return dialogs


async def scanner_loop(client, account_id):
    print("[SCAN] scanner loop started", flush=True)
    while True:
        try:
            count = await scan_dialogs(client, account_id)
            print(f"[SCAN] finished {count} files", flush=True)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print("[SCAN] error:", repr(exc), flush=True)
        print(f"[SCAN] sleep {SCAN_INTERVAL}s", flush=True)
        await asyncio.sleep(SCAN_INTERVAL)
