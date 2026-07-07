# OpenAPI Direction for py-seed

## What We Are Doing

- Keep py-seed as the high-level SDK people code against.
- Use OpenAPI generation to cover endpoints faster.
- Keep generated code internal and route it through a small adapter layer.

## What We Are Not Doing

- We are not replacing `SeedClient` with raw generated methods.
- We are not turning this repo into an MCP server.

## Lightweight Implementation Plan

1. Add a generation script and generated-code folder.
2. Add an adapter layer for auth, retries/pagination, and exception mapping.
3. Migrate high-value methods incrementally.
4. Keep behavior-compatible tests around high-level methods.

## Rule of Thumb

If a change makes endpoint coverage better but high-level usability worse, do not merge it as-is.
