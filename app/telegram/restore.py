from repositories.accounts import AccountRepository
from telegram.account_lock import account_lock
from telegram.client import get_client, restore_account_session as move_restored_session
from telegram.runtime_events import notify_dialog_refresh


account_repository = AccountRepository()


async def restore_account(session_name):
    async with account_lock:
        session_path = move_restored_session(session_name)
        account_repository.upsert_session(session_path.stem)
        get_client(session_path.stem)
        notify_dialog_refresh()
        return {
            "status": "ok",
            "session": session_path.name,
            "restored": True,
        }
