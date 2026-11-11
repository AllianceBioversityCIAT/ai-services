#!/usr/bin/env bash
# Build the Lambda zip (Python 3.13, arm64) used by Terraform for the smoke test and the worker.
# Run from ai-qa-helper/:  scripts/build.sh   ->   dist/ai-qa-helper-lambda.zip
set -euo pipefail
cd "$(dirname "$0")/.."

BUILD=build/lambda
OUT=dist/ai-qa-helper-lambda.zip
rm -rf "$BUILD" "$OUT"
mkdir -p "$BUILD" dist

# requirements.txt is the locked runtime set (no dev tools), kept in sync with uv.lock.
uv export --frozen --no-dev --no-hashes --no-emit-project --format requirements-txt -o requirements.txt >/dev/null

# Linux arm64 wheels only (manylinux_2_28; the python3.13 runtime is Amazon Linux 2023, glibc 2.34),
# so the zip matches the Lambda runtime regardless of the build machine.
uv pip install --quiet --no-deps --only-binary :all: \
  --python-platform aarch64-manylinux_2_28 --python-version 3.13 \
  --target "$BUILD" -r requirements.txt

cp -R app "$BUILD/app"
cp -R prompts "$BUILD/prompts"
find "$BUILD" -type d -name __pycache__ -prune -exec rm -rf {} +

(cd "$BUILD" && zip -qr -X "../../$OUT" .)
unzipped=$(du -sk "$BUILD" | cut -f1)
echo "built $OUT ($(du -h "$OUT" | cut -f1) zipped, $((unzipped / 1024)) MB unzipped; Lambda limit 250 MB)"
