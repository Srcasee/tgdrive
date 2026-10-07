import os
from telethon import TelegramClient


api_id = int(os.getenv("TG_API_ID"))
api_hash = os.getenv("TG_API_HASH")


client = TelegramClient(
    "telegram_session",
    api_id,
    api_hash,
    proxy={
        "proxy_type": "socks5",
        "addr": "127.0.0.1",
        "port": 1080,
        "rdns": True
    }
)


async def main():

    await client.start()

    dialogs = await client.get_dialogs()

    print("\n===== Telegram会话列表 =====\n")

    for dialog in dialogs:

        print(
            f"名称: {dialog.name}"
        )

        print(
            f"ID: {dialog.id}"
        )

        print(
            f"类型: {type(dialog.entity).__name__}"
        )

        print("------------------------")


    await client.disconnect()


with client:
    client.loop.run_until_complete(main())
