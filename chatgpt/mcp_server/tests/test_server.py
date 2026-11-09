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


if __name__ == "__main__":
    unittest.main()
