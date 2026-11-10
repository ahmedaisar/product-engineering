# MCP skill retrieval investigation

Date: 2026-11-10

## Observation

The connected Product Engineering MCP client successfully returned structured results for repository metadata, skill-pack listing, app-stack listing, and skill search. In contrast, `get_skill` and `get_skill_file` calls were surfaced as empty objects (`{}`) by the client.

The canonical implementations in `server.py` return ordinary dictionaries with a `content` string and metadata. This source inspection does not establish that the server itself emitted an empty result.

## Current diagnosis

The failure boundary is not yet known. Plausible causes include:

1. The deployed Vercel service is not running the current `main` revision.
2. The raw MCP response envelope differs from the tool result exposed by the connector (for example, content is in `content` but not normalized into `structuredContent`).
3. The MCP client/connector adapter drops large or text-bearing structured results.
4. A server-side exception or output serialization issue occurs only for retrieval methods.

## Required reproduction

Call the deployed Streamable HTTP MCP endpoint directly using MCP `tools/call` for `get_skill` and `get_skill_file`. Record the raw JSON-RPC result, including `content`, `structuredContent`, and `isError`. Then compare that response with the connected client result.

Also verify the deployed Git commit/ref and add integration coverage that checks both retrieval tools return non-empty UTF-8 content.

## Scope

No service code was changed because the currently available evidence does not identify a safe, verified code fix. This note records the reproduced symptom and the next diagnostic step.
