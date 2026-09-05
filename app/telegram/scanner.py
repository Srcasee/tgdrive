import asyncio
import os

from ingestion.recognizer import TelegramMessageRecognizer
from ingestion.service import IngestionService
from repositories.resources import ResourceRepository
from repositories.sources import SourceRepository
from repositories.telegram_files import TelegramFileRepository


SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "300"))

source_repository = SourceRepository()
file_repository = TelegramFileRepository()
resource_repository = ResourceRepository()
ingestion_service = IngestionService(source_repository, file_repository, resource_repository)
recognizer = TelegramMessageRecognizer()


async def scan_dialogs(client, account_id):
    """Scan every enabled source for an account, one source at a time."""
    count = 0
    source_rows = await asyncio.to_thread(source_repository.list_enabled_for_account, account_id)
    for source in source_rows:
        try:
            count += await _scan_source(client, account_id, source)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(
                f"[SCAN] source failed: {source['name']} ({source['telegram_chat_id']}): {exc!r}",
                flush=True,
            )
    return count


async def _scan_source(client, account_id, source):
    source_for_scan = {**source, "sync_mode": "full"}
    chat_id = source["telegram_chat_id"]
    await asyncio.to_thread(ingestion_service.begin_source_scan, source_for_scan, account_id, chat_id)
    current_max_message_id = 0
    count = 0
    print("[SCAN] dialog:", source["name"], "id:", chat_id, flush=True)
    try:
        async for message in client.iter_messages(chat_id):
            observation = recognizer.recognize(
                message, chat_id=chat_id, account_id=account_id
            )
            if observation is None:
                continue
            current_max_message_id = max(current_max_message_id, message.id)
            await asyncio.to_thread(ingestion_service.ingest, observation)
            count += 1

        await asyncio.to_thread(
            ingestion_service.finish_source_scan,
            source_for_scan,
            account_id,
            chat_id,
            current_max_message_id,
        )
        return count
    except asyncio.CancelledError:
        await asyncio.to_thread(
            ingestion_service.fail_source_scan,
            source_for_scan,
            account_id,
            chat_id,
        )
        raise
    except Exception:
        await asyncio.to_thread(
            ingestion_service.fail_source_scan,
            source_for_scan,
            account_id,
            chat_id,
        )
        raise


async def scanner_loop(client, account_id, source, scanner_manager=None):
    """Continuously scan one Source; source changes do not restart other Sources."""
    source_id = source["id"]
    print("[SCAN] scanner loop started:", source["name"], "id:", source_id, flush=True)
    while True:
        try:
            current = await asyncio.to_thread(source_repository.get, source_id)
            if current is None or not current["enabled"]:
                return
            source_for_scan = {**source, **current}
            count = await _scan_source(client, account_id, source_for_scan)
            print(f"[SCAN] source {source_id} finished {count} files", flush=True)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[SCAN] source {source_id} error: {exc!r}", flush=True)

        await asyncio.sleep(SCAN_INTERVAL)
