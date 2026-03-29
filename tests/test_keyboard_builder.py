from keyboard_builder import build_project_keyboard
from constants import CALLBACK_PREFIX, INVALID_MARKER


class TestBuildProjectKeyboard:
    def test_no_projects(self):
        header, keyboard = build_project_keyboard(None, [])
        assert "No projects found" in header
        assert keyboard is None

    def test_with_current_marked(self, sample_projects):
        header, keyboard = build_project_keyboard("my_research", sample_projects)
        assert "My Research" in header
        assert "\u2705" in header
        # Find the button with checkmark
        texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        checked = [t for t in texts if "\u2705" in t]
        assert len(checked) == 1
        assert "My Research" in checked[0]

    def test_two_column_layout(self, sample_projects):
        _, keyboard = build_project_keyboard(None, sample_projects)
        assert len(keyboard.inline_keyboard) == 2  # 3 projects -> 2 rows
        assert len(keyboard.inline_keyboard[0]) == 2
        assert len(keyboard.inline_keyboard[1]) == 1

    def test_callback_data_limit(self):
        long_name = "x" * 70
        projects = [{"name": long_name, "title": "Long Project"}]
        _, keyboard = build_project_keyboard(None, projects)
        btn = keyboard.inline_keyboard[0][0]
        assert "name too long" in btn.text
        assert btn.callback_data == f"{CALLBACK_PREFIX}{INVALID_MARKER}"

    def test_callback_data_within_limit(self, sample_projects):
        _, keyboard = build_project_keyboard(None, sample_projects)
        for row in keyboard.inline_keyboard:
            for btn in row:
                assert len(btn.callback_data.encode("utf-8")) <= 64
                assert btn.callback_data.startswith(CALLBACK_PREFIX)

    def test_no_current(self, sample_projects):
        header, keyboard = build_project_keyboard(None, sample_projects)
        assert "(none)" in header
        texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert not any("\u2705" in t for t in texts)

    def test_sorted_by_title(self):
        projects = [
            {"name": "c", "title": "Z Project"},
            {"name": "a", "title": "A Project"},
            {"name": "b", "title": "M Project"},
        ]
        _, keyboard = build_project_keyboard(None, projects)
        texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert texts.index("A Project") < texts.index("M Project") < texts.index("Z Project")
