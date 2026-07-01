#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

pass() { printf "[PASS] %s\n" "$*"; }
fail() { printf "[FAIL] %s\n" "$*"; exit 1; }
check_code() {
  local got="$1" expected="$2" label="$3"
  [[ "$got" == "$expected" ]] && pass "$label ($got)" || fail "$label expected $expected got $got"
}

req() {
  local method="$1" url="$2" data="${3:-}"
  local tmp
  tmp=$(mktemp)
  local code
  if [[ -n "$data" ]]; then
    code=$(curl -s -o "$tmp" -w "%{http_code}" -X "$method" "$url" -H 'Content-Type: application/json' -d "$data")
  else
    code=$(curl -s -o "$tmp" -w "%{http_code}" -X "$method" "$url")
  fi
  printf '%s\n' "$code"
  cat "$tmp"
  rm -f "$tmp"
}

echo "Base URL: $BASE_URL"

a=$(req GET "$BASE_URL/docs")
code=$(echo "$a" | head -n1)
check_code "$code" "200" "GET /docs"

b=$(req GET "$BASE_URL/openapi.json")
code=$(echo "$b" | head -n1)
check_code "$code" "200" "GET /openapi.json"

c=$(req GET "$BASE_URL/api/stories")
code=$(echo "$c" | head -n1)
check_code "$code" "200" "GET /api/stories"

d=$(req GET "$BASE_URL/api/corpus/sources")
code=$(echo "$d" | head -n1)
check_code "$code" "200" "GET /api/corpus/sources"

e=$(req GET "$BASE_URL/api/corpus/topics?source=aozora&level=N4")
code=$(echo "$e" | head -n1)
check_code "$code" "200" "GET /api/corpus/topics aozora N4"

f=$(req POST "$BASE_URL/api/puzzle/generate" '{}')
code=$(echo "$f" | head -n1)
check_code "$code" "422" "POST /api/puzzle/generate empty body"

g=$(req POST "$BASE_URL/api/corpus/puzzle/generate" '{"source":"aozora","topic_id":"does-not-exist","level":"N4"}')
code=$(echo "$g" | head -n1)
check_code "$code" "404" "POST /api/corpus/puzzle/generate bad topic"

ao=$(req POST "$BASE_URL/api/puzzle/generate" '{"file_path":"modern.txt","level":"N5"}')
code=$(echo "$ao" | head -n1)
check_code "$code" "200" "POST /api/puzzle/generate story"

ao2=$(req POST "$BASE_URL/api/corpus/puzzle/generate" '{"source":"aozora","topic_id":"modern","level":"N5"}')
code=$(echo "$ao2" | head -n1)
check_code "$code" "200" "POST /api/corpus/puzzle/generate corpus"

echo "All checks passed."
