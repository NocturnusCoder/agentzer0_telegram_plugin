import sys
import os
from types import ModuleType
from unittest.mock import MagicMock, AsyncMock

import pytest

# Add src to path so tests can import modules directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "telegram_project_switch_fix", "src"))

# --- Mock framework modules so context_resolver can import at module level ---
_mock_modules = {
    "plugins": MagicMock(),
    "plugins._telegram_integration": MagicMock(),
    "plugins._telegram_integration.helpers": MagicMock(),
    "plugins._telegram_integration.helpers.bot_manager": MagicMock(),
    "plugins._telegram_integration.helpers.constants": MagicMock(),
    "helpers": MagicMock(),
    "helpers.files": MagicMock(),
    "helpers.projects": MagicMock(),
    "agent": MagicMock(),
    "aiogram": MagicMock(),
    "aiogram.types": MagicMock(),
    "aiogram.exceptions": MagicMock(),
}
for _name, _mod in _mock_modules.items():
    if _name not in sys.modules:
        sys.modules[_name] = _mod

# Provide concrete constants expected by context_resolver
sys.modules["plugins._telegram_integration.helpers.constants"].STATE_FILE = "data/state.json"

# Make aiogram.Message a real class so isinstance checks work in tests
sys.modules["aiogram"].Message = MagicMock

# Concrete stubs for aiogram types used by keyboard_builder tests
class _InlineKeyboardButton:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class _InlineKeyboardMarkup:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

sys.modules["aiogram.types"].InlineKeyboardButton = _InlineKeyboardButton
sys.modules["aiogram.types"].InlineKeyboardMarkup = _InlineKeyboardMarkup





@pytest.fixture
def sample_projects():
    return [
        {"name": "project_a", "title": "Project A"},
        {"name": "my_research", "title": "My Research"},
        {"name": "project_c", "title": "Project C"},
    ]


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.token = "123456:ABC-DEF"
    return bot


@pytest.fixture
def mock_message(mock_bot):
    message = MagicMock()
    message.bot = mock_bot
    message.from_user.id = 42
    message.chat.id = 100
    message.text = "/project"
    message.answer = AsyncMock()
    message.edit_text = AsyncMock()
    return message


@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.id = "ctx-uuid-001"
    ctx.get_data = MagicMock(return_value="project_a")
    ctx.reset = MagicMock()
    return ctx


@pytest.fixture
def mock_callback(mock_bot, mock_message):
    callback = MagicMock()
    callback.bot = mock_bot
    callback.from_user.id = 42
    callback.message = mock_message
    callback.data = "switch_project:project_a"
    callback.answer = AsyncMock()
    return callback
