from unittest.mock import patch, MagicMock

from project_switcher import switch_project, list_projects, SwitchResult


class TestSwitchProject:
    @patch("project_switcher.projects")
    def test_success(self, mock_projects, mock_context, sample_projects):
        mock_projects.get_active_projects_list.return_value = sample_projects
        mock_projects.activate_project.return_value = None
        result = switch_project(mock_context, "my_research")
        assert result.success is True
        assert result.title == "My Research"
        assert result.error is None
        mock_projects.activate_project.assert_called_once_with("ctx-uuid-001", "my_research")
        mock_context.reset.assert_called_once()

    @patch("project_switcher.projects")
    def test_not_found(self, mock_projects, mock_context, sample_projects):
        mock_projects.get_active_projects_list.return_value = sample_projects
        result = switch_project(mock_context, "nonexistent")
        assert result.success is False
        assert result.error is not None
        assert "nonexistent" in result.error
        assert "Project A" in result.error
        mock_context.reset.assert_not_called()

    @patch("project_switcher.projects")
    def test_empty_projects(self, mock_projects, mock_context):
        mock_projects.get_active_projects_list.return_value = []
        result = switch_project(mock_context, "anything")
        assert result.success is False
        assert "(none)" in result.error

    @patch("project_switcher.projects")
    def test_activate_raises(self, mock_projects, mock_context, sample_projects):
        mock_projects.get_active_projects_list.return_value = sample_projects
        mock_projects.activate_project.side_effect = RuntimeError("boom")
        result = switch_project(mock_context, "project_a")
        assert result.success is False
        assert "server logs" in result.error

    @patch("project_switcher.projects")
    def test_project_without_title(self, mock_projects, mock_context):
        mock_projects.get_active_projects_list.return_value = [
            {"name": "bare_name"},
        ]
        mock_projects.activate_project.return_value = None
        result = switch_project(mock_context, "bare_name")
        assert result.success is True
        assert result.title == "bare_name"


class TestListProjects:
    @patch("project_switcher.projects")
    def test_returns_list(self, mock_projects, sample_projects):
        mock_projects.get_active_projects_list.return_value = sample_projects
        result = list_projects()
        assert result == sample_projects
