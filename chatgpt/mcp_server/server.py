"""Read-only MCP catalogue for Product Engineering skills."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import PurePosixPath
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import quote

import yaml
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse, Response

REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "ahmedaisar/product-engineering")
REF = os.environ.get("GITHUB_REF", "main")
PACKS = {
    "product",
    "ai-shipping",
    "agent-teams",
    "agent-harness",
    "app-stack",
    "work-humanizer",
}
CACHE_SECONDS = int(os.environ.get("CACHE_SECONDS", "300"))
REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "8"))
MAX_FILE_BYTES = 256_000

def _vercel_allowed_hosts() -> list[str]:
    """Build an exact Host allowlist from Vercel's deployment environment."""
    configured = os.environ.get("MCP_ALLOWED_HOSTS", "")
    hosts = {value.strip().lower() for value in configured.split(",") if value.strip()}
    # VERCEL_URL is deployment-specific; the project production URL is stable.
    for key in ("VERCEL_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
        value = os.environ.get(key, "").strip().lower()
        if value:
            hosts.add(value.removeprefix("https://").removeprefix("http://").rstrip("/"))
    # The SDK matches exact Host values; explicitly allow an optional port too.
    return sorted(host for value in hosts for host in (value, f"{value}:*"))


VERCEL_ALLOWED_HOSTS = _vercel_allowed_hosts()
TRANSPORT_SECURITY = (
    TransportSecuritySettings(allowed_hosts=VERCEL_ALLOWED_HOSTS)
    if VERCEL_ALLOWED_HOSTS
    else None
)

server = FastMCP(
    "product-engineering-skills",
    instructions=(
        "Use these read-only tools to discover and retrieve Product Engineering skills. "
        "Search before retrieving when the user describes a task but not a skill name. "
        "Read the full skill and required references before applying its workflow."
    ),
    host=os.environ.get("HOST", "0.0.0.0"),
    port=int(os.environ.get("PORT", "8000")),
    stateless_http=True,
    transport_security=TRANSPORT_SECURITY,
)
_cache: dict[str, tuple[float, Any]] = {}


class RepositoryError(RuntimeError):
    """A bounded, user-safe repository retrieval error."""


def _cached(key: str, loader):
    now = time.monotonic()
    entry = _cache.get(key)
    if entry and now - entry[0] < CACHE_SECONDS:
        return entry[1]
    value = loader()
    _cache[key] = (now, value)
    return value


def _github_text(url: str, max_bytes: int = MAX_FILE_BYTES) -> str:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "product-engineering-skills-mcp/1.0",
        },
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            raw = response.read(max_bytes + 1)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RepositoryError(f"GitHub request failed: {type(exc).__name__}") from exc
    if len(raw) > max_bytes:
        raise RepositoryError("Requested repository content exceeds the size limit.")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RepositoryError("Requested repository content is not UTF-8 text.") from exc


def _api_url(path: str) -> str:
    return f"https://api.github.com/repos/{REPOSITORY}/{path}"


def _raw_url(path: str) -> str:
    ref = quote(REF, safe="")
    encoded_path = quote(path, safe="/")
    return f"https://raw.githubusercontent.com/{REPOSITORY}/{ref}/{encoded_path}"


def _tree() -> dict:
    def load():
        payload = json.loads(_github_text(_api_url(f"git/trees/{REF}?recursive=1"), 5_000_000))
        if payload.get("truncated"):
            raise RepositoryError("GitHub returned a truncated repository tree.")
        return payload

    return _cached("tree", load)


def _parse_skill(markdown: str, fallback_name: str) -> dict[str, str]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", markdown, re.S)
    frontmatter = yaml.safe_load(match.group(1)) if match else {}
    if not isinstance(frontmatter, dict):
        frontmatter = {}
    name = frontmatter.get("name")
    description = frontmatter.get("description")
    return {
        "name": str(name or fallback_name),
        "description": str(description or "").strip().strip('"').strip("'"),
    }


def _catalogue() -> list[dict[str, str]]:
    def load():
        items = []
        for entry in _tree()["tree"]:
            path = entry.get("path", "")
            match = re.fullmatch(r"([^/]+)/skills/([^/]+)/SKILL\.md", path)
            if not match or match.group(1) not in PACKS:
                continue
            pack, folder = match.groups()
            raw_url = _raw_url(path)
            metadata = _parse_skill(_github_text(raw_url), folder)
            items.append(
                {
                    "name": metadata["name"],
                    "folder": folder,
                    "pack": pack,
                    "description": metadata["description"],
                    "path": path,
                }
            )
        return sorted(items, key=lambda item: (item["pack"], item["name"]))

    return _cached("catalogue", load)


def _skill(name: str) -> dict[str, str]:
    for item in _catalogue():
        if item["name"] == name or item["folder"] == name:
            return item
    raise ValueError(f"Unknown skill: {name}")


def _safe_skill_path(skill: dict[str, str], relative_path: str) -> str:
    if not relative_path or "\\" in relative_path:
        raise ValueError("Provide a relative path inside the selected skill folder.")
    path = PurePosixPath(relative_path)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("Path must stay inside the selected skill folder.")
    prefix = str(PurePosixPath(skill["path"]).parent)
    candidate = f"{prefix}/{path.as_posix()}"
    tracked = {entry.get("path") for entry in _tree()["tree"]}
    if candidate not in tracked:
        raise ValueError("That file is not tracked inside this skill folder.")
    return candidate


@server.tool()
def list_skill_packs() -> dict:
    """List the six Product Engineering skill packs and their skill counts."""
    catalogue = _catalogue()
    return {
        "repository": REPOSITORY,
        "ref": REF,
        "packs": [
            {
                "name": pack,
                "skill_count": sum(1 for item in catalogue if item["pack"] == pack),
            }
            for pack in sorted(PACKS)
        ],
        "total_skills": len(catalogue),
    }


@server.tool()
def list_skills(pack: str = "") -> dict:
    """List skills, optionally filtered to one pack name."""
    if pack and pack not in PACKS:
        raise ValueError(f"Unknown pack {pack!r}.")
    items = [item for item in _catalogue() if not pack or item["pack"] == pack]
    return {"count": len(items), "skills": items}


@server.tool()
def search_skills(query: str, limit: int = 8) -> dict:
    """Find relevant skills by matching a task description against skill names and descriptions."""
    query = query.strip().lower()
    if not query:
        raise ValueError("Query must not be empty.")
    if not 1 <= limit <= 20:
        raise ValueError("Limit must be between 1 and 20.")
    terms = {term for term in re.findall(r"[a-z0-9][a-z0-9-]*", query) if len(term) > 1}
    scored = []
    for item in _catalogue():
        haystack = f"{item['name']} {item['pack']} {item['description']}".lower()
        score = sum(3 if term == item["name"] else 2 if term in item["name"] else 1 for term in terms if term in haystack)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["pack"], pair[1]["name"]))
    return {"query": query, "results": [item for _, item in scored[:limit]]}


@server.tool()
def get_skill(name: str) -> dict:
    """Retrieve the complete SKILL.md instructions for a skill by name or folder."""
    item = _skill(name)
    url = _raw_url(item["path"])
    content = _cached(f"file:{item['path']}", lambda: _github_text(url))
    return {**item, "content": content, "source_url": f"https://github.com/{REPOSITORY}/blob/{REF}/{item['path']}"}


@server.tool()
def get_skill_file(name: str, relative_path: str) -> dict:
    """Retrieve a tracked UTF-8 text reference, script or template from inside a skill folder."""
    item = _skill(name)
    path = _safe_skill_path(item, relative_path)
    url = _raw_url(path)
    content = _cached(f"file:{path}", lambda: _github_text(url))
    return {
        "skill": item["name"],
        "path": path,
        "content": content,
        "source_url": f"https://github.com/{REPOSITORY}/blob/{REF}/{path}",
    }


@server.tool()
def check_skill_updates(installed_revision: str = "") -> dict:
    """Compare an installed package's source revision with the current configured repository ref."""
    tree = _tree()
    current = tree.get("sha", "")
    return {
        "repository": REPOSITORY,
        "ref": REF,
        "current_revision": current,
        "installed_revision": installed_revision or None,
        "update_available": bool(installed_revision and current and installed_revision != current),
        "note": "This reports source drift only; updating the installed plugin is an explicit user action.",
    }


@server.tool()
def get_repository_info() -> dict:
    """Return repository identity, current source revision and the number of indexed skills."""
    tree = _tree()
    return {
        "repository": REPOSITORY,
        "ref": REF,
        "revision": tree.get("sha", ""),
        "skill_count": len(_catalogue()),
        "packs": sorted(PACKS),
        "source_url": f"https://github.com/{REPOSITORY}",
    }


@server.custom_route("/health", methods=["GET"])
async def health(_request: StarletteRequest) -> Response:
    """Public liveness endpoint; it intentionally exposes no repository data."""
    return JSONResponse({"status": "ok", "service": "product-engineering-skills"})


# FastMCP 1.26.0 accepts transport security in its constructor;
# streamable_http_app() itself takes no keyword arguments in this pinned SDK.
app = server.streamable_http_app()


if __name__ == "__main__":
    server.run(transport="streamable-http")
