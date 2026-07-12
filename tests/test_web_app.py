import unittest
from pathlib import Path

from src.dashboard.web_app import APP_HTML, get_app_version, load_web_settings


class AppVersionTests(unittest.TestCase):
    def test_version_uses_semantic_version_format(self):
        self.assertRegex(get_app_version(), r"^\d+\.\d+\.\d+$")

    def test_version_placeholder_exists_in_web_page(self):
        self.assertIn("{{APP_VERSION}}", APP_HTML)
        rendered = APP_HTML.replace("{{APP_VERSION}}", get_app_version())
        self.assertNotIn("{{APP_VERSION}}", rendered)
        self.assertIn(f"Version {get_app_version()}", rendered)


class WebSettingsTests(unittest.TestCase):
    def test_dashboard_template_comes_from_settings(self):
        settings = load_web_settings()

        self.assertEqual(Path(settings["dashboard_template"]).name, "PsO_dashboard_v4.html")
        self.assertTrue(Path(settings["dashboard_template"]).is_file())
