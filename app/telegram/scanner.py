import asyncio
import os

from repositories.files import FileRepository
from repositories.sources import SourceRepository


TG_STORAGE_CHAT_ID = int(os.getenv("TG_STORAGE_CHAT_ID", "0"))
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "300"))

file_repository = FileRepository()
source_repository = SourceRepository()


async def scan_dialogs(client, account_id):
    return await _scan_dialogs(client, account_id)


async def _scan_dialogs(client, account_id):
    print("[SCAN] start telegram scan", flush=True)
    source_rows = source_repository.list_enabled_for_account(account_id)
    sources = {row["telegram_chat_id"]: row for row in source_rows}
    source_chat_ids = set(sources)
    count = 0

    async for dialog in client.iter_dialogs():
        if dialog.id not in source_chat_ids:
            continue

        source = sources[dialog.id]
        source_repository.mark_scanning(source["id"])
        print("[SCAN] dialog:", dialog.name, "id:", dialog.id, flush=True)

        if source["sync_mode"] == "full":
            file_repository.mark_checking(account_id, dialog.id)

        last_message_id = source["last_message_id"] or 0
        current_max_message_id = last_message_id

        async for message in client.iter_messages(
            dialog.entity,
            min_id=last_message_id,
        ):
            if not message.media or not message.file:
                continue

            current_max_message_id = max(current_max_message_id, message.id)
            filename = message.file.name or f"{message.id}.bin"
            print("[SCAN] file:", message.id, filename, flush=True)

            # One DB transaction per indexed message instead of two independent
            # transactions. This also fixes the old ordering bug where a newly
            # inserted file could miss the preceding mark_verified UPDATE.
            file_repository.upsert_verified_message(
                filename=filename,
                size=message.file.size,
                mime_type=message.file.mime_type,
                chat_id=dialog.id,
                message_id=message.id,
                upload_time=int(message.date.timestamp()),
                account_id=account_id,
            )
            count += 1

        if source["sync_mode"] == "full":
            file_repository.mark_unverified_deleted(account_id, dialog.id)

        source_repository.mark_success(source["id"], current_max_message_id)

    print(f"[SCAN] finished {count} files", flush=True)


async def scanner_loop(client, account_id):
    print("[SCAN] scanner loop started", flush=True)
    while True:
        try:
            await scan_dialogs(client, account_id)
        except Exception as exc:
            print("[SCAN] error:", repr(exc), flush=True)
        print(f"[SCAN] sleep {SCAN_INTERVAL}s", flush=True)
        await asyncio.sleep(SCAN_INTERVAL)
