# Telegram Project Switch Plugin

An **Agent Zero** plugin that adds a `/project` command to Telegram bots for dynamic project switching.

## Features

- `/project` — shows inline keyboard with available projects
- `/project <name>` — switch to a project directly via text
- Inline keyboard buttons with current project marked ✅
- Conversation auto-clears on project switch
- Idempotent bot registration with restart detection (token-based)
- Stale/expired session detection
- Handles Telegram's 64-byte `callback_data` limit gracefully
- Robust error handling — no internal details leaked to users

## Requirements

- [Agent Zero](https://github.com/frdel/agent-zero) framework
- [_telegram_integration](https://github.com/frdel/agent-zero) plugin (built-in Telegram bot) — **must be enabled first**

## Installation

1. Copy `telegram_project_switch/` into your Agent Zero `usr/plugins/` directory:
   ```bash
   cp -r telegram_project_switch/ /path/to/agent-zero/usr/plugins/_telegram_project_switch/
   ```
2. Enable the plugin by creating the toggle file:
   ```bash
   touch /path/to/agent-zero/usr/plugins/_telegram_project_switch/.toggle-1
   ```
3. Restart Agent Zero.

## Usage

- Send `/project` to see available projects as buttons
- Tap a button or send `/project <name>` to switch
- Current project is marked with ✅ in the list
- Conversation history is cleared on switch for a fresh context

## How It Works

The plugin registers an aiogram `Router` on existing Telegram bot instances managed by the `_telegram_integration` plugin. It uses the framework's `STATE_FILE` constant and `files.get_abs_path()` for reliable state.json lookup, then calls `projects.activate_project()` to switch and `ctx.reset()` to clear the conversation.

The router is inserted at position 0 in the dispatcher's sub-routers, ensuring the `/project` command handler runs **before** the telegram plugin's catch-all `on_message` handler.

## ⚠️ Limitations

- **Restart persistence:** Dynamic project choices do **not** survive server restarts. After a restart, the user falls back to the `user_projects` or `default_project` configured in the Telegram integration settings. To make a project assignment permanent, configure it in the Telegram plugin's GUI under 