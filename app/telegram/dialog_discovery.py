class DialogDiscoveryService:
    """Read the complete Dialog list from Telegram for one authorized client."""

    async def discover(self, client):
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
        return dialogs
