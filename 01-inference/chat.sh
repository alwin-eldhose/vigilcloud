#!/usr/bin/env bash
# One chat request with curl, so you can see the raw HTTP call and the raw JSON reply.
# Run from the repo folder: bash 01-inference/chat.sh
set -euo pipefail

# Read one value from .env. tr drops the \r that Windows editors add.
get() { grep "^$1=" .env | tail -n 1 | cut -d= -f2- | tr -d '\r'; }

BASE_URL=$(get AKAMAI_BASE_URL)
API_KEY=$(get AKAMAI_API_KEY)
MODEL=$(get CHAT_MODEL)

curl -sS "$BASE_URL/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "model": "$MODEL",
  "messages": [{"role": "user", "content": "Which ocean is closest to Seattle? Answer in one short sentence."}],
  "max_tokens": 100
}
EOF
echo
