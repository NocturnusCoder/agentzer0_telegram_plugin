import json
from unittest.mock import patch, MagicMock

from context_resolver import resolve_bot_name, resolve_context, ContextResult


class TestResolveBotName:
    @patch("context_resolver.get_all_bots")
    def test_found(self, mock_get_all, mock_message):
        mock_instance = MagicMock()
        mock_instance.bot.token = "123456:ABC-DEF"
        mock_get_all.return_value = {"my_bot": mock_instance}
        assert resolve_bot_name(mock_message) == "my_bot"

    @patch("context_resolver.get_all_bots")
    def test_not_found(self, mock_get_all, mock_message):
        mock_instance = MagicMock()
        mock_instance.bot.token = "999:XXX"
        mock_get_all.return_value = {"my_bot": mock_instance}
        assert resolve_bot_name(mock_message) is None

    @patch("context_resolver.get_all_bots")
    def test_empty_registry(self, mock_get_all, mock_message):
        mock_get_all.return_value = {}
        assert resolve_bot_name(mock_message) is None


class TestResolveContext:
    @patch("context_resolver.get_all_bots")
    @patch("context_resolver.AgentContext")
    @patch("context_resolver.get_context_for_chat")
    def test_ok(self, mock_get_ctx, mock_ac, mock_get_all, mock_message, mock_context):
        mock_instance = MagicMock()
        mock_instance.bot.token = "123456:ABC-DEF"
        mock_get_all.return_value = {"my_bot": mock_instance}
        mock_get_ctx.return_value = (mock_context, False)
        result = resolve_context(mock_message)
        assert result.status == "ok"
        assert result.ctx is mock_context
        assert result.bot_name == "my_bot"

    @patch("context_resolver.get_all_bots")
    @patch("context_resolver.AgentContext")
    @patch("context_resolver.get_context_for_chat")
    def test_bot_unknown(self, mock_get_ctx, mock_ac, mock_get_all, mock_message):
        mock_get_all.return_value = {}
        result = resolve_context(mock_message)
        assert result.status == "bot_unknown"
        assert result.ctx is None

    @patch("context_resolver.get_all_bots")
    @patch("context_resolver.AgentContext")
    @patch("context_resolver.get_context_for_chat")
    def test_expired(self, mock_get_ctx, mock_ac, mock_get_all, mock_message):
        mock_instance = MagicMock()
        mock_instance.bot.token = "123456:ABC-DEF"
        mock_get_all.return_value = {"my_bot": mock_instance}
        mock_get_ctx.return_value = (None, True)
        result = resolve_context(mock_message)
        assert result.status == "expired"
        assert result.ctx is None

    @patch("context_resolver.get_all_bots")
    @patch("context_resolver.AgentContext")
    @patch("context_resolver.get_context_for_chat")
    def test_no_session(self, mock_get_ctx, mock_ac, mock_get_all, mock_message):
        mock_instance = MagicMock()
        mock_instance.bot.token = "123456:ABC-DEF"
        mock_get_all.return_value = {"my_bot": mock_instance}
        mock_get_ctx.return_value = (None, False)
        result = resolve_context(mock_message)
        assert result.status == "no_session"

    @patch("context_resolver.get_all_bots")
    @patch("context_resolver.AgentContext")
    @patch("context_resolver.get_context_for_chat")
    def test_user_override(self, mock_get_ctx, mock_ac, mock_get_all, mock_message, mock_context):
        """user_override should be used instead of message.from_user for key lookup."""
        mock_instance = MagicMock()
        mock_instance.bot.token = "123456:ABC-DEF"
        mock_get_all.return_value = {"my_bot": mock_instance}
        mock_get_ctx.return_value = (mock_context, False)

        override_user = MagicMock()
        override_user.id = 99

        result = resolve_context(mock_message, user_override=override_user)
        assert result.status == "ok"
        # Verify the override user ID was used, not message.from_user.id
        mock_get_ctx.assert_called_once_with("my_bot", 99, 100)

    @patch("context_resolver.get_all_bots")
    @patch("context_resolver.AgentContext")
    @patch("context_resolver.get_context_for_chat")
    def test_no_override_uses_message_from_user(self, mock_get_ctx, mock_ac, mock_get_all, mock_message, mock_context):
        """Without user_override, message.from_user should be used."""
        mock_instance = MagicMock()
        mock_instance.bot.token = "123456:ABC-DEF"
        mock_get_all.return_value = {"my_bot": mock_instance}
        mock_get_ctx.return_value = (mock_context, False)

        result = resolve_context(mock_message)
        assert result.status == "ok"
        mock_get_ctx.assert_called_once_with("my_bot", 42, 100)
        assert result.ctx is mock_context


class TestGetContextForChat:
    @patch("context_resolver.os.path.isfile", return_value=True)
    @patch("context_resolver.AgentContext")
    @patch("context_resolver.files")
    def test_found(self, mock_files, mock_ac, mock_isfile):
        mock_files.get_abs_path.return_value = "/tmp/state.json"
        mock_files.read_file.return_value = json.dumps({"chats": {"bot:42:100": "ctx-uuid"}})
        mock_ctx = MagicMock()
        mock_ac.get.return_value = mock_ctx
        from context_resolver import get_context_for_chat
        ctx, stale = get_context_for_chat("bot", 42, 100)
        assert ctx is mock_ctx
        assert stale is False

    @patch("context_resolver.os.path.isfile", return_value=True)
    @patch("context_resolver.AgentContext")
    @patch("context_resolver.files")
    def test_no_mapping(self, mock_files, mock_ac, mock_isfile):
        mock_files.get_abs_path.return_value = "/tmp/state.json"
        mock_files.read_file.return_value = json.dumps({"chats": {}})
        from context_resolver import get_context_for_chat
        ctx, stale = get_context_for_chat("bot", 42, 100)
        assert ctx is None
        assert stale is False

    @patch("context_resolver.os.path.isfile", return_value=True)
    @patch("context_resolver.AgentContext")
    @patch("context_resolver.files")
    def test_stale(self, mock_files, mock_ac, mock_isfile):
        mock_files.get_abs_path.return_value = "/tmp/state.json"
        mock_files.read_file.return_value = json.dumps({"chats": {"bot:42:100": "ctx-uuid"}})
        mock_ac.get.return_value = None
        from context_resolver import get_context_for_chat
        ctx, stale = get_context_for_chat("bot", 42, 100)
        assert ctx is None
        assert stale is True

    @patch("context_resolver.files")
    def test_missing_file(self, mock_files):
        mock_files.get_abs_path.return_value = "/tmp/state.json"
        with patch("context_resolver.os.path.isfile", return_value=False):
            from context_resolver import get_context_for_chat
            ctx, stale = get_context_for_chat("bot", 42, 100)
            assert ctx is None
            assert stale is False

    @patch("context_resolver.os.path.isfile", return_value=True)
    @patch("context_resolver.AgentContext")
    @patch("context_resolver.files")
    def test_malformed_json(self, mock_files, mock_ac, mock_isfile):
        mock_files.get_abs_path.return_value = "/tmp/state.json"
        mock_files.read_file.return_value = "not json{{{"
        from context_resolver import get_context_for_chat
        ctx, stale = get_context_for_chat("bot", 42, 100)
        assert ctx is None
        assert stale is False
