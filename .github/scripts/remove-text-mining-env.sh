#!/usr/bin/env bash
# Removes the AI Text Mining service DEV .env written by write-text-mining-env.sh. Runs as an `if: always()` step, so it also
# runs when a previous step failed. Never fails the job. The build runs inside `docker build`, so no workspace cache
# holds a copy of the file (the image does, as today).
set -uo pipefail
rm -f "text-mining-service/.env"
echo "Text mining .env removed"
