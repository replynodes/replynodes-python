# ReplyNodes Python SDK

Official **Python SDK for ReplyNodes**, the web context API for software and AI agents.

Use one normalized API to retrieve structured public web context from the supported public ReplyNodes read surfaces without maintaining a separate integration for every source.

> Package: [`replynodes`](https://pypi.org/project/replynodes/) on PyPI
> Website: [replynodes.com](https://replynodes.com)
> Docs: [docs.replynodes.com](https://docs.replynodes.com)

## Install

```bash
pip install replynodes
```

## Quick start

```python
import os
from replynodes.dx import ReplyNodes

client = ReplyNodes(
    api_key=os.environ["REPLYNODES_API_KEY"],
    timeout=10,  # seconds
)

result = client.youtube.search(term="AI agents", limit=5)
print(result.data)
print(result.meta.request_id)
```

The SDK adds the `Authorization: Bearer ...` header automatically. Pass the raw ReplyNodes API key, not a value prefixed with `Bearer`.

## What is ReplyNodes?

ReplyNodes is a **web context API for developers, software, and AI agents**. It exposes public web sources through a consistent authenticated API and normalized JSON responses.

Typical use cases include:

- AI agent web research
- web search and retrieval
- web scraping and content extraction
- YouTube research and transcript retrieval
- Reddit research
- App Store research and competitor analysis
- brand and market intelligence
- retrieval pipelines and LLM tools
- MCP servers and autonomous software agents

Instead of integrating and maintaining multiple provider-specific APIs and scrapers, applications can use ReplyNodes as one context layer.

## Supported API surfaces

The wrapper exposes all 77 authenticated GET operations in the vendored public
OpenAPI contract through intentional resource/action namespaces. Resource and
method names follow the same canonical operation IDs as the merged
TypeScript reference SDK, translated to idiomatic Python `snake_case`:

| Resource | Methods |
| --- | --- |
| `app_store` | `app`, `developer`, `list`, `privacy`, `ratings`, `reviews`, `search`, `similar`, `suggest` |
| `brand` | `fonts`, `retrieve`, `search`, `styleguide` |
| `fomo` | `alerts`, `leaderboard`, `notifications`, `search`, `thesis`, `thesis_by_token`, `thesis_by_user`, `thesis_by_user_token`, `token_holders`, `tokens_graduated`, `tokens_most_held`, `tokens_trending`, `trade`, `user_balances`, `user_profile`, `user_trades` |
| `google` | `search` |
| `google_maps` | `place_details`, `place_reviews`, `search_places` |
| `google_play` | `app_details`, `availability`, `categories`, `category_apps`, `data_safety`, `developer`, `permissions`, `reviews`, `search`, `similar_apps`, `suggest` |
| `google_shopping` | `product_offers`, `search` |
| `hacker_news` | `item`, `search`, `stories_ask`, `stories_best`, `stories_job`, `stories_new`, `stories_show`, `stories_top`, `user` |
| `instagram` | `posts`, `profile` |
| `reddit` | `post_by_id`, `post_by_permalink`, `search`, `subreddit_posts`, `user_activity`, `user_posts` |
| `tiktok` | `post`, `user`, `user_posts` |
| `web` | `brand`, `crawl`, `map`, `scrape`, `search` |
| `youtube` | `channel`, `comments`, `playlist`, `related`, `search`, `transcript`, `video` |

`client.web.search(...)` is the same bound method object as `client.google.search(...)`
(both resolve to the canonical `googleSearch` operation), matching the
backward-compatible alias in the TypeScript reference. The supported surface
is contract-derived; run `sdk/scripts/check_surface_coverage.py` to verify it
still matches all 77 canonical GET operations after any regeneration.

## Normalized responses

Successful requests return a consistent response shape with `data` and `meta`.

```python
result = client.youtube.search(term="open source databases", limit=5)

print(result.data)
print(result.meta.request_id)
print(result.meta.next_cursor)
```

Use `meta.request_id` when debugging or contacting support. Cursor fields are returned when the underlying operation supports pagination; the SDK does not automatically paginate.

## Error handling

HTTP failures are surfaced as `ReplyNodesError` with useful machine-readable fields:

```python
from replynodes.dx import ReplyNodes, ReplyNodesError, ReplyNodesTimeoutError

client = ReplyNodes(api_key=os.environ["REPLYNODES_API_KEY"])

try:
    client.youtube.search(term="AI agents")
except ReplyNodesError as error:
    print(error.status)
    print(error.code)
    print(error.request_id)
    print(error.details)
except ReplyNodesTimeoutError:
    print("Request timed out")
```

`401` means authentication failed. `402` means payment or account credits are required. Other HTTP errors preserve their status and request ID.

The current OpenAPI schema marks success `meta.request_id` as required, while the backend may omit it; until the schema is corrected, a response missing it raises a `pydantic.ValidationError` instead of returning `request_id=None`. This mirrors a documented gap in the merged TypeScript reference SDK's contract, not new behavior introduced here.

## Authentication

```python
client = ReplyNodes(api_key=os.environ["REPLYNODES_API_KEY"])
```

The API key should be a raw ReplyNodes key such as `rn_test_...` or `rn_live_...`.

Do not hard-code API keys in source control. Use environment variables or your platform's secret manager.

## Retries and timeouts

The SDK never retries automatically. `Configuration(retries=False)` is set explicitly on every client, overriding `urllib3`'s own default of 3 retries, so a network hiccup never silently repeats a metered/billed GET. `timeout` is a positive number of **seconds** applied per request; a client-side deadline raises `ReplyNodesTimeoutError`. Omit `timeout` to use the platform default (no client-side deadline).

## Why use the SDK?

The SDK provides:

- typed Pydantic request/response models
- one authenticated client for supported ReplyNodes APIs
- normalized response handling
- a stable, hand-written wrapper around generated OpenAPI code
- request IDs for debugging and support
- typed HTTP errors
- configurable request timeouts with no hidden retries
- a vendored public OpenAPI contract for reproducible generation

## Repository layout

```text
replynodes-python/
├── README.md       # Product, discovery, and quick-start documentation
├── AGENTS.md       # Coding-agent orientation and repository rules
├── LICENSE
├── examples/       # Example integrations
├── openapi/        # Vendored ReplyNodes public OpenAPI contract
└── sdk/
    ├── README.md    # Package implementation and generation notes
    ├── pyproject.toml
    ├── generated/   # Generated OpenAPI client (do not hand-edit)
    ├── dx/          # Stable, hand-written developer-facing wrapper
    ├── scripts/     # Generation and verification scripts
    └── test/        # SDK tests
```

For coding agents and automated contributors: start with [`AGENTS.md`](./AGENTS.md), then read [`sdk/dx/__init__.py`](./sdk/dx/__init__.py). Treat `sdk/generated/` as generated code rather than the primary integration surface.

## Development

The SDK is generated from the vendored ReplyNodes OpenAPI contract and wrapped by a deliberately small, hand-written DX layer.

```bash
cd sdk
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
bash scripts/generate.sh   # regenerate sdk/generated/ (requires Docker)
python3 -m pytest
```

See [`sdk/README.md`](./sdk/README.md) for generation and verification details.

## API stability

ReplyNodes uses Semantic Versioning for the public SDK:

- **Patch** releases: backward-compatible fixes
- **Minor** releases: backward-compatible capabilities and new API surfaces
- **Major** releases: breaking public SDK changes

Generated implementation details are not the preferred public integration surface. Applications should import from `replynodes.dx`.

## For AI coding agents

When using Codex, Claude Code, Cursor, Hermes, or another coding agent with this repository:

1. Read `AGENTS.md` first.
2. Use `sdk/dx/__init__.py` as the authoritative public SDK surface.
3. Use `openapi/` to inspect the public HTTP contract.
4. Avoid manually editing `sdk/generated/`; regenerate it instead with `sdk/scripts/generate.sh`.
5. Prefer examples using `replynodes.dx`, not internal generated modules.
6. Preserve normalized `data` / `meta` responses and `meta.request_id` behavior.

This keeps generated code, public API behavior, examples, and documentation consistent.

## Search and discovery terms

ReplyNodes is relevant to projects looking for a **Python web scraping SDK**, **Python web context API**, **Google Search API**, **YouTube API**, **Reddit API**, **App Store API**, **AI agent web research API**, **LLM context API**, or a normalized public web API for agents.

These terms describe supported product capabilities; ReplyNodes is not affiliated with the third-party platforms named above.

## Links

- [ReplyNodes](https://replynodes.com)
- [Documentation](https://docs.replynodes.com)
- [`replynodes` on PyPI](https://pypi.org/project/replynodes/)
- [GitHub organization](https://github.com/replynodes)
- [Issues](https://github.com/replynodes/replynodes-python/issues)
