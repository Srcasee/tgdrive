import asyncio
import os
import re
import uuid
from pathlib import Path

from telethon import TelegramClient, errors

from config import settings, validate_telegram_credentials
from plugins.runtime import PluginRuntime
from repositories.accounts import AccountRepository
from telegram import client as telegram_client


_ACCOUNT_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


class TelegramLoginService:
    def __init__(self):
        self._sessions = {}
        self._lock = asyncio.Lock()
        self._accounts = AccountRepository()
        self._plugins = PluginRuntime()

    def _session_path(self, login_name: str) -> Path:
        if not _ACCOUNT_NAME_RE.fullmatch(login_name) or login_name in {".", ".."}:
            raise ValueError("登录名只能包含字母、数字、点、下划线和连字符")
        session_dir = Path(settings.TG_SESSION_DIR)
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir / login_name

    def _snapshot(self, state):
        return {
            "id": state["id"],
            "login_name": state["login_name"],
            "phone": state["phone"],
            "status": state["status"],
            "message": state.get("message", ""),
            "needs_code": state["status"] == "code_required",
            "needs_password": state["status"] == "password_required",
            "account": state.get("account"),
        }

    async def start(self, login_name: str, phone: str):
        validate_telegram_credentials()
        login_name = login_name.strip()
        phone = phone.strip()
        if not login_name:
            raise ValueError("请输入登录名")
        if not phone:
            raise ValueError("请输入手机号")

        session_path = self._session_path(login_name)
        if session_path.with_suffix(".session").exists() or self._accounts.get_id_by_session(login_name):
            raise ValueError("该登录名已经存在，请换一个登录名")

        async with self._lock:
            login_id = uuid.uuid4().hex
            proxy_plugin = self._plugins.get_capability("telegram.proxy")
            proxy = proxy_plugin.get_proxy(login_name) if proxy_plugin else None
            client = TelegramClient(
                str(session_path),
                settings.TG_API_ID,
                settings.TG_API_HASH,
                proxy=proxy,
            )
            state = {
                "id": login_id,
                "login_name": login_name,
                "phone": phone,
                "client": client,
                "status": "starting",
                "message": "正在连接 Telegram",
            }
            self._sessions[login_id] = state

            try:
                await client.connect()
                if await client.is_user_authorized():
                    raise ValueError("该登录名对应的 session 已经登录")
                await client.send_code_request(phone)
                state["status"] = "code_required"
                state["message"] = "验证码已发送，请输入 Telegram 验证码"
                return self._snapshot(state)
            except Exception:
                self._sessions.pop(login_id, None)
                await client.disconnect()
                session_file = session_path.with_suffix(".session")
                if session_file.exists():
                    session_file.unlink()
                raise

    async def submit_code(self, login_id: str, code: str):
        state = self._get(login_id)
        code = code.strip()
        if not code:
            raise ValueError("请输入 Telegram 验证码")
        if state["status"] != "code_required":
            raise ValueError("当前登录流程不需要验证码")

        try:
            me = await state["client"].sign_in(phone=state["phone"], code=code)
        except errors.SessionPasswordNeededError:
            state["status"] = "password_required"
            state["message"] = "该账号启用了两步验证，请输入 Telegram 密码"
            return self._snapshot(state)
        except Exception as exc:
            state["message"] = str(exc)
            raise

        return await self._complete(state, me)

    async def submit_password(self, login_id: str, password: str):
        state = self._get(login_id)
        if state["status"] != "password_required":
            raise ValueError("当前登录流程不需要两步验证密码")
        if not password:
            raise ValueError("请输入 Telegram 两步验证密码")

        try:
            me = await state["client"].sign_in(password=password)
        except Exception as exc:
            state["message"] = str(exc)
            raise
        return await self._complete(state, me)

    async def cancel(self, login_id: str):
        state = self._sessions.pop(login_id, None)
        if state:
            await state["client"].disconnect()
            session_file = Path(settings.TG_SESSION_DIR) / f"{state['login_name']}.session"
            if session_file.exists():
                session_file.unlink()
        return {"status": "cancelled"}

    def status(self, login_id: str):
        return self._snapshot(self._get(login_id))

    async def _complete(self, state, me):
        name = " ".join(filter(None, [getattr(me, "first_name", None), getattr(me, "last_name", None)]))
        self._accounts.upsert_session(state["login_name"], name or state["login_name"])
        account = self._accounts.get(self._accounts.get_id_by_session(state["login_name"]))
        state["account"] = {
            "id": account["id"],
            "login_name": state["login_name"],
            "nickname": name or getattr(me, "username", None) or state["login_name"],
            "username": getattr(me, "username", None),
            "phone": getattr(me, "phone", None) or state["phone"],
            "telegram_user_id": getattr(me, "id", None),
            "enabled": True,
        }
        state["status"] = "completed"
        state["message"] = "Telegram 登录成功"
        await state["client"].disconnect()
        self._sessions.pop(state["id"], None)

        # Let the normal runtime own this session from this point on.
        telegram_client.refresh_clients()
        return self._snapshot(state)

    def _get(self, login_id: str):
        state = self._sessions.get(login_id)
        if not state:
            raise ValueError("登录流程不存在或已经结束")
        return state


login_service = TelegramLoginService()
