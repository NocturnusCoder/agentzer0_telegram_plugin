import logging
from dataclasses import dataclass

from helpers import projects
from agent import AgentContext

_log = logging.getLogger(__name__)


@dataclass
class SwitchResult:
    success: bool
    title: str | None
    error: str | None


def switch_project(ctx: AgentContext, project_name: str, all_projects: list | None = None) -> SwitchResult:
    if all_projects is None:
        all_projects = projects.get_active_projects_list()
    project_names = [p["name"] for p in all_projects]
    if project_name not in project_names:
        display = [p.get("title", p["name"]) for p in all_projects]
        available = ", ".join(display) if display else "(none)"
        return SwitchResult(False, None, f'Project "{project_name}" not found.\nAvailable: {available}')

    try:
        projects.activate_project(ctx.id, project_name)
    except Exception as e:
        _log.error("Failed to activate project: %s", e, exc_info=True)
        return SwitchResult(False, None, "Failed to switch project. Check server logs.")

    ctx.reset()
    project_info = next((p for p in all_projects if p["name"] == project_name), None)
    title = project_info.get("title", project_name) if project_info else project_name
    _log.info("Project switched to \"%s\" for context %s", title, ctx.id)
    return SwitchResult(True, title, None)


def list_projects() -> list:
    return projects.get_active_projects_list()
