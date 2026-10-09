import asyncio

from . import scanner


class SourceScanCoordinator:
    """Coordinate one Source scan cycle and its ingestion state transitions."""

    def __init__(self, ingestion_service):
        self.ingestion_service = ingestion_service

    async def scan_source(self, client, account_id, source):
        dialog = await scanner.find_source_dialog(client, source)
        if dialog is None:
            print(
                f"[SCAN] dialog not found: {source['name']} ({source['telegram_chat_id']})",
                flush=True,
            )
            return 0

        source_for_scan = {**source, "sync_mode": "full"}
        await asyncio.to_thread(
            self.ingestion_service.begin_source_scan,
            source_for_scan,
            account_id,
            dialog.id,
        )
        current_max_message_id = 0
        count = 0
        print("[SCAN] dialog:", dialog.name, "id:", dialog.id, flush=True)
        try:
            async for observation in scanner.iter_observations(
                client, dialog, account_id
            ):
                current_max_message_id = max(
                    current_max_message_id, observation.message_id
                )
                await asyncio.to_thread(
                    self.ingestion_service.ingest, observation
                )
                count += 1

            await asyncio.to_thread(
                self.ingestion_service.finish_source_scan,
                source_for_scan,
                account_id,
                dialog.id,
                current_max_message_id,
            )
            return count
        except asyncio.CancelledError:
            await asyncio.to_thread(
                self.ingestion_service.fail_source_scan,
                source_for_scan,
                account_id,
                dialog.id,
            )
            raise
        except Exception:
            await asyncio.to_thread(
                self.ingestion_service.fail_source_scan,
                source_for_scan,
                account_id,
                dialog.id,
            )
            raise
