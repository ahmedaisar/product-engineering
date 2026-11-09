# Product Engineering for ChatGPT

A portable ChatGPT plugin package for the Product Engineering skills collection.

This directory contains the packaging and MCP integration source. The installable plugin is generated from the canonical skill folders in the repository; skills are not maintained as duplicate copies.

## What is included

- All skills from the six existing packs: `product`, `ai-shipping`, `agent-teams`, `agent-harness`, `app-stack`, and `work-humanizer`.
- Supporting references, scripts, templates and assets located inside each skill folder.
- A small, read-only MCP service for live skill discovery, retrieval and source revision checks.
- A portable Agent Plugins manifest compatible with ChatGPT and Codex plugin packaging.

## Build the plugin

Requires Python 3.10+ and no third-party packages for packaging:

```bash
python chatgpt/build.py
```

This creates `dist/product-engineering/` and a repo-scoped marketplace at `.agents/plugins/marketplace.json`. The generated directories are build outputs and should not be edited by hand.

To include the optional remote MCP connection:

```bash
python chatgpt/build.py --mcp-url https://YOUR-HOST.example/mcp
```

The URL must be the deployed HTTPS Streamable HTTP endpoint. Without `--mcp-url`, the package is skills-only and remains useful without the MCP service.

## Install and test

There are two distinct installation paths. The local/repo marketplace workflow is for the ChatGPT desktop app; the web workflow connects the hosted MCP service as a personal plugin.

### ChatGPT desktop: local repository marketplace

1. Clone this repository and run `python chatgpt/build.py`.
2. Open the ChatGPT desktop app and add the repo-scoped marketplace at `.agents/plugins/marketplace.json`.
3. Restart the desktop app, open Plugins, choose the Product Engineering marketplace and install the plugin.
4. Start a new chat and invoke Product Engineering or ask a task that matches one of its skills.

The generated marketplace points to `./dist/product-engineering`. Re-run the build after pulling repository changes to refresh the generated package.

### ChatGPT web: connect the MCP service

1. Deploy the MCP service and obtain its stable HTTPS endpoint ending in `/mcp`.
2. In ChatGPT web, open Plugins, select **Add custom MCP server**, and enter that endpoint.
3. Choose no authentication for this public, read-only service, review the connection warning and create it as a plugin.
4. Install the resulting personal plugin, switch to a supported Work chat, and invoke it with `@` or ask ChatGPT to find a skill.
5. Try: "Find the skill for reviewing a release" and "Retrieve the release-gate skill instructions."

This web flow exposes the live MCP tools. It does not automatically import the bundled skill folders into your account. To use bundled native skills, install the portable package through a supported plugin marketplace/source or upload individual skills using the Skills interface when your account and workspace support it.

Public directory distribution is a separate release step: deploy the stable HTTPS MCP endpoint, prepare the package and submit it through OpenAI's plugin submission process. Creating files in this repository does not publish a plugin to the public directory.

**Plan and workspace note:** OpenAI documents the Plugins directory across plans, but native Skills in ChatGPT are currently available only to eligible Business, Enterprise, Healthcare and Edu users, subject to workspace settings. Work and custom MCP app access also depend on plan and workspace controls. A valid package does not override account eligibility. See [Skills in ChatGPT](https://help.openai.com/en/articles/20001066-skills-in-chatgpt) and [Plugins in ChatGPT](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt).

## MCP service

The service is in `chatgpt/mcp_server/`. It reads the public GitHub repository and exposes read-only tools:

- `list_skill_packs`
- `list_skills`
- `search_skills`
- `get_skill`
- `get_skill_file`
- `check_skill_updates`
- `get_repository_info`

Run locally:

```bash
cd chatgpt/mcp_server
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python server.py
```

The server listens on port 8000 and exposes Streamable HTTP at `/mcp`. Configure the host to route HTTPS traffic to port 8000. Set `GITHUB_REPOSITORY` and optionally `GITHUB_REF` to point at a fork or pinned ref.

The MCP service is optional. Do not put GitHub tokens or other secrets in the plugin package. The default public repository requires no credentials.

## Security and behavior

- MCP tools are read-only.
- Skill file retrieval is restricted to tracked files inside known skill directories.
- Paths containing traversal segments, absolute paths, or backslashes are rejected.
- The service fetches only from the configured GitHub repository.
- The service uses bounded timeouts and a short in-memory cache.
- Updating the plugin package is an explicit user action; MCP can report a newer source revision but cannot silently update an installed plugin.

## Development checks

From the repository root:

```bash
python -m unittest discover -s chatgpt/mcp_server/tests -v
python chatgpt/build.py --output /tmp/product-engineering-plugin
```

The existing collection validator remains authoritative for canonical skill quality:

```bash
VALIDATE_STRICT=1 python -B tools/validate.py
```
