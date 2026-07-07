# py-seed Guardrails

Short version for a small team:

- Keep py-seed as a high-level Python SDK.
- Use OpenAPI-generated code only behind the scenes.
- Keep generated code internal; user-facing APIs stay in `SeedClient` and related high-level modules.
- Do not turn this repo into an MCP server.

## Practical Rules

- Keep existing high-level method signatures stable unless you intentionally make a breaking change.
- Map generated-client errors to py-seed exceptions so behavior stays predictable.
- Treat generated files as generated: no hand-edits.
- Add or update tests when migrating methods to generated internals.

## MCP Note

If we build MCP tools, they should consume py-seed from a separate package/repo.
