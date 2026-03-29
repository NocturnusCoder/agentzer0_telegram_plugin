import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

from helpers.extension import Extension
from plugins._telegram_integration.helpers.bot_manager import get_all_bots
from aiogram import Router, F
from aiogram.filters import Command

from constants import CALLBACK_PREFIX, COMMAND_NAME
from handlers import handle_project_command, handle_project_callback

_log = logging.getLogger(__name__)

_registered: dict[str, tuple[str, Router]] = {}


def _create_project_router(bot_name: str) -> Router:
    router = Router(name=f"project_switch_{bot_name}")
    router.message.register(handle_project_command, Command(COMMAND_NAME))
    router.callback_query.register(
        handle_project_callback, F.data.startswith(CALLBACK_PREFIX)
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

            if cached:
                old_router = cached[1]
                try:
                    instance.dispatcher.sub_routers.remove(old_router)
                except ValueError:
                    pass

            router = _create_project_router(bot_name)
            instance.dispatcher.sub_routers.insert(0, router)
            _registered[bot_name] = (bot_token, router)
            _log.info("Registered /project command on bot: %s", bot_name)
