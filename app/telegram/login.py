import argparse
import asyncio
import os
from pathlib import Path

from telethon import TelegramClient

from database_pool import close_pool, initialize, open_pool
from plugins.runtime import PluginRuntime
from repositories.accounts import AccountRepository


def parse_args():
    parser = argparse.ArgumentParser(description="Log in a Telegram account")
    parser.add_argument(
        "--account",
        default=os.getenv("TG_ACCOUNT_NAME"),
        help="session/account name; also accepted through TG_ACCOUNT_NAME",
    )
    args = parser.parse_args()
    if not args.account:
        parser.error("--account is required (or set TG_ACCOUNT_NAME)")
    if args.account in {".", ".."} or "/" in args.account or "\\" in args.account:
        parser.error("account name must be a single path-safe name")
    return args


async def main():
    args = parse_args()
    api_id = int(os.environ["TG_API_ID"])
    api_hash = os.environ["TG_API_HASH"]
    phone = os.environ["TG_PHONE"]
    session_dir = Path(os.getenv("TG_SESSION_DIR", "/data/accounts"))
    session_dir.mkdir(parents=True, exist_ok=True)
    session = str(session_dir / args.account)

    open_pool()
    try:
        initialize()

        plugin_runtime = PluginRuntime()
        proxy_plugin = plugin_runtime.get_capability("telegram.proxy")
        proxy = proxy_plugin.get_proxy(args.account) if proxy_plugin else None

        client = TelegramClient(session, api_id, api_hash, proxy=proxy)

        print(f"[LOGIN] starting Telegram login account={args.account}", flush=True)
        try:
            await client.start(phone=phone)
            me = await client.get_me()
            AccountRepository().upsert_session(
                args.account, me.username or me.first_name or args.account
            )
            print(
                f"[LOGIN] authorized account={args.account}: {me.username or me.first_name}",
                flush=True,
            )
        finally:
            await client.disconnect()
    finally:
        close_pool()


if __name__ == "__main__":
    asyncio.run(main())
