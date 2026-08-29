import asyncio
import os

from ingestion.service import IngestionService
from repositories.files import FileRepository
from repositories.resources import ResourceRepository
from repositories.sources import SourceRepository


SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "300"))

file_repository = FileRepository()
resource_repository = ResourceRepository()
source_repository = SourceRepository()


async def scan_dialogs(client, account_id):
    service = IngestionService(source_repository, file_repository, resource_repository)
    print("[SCAN] start telegram scan", flush=True)
    count = await service.scan_account(client, account_id)
    print(f"[SCAN] finished {count} files", flush=True)
    return count


async def scanner_loop(client, account_id):
    print("[SCAN] scanner loop started", flush=True)
    while True:
        try:
            await scan_dialogs(client, account_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print("[SCAN] error:", repr(exc), flush=True)
        print(f"[SCAN] sleep {SCAN_INTERVAL}s", flush=True)
        await asyncio.sleep(SCAN_INTERVAL)
