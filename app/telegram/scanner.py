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
    """Scan all enabled Telegram sources for an account once."""
    count = 0
    source_rows = await asyncio.to_thread(source_repository.list_enabled_for_account, account_id)
    sources = {row["telegram_chat_id"]: row for row in source_rows}
    async for dialog in _iter_dialogs(client):
        source = sources.get(dialog.id)
        if source is None:
            continue
        try:
            count += await scan_source(client, account_id, dialog, source)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(
                f"[SCAN] source failed: {dialog.name} ({dialog.id}): {exc!r}",
                flush=True,
            )
    return count


async def scan_source(client, account_id, source):
    """Resolve one Telegram source to its dialog and scan it once.

    Telegram message iteration deliberately uses the resolved dialog entity,
    matching the working Telethon path used by the account-wide scanner.
    """
    target_chat_id = source["telegram_chat_id"]
    async for dialog in _iter_dialogs(client):
        if dialog.id != target_chat_id:
            continue
        return await _scan_source(client, account_id, dialog, source)

    print(
        f"[SCAN] dialog not found: {source['name']} ({target_chat_id})",
        flush=True,
    )
    return 0


async def _scan_source(client, account_id, dialog, source):
    source_for_scan = {**source, "sync_mode": "full"}
    await asyncio.to_thread(ingestion_service.begin_source_scan, source_for_scan, account_id, dialog.id)
    current_max_message_id = 0
    count = 0
    print("[SCAN] dialog:", dialog.name, "id:", dialog.id, flush=True)
    try:
        async for message in client.iter_messages(dialog.entity):
            observation = recognizer.recognize(
                message, chat_id=dialog.id, account_id=account_id
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
            dialog.id,
            current_max_message_id,
        )
        return count
    except asyncio.CancelledError:
        await asyncio.to_thread(
            ingestion_service.fail_source_scan,
            source_for_scan,
            account_id,
            dialog.id,
        )
        raise
    except Exception:
        await asyncio.to_thread(
            ingestion_service.fail_source_scan,
            source_for_scan,
            account_id,
            dialog.id,
        )
        raise


async def _iter_dialogs(client):
    async for dialog in client.iter_dialogs():
        yield dialog


async def scanner_loop(client, account_id, scanner_manager=None):
    """Compatibility loop for callers that still request an account-wide scan."""
    print("[SCAN] scanner loop started", flush=True)
    while True:
        try:
            count = await scan_dialogs(client, account_id)
            print(f"[SCAN] finished {count} files", flush=True)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print("[SCAN] error:", repr(exc), flush=True)

        print(f"[SCAN] wait {SCAN_INTERVAL}s or source change", flush=True)
        if scanner_manager is not None:
            await scanner_manager.wait_or_wakeup(SCAN_INTERVAL)
        else:
            await asyncio.sleep(SCAN_INTERVAL)
