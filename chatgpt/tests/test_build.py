import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

BUILD_PATH = Path(__file__).resolve().parents[1] / "build.py"
spec = importlib.util.spec_from_file_location("product_engineering_build", BUILD_PATH)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class SkillAdaptationTests(unittest.TestCase):
    def test_user_started_skill_gets_explicit_only_description(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "SKILL.md"
            path.write_text(
                '---\nname: handover\ndescription: "Write a handover note."\n'
                'disable-model-invocation: true\n---\n\n# Body\n',
                encoding="utf-8",
            )
            builder.adapt_skill_for_chatgpt(path)
            result = path.read_text(encoding="utf-8")
            self.assertIn(
                'description: "Only activate when the user explicitly asks to run this skill by name.',
                result,
            )
            self.assertIn("disable-model-invocation: true", result)
            self.assertTrue(result.endswith("# Body\n"))

    def test_automatic_skill_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "SKILL.md"
            original = "---\nname: propose\ndescription: Make a proposal.\n---\n\n# Body\n"
            path.write_text(original, encoding="utf-8")
            builder.adapt_skill_for_chatgpt(path)
            self.assertEqual(path.read_text(encoding="utf-8"), original)


class PackageBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.chatgpt = self.root / "chatgpt"
        self.chatgpt.mkdir(parents=True)
        (self.chatgpt / "plugin.json").write_text(
            json.dumps({"name": "product-engineering"}), encoding="utf-8"
        )
        (self.chatgpt / "mcp.json").write_text(
            json.dumps({
                "mcpServers": {
                    "product-engineering": {
                        "type": "streamable-http",
                        "url": "https://example.vercel.app/mcp",
                    }
                }
            }),
            encoding="utf-8",
        )
        guide = self.chatgpt / "skills" / "product-engineering-guide"
        guide.mkdir(parents=True)
        (guide / "SKILL.md").write_text(
            "---\nname: product-engineering-guide\ndescription: Guide.\n---\n",
            encoding="utf-8",
        )
        self.original_root = builder.ROOT
        self.original_chatgpt = builder.CHATGPT
        builder.ROOT = self.root
        builder.CHATGPT = self.chatgpt
        for pack in builder.PACKS:
            skill = self.root / pack / "skills" / f"{pack}-skill"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                f"---\nname: {pack}-skill\ndescription: A {pack} skill.\n---\n",
                encoding="utf-8",
            )
            (skill / "references").mkdir()
            (skill / "references" / "guide.md").write_text("Reference", encoding="utf-8")

    def tearDown(self):
        builder.ROOT = self.original_root
        builder.CHATGPT = self.original_chatgpt
        self.temp.cleanup()

    def test_build_copies_all_packs_and_generates_marketplace(self):
        result = builder.build(self.root / "dist")
        plugin = self.root / "dist" / "product-engineering"
        self.assertEqual(result["skill_count"], len(builder.PACKS))
        self.assertTrue((plugin / "skills" / "product-engineering-guide" / "SKILL.md").is_file())
        self.assertTrue((plugin / "skills" / "product-skill" / "references" / "guide.md").is_file())
        self.assertTrue((self.root / "dist" / "product-engineering-chatgpt.zip").is_file())
        marketplace = json.loads(
            (self.root / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            marketplace["plugins"][0]["source"]["path"],
            "./dist/product-engineering",
        )
        self.assertEqual(marketplace["plugins"][0]["policy"]["installation"], "AVAILABLE")

    def test_external_output_does_not_create_repo_marketplace(self):
        output = Path(self.temp.name) / "external-output"
        builder.build(output)
        self.assertFalse((self.root / ".agents" / "plugins" / "marketplace.json").exists())
        self.assertTrue((output / "product-engineering" / "plugin.json").is_file())

    def test_submission_package_bundles_mcp_configuration(self):
        builder.build(self.root / "dist")
        plugin = self.root / "dist" / "product-engineering"
        self.assertTrue((plugin / "mcp.json").is_file())
        mcp_config = json.loads((plugin / "mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(
            mcp_config["mcpServers"]["product-engineering"]["type"],
            "streamable-http",
        )
        self.assertEqual(
            mcp_config["mcpServers"]["product-engineering"]["url"],
            "https://example.vercel.app/mcp",
        )
        self.assertEqual(
            json.loads((plugin / "build-info.json").read_text(encoding="utf-8"))["skill_count"],
            len(builder.PACKS),
        )

    def test_source_root_cannot_be_used_as_output(self):
        with self.assertRaises(ValueError):
            builder.build(self.root)


if __name__ == "__main__":
    unittest.main()
