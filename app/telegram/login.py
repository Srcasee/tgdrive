import asyncio
import os

from telethon import TelegramClient

from plugins.runtime import PluginRuntime


async def main():
    api_id = int(os.environ["TG_API_ID"])
    api_hash = os.environ["TG_API_HASH"]
    phone = os.environ["TG_PHONE"]
    session = os.getenv("TG_SESSION", "/data/accounts/default")

    plugin_runtime = PluginRuntime()
    proxy_plugin = plugin_runtime.get_capability("telegram.proxy")
    proxy = proxy_plugin.get_proxy("default") if proxy_plugin else None

    client = TelegramClient(session, api_id, api_hash, proxy=proxy)

    print("[LOGIN] starting Telegram login", flush=True)
    await client.start(phone=phone)
    me = await client.get_me()
    print(f"[LOGIN] authorized: {me.username or me.first_name}", flush=True)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
