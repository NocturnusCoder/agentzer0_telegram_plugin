import json
import os
import logging

from helpers.extension import Extension
from helpers import files
from plugins._telegram_integration.helpers.bot_manager import get_all_bots
from plugins._telegram_integration.helpers.constants import STATE_FILE
from helpers import projects
from agent import AgentContext

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command

_log = logging.getLogger(__name__)

# Module-level tracking for idempotent registration.
# Key: bot_name, Value: (bot_token, router)
# Using token instead of id() so detection survives object rebuilds.
_registered: dict[str, tuple[str, Router]] = {}


def _map_key(bot_name: str, user_id: int, chat_id: int) -> str:
    """Build the state.json chat mapping key."""
    return f"{bot_name}:{user_id}:{chat_id}"


def _resolve_bot_name(message: Message) -> str | None:
    """Find the bot_name by matching the bot token from the message."""
    msg_token = message.bot.token
    for bot_name, instance in get_all_bots().items():
        if instance.bot.token == msg_token:
            return bot_name
    return None


def _get_context_for_chat(
    bot_name: str, user_id: int, chat_id: int
) -> tuple[AgentContext | None, bool]:
    """Look up the AgentContext for a telegram chat via state.json.

    Returns (context, was_stale):
        - (AgentContext, False) — live context found
        - (None, False) — no mapping exists (never started)
        - (None, True) — mapping exists but context is gone (stale/expired)
    """
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


async def _switch_project(
    ctx: AgentContext, project_name: str, all_projects: list | None = None
) -> str | None:
    """Switch project and reset conversation. Returns error string or None on success."""
    if all_projects is None:
        all_projects = projects.get_active_projects_list()
    project_names = [p["name"] for p in all_projects]

    if project_name not in project_names:
        available = ", ".join(project_names) if project_names else "(none)"
        return f'Project "{project_name}" not found.\nAvailable: {available}'

    try:
        projects.activate_project(ctx.id, project_name)
    except Exception as e:
        _log.error("Failed to activate project: %s", e, exc_info=True)
        return "Failed to switch project. Check server logs."

    ctx.reset()
    return None


def _build_project_keyboard(
    current_project: str | None = None,
    all_projects: list | None = None,
) -> tuple[str, InlineKeyboardMarkup | None]:
    """Build the project selection inline keyboard."""
    if all_projects is None:
        all_projects = projects.get_active_projects_list()

    if not all_projects:
        return "\u26a0\ufe0f No projects found. Create one first.", None

    current_display = current_project or "(none)"
    header = f"\U0001f4cb Current: {current_display}"

    buttons = []
    sorted_projects = sorted(
        all_projects, key=lambda p: p.get("title", p["name"])
    )

    for i in range(0, len(sorted_projects), 2):
        row = []
        for j in range(2):
            if i + j < len(sorted_projects):
                p = sorted_projects[i + j]
                label = p.get("title", p["name"])
                if p["name"] == current_project:
                    label = f"{label} \u2705"
                cb_data = f"switch_project:{p['name']}"
                if len(cb_data.encode("utf-8")) > 64:
                    label = f"{label} (name too long)"
                    row.append(
                        InlineKeyboardButton(
                            text=label, callback_data="switch_project:_invalid"
                        )
                    )
                else:
                    row.append(
                        InlineKeyboardButton(text=label, callback_data=cb_data)
                    )
        buttons.append(row)

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return header, keyboard


async def _handle_project_command(message: Message):
    """Handle /project command -- with or without arguments."""
    try:
        bot_name = _resolve_bot_name(message)
        if not bot_name:
            await message.answer("Could not identify the bot.")
            return

        ctx, was_stale = _get_context_for_chat(
            bot_name, message.from_user.id, message.chat.id
        )
        if was_stale:
            await message.answer(
                "\u26a0\ufe0f Session expired. Send a message to start fresh."
            )
            return
        if ctx is None:
            await message.answer(
                "\U0001f4a1 Send a regular message first to start a session"
            )
            return

        text = message.text or ""
        parts = text.split(maxsplit=1)
        project_arg = parts[1].strip() if len(parts) > 1 else ""

        all_projects = projects.get_active_projects_list()

        if not project_arg:
            current = ctx.get_data("project")
            header, keyboard = _build_project_keyboard(current, all_projects)
            if keyboard:
                await message.answer(header, reply_markup=keyboard)
            else:
                await message.answer(header)
            return

        error = await _switch_project(ctx, project_arg, all_projects)
        if error:
            await message.answer(f"\u274c {error}")
            return

        project_info = next(
            (p for p in all_projects if p["name"] == project_arg), None
        )
        title = (
            project_info.get("title", project_arg) if project_info else project_arg
        )
        await message.answer(f'\u2705 Switched to project "{title}"')
    except Exception as e:
        _log.error("Error in /project handler: %s", e, exc_info=True)
        try:
            await message.answer("\u26a0\ufe0f An error occurred. Check server logs.")
        except Exception:
            pass


async def _handle_project_callback(callback: CallbackQuery):
    """Handle inline keyboard button tap for project switching."""
    data = callback.data or ""
    if not data.startswith("switch_project:"):
        return

    project_name = data.split(":", 1)[1]

    if project_name == "_invalid":
        await callback.answer(
            "Project name is too long for Telegram. Use /project <name> instead.",
            show_alert=True,
        )
        return

    message = callback.message

    bot_name = _resolve_bot_name(message)
    if not bot_name:
        await callback.answer(
            "Could not identify the bot.", show_alert=True
        )
        return

    ctx, was_stale = _get_context_for_chat(
        bot_name, callback.from_user.id, message.chat.id
    )
    if was_stale:
        await callback.answer(
            "\u26a0\ufe0f Session expired. Send a message to start fresh.",
            show_alert=True,
        )
        return
    if ctx is None:
        await callback.answer(
            "\U0001f4a1 Send a regular message first to start a session",
            show_alert=True,
        )
        return

    current = ctx.get_data("project")
    if current == project_name:
        await callback.answer("Already on this project.")
        return

    error = await _switch_project(ctx, project_name)
    if error:
        await callback.answer(f"\u274c {error}", show_alert=True)
        return

    all_projects = projects.get_active_projects_list()
    project_info = next(
        (p for p in all_projects if p["name"] == project_name), None
    )
    title = (
        project_info.get("title", project_name)
        if project_info
        else project_name
    )

    try:
        await message.edit_text(
            f'\u2705 Switched to project "{title}"'
        )
    except Exception:
        # Fallback: edit may fail if message is too old (>48h)
        # or already has no markup — send a new message instead
        try:
            await message.answer(f'\u2705 Switched to project "{title}"')
        except Exception:
            pass

    await callback.answer()


def _create_project_router(bot_name: str) -> Router:
    """Create an aiogram Router with /project command and callback handlers."""
    router = Router(name=f"project_switch_{bot_name}")

    router.message.register(_handle_project_command, Command("project"))
    router.callback_query.register(
        _handle_project_callback, F.data.startswith("switch_project:")
    )

    return router


class TelegramProjectSwitch(Extension):
    async def execute(self, action: str = "", **kwargs):
        bots = get_all_bots()
        if not bots:
            return

        for bot_name, instance in bots.items():
            bot_token = instance.bot.token
            cached = _registered.get(bot_name)

            if cached and cached[0] == bot_token:
                continue

            # Remove old router if present (bot restart with same dispatcher)
            if cached:
                old_router = cached[1]
                try:
                    instance.dispatcher.sub_routers.remove(old_router)
                except ValueError:
                    pass  # Already removed (dispatcher was replaced)

            router = _create_project_router(bot_name)
            # Insert at position 0 so our /project command handler runs BEFORE
            # the telegram plugin's catch-all on_message handler
            instance.dispatcher.sub_routers.insert(0, router)
            _registered[bot_name] = (bot_token, router)
            _log.info("Registered /project command on bot: %s", bot_name)
