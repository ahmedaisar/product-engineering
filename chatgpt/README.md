# Product Engineering for ChatGPT

A portable ChatGPT plugin package for the Product Engineering skills collection.

This directory contains the packaging and MCP integration source. The installable plugin is generated from the canonical skill folders in the repository; skills are not maintained as duplicate copies.

## What is included

- All skills from the six existing packs: `product`, `ai-shipping`, `agent-teams`, `agent-harness`, `app-stack`, and `work-humanizer`.
- Supporting references, scripts, templates and assets located inside each skill folder.
- A small, read-only MCP service for live skill discovery, retrieval and source revision checks.
- A portable Agent Plugins manifest compatible with ChatGPT and Codex plugin packaging.
- A ChatGPT onboarding skill, `product-engineering-guide`, that routes users to the canonical workflows and preserves explicit-only invocation for four user-started skills.

## Build the plugin

Requires Python 3.10+ and no third-party packages for packaging:

```bash
python chatgpt/build.py
```

This creates `dist/product-engineering/`, a distributable archive at `dist/product-engineering-chatgpt.zip`, and a repo-scoped marketplace at `.agents/plugins/marketplace.json`. The generated files are build outputs and should not be edited by hand.

## Install in ChatGPT web

The generated ZIP is a skills-only plugin so it can be uploaded for ChatGPT web use without declaring a bundled MCP server.

1. Run `python chatgpt/build.py`.
2. Open **Admin Console** in ChatGPT, select the intended workspace and open **Plugins**.
3. Select **Add → Upload plugin** and upload `dist/product-engineering-chatgpt.zip`.
4. Review the imported plugin and configure its installation policy for the intended workspace roles.
5. Test it in a new chat by asking it to find the relevant Product Engineering workflow.

Uploading requires an eligible workspace owner or administrator with plugin upload permission. Installation and Skills availability still depend on plan, role and workspace settings. OpenAI documents native Skills in ChatGPT for eligible Business, Enterprise, Healthcare and Edu users; a valid ZIP does not grant eligibility.

## Install from the desktop app

For local development, the build also generates `.agents/plugins/marketplace.json`, pointing to `./dist/product-engineering`. Add this repository-scoped marketplace in the ChatGPT desktop app, restart the app, then install Product Engineering from the marketplace.

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

The server listens on port 8000 and exposes Streamable HTTP at `/mcp`. Build the container from the repository root with `docker build -f chatgpt/mcp_server/Dockerfile -t product-engineering-mcp .`, then run it with `docker run --rm -p 8000:8000 product-engineering-mcp`. Configure the host to route HTTPS traffic to port 8000. Set `GITHUB_REPOSITORY` and optionally `GITHUB_REF` to point at a fork or pinned ref.

The MCP service is optional and intentionally separate from the web-uploaded skills plugin. In ChatGPT web, when custom MCP servers are available to your account or workspace, deploy the service and add it through **Plugins → Add custom MCP server** using the HTTPS `/mcp` endpoint. Create the connection as a separate plugin and invoke it in a supported Work chat. This separation keeps the skills package free of an embedded MCP declaration, which can cause imported plugins to be labelled Desktop only.

Do not put GitHub tokens or other secrets in the plugin package. The default public repository requires no credentials.

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
