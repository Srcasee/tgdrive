from repositories.accounts import AccountRepository
from telegram.account_registry import account_lock
from telegram.client import archive_account_session, disconnect_account_session, restore_account_session
from telegram.runtime_events import notify_source_change


account_repository = AccountRepository()


async def delete_account(account_id):
    async with account_lock:
        account = account_repository.get(account_id)
        if not account:
            raise ValueError("account not found")

        session_name = account["session"]
        await disconnect_account_session(session_name)
        archive_account_session(session_name)

        deleted = account_repository.delete(account_id)
        if not deleted:
            try:
                restore_account_session(session_name)
            except Exception as restore_exc:
                print(
                    f"[ACCOUNT] restore after delete failure failed: "
                    f"{session_name}: {restore_exc!r}",
                    flush=True,
                )
            raise ValueError("account not found")

        notify_source_change()
        return {
            "status": "ok",
            "session": session_name,
            "session_archived": True,
        }
