# Privacy policy

Last updated: 2026-11-10

Product Engineering is an open-source collection of product and software engineering workflows.

## Information processed

The Product Engineering ChatGPT plugin includes packaged skill instructions and connects to a read-only MCP service hosted at https://product-engineering-self.vercel.app/mcp.

When the MCP service is used, it receives the tool inputs needed to search and retrieve public files from the configured public GitHub repository, ahmedaisar/product-engineering. The service does not request or require a GitHub account, GitHub token, or other user credentials.

The service may process request metadata needed to deliver the MCP connection. Hosting infrastructure providers may independently process standard operational logs.

## Data access and retention

The MCP tools only read public repository content. They do not create, update, or delete repository data, and they do not access private repositories or user accounts.

The service uses a short-lived in-memory cache for repository responses. It does not intentionally store conversation content or build user profiles.

## Third parties

The service retrieves repository content from GitHub and is hosted by Vercel. Their own privacy policies govern information they process on their infrastructure.

## Changes and contact

This policy may be updated as the service changes. For questions or privacy requests, open an issue at https://github.com/ahmedaisar/product-engineering/issues.
