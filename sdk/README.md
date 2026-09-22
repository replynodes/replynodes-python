# replynodes 0.1.0

One small Python package for the authenticated, public ReplyNodes read API. The generated `python` (urllib3 + Pydantic) client is kept under `generated/`; `dx/` is the stable developer-facing wrapper and deterministic operation registry. Both are merged into a single installable `replynodes` distribution at build time via `pyproject.toml`'s `package-dir` mapping — `generated/replynodes` becomes the `replynodes` package, `dx/` becomes the `replynodes.dx` subpackage. Neither directory is ever copied; they are packaged in place.

## Install and quickstart

```sh
pip install replynodes
```

```python
import os
from replynodes.dx import ReplyNodes

client = ReplyNodes(
    api_key=os.environ["REPLYNODES_API_KEY"],
    timeout=10,  # seconds
)

result = client.youtube.search(term="open source databases", limit=5)
print(result.data)
print(result.meta.request_id)
```

The API key is the raw `rn_test_...` or `rn_live_...` value. The SDK adds `Authorization: Bearer ...`; do not include the `Bearer ` prefix yourself. `base_url` can override the production URL for tests or compatible gateways (restricted to the official origin, `localhost`/`127.0.0.1`, or `https://test.invalid`). An optional trailing `/v1` is normalized because generated endpoint paths already include that prefix.

The repository-level `examples/quickstart.py`, `examples/web_search.py`, and `examples/brand_info.py` are runnable documentation; they are not part of the published package.

The wrapper exposes all 77 canonical operations through resource-oriented namespaces: `app_store`, `brand`, `fomo`, `google`, `google_maps`, `google_play`, `google_shopping`, `hacker_news`, `instagram`, `reddit`, `tiktok`, `web`, and `youtube`. Each namespace uses intentional `snake_case` action names matching `PUBLIC_OPERATION_REGISTRY`; `web.search` and `google.search` are the same bound method object (a backward-compatible alias for the canonical `googleSearch` operation). Responses contain normalized `data` and `meta`; use `meta.request_id` for support and `meta.next_cursor` when returned by an operation. The SDK does not automatically paginate or retry requests.

Errors are `ReplyNodesError` with `status`, `code`, `request_id`, and parsed `details`. `401` means authentication failed; `402` means payment or account credits are required; other HTTP errors retain their status and request ID. A client-side deadline raises `ReplyNodesTimeoutError`. Set `timeout` in seconds; omit it to have no client-side deadline.

Request IDs are backend-owned. The current OpenAPI schema marks success `meta.request_id` as `required`, so the generated Pydantic model enforces it: a 200 response that omits `request_id` raises `pydantic.ValidationError` rather than returning `request_id=None`. This is a known, documented gap between the schema and backend behavior — the same one flagged in the merged TypeScript reference SDK's `sdk/README.md` — not something this wrapper can silently paper over without diverging from the canonical contract. For errors, `request_id` uses the parsed `error.request_id`, then falls back to the `X-Request-Id` response header.

## Package layout

```text
sdk/
├── pyproject.toml               # packaging: merges generated/ + dx/ into one `replynodes` distribution
├── openapi-generator-config.json  # vendored copy of replynodes-fetcher/sdk-generation/config/python.json
├── .openapi-generator-ignore    # vendored copy of the pinned python ignore file
├── scripts/
│   ├── project_public_openapi.py  # scrubs vendored contract -> .generated/ (gitignored input to the generator)
│   ├── generate.sh                # runs OpenAPI Generator via Docker into generated/
│   └── check_surface_coverage.py  # verifies PUBLIC_OPERATION_REGISTRY against the canonical contract
├── generated/replynodes/        # generated client -- do not hand-edit
├── dx/__init__.py                # hand-written wrapper -- the public API
└── test/                         # pytest suite
```

## Versioning and boundaries

The SDK follows SemVer: patch releases contain backwards-compatible fixes, minor releases add backwards-compatible APIs, and major releases may change or remove public behavior. `replynodes` is the typed REST client for direct API calls.

To transfer or manage this package under the official ReplyNodes PyPI organization/account, a PyPI project owner should configure [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) from the official GitHub repository/workflow rather than relying on a long-lived personal API token (tracked by issue #460, which gates publication, not implementation).

From a clean environment, verify the published package with `pip download replynodes`, install it in a fresh virtual environment, and run `python -c "import replynodes; from replynodes.dx import ReplyNodes; print(ReplyNodes)"`.

## Local generation and verification

The canonical, vendored input is `../openapi/replynodes-fetcher.openapi.json`. Its SHA-256 is `46e5807e5164904e31dbdc7a14a61f87ffbe0a4617c076066c8685de8d5e6edf` — byte-identical to `replynodes-fetcher`'s `api-docs/replynodes-fetcher.openapi.json` at the time this SDK was generated.

Generation is pinned to OpenAPI Generator `v7.10.0` (see `../openapi-generator-config.json`'s implicit pin and `scripts/generate.sh`):

```sh
bash scripts/generate.sh
pip install -e ".[dev]"
python3 -m pytest
python3 scripts/check_surface_coverage.py
```

`scripts/project_public_openapi.py` mirrors the scrub step in the merged TypeScript reference SDK (`replynodes/replynodes-typescript sdk/scripts/project-public-openapi.js`) so generated docstrings stay consistent across languages; it never touches the vendored contract itself, only a derived, gitignored `.generated/` copy fed to the generator.

`scripts/generate.sh` uses the official Docker image and `openapi-generator-config.json`; it writes only to `generated/replynodes/`. The pinned `.openapi-generator-ignore`'s bare `docs/`/`test/` patterns do not reach the nested `replynodes/docs/`/`replynodes/test/` directories this generator version actually writes (verified reproducible against the same pin in the `replynodes-fetcher` source-of-truth repo); `generate.sh` removes that generated-but-unused scaffolding explicitly instead. `replynodes_README.md` is kept as generated (with only deterministic whitespace normalization), matching the precedent set by the merged TypeScript reference SDK, which also keeps its default generated `README.md` rather than overriding it.

`python3 scripts/check_surface_coverage.py` verifies every `PUBLIC_OPERATION_REGISTRY` entry against all canonical GET operation IDs, that every registry method is callable on an instantiated client, and that `web.search`/`google.search` remain the same bound alias — without making network requests. `python3 -m pytest` includes this as `test/test_surface_coverage.py`, plus a wheel-build-and-clean-install smoke test (`test/test_package_smoke.py`, marked `slow`).

## Generated-code customization

The `python` OpenAPI Generator target is used with `generateSourceCodeOnly: true` and `library: urllib3` (see `../openapi-generator-config.json`, vendored from `replynodes-fetcher/sdk-generation/config/python.json`). No template overrides are applied — same precedent as the merged TypeScript reference SDK, which also runs the generator without custom templates. The only non-generator-default choice made downstream is `Configuration(retries=False)` in `dx/__init__.py`, set explicitly because `urllib3.PoolManager` retries 3 times by default when `Configuration.retries` is left at its generated default of `None` (see the comment in `generated/replynodes/configuration.py`) — an explicit override to guarantee this SDK never issues a hidden retry against a metered/billed GET.
