# MCP skill retrieval investigation

Date: 2026-11-10

## Observation

The connected Product Engineering MCP client successfully returned structured results for repository metadata, skill-pack listing, app-stack listing, and skill search. In contrast, `get_skill` and `get_skill_file` calls were surfaced as empty objects (`{}`) by the client.

The canonical implementations in `server.py` return ordinary dictionaries with a `content` string and metadata. This source inspection does not establish that the server itself emitted an empty result.

## Root cause

A direct MCP `tools/call` against the original production deployment showed that FastMCP serialized the returned dictionary as a JSON string inside the MCP text content block. That JSON string itself contained a `content` property holding the full skill Markdown. The connected tool adapter surfaced this shape as an empty object (`{}`), even though the raw server response contained the file.

## Fix

Both retrieval tools now return plain text strings instead of dictionaries:

- `get_skill` returns a source line followed by the complete `SKILL.md`.
- `get_skill_file` returns skill/path/source metadata followed by the complete file.

This avoids nesting a second `content` field inside the MCP text payload and gives clients a simple text result to render. Added unit tests cover both functions.

## Validation

- Ran `python -m unittest discover -s chatgpt/mcp_server/tests -v`: all 12 tests passed.
- Deployed the fix to a Vercel preview for commit `b1dff6729cb290f5b385196cc07bcd594094f69a`.
- Called `get_skill({name: "ui-design"})` over the preview's raw Streamable HTTP MCP endpoint. It returned HTTP 200 with an MCP text content block containing the complete skill (13,765 characters; response 28,124 bytes).
- The original production response was also inspected: it contained a JSON-serialized object with a nested `content` key, confirming the problematic result shape.

The preview's raw MCP endpoint was tested directly. The connected ChatGPT tool adapter will need to pick up the merged production deployment before the end-to-end client symptom can be rechecked.
