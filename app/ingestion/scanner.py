from .recognizer import TelegramMessageRecognizer


recognizer = TelegramMessageRecognizer()


async def find_source_dialog(client, source):
    """Resolve a configured Source to its Telegram dialog."""
    target_chat_id = source["telegram_chat_id"]
    async for dialog in client.iter_dialogs():
        if dialog.id == target_chat_id:
            return dialog
    return None


async def iter_observations(client, dialog, account_id):
    """Traverse a dialog and yield normalized media observations only."""
    async for message in client.iter_messages(dialog.entity):
        observation = recognizer.recognize(
            message, chat_id=dialog.id, account_id=account_id
        )
        if observation is not None:
            yield observation
