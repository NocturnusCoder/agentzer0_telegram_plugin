# Telegram Project Switch

Adds a `/project` command to Agent Zero Telegram bots for dynamic project switching within a chat session.

## Features

- `/project` — show current project and inline keyboard with all available projects
- `/project <name>` — switch to a project by name
- Inline keyboard buttons for quick switching
- Works with multiple bots, group chats, and private chats
- Project persists through `/clear` commands

## Architecture

```
telegram_project_switch/
├── plugin.yaml
├── README.md
├── extensions/
│   └── python/
│       └── job_loop/
│           └── _15_register_project_command.py  # Extension entry point
└── src/
    ├── constants.py         # Magic strings and callback prefixes
    ├── context_resolver.py  # AgentContext lookup from Telegram chat
    ├── project_switcher.py  # Business logic for switching projects
    ├── keyboard_builder.py  # Inline keyboard construction
    └── handlers.py          # aiogram command/callback handlers
```

Each module has one responsibility and can be tested independently.

## Requirements

- Agent Zero with the built-in `_telegram_integration` plugin enabled
- At least one Telegram bot configured

## Installation

1. Copy `telegram_project_switch/` to `/a0/usr/plugins/_telegram_project_switch/`
2. Enable the plugin in Agent Zero settings
3. Restart the Agent Zero server

## Testing

```bash
pytest tests/
```

## Changelog

### v1.2.1 — Fix inline keyboard callbacks in group chats
- Fixed "Send a regular message first to start a session" error when clicking project switch buttons in group chats
- Root cause: callback handler used `callback.message.from_user` (the bot) instead of `callback.from_user` (the human who clicked) for state.json key lookup
- Added `user_override` parameter to `resolve_context()` for callback scenarios
- Added 3 regression tests with realistic mock separation (bot vs user identity)

### v1.2.0 — Modular refactor with unit tests
