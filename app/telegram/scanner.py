import asyncio
import os

from ingestion.recognizer import TelegramMessageRecognizer
from ingestion.service import IngestionService
from repositories.files import FileRepository
from repositories.resources import ResourceRepository
from repositories.sources import SourceRepository


SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "300"))

source_repository = SourceRepository()
file_repository = FileRepository()
resource_repository = ResourceRepository()
ingestion_service = IngestionService(source_repository, file_repository, resource_repository)
recognizer = TelegramMessageRecognizer()


async def scan_dialogs(client, account_id):
    """Discover Telegram messages and hand normalized observations to ingestion."""
    count = 0
    source_rows = source_repository.list_enabled_for_account(account_id)
    sources = {row["telegram_chat_id"]: row for row in source_rows}
    for dialog in _iter_dialogs(client):
        if dialog.id not in sources:
            continue
        count += await _scan_source(client, account_id, dialog, sources[dialog.id])
    return count


async def _scan_source(client, account_id, dialog, source):
    full_sync = ingestion_service.begin_source_scan(source, account_id, dialog.id)
    last_message_id = source["last_message_id"] or 0
    current_max_message_id = last_message_id
    count = 0
    print("[SCAN] dialog:", dialog.name, "id:", dialog.id, flush=True)
    try:
        message_kwargs = {} if full_sync else {"min_id": last_message_id}
        async for message in client.iter_messages(dialog.entity, **message_kwargs):
            observation = recognizer.recognize(
                message, chat_id=dialog.id, account_id=account_id
            )
            if observation is None:
                continue
            current_max_message_id = max(current_max_message_id, message.id)
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


async def _iter_dialogs(client):
    async for dialog in client.iter_dialogs():
        yield dialog


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
