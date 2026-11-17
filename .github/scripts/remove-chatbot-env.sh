#!/usr/bin/env bash
# Removes the AI Chatbot service PROD .env written by write-chatbot-env.sh. Runs as an `if: always()` step, so it also
# runs when a previous step failed. Never fails the job. The build runs inside `docker build`, so no workspace cache
# holds a copy of the file (the image does, as today).
set -uo pipefail
rm -f "chatbot-service/.env"
echo "Chatbot .env removed"
