from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from constants import CALLBACK_PREFIX, INVALID_MARKER


def build_project_keyboard(
    current_project: str | None = None,
    all_projects: list | None = None,
) -> tuple[str, InlineKeyboardMarkup | None]:
    if all_projects is None:
        from project_switcher import list_projects
        all_projects = list_projects()

    if not all_projects:
        return "\u26a0\ufe0f No projects found. Create one first.", None

    sorted_projects = sorted(all_projects, key=lambda p: p.get("title", p["name"]))

    current_info = next((p for p in sorted_projects if p["name"] == current_project), None)
    current_display = current_info.get("title", current_project) if current_info else "(none)"
    checkmark = " \u2705" if current_project else ""
    header = f"\U0001f4cb Current: {current_display}{checkmark}"

    buttons = []

    for i in range(0, len(sorted_projects), 2):
        row = []
        for j in range(2):
            if i + j < len(sorted_projects):
                p = sorted_projects[i + j]
                label = p.get("title", p["name"])
                if p["name"] == current_project:
                    label = f"{label} \u2705"
                cb_data = f"{CALLBACK_PREFIX}{p['name']}"
                if len(cb_data.encode("utf-8")) > 64:
                    label = f"{label} (name too long)"
                    row.append(
                        InlineKeyboardButton(
                            text=label,
                            callback_data=f"{CALLBACK_PREFIX}{INVALID_MARKER}",
                        )
                    )
                else:
                    row.append(InlineKeyboardButton(text=label, callback_data=cb_data))
        buttons.append(row)

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return header, keyboard
