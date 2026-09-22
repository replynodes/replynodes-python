# AGENTS.md — ReplyNodes Python SDK

This file is the fast orientation guide for AI coding agents working in this repository.

## Purpose

This repository contains the official Python SDK for the ReplyNodes public read API.

ReplyNodes provides normalized public web context for software and AI agents. The supported SDK surface mirrors the merged TypeScript reference SDK (`replynodes/replynodes-typescript`): App Store, Brand, FOMO, Google, Google Maps, Google Play, Google Shopping, Hacker News, Instagram, Reddit, TikTok, Web, and YouTube.

## Read these files first

1. `README.md` — product context, quick start, supported public SDK surface.
2. `sdk/dx/__init__.py` — authoritative developer-facing Python wrapper.
3. `sdk/README.md` — package generation, testing, and implementation notes.
4. `openapi/` — vendored public OpenAPI contract used to generate the low-level client.

## Source of truth

- Public developer-facing API: `sdk/dx/__init__.py`
- HTTP contract: `openapi/replynodes-fetcher.openapi.json` (vendored, byte-identical to the canonical `replynodes-fetcher` repo's `api-docs/replynodes-fetcher.openapi.json`)
- Generated client: `sdk/generated/replynodes/`

Do not treat generated files as the primary SDK API.

## Generated code rule

Do not manually edit `sdk/generated/` unless the task explicitly requires investigating generated output. Everything under `sdk/generated/replynodes/` (`api/`, `models/`, `api_client.py`, `configuration.py`, `exceptions.py`, `rest.py`, `api_response.py`, `__init__.py`) is produced by OpenAPI Generator `v7.10.0` and must never be hand-edited; `sdk/dx/` is never touched by regeneration.

When the OpenAPI contract changes, regenerate the client using the SDK generation workflow.

```bash
cd sdk
bash scripts/generate.sh   # requires Docker; regenerates sdk/generated/ only
python3 -m pytest
python3 scripts/check_surface_coverage.py
```

## Public SDK conventions

Preserve these behaviors unless the task explicitly changes the public contract:

- users instantiate the SDK with `ReplyNodes(api_key, base_url=None, timeout=None)`
- API keys are raw values; the SDK adds the Bearer authorization header
- successful responses expose normalized `data` and `meta`
- `meta.request_id` is retained for debugging/support
- pagination metadata may include `meta.next_cursor`
- HTTP failures are surfaced as `ReplyNodesError`
- request deadlines are surfaced as `ReplyNodesTimeoutError`
- retries are always explicitly disabled (`Configuration(retries=False)`); never let a hidden library default retry a request
- `timeout` is in **seconds** (not milliseconds — a deliberate, documented deviation from the TypeScript reference, matching Python HTTP client convention)

## Current public methods (representative, not exhaustive)

```text
client.youtube.search(...)
client.youtube.comments(...)
client.youtube.transcript(...)
client.reddit.search(...)
client.web.scrape(...)
client.google.search(...)
client.app_store.search(...)
client.app_store.reviews(...)
```

Do not document or expose a provider that is not present in the public contract. `PUBLIC_OPERATION_REGISTRY` in `sdk/dx/__init__.py` is the exhaustive, checked list.

## Documentation rules

When adding or changing a public SDK method:

1. update `openapi/replynodes-fetcher.openapi.json` when applicable (must stay byte-identical to the canonical `replynodes-fetcher` contract; never hand-edit it for presentation — that belongs in `sdk/scripts/project_public_openapi.py`)
2. regenerate generated code (`sdk/scripts/generate.sh`)
3. update the stable wrapper and `PUBLIC_OPERATION_REGISTRY` in `sdk/dx/__init__.py`
4. add or update tests in `sdk/test/`
5. run `python3 sdk/scripts/check_surface_coverage.py`
6. update `sdk/README.md` for package-specific behavior
7. update root `README.md` when discovery, supported providers, installation, or quick-start behavior changes

Examples should import from `replynodes.dx`, not from `sdk/generated/`.

## Agent efficiency

Avoid scanning the entire generated client before understanding the task. Start from `sdk/dx/__init__.py` and only inspect generated files or OpenAPI operations relevant to the requested method.

Prefer small, explicit changes to the stable wrapper over exposing the full generated client surface.

## Validation

Before completing SDK changes, run:

```bash
cd sdk
pip install -e ".[dev]"
python3 -m pytest
python3 scripts/check_surface_coverage.py
```

If generation inputs changed, run `bash scripts/generate.sh` first (requires Docker).
