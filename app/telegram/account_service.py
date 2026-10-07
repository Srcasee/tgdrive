import asyncio
import re
from pathlib import Path

from telethon import functions, types

from config import settings
from repositories.accounts import AccountRepository
from telegram import client as telegram_client


_ACCOUNT_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


class TelegramAccountService:
    def __init__(self):
        self._accounts = AccountRepository()
        self._phone_changes = {}
        self._email_changes = {}
        self._lock = asyncio.Lock()

    def _validate_login_name(self, value):
        value = value.strip()
        if not _ACCOUNT_NAME_RE.fullmatch(value) or value in {".", ".."}:
            raise ValueError("登录名只能包含字母、数字、点、下划线和连字符")
        return value

    async def _get_authorized_client(self, account_id):
        client = telegram_client.get_client(account_id)
        if not client.is_connected():
            await client.connect()
        if not await client.is_user_authorized():
            raise ValueError("Telegram 账号尚未登录")
        return client

    async def update_profile(self, account_id, login_name=None, nickname=None, username=None):
        async with self._lock:
            account = self._accounts.get(account_id)
            if not account:
                raise ValueError("account not found")

            if login_name is not None:
                login_name = self._validate_login_name(login_name)
                if login_name != account["session"]:
                    existing = self._accounts.get_id_by_session(login_name)
                    new_path = Path(settings.TG_SESSION_DIR) / f"{login_name}.session"
                    if existing is not None or new_path.exists():
                        raise ValueError("该登录名已经存在，请换一个登录名")

            client = await self._get_authorized_client(account_id)

            first_name = last_name = None
            if nickname is not None:
                nickname = nickname.strip()
                if not nickname:
                    raise ValueError("昵称不能为空")
                parts = nickname.split(maxsplit=1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ""
                await client(functions.account.UpdateProfileRequest(
                    first_name=first_name,
                    last_name=last_name,
                ))

            if username is not None:
                username = username.strip().lstrip("@")
                await client(functions.account.UpdateUsernameRequest(username))

            if nickname is not None or username is not None:
                me = await client.get_me()
                self._accounts.update_profile(
                    account_id,
                    name=" ".join(filter(None, [me.first_name, me.last_name])),
                    username=me.username,
                )

            if login_name is not None and login_name != account["session"]:
                old_file = Path(settings.TG_SESSION_DIR) / f"{account['session']}.session"
                new_file = Path(settings.TG_SESSION_DIR) / f"{login_name}.session"
                if new_file.exists():
                    raise ValueError("新的 session 文件名已经存在")
                await telegram_client.disconnect_account_session(account["session"])
                old_file.rename(new_file)
                self._accounts.update_session(account_id, login_name)
                telegram_client.refresh_clients()

            return self._accounts.get(account_id)

    async def start_phone_change(self, account_id, phone):
        phone = phone.strip()
        if not phone:
            raise ValueError("请输入新的手机号")
        client = await self._get_authorized_client(account_id)
        sent = await client(functions.account.SendChangePhoneCodeRequest(phone_number=phone))
        self._phone_changes[account_id] = {
            "phone": phone,
            "phone_code_hash": sent.phone_code_hash,
        }
        return {"status": "code_required", "message": "验证码已发送，请输入 Telegram 验证码"}

    async def start_login_email_change(self, account_id, email):
        email = email.strip()
        if not email or "@" not in email:
            raise ValueError("请输入有效的登录邮箱")
        client = await self._get_authorized_client(account_id)
        sent = await client(functions.account.SendVerifyEmailCodeRequest(
            purpose=types.EmailVerifyPurposeLoginChange(),
            email=email,
        ))
        self._email_changes[account_id] = {
            "email": email,
            "length": getattr(sent, "length", None),
        }
        return {
            "status": "code_required",
            "email": email,
            "length": getattr(sent, "length", None),
            "message": "验证邮件已发送，请输入邮箱中的验证码",
        }

    async def confirm_login_email_change(self, account_id, code):
        state = self._email_changes.get(account_id)
        if not state:
            raise ValueError("登录邮箱修改流程不存在或已过期")
        client = await self._get_authorized_client(account_id)
        try:
            result = await client(functions.account.VerifyEmailRequest(
                purpose=types.EmailVerifyPurposeLoginChange(),
                verification=types.EmailVerificationCode(code=code.strip()),
            ))
        finally:
            self._email_changes.pop(account_id, None)
        email = getattr(result, "email", None) or state["email"]
        return {
            "status": "ok",
            "email": email,
        }

    async def confirm_phone_change(self, account_id, code):
        state = self._phone_changes.get(account_id)
        if not state:
            raise ValueError("手机号修改流程不存在或已过期")
        client = await self._get_authorized_client(account_id)
        try:
            me = await client(functions.account.ChangePhoneRequest(
                phone_number=state["phone"],
                phone_code_hash=state["phone_code_hash"],
                phone_code=code.strip(),
            ))
        except Exception:
            raise
        finally:
            self._phone_changes.pop(account_id, None)
        return {
            "status": "ok",
            "phone": getattr(me, "phone", None),
        }


telegram_account_service = TelegramAccountService()
