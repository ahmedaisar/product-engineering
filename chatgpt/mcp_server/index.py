"""Vercel Python runtime entrypoint for the Product Engineering MCP service."""

from server import app

# Vercel discovers the ASGI application exported as ``app``.
