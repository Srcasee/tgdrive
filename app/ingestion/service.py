import asyncio


class IngestionService:
    """Own Telegram observation -> resource recognition persistence."""

    def __init__(self, source_repository, file_repository, resource_repository):
        self.source_repository = source_repository
        self.file_repository = file_repository
        self.resource_repository = resource_repository

    async def scan_account(self, client, account_id):
        count = 0
        source_rows = self.source_repository.list_enabled_for_account(account_id)
        sources = {row["telegram_chat_id"]: row for row in source_rows}
        async for dialog in client.iter_dialogs():
            if dialog.id not in sources:
                continue
            count += await self.scan_source(client, account_id, dialog, sources[dialog.id])
        return count

    async def scan_source(self, client, account_id, dialog, source):
        source_id = source["id"]
        full_sync = source["sync_mode"] == "full"
        self.source_repository.mark_scanning(source_id)
        print("[SCAN] dialog:", dialog.name, "id:", dialog.id, flush=True)
        if full_sync:
            self.file_repository.mark_checking(account_id, dialog.id)

        last_message_id = source["last_message_id"] or 0
        current_max_message_id = last_message_id
        count = 0
        try:
            message_kwargs = {} if full_sync else {"min_id": last_message_id}
            async for message in client.iter_messages(dialog.entity, **message_kwargs):
                observation = self._recognize_message(message, dialog.id, account_id)
                if observation is None:
                    continue
                current_max_message_id = max(current_max_message_id, message.id)
                resource_id = self.resource_repository.get_or_create(**observation["resource"])
                self.file_repository.upsert_verified_message(
                    **observation["file"], resource_id=resource_id
                )
                count += 1

            if full_sync:
                self.file_repository.mark_unverified_deleted(account_id, dialog.id)
            self.source_repository.mark_success(source_id, current_max_message_id)
            return count
        except asyncio.CancelledError:
            self._reset_after_failure(account_id, dialog.id, source_id, full_sync)
            raise
        except Exception:
            self._reset_after_failure(account_id, dialog.id, source_id, full_sync)
            raise

    @staticmethod
    def _recognize_message(message, chat_id, account_id):
        if not message.media or not message.file:
            return None
        filename = message.file.name or f"{message.id}.bin"
        size = message.file.size
        mime_type = message.file.mime_type
        return {
            "resource": {"filename": filename, "size": size, "mime_type": mime_type},
            "file": {
                "filename": filename,
                "size": size,
                "mime_type": mime_type,
                "chat_id": chat_id,
                "message_id": message.id,
                "upload_time": int(message.date.timestamp()),
                "account_id": account_id,
            },
        }

    def _reset_after_failure(self, account_id, chat_id, source_id, full_sync):
        if full_sync:
            self.file_repository.reset_checking(account_id, chat_id)
        self.source_repository.mark_failed(source_id)
