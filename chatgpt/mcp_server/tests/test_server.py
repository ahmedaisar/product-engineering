import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"
spec = importlib.util.spec_from_file_location("product_engineering_mcp_server", SERVER_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class SkillParsingTests(unittest.TestCase):
    def test_parse_skill_frontmatter(self):
        text = '---\nname: release-gate\ndescription: "Review a release safely."\n---\n\n# Body\n'
        self.assertEqual(
            module._parse_skill(text, "fallback"),
            {"name": "release-gate", "description": "Review a release safely."},
        )

    def test_parse_missing_frontmatter(self):
        self.assertEqual(module._parse_skill("# no metadata", "fallback")["name"], "fallback")


class PathSafetyTests(unittest.TestCase):
    def setUp(self):
        self.skill = {
            "name": "demo",
            "path": "product/skills/demo/SKILL.md",
        }

    def test_reject_parent_traversal(self):
        with self.assertRaises(ValueError):
            module._safe_skill_path(self.skill, "../README.md")

    def test_reject_absolute_path(self):
        with self.assertRaises(ValueError):
            module._safe_skill_path(self.skill, "/etc/passwd")

    def test_reject_backslash(self):
        with self.assertRaises(ValueError):
            module._safe_skill_path(self.skill, "references\\secret.md")

    @patch.object(module, "_tree", return_value={"tree": [{"path": "product/skills/demo/references/guide.md"}]})
    def test_accept_tracked_relative_path(self, _tree):
        self.assertEqual(
            module._safe_skill_path(self.skill, "references/guide.md"),
            "product/skills/demo/references/guide.md",
        )

    @patch.object(module, "_tree", return_value={"tree": []})
    def test_reject_untracked_file(self, _tree):
        with self.assertRaises(ValueError):
            module._safe_skill_path(self.skill, "secrets.txt")


class VercelDeploymentTests(unittest.TestCase):
    @patch.dict(
        module.os.environ,
        {
            "VERCEL_URL": "product-engineering-preview.vercel.app",
            "VERCEL_PROJECT_PRODUCTION_URL": "product-engineering.vercel.app",
            "MCP_ALLOWED_HOSTS": "mcp.example.com",
        },
        clear=True,
    )
    def test_vercel_hosts_are_allowlisted_with_optional_ports(self):
        self.assertEqual(
            module._vercel_allowed_hosts(),
            [
                "mcp.example.com",
                "mcp.example.com:*",
                "product-engineering-preview.vercel.app",
                "product-engineering-preview.vercel.app:*",
                "product-engineering.vercel.app",
                "product-engineering.vercel.app:*",
            ],
        )

    def test_asgi_app_has_mcp_and_health_routes(self):
        paths = {route.path for route in module.app.routes}
        self.assertIn("/mcp", paths)
        self.assertIn("/health", paths)
        self.assertIn("/.well-known/openai-apps-challenge", paths)

    def test_app_factory_uses_pinned_sdk_no_argument_signature(self):
        # MCP 1.26.0 accepts transport_security on FastMCP(), not on this method.
        self.assertTrue(callable(module.server.streamable_http_app))
        self.assertIsNotNone(module.app)
        self.assertIs(module.server.settings.transport_security, module.TRANSPORT_SECURITY)


if __name__ == "__main__":
    unittest.main()


class SkillRetrievalTests(unittest.TestCase):
    @patch.object(module, "_skill", return_value={
        "name": "ui-design",
        "folder": "ui-design",
        "pack": "app-stack",
        "path": "app-stack/skills/ui-design/SKILL.md",
        "description": "UI design rules",
    })
    @patch.object(module, "_github_text", return_value="# UI design\\n\\nFull skill body.")
    def test_get_skill_returns_renderable_plain_text(self, _github_text, _skill):
        result = module.get_skill("ui-design")
        self.assertIsInstance(result, str)
        self.assertIn("https://github.com/ahmedaisar/product-engineering/blob/main/app-stack/skills/ui-design/SKILL.md", result)
        self.assertIn("# UI design\\n\\nFull skill body.", result)

    @patch.object(module, "_safe_skill_path", return_value="app-stack/skills/ui-design/references/tokens.md")
    @patch.object(module, "_skill", return_value={
        "name": "ui-design",
        "folder": "ui-design",
        "pack": "app-stack",
        "path": "app-stack/skills/ui-design/SKILL.md",
        "description": "UI design rules",
    })
    @patch.object(module, "_github_text", return_value="# Design tokens\\n\\nReference body.")
    def test_get_skill_file_returns_renderable_plain_text(self, _github_text, _skill, _safe_path):
        result = module.get_skill_file("ui-design", "references/tokens.md")
        self.assertIsInstance(result, str)
        self.assertIn("references/tokens.md", result)
        self.assertIn("# Design tokens\\n\\nReference body.", result)
