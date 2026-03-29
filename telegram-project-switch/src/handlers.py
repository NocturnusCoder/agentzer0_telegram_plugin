import logging

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.exceptions import TelegramAPIError

from constants import CALLBACK_PREFIX, INVALID_MARKER, COMMAND_NAME
from context_resolver import resolve_context, ContextResult
from project_switcher import switch_project, list_projects
from keyboard_builder import build_project_keyboard

_log = logging.getLogger(__name__)


async def _answer_error(message: Message, text: str):
    await message.answer(f"\u274c {text}")


async def _reject_context(message: Message, result: ContextResult):
    responses = {
        "bot_unknown": "Could not identify the bot.",
        "expired": "\u26a0\ufe0f Session expired. Send a message to start fresh.",
        "no_session": "\U0001f4a1 Send a regular message first to start a session",
    }
    await message.answer(responses.get(result.status, "Unknown error."))


async def _reject_context_callback(callback: CallbackQuery, result: ContextResult):
    responses = {
        "bot_unknown": "Could not identify the bot.",
        "expired": "\u26a0\ufe0f Session expired. Send a message to start fresh.",
        "no_session": "\U0001f4a1 Send a regular message first to start a session",
    }
    await callback.answer(responses.get(result.status, "Unknown error."), show_alert=True)


async def handle_project_command(message: Message):
    try:
        result = resolve_context(message)
        if result.status != "ok":
            await _reject_context(message, result)
            return

        text = message.text or ""
        parts = text.split(maxsplit=1)
        project_arg = parts[1].strip() if len(parts) > 1 else ""

        all_projects = list_projects()

        if not project_arg:
            current = result.ctx.get_data("project")
            header, keyboard = build_project_keyboard(current, all_projects)
            if keyboard:
                await message.answer(header, reply_markup=keyboard)
            else:
                await message.answer(header)
            return

        switch_result = switch_project(result.ctx, project_arg, all_projects)
        if not switch_result.success:
            await _answer_error(message, switch_result.error)
            return

        await message.answer(f'\u2705 Switched to project "{switch_result.title}"')
    except Exception:
        _log.error("/project command failed", exc_info=True)
        await message.answer("\u26a0\ufe0f An error occurred. Check server logs.")


async def handle_project_callback(callback: CallbackQuery):
    try:
        data = callback.data or ""
        if not data.startswith(CALLBACK_PREFIX):
            return

        project_name = data[len(CALLBACK_PREFIX):]

        if project_name == INVALID_MARKER:
            await callback.answer(
                "Project name is too long for Telegram. Use /project <name> instead.",
                show_alert=True,
            )
            return

        message = callback.message
        result = resolve_context(message)
        if result.status != "ok":
            await _reject_context_callback(callback, result)
            return

        current = result.ctx.get_data("project")
        if current == project_name:
            await callback.answer("Already on this project.")
            return

        switch_result = switch_project(result.ctx, project_name)
        if not switch_result.success:
            await callback.answer(f"\u274c {switch_result.error}", show_alert=True)
            return

        success_text = f'\u2705 Switched to project "{switch_result.title}"'
        try:
            await message.edit_text(success_text)
        except TelegramAPIError:
            _log.debug("edit_text failed (likely 48h limit), sending new message")
            await message.answer(success_text)

        await callback.answer()
    except Exception:
        _log.error("/project callback failed", exc_info=True)
        await callback.answer(
            "\u26a0\ufe0f An error occurred. Check server logs.", show_alert=True
        )
