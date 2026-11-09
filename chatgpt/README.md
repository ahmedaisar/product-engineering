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

The generated ZIP includes both the packaged skills and the remote Vercel MCP server configuration. This is intentional: OpenAI does not currently support adding an MCP server to an already-submitted skills-only plugin.

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

The MCP service is packaged with the skills as one portable plugin. The root `mcp.json` declares the public Vercel Streamable HTTP endpoint. During public directory submission, upload the generated ZIP, connect the declared server through the **With MCP** flow, complete domain verification, and scan the discovered tools. The MCP service is read-only; the skills provide the workflows and the MCP tools provide live catalogue discovery and retrieval.

Do not put GitHub tokens or other secrets in the plugin package. The default public repository requires no credentials.

## Deploy the MCP service to Vercel

The MCP service is prepared as a Vercel Python/ASGI Function. The `index.py` entrypoint exports the FastMCP Streamable HTTP ASGI application, and Vercel installs dependencies from this directory's `requirements.txt`.

1. In Vercel, choose **Add New → Project** and import `ahmedaisar/product-engineering` from GitHub.
2. Set **Root Directory** to `chatgpt/mcp_server` and leave **Include files outside the Root Directory** disabled.
3. Use the **Other** framework preset (or let Vercel detect the Python ASGI app). Leave Build Command and Output Directory blank.
4. Optionally set `GITHUB_REPOSITORY=ahmedaisar/product-engineering`, `GITHUB_REF=main`, `CACHE_SECONDS=300`, and `REQUEST_TIMEOUT=8`. The repository and ref defaults already match this project.
5. Deploy. Vercel injects `VERCEL_URL` and `VERCEL_PROJECT_PRODUCTION_URL`; the app uses those values to configure the MCP SDK Host allowlist. If you use an additional custom domain, add its hostname to `MCP_ALLOWED_HOSTS` as a comma-separated value.
6. Verify `https://<deployment-host>/health` returns `{"status":"ok","service":"product-engineering-skills"}`.
7. Connect your MCP client to `https://<deployment-host>/mcp`.
8. When the OpenAI submission portal gives you a domain-verification token, set it as `OPENAI_APPS_CHALLENGE_TOKEN` in Vercel and redeploy. The service then returns that exact token as plain text at `/.well-known/openai-apps-challenge`. Remove the variable after verification if you no longer need the challenge route.

The public GitHub repository requires no token. The MCP tools are read-only. The endpoint currently has no user authentication, so keep it intended for the connected integration and add authentication before exposing it to untrusted clients. Vercel function duration and streaming limits depend on your plan.

The repository changes prepare the service but do not create a Vercel project or deploy it; project creation and deployment remain under your account.

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


## Public ChatGPT app submission

The package includes both skills and the remote MCP configuration from the first upload. Do not remove `mcp.json` for the initial directory submission: OpenAI currently does not support adding an MCP server to a plugin first submitted as skills-only.

Build the submission archive:

```bash
python chatgpt/build.py
```

The ZIP contains `plugin.json`, `mcp.json`, the onboarding skill, and the canonical skills from all six packs. The manifest includes five positive and three negative MCP review cases. Before submitting, run all eight cases against the live service and capture a reviewer-accessible walkthrough video. Add its URL to `extensions.com.openai.review.demo_recording_url` in `plugin.json`, rebuild, and upload the final ZIP.

OpenAI's submission portal also requires a verified developer identity, domain verification, a successful MCP tool scan, and completed policy attestations. For domain verification, copy the exact token shown by the portal into Vercel's `OPENAI_APPS_CHALLENGE_TOKEN` environment variable, redeploy, and confirm that `https://<deployment-host>/.well-known/openai-apps-challenge` returns only that token as plain text. Never commit the token to Git.

The privacy policy and terms are published in `chatgpt/PRIVACY.md` and `chatgpt/TERMS.md`. Review these documents for accuracy and ensure the developer identity selected in the OpenAI portal matches the publisher information in the package before submission.
