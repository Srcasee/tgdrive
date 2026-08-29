"""Real-server Telegram connectivity smoke test.

Run this on the deployment host/container with TG_PROXY_ENABLED=true and valid
Telegram credentials. It exercises the exact proxy object used by tgdrive.
"""

import asyncio
import os

from telethon import TelegramClient

from config import settings, validate_telegram_credentials
from plugins.proxy.plugin import ProxyPlugin


async def main():
    validate_telegram_credentials()
    session = os.environ.get("TG_PROXY_TEST_SESSION", "proxy-smoke")
    proxy = ProxyPlugin().get_proxy()
    if proxy is None:
        raise SystemExit("TG_PROXY_ENABLED must be true for the proxy smoke test")

    client = TelegramClient(session, settings.TG_API_ID, settings.TG_API_HASH, proxy=proxy)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise SystemExit("Telegram session is not authorized")
        me = await client.get_me()
        print(f"Telegram proxy connectivity OK: user_id={me.id}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
