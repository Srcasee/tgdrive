import asyncio
import os

from telethon import TelegramClient

from plugins.proxy.runtime import ProxyRuntime


async def main():
    api_id = int(os.environ["TG_API_ID"])
    api_hash = os.environ["TG_API_HASH"]
    phone = os.environ["TG_PHONE"]
    session = os.getenv("TG_SESSION", "/data/accounts/default")

    proxy = ProxyRuntime().resolve("default")
    client = TelegramClient(session, api_id, api_hash, proxy=proxy)

    print("[LOGIN] starting Telegram login", flush=True)
    await client.start(phone=phone)
    me = await client.get_me()
    print(f"[LOGIN] authorized: {me.username or me.first_name}", flush=True)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
