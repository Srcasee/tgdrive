from dataclasses import replace

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
    topic_names = {}
    async for message in client.iter_messages(dialog.entity):
        observation = recognizer.recognize(
            message, chat_id=dialog.id, account_id=account_id
        )
        if observation is not None:
            topic_id = observation.topic_id
            if topic_id is not None:
                if topic_id not in topic_names:
                    topic_names[topic_id] = await _get_topic_name(
                        client, dialog.entity, topic_id
                    )
                observation = replace(observation, topic_name=topic_names[topic_id])
            yield observation


async def _get_topic_name(client, entity, topic_id):
    """Read a forum topic's title from its root service message when available."""
    get_messages = getattr(client, "get_messages", None)
    if get_messages is None:
        return None
    try:
        root_message = await get_messages(entity, ids=topic_id)
    except Exception:
        # Topic titles are enrichment metadata; a failed lookup must not stop scanning.
        return None
    action = getattr(root_message, "action", None)
    title = getattr(action, "title", None)
    return title.strip() if isinstance(title, str) and title.strip() else None
