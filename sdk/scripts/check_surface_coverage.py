#!/usr/bin/env python3
"""Verify the stable wrapper exposes every canonical GET operation.

This is a build-time verification check, not a test: it reads the vendored
contract and the installed public wrapper and never makes an HTTP request.
Mirrors replynodes/replynodes-typescript sdk/scripts/check-surface-coverage.js.

Usage: run from the sdk/ directory after `pip install -e .`:

    python3 scripts/check_surface_coverage.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SDK_DIR = Path(__file__).resolve().parent.parent
SPEC_PATH = SDK_DIR.parent / "openapi" / "replynodes-fetcher.openapi.json"


def fail(message: str) -> None:
    sys.stderr.write(f"Surface coverage check failed: {message}\n")


def main() -> int:
    try:
        from replynodes.dx import PUBLIC_OPERATION_REGISTRY, ReplyNodes, operation_id_to_method_name
    except ImportError as exc:
        fail(f"unable to import replynodes.dx; run `pip install -e sdk` first: {exc}")
        return 1

    try:
        spec = json.loads(SPEC_PATH.read_text())
    except OSError as exc:
        fail(f"unable to read canonical OpenAPI at {SPEC_PATH}: {exc}")
        return 1

    canonical_operation_ids = sorted(
        operation["operationId"]
        for path_item in spec.get("paths", {}).values()
        for method, operation in path_item.items()
        if method.lower() == "get" and operation.get("operationId")
    )
    canonical_duplicates = sorted(
        operation_id
        for operation_id in set(canonical_operation_ids)
        if canonical_operation_ids.count(operation_id) > 1
    )
    if canonical_duplicates:
        fail("canonical GET operation IDs are not unique: " + ", ".join(canonical_duplicates))
        return 1

    entries = [
        (resource, method, operation_id)
        for resource, methods in PUBLIC_OPERATION_REGISTRY.items()
        for method, operation_id in methods.items()
    ]
    registry_operation_ids = sorted({operation_id for _, _, operation_id in entries})

    missing = sorted(set(canonical_operation_ids) - set(registry_operation_ids))
    unexpected = sorted(set(registry_operation_ids) - set(canonical_operation_ids))
    if missing or unexpected:
        lines = ["Canonical operation IDs and public registry drift detected."]
        if missing:
            lines.append(f"Missing: {', '.join(missing)}")
        if unexpected:
            lines.append(f"Unexpected: {', '.join(unexpected)}")
        fail("\n".join(lines))
        return 1

    all_ids = [operation_id for _, _, operation_id in entries]
    duplicates = sorted({op for op in all_ids if all_ids.count(op) > 1})
    if duplicates != ["googleSearch"] or all_ids.count("googleSearch") != 2:
        fail(f"registry contains unexpected duplicate operation IDs: {duplicates}")
        return 1

    try:
        client = ReplyNodes(api_key="placeholder", base_url="https://test.invalid")
    except Exception as exc:  # noqa: BLE001 - report any construction failure
        fail(f"could not instantiate the wrapper: {exc}")
        return 1

    missing_methods = [
        f"{resource}.{method} ({operation_id})"
        for resource, method, operation_id in entries
        if not callable(getattr(getattr(client, resource, None), method, None))
    ]
    if missing_methods:
        fail("registry methods are not callable:\n" + "\n".join(missing_methods))
        return 1

    if client.web.search is not client.google.search:
        fail("web.search and google.search are not the same compatibility alias")
        return 1

    for resource, methods in PUBLIC_OPERATION_REGISTRY.items():
        for method, operation_id in methods.items():
            expected = operation_id_to_method_name(operation_id)
            api_namespace = getattr(client, resource)
            actual_name = getattr(api_namespace, method).__name__
            if actual_name != expected:
                fail(f"{resource}.{method} bound to unexpected generated method {actual_name!r}, expected {expected!r}")
                return 1

    print(
        f"Surface coverage OK: {len(canonical_operation_ids)}/{len(canonical_operation_ids)} "
        f"canonical GET operations; {len(entries)} registry entries."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
