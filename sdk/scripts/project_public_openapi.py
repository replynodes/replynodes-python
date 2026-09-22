#!/usr/bin/env python3
"""Build the public generator input from the vendored canonical contract.

The vendored OpenAPI document (../../openapi/replynodes-fetcher.openapi.json)
is a byte-identical copy of the canonical replynodes-fetcher SDK contract and
must not be edited for SDK presentation concerns. This projection is
deterministic, local-only, and contains no credentials or network access. It
mirrors the scrub step in the merged TypeScript reference SDK
(replynodes/replynodes-typescript sdk/scripts/project-public-openapi.js) so
generated docs/model descriptions stay consistent across languages.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SDK_DIR = Path(__file__).resolve().parent.parent
SOURCE_PATH = SDK_DIR.parent / "openapi" / "replynodes-fetcher.openapi.json"
OUTPUT_DIR = SDK_DIR / ".generated"
OUTPUT_PATH = OUTPUT_DIR / "replynodes-fetcher.public.openapi.json"

_SCRUBS = [
    (
        re.compile(
            r" Returns the normalized public contract; raw provider records are internal to the runtime boundary and never cross the public gateway\.?",
            re.IGNORECASE,
        ),
        " Returns the normalized public contract.",
    ),
    (re.compile(r"Provider collection constant\.?", re.IGNORECASE), "Collection constant."),
    (re.compile(r"Provider category constant\.?", re.IGNORECASE), "Category constant."),
    (re.compile(r"Provider review sort constant\.?", re.IGNORECASE), "Review sort constant."),
    (
        re.compile(
            r" Backed by a privately deployed webclaw-server instance; upstream implementation details are never exposed\.?",
            re.IGNORECASE,
        ),
        "",
    ),
    (
        re.compile(
            r"max_pages/max_depth are clamped server-side regardless of the requested value\.?",
            re.IGNORECASE,
        ),
        "The service clamps max_pages/max_depth regardless of the requested value.",
    ),
]


def scrub(value):
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, dict):
        for key, child in list(value.items()):
            if key == "description" and isinstance(child, str):
                for pattern, replacement in _SCRUBS:
                    child = pattern.sub(replacement, child)
                value[key] = child
            else:
                value[key] = scrub(child)
        return value
    return value


def main() -> None:
    document = json.loads(SOURCE_PATH.read_text())
    scrub(document)

    schemas = document["components"]["schemas"]
    for schema_name in ("CreditTopupRequired",):
        prop = schemas[schema_name]["properties"]["topup_url"]
        prop.pop("enum", None)
        prop["description"] = "URL for completing the required account action."

    prepaid_topup = schemas["PaymentRequiredPrepaidExtensions"]["properties"]["topup"]["properties"]["topup_url"]
    prepaid_topup.pop("enum", None)
    prepaid_topup["description"] = "URL for completing the required account action."

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(document, indent=2) + "\n")
    print(OUTPUT_PATH.relative_to(Path.cwd()) if OUTPUT_PATH.is_relative_to(Path.cwd()) else OUTPUT_PATH)


if __name__ == "__main__":
    main()
