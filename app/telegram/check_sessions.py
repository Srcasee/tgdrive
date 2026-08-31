import argparse
import asyncio

from telegram.client import get_clients


def parse_args():
    parser = argparse.ArgumentParser(description="Check Telegram account sessions")
    parser.add_argument("--account", help="check only this session/account name")
    return parser.parse_args()


async def check(name, client):
    await client.connect()
    try:
        authorized = await client.is_user_authorized()
        print(f"{name} authorized: {authorized}", flush=True)
        if authorized:
            me = await client.get_me()
            print(
                f" id: {me.id} username: {me.username!r} name: {me.first_name!r}",
                flush=True,
            )
    finally:
        await client.disconnect()


async def main():
    args = parse_args()
    clients = get_clients()
    if args.account:
        client = clients.get(args.account)
        if client is None:
            raise RuntimeError(f"Telegram account {args.account!r} not found or disabled")
        await check(args.account, client)
        return

    if not clients:
        print("No Telegram sessions found", flush=True)
        return

    for name, client in clients.items():
        await check(name, client)


if __name__ == "__main__":
    asyncio.run(main())
