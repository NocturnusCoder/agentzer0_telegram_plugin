import json
import os
import logging
from dataclasses import dataclass
from typing import Literal

from plugins._telegram_integration.helpers.bot_manager import get_all_bots
from plugins._telegram_integration.helpers.constants import STATE_FILE
from helpers import files
from agent import AgentContext
from aiogram import Message

_log = logging.getLogger(__name__)


@dataclass
class ContextResult:
    ctx: AgentContext | None
    status: Literal["ok", "no_session", "expired", "bot_unknown"]
    bot_name: str | None = None


def _map_key(bot_name: str, user_id: int, chat_id: int) -> str:
    return f"{bot_name}:{user_id}:{chat_id}"


def resolve_bot_name(message: Message) -> str | None:
    msg_token = message.bot.token
    for bot_name, instance in get_all_bots().items():
        if instance.bot.token == msg_token:
            return bot_name
    return None


def get_context_for_chat(
    bot_name: str, user_id: int, chat_id: int
) -> tuple[AgentContext | None, bool]:
    state_path = files.get_abs_path(STATE_FILE)
    if not os.path.isfile(state_path):
        return None, False

    try:
        state = json.loads(files.read_file(STATE_FILE))
    except (json.JSONDecodeError, OSError):
        _log.warning("Failed to read state.json")
        return None, False

    key = _map_key(bot_name, user_id, chat_id)
    ctx_id = state.get("chats", {}).get(key)
    if not ctx_id:
        return None, False

    ctx = AgentContext.get(ctx_id)
    if ctx is None:
        return None, True
    return ctx, False


def resolve_context(message: Message) -> ContextResult:
    bot_name = resolve_bot_name(message)
    if not bot_name:
        return ContextResult(None, "bot_unknown")

    _log.debug("Resolving context for chat %s:%s:%s", bot_name, message.from_user.id, message.chat.id)

    ctx, was_stale = get_context_for_chat(bot_name, message.from_user.id, message.chat.id)
    if was_stale:
        _log.info("Session expired for user %s in chat %s", message.from_user.id, message.chat.id)
        return ContextResult(None, "expired", bot_name)
    if ctx is None:
        _log.debug("No session found for user %s in chat %s", message.from_user.id, message.chat.id)
        return ContextResult(None, "no_session", bot_name)
    return ContextResult(ctx, "ok", bot_name)
