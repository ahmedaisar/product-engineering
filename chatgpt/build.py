#!/usr/bin/env python3
"""Build a portable ChatGPT Agent Plugin from the canonical skill packs."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHATGPT = Path(__file__).resolve().parent
PACKS = (
    "product",
    "ai-shipping",
    "agent-teams",
    "agent-harness",
    "app-stack",
    "work-humanizer",
)
PLUGIN_NAME = "product-engineering"


def current_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"



def adapt_skill_for_chatgpt(skill_file: Path) -> None:
    """Preserve user-started workflows by making their activation rule explicit in metadata."""
    text = skill_file.read_text(encoding="utf-8")
    match = re.match(r"\\A---\\s*\\n(.*?)\\n---(.*)\\Z", text, re.S)
    if not match:
        return
    frontmatter, body = match.groups()
    if not re.search(r"(?m)^disable-model-invocation:\\s*true\\s*$", frontmatter):
        return

    description_match = re.search(
        r'(?m)^description:\\s*("(?:\\\\.|[^"\\\\])*"|' + r"'[^']*'|[^\\n]+)$",
        frontmatter,
    )
    prefix = "Only activate when the user explicitly asks to run this skill by name. "
    if description_match:
        raw_value = description_match.group(1).strip()
        if raw_value.startswith('"'):
            description = json.loads(raw_value)
        elif raw_value.startswith("'") and raw_value.endswith("'"):
            description = raw_value[1:-1].replace("''", "'")
        else:
            description = raw_value
        replacement = "description: " + json.dumps(prefix + str(description))
        frontmatter = (
            frontmatter[:description_match.start()]
            + replacement
            + frontmatter[description_match.end():]
        )
    else:
        frontmatter += "\\ndescription: " + json.dumps(prefix.rstrip())
    skill_file.write_text("---\\n" + frontmatter + "\\n---" + body, encoding="utf-8")


def build(output: Path, mcp_url: str | None = None) -> dict:
    output = output.resolve()
    if output == ROOT or (ROOT in output.parents and output != ROOT / "dist"):
        raise ValueError("Use the default repository dist/ directory or an output directory outside the source repository.")
    output.mkdir(parents=True, exist_ok=True)
    plugin_root = output / PLUGIN_NAME
    if plugin_root.is_symlink():
        plugin_root.unlink()
    elif plugin_root.exists():
        shutil.rmtree(plugin_root)
    plugin_root.mkdir()
    shutil.copy2(CHATGPT / "plugin.json", plugin_root / "plugin.json")

    skills_root = plugin_root / "skills"
    skills_root.mkdir()
    shutil.copytree(
        CHATGPT / "skills" / "product-engineering-guide",
        skills_root / "product-engineering-guide",
    )

    seen: dict[str, str] = {}
    total = 0
    for pack in PACKS:
        source_root = ROOT / pack / "skills"
        if not source_root.is_dir():
            raise FileNotFoundError(f"Missing canonical skill directory: {source_root}")
        for skill_dir in sorted(p for p in source_root.iterdir() if p.is_dir()):
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.is_file():
                continue
            name = skill_dir.name
            if name in seen:
                raise ValueError(
                    f"Duplicate skill folder name {name!r}: {seen[name]} and {skill_dir}"
                )
            seen[name] = str(skill_dir.relative_to(ROOT))
            packaged_skill = skills_root / name
            shutil.copytree(skill_dir, packaged_skill)
            adapt_skill_for_chatgpt(packaged_skill / "SKILL.md")
            total += 1

    if total == 0:
        raise ValueError("No canonical skills were found.")

    if mcp_url:
        if not mcp_url.startswith("https://") or not mcp_url.endswith("/mcp"):
            raise ValueError("--mcp-url must be an HTTPS URL ending in /mcp")
        mcp_manifest = {
            "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": {
                "product-engineering": {
                    "type": "streamable-http",
                    "url": mcp_url,
                    "extensions": {"com.openai": {"auth": {"type": "none"}}},
                }
            },
        }
        (plugin_root / "mcp.json").write_text(
            json.dumps(mcp_manifest, indent=2) + "\n", encoding="utf-8"
        )

    metadata = {
        "plugin": PLUGIN_NAME,
        "source_repository": "https://github.com/ahmedaisar/product-engineering",
        "source_revision": current_revision(),
        "packs": list(PACKS),
        "skill_count": total,
        "skills": seen,
        "mcp_included": bool(mcp_url),
    }
    (plugin_root / "build-info.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )

    if ROOT in plugin_root.parents:
        relative_plugin_path = "./" + plugin_root.relative_to(ROOT).as_posix()
        marketplace_dir = ROOT / ".agents" / "plugins"
        marketplace_dir.mkdir(parents=True, exist_ok=True)
        marketplace = {
            "name": "product-engineering",
            "interface": {"displayName": "Product Engineering"},
            "plugins": [
                {
                    "name": "product-engineering",
                    "source": {"source": "local", "path": relative_plugin_path},
                    "policy": {
                        "installation": "AVAILABLE",
                        "authentication": "ON_INSTALL",
                    },
                    "category": "Productivity",
                }
            ],
        }
        (marketplace_dir / "marketplace.json").write_text(
            json.dumps(marketplace, indent=2) + "\n", encoding="utf-8"
        )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist",
        help="Build output directory (default: repository dist/)",
    )
    parser.add_argument(
        "--mcp-url",
        help="Optional deployed HTTPS MCP endpoint, ending in /mcp",
    )
    args = parser.parse_args()
    result = build(args.output, args.mcp_url)
    print(
        f"Built {result['plugin']} with {result['skill_count']} canonical skills "
        f"from {len(result['packs'])} packs at {args.output.resolve()}"
    )
    if not result["mcp_included"]:
        print("MCP omitted: this is a standalone skills-only package.")


if __name__ == "__main__":
    main()
