import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from handlers import handle_project_command, handle_project_callback
from context_resolver import ContextResult
from constants import CALLBACK_PREFIX, INVALID_MARKER


class TestHandleProjectCommand:
    @patch("handlers.resolve_context")
    async def test_bot_unknown(self, mock_resolve, mock_message):
        mock_resolve.return_value = ContextResult(None, "bot_unknown")
        await handle_project_command(mock_message)
        mock_message.answer.assert_called_once_with("Could not identify the bot.")

    @patch("handlers.resolve_context")
    async def test_expired(self, mock_resolve, mock_message):
        mock_resolve.return_value = ContextResult(None, "expired", "bot1")
        await handle_project_command(mock_message)
        mock_message.answer.assert_called_once_with("\u26a0\ufe0f Session expired. Send a message to start fresh.")

    @patch("handlers.resolve_context")
    async def test_no_session(self, mock_resolve, mock_message):
        mock_resolve.return_value = ContextResult(None, "no_session", "bot1")
        await handle_project_command(mock_message)
        mock_message.answer.assert_called_once_with("\U0001f4a1 Send a regular message first to start a session")

    @patch("handlers.build_project_keyboard")
    @patch("handlers.list_projects")
    @patch("handlers.resolve_context")
    async def test_no_arg_shows_keyboard(self, mock_resolve, mock_list, mock_kb, mock_message, mock_context):
        mock_resolve.return_value = ContextResult(mock_context, "ok", "bot1")
        mock_context.get_data.return_value = "p1"
        mock_list.return_value = [{"name": "p1", "title": "P1"}]
        mock_kb.return_value = ("\U0001f4cb Current: p1", MagicMock())
        mock_message.text = "/project"
        await handle_project_command(mock_message)
        mock_kb.assert_called_once_with("p1", mock_list.return_value)
        mock_message.answer.assert_called_once()

    @patch("handlers.switch_project")
    @patch("handlers.list_projects")
    @patch("handlers.resolve_context")
    async def test_switch_success(self, mock_resolve, mock_list, mock_switch, mock_message, mock_context):
        from project_switcher import SwitchResult
        mock_resolve.return_value = ContextResult(mock_context, "ok", "bot1")
        mock_list.return_value = [{"name": "p1", "title": "P1"}]
        mock_switch.return_value = SwitchResult(True, "P1", None)
        mock_message.text = "/project p1"
        await handle_project_command(mock_message)
        mock_message.answer.assert_called_once_with('\u2705 Switched to project "P1"')

    @patch("handlers.switch_project")
    @patch("handlers.list_projects")
    @patch("handlers.resolve_context")
    async def test_switch_error(self, mock_resolve, mock_list, mock_switch, mock_message, mock_context):
        from project_switcher import SwitchResult
        mock_resolve.return_value = ContextResult(mock_context, "ok", "bot1")
        mock_list.return_value = []
        mock_switch.return_value = SwitchResult(False, None, 'Project "x" not found.')
        mock_message.text = "/project x"
        await handle_project_command(mock_message)
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "\u274c" in call_args

    @patch("handlers.resolve_context")
    async def test_exception_logged_and_user_notified(self, mock_resolve, mock_message):
        mock_resolve.side_effect = RuntimeError("unexpected")
        with patch("handlers._log") as mock_log:
            await handle_project_command(mock_message)
            mock_log.error.assert_called_once()
            assert mock_log.error.call_args[1].get("exc_info") is True
        mock_message.answer.assert_called_once_with("\u26a0\ufe0f An error occurred. Check server logs.")


class TestHandleProjectCallback:
    @patch("handlers.resolve_context")
    async def test_invalid_marker(self, mock_resolve, mock_callback):
        mock_callback.data = f"{CALLBACK_PREFIX}{INVALID_MARKER}"
        await handle_project_callback(mock_callback)
        mock_callback.answer.assert_called_once_with(
            "Project name is too long for Telegram. Use /project <name> instead.",
            show_alert=True,
        )

    @patch("handlers.resolve_context")
    async def test_bot_unknown(self, mock_resolve, mock_callback):
        mock_resolve.return_value = ContextResult(None, "bot_unknown")
        await handle_project_callback(mock_callback)
        mock_callback.answer.assert_called_once_with("Could not identify the bot.", show_alert=True)

    @patch("handlers.resolve_context")
    async def test_expired(self, mock_resolve, mock_callback):
        mock_resolve.return_value = ContextResult(None, "expired", "bot1")
        await handle_project_callback(mock_callback)
        mock_callback.answer.assert_called_once_with(
            "\u26a0\ufe0f Session expired. Send a message to start fresh.", show_alert=True
        )

    @patch("handlers.resolve_context")
    async def test_no_session(self, mock_resolve, mock_callback):
        mock_resolve.return_value = ContextResult(None, "no_session", "bot1")
        await handle_project_callback(mock_callback)
        mock_callback.answer.assert_called_once_with(
            "\U0001f4a1 Send a regular message first to start a session", show_alert=True
        )

    @patch("handlers.switch_project")
    @patch("handlers.list_projects")
    @patch("handlers.resolve_context")
    async def test_already_on_project(self, mock_resolve, mock_list, mock_switch, mock_callback, mock_context):
        mock_resolve.return_value = ContextResult(mock_context, "ok", "bot1")
        mock_callback.data = f"{CALLBACK_PREFIX}project_a"
        await handle_project_callback(mock_callback)
        mock_callback.answer.assert_called_once_with("Already on this project.")
        mock_switch.assert_not_called()

    @patch("handlers.switch_project")
    @patch("handlers.list_projects")
    @patch("handlers.resolve_context")
    async def test_switch_success_edits_message(self, mock_resolve, mock_list, mock_switch, mock_callback, mock_context):
        from project_switcher import SwitchResult
        mock_resolve.return_value = ContextResult(mock_context, "ok", "bot1")
        mock_context.get_data.return_value = "project_b"
        mock_callback.data = f"{CALLBACK_PREFIX}project_a"
        mock_list.return_value = [{"name": "project_a", "title": "Project A"}]
        mock_switch.return_value = SwitchResult(True, "Project A", None)
        await handle_project_callback(mock_callback)
        mock_callback.message.edit_text.assert_called_once_with('\u2705 Switched to project "Project A"')

    @patch("handlers.switch_project")
    @patch("handlers.list_projects")
    @patch("handlers.resolve_context")
    async def test_edit_fallback_to_answer(self, mock_resolve, mock_list, mock_switch, mock_callback, mock_context):
        from project_switcher import SwitchResult
        from aiogram.exceptions import TelegramAPIError
        mock_resolve.return_value = ContextResult(mock_context, "ok", "bot1")
        mock_context.get_data.return_value = "project_b"
        mock_callback.data = f"{CALLBACK_PREFIX}project_a"
        mock_list.return_value = [{"name": "project_a", "title": "Project A"}]
        mock_switch.return_value = SwitchResult(True, "Project A", None)
        mock_callback.message.edit_text.side_effect = TelegramAPIError("message can't be edited")
        await handle_project_callback(mock_callback)
        mock_callback.message.answer.assert_called_once_with('\u2705 Switched to project "Project A"')

    @patch("handlers.switch_project")
    @patch("handlers.list_projects")
    @patch("handlers.resolve_context")
    async def test_switch_error_in_callback(self, mock_resolve, mock_list, mock_switch, mock_callback, mock_context):
        from project_switcher import SwitchResult
        mock_resolve.return_value = ContextResult(mock_context, "ok", "bot1")
        mock_context.get_data.return_value = "project_b"
        mock_callback.data = f"{CALLBACK_PREFIX}project_a"
        mock_list.return_value = []
        mock_switch.return_value = SwitchResult(False, None, "not found")
        await handle_project_callback(mock_callback)
        mock_callback.answer.assert_called_once()
        assert "\u274c" in mock_callback.answer.call_args[0][0]

    @patch("handlers.resolve_context")
    async def test_exception_in_callback(self, mock_resolve, mock_callback):
        mock_resolve.side_effect = RuntimeError("boom")
        with patch("handlers._log") as mock_log:
            await handle_project_callback(mock_callback)
            mock_log.error.assert_called_once()
        mock_callback.answer.assert_called_once_with(
            "\u26a0\ufe0f An error occurred. Check server logs.", show_alert=True
        )
