#!/usr/bin/env bash
# Regenerate sdk/generated/replynodes from the vendored canonical OpenAPI
# contract. Mirrors the merged TypeScript reference SDK's `npm run generate`
# (replynodes/replynodes-typescript sdk/package.json).
#
# Pinned to OpenAPI Generator v7.10.0, matching
# replynodes-fetcher/sdk-generation/VERSION and
# replynodes-fetcher/sdk-generation/config/python.json.
set -euo pipefail

sdk_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
repo_root="$(dirname "$sdk_dir")"
image="openapitools/openapi-generator-cli:v7.10.0"
out_dir="$sdk_dir/generated"

python3 "$sdk_dir/scripts/project_public_openapi.py"

mkdir -p "$out_dir"
cp "$sdk_dir/.openapi-generator-ignore" "$out_dir/.openapi-generator-ignore"

docker run --rm -u "$(id -u):$(id -g)" \
  -v "$repo_root:/workspace" \
  -w /workspace \
  "$image" generate \
  -i "/workspace/sdk/.generated/replynodes-fetcher.public.openapi.json" \
  -g python \
  -c "/workspace/sdk/openapi-generator-config.json" \
  -o "/workspace/sdk/generated"

# The pinned .openapi-generator-ignore file's bare `docs/`/`test/` patterns
# only match those directory names at the ignore file's own root; this
# generator version does not apply them to the nested
# `replynodes/docs/`/`replynodes/test/` directories the "python" generator
# actually writes into (verified against the same ignore file and pin in the
# replynodes-fetcher source-of-truth repo). Remove that generated-but-inert
# scaffolding explicitly rather than relying on the ignore file: our own
# docs live in README.md/sdk/README.md and our own tests live in sdk/test/.
rm -rf "$out_dir/replynodes/docs" "$out_dir/replynodes/test"

# Normalize trailing whitespace and extra EOF blank lines the generator leaves
# in some Python and Markdown templates. This keeps generated output stable
# and makes repository whitespace checks deterministic without hand-editing it.
find "$out_dir" -type f \( -name '*.py' -o -name '*.md' \) -exec sed -i 's/[[:blank:]]*$//' {} +
find "$out_dir" -type f \( -name '*.py' -o -name '*.md' \) -exec perl -0pi -e 's/\n+\z/\n/' {} +

echo "[generate] wrote $out_dir/replynodes"
