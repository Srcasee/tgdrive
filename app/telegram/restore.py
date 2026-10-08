from repositories.accounts import AccountRepository
from telegram.account_registry import account_lock
from telegram.client import refresh_clients, restore_account_session
from telegram.runtime_events import notify_source_change


account_repository = AccountRepository()


def restore_account(session_name):
    with_account_lock = account_lock

    # The lock is an asyncio.Lock shared with runtime reconciliation. The
    # restore operation itself is synchronous, so the API layer must call the
    # async wrapper below.
    return session_name


async def restore_account_session_to_runtime(session_name):
    async with account_lock:
        session_path = restore_account_session(session_name)
        account_repository.upsert_session(session_path.stem)
        refresh_clients([session_path.stem])
        notify_source_change()
        return session_path
