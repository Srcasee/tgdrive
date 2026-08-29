from .recognizer import TelegramMessageRecognizer


class IngestionService:
    """Own recognition persistence and full/incremental reconciliation semantics."""

    def __init__(self, source_repository, file_repository, resource_repository):
        self.source_repository = source_repository
        self.file_repository = file_repository
        self.resource_repository = resource_repository

    def begin_source_scan(self, source, account_id, chat_id):
        full_sync = source["sync_mode"] == "full"
        self.source_repository.mark_scanning(source["id"])
        if full_sync:
            self.file_repository.mark_checking(account_id, chat_id)
        return full_sync

    def ingest(self, observation):
        resource_id = self.resource_repository.get_or_create(**observation.resource_metadata)
        self.file_repository.upsert_verified_message(
            **observation.file_metadata,
            resource_id=resource_id,
        )
        return resource_id

    def finish_source_scan(self, source, account_id, chat_id, current_max_message_id):
        full_sync = source["sync_mode"] == "full"
        if full_sync:
            self.file_repository.mark_unverified_deleted(account_id, chat_id)
        self.source_repository.mark_success(source["id"], current_max_message_id)

    def fail_source_scan(self, source, account_id, chat_id):
        full_sync = source["sync_mode"] == "full"
        if full_sync:
            self.file_repository.reset_checking(account_id, chat_id)
        self.source_repository.mark_failed(source["id"])

    @staticmethod
    def recognizer():
        return TelegramMessageRecognizer()
