from repositories.dialogs import DialogRepository
from repositories.sources import SourceRepository
from catalog.repository import CatalogRepository


class DialogDiscoveryService:
    def __init__(self, dialog_repository=None, source_repository=None, catalog_repository=None):
        self.dialog_repository = dialog_repository or DialogRepository()
        self.source_repository = source_repository or SourceRepository()
        self.catalog_repository = catalog_repository or CatalogRepository()

    async def refresh(self, client, account_id, account_name):
        if account_id is None:
            return

        dialogs = []
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            dialogs.append({
                "id": dialog.id,
                "name": dialog.name,
                "username": getattr(entity, "username", None),
                "entity_type": type(entity).__name__,
                "is_group": bool(dialog.is_group),
                "is_channel": bool(dialog.is_channel),
            })

        selectable = [d for d in dialogs if d["is_group"] or d["is_channel"]]
        selectable_ids = [d["id"] for d in selectable]

        removed_chat_ids = self.source_repository.remove_missing_dialogs(account_id, selectable_ids)
        removed_dialog_ids = self.dialog_repository.replace_for_account(account_id, selectable)

        stale_ids = sorted(set(removed_chat_ids) | set(removed_dialog_ids))
        if stale_ids:
            self.catalog_repository.deactivate_telegram_chats(account_id, stale_ids)

        print(f"[TG] dialogs refreshed: {account_name} ({len(selectable)})", flush=True)
