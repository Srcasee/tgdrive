"""
Compatibility entry point for Telegram API.

The router keeps the original URL prefix while implementation is split
into domain modules under app/telegram/api/.
"""

from telegram.api import router

__all__ = ["router"]
