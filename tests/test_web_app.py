import unittest

from src.dashboard.web_app import APP_HTML, get_app_version


class AppVersionTests(unittest.TestCase):
    def test_version_uses_semantic_version_format(self):
        self.assertRegex(get_app_version(), r"^\d+\.\d+\.\d+$")

    def test_version_placeholder_exists_in_web_page(self):
        self.assertIn("{{APP_VERSION}}", APP_HTML)
        rendered = APP_HTML.replace("{{APP_VERSION}}", get_app_version())
        self.assertNotIn("{{APP_VERSION}}", rendered)
        self.assertIn(f"Version {get_app_version()}", rendered)
