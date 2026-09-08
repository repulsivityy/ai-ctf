#!/usr/bin/env bash
#
# Rebuild + redeploy the INFERNO CTF stack.
#
# Why this script exists: nginx resolves the app container's IP once, at startup.
# If you recreate ONLY the app service (e.g. `docker compose up -d --build
# aegis-ctf`), it comes back with a new IP and nginx keeps proxying to the dead
# one — the whole site 502s until nginx is also restarted. This script always
# cycles BOTH services together, then smoke-tests the result.
#
# Usage:
#   ./deploy.sh              rebuild changed layers, recreate both services
#   ./deploy.sh --no-cache   full clean rebuild (after a requirements.txt change)
#   ./deploy.sh --pull       also pull newer base images
#
set -euo pipefail
cd "$(dirname "$0")"

BUILD_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --no-cache) BUILD_ARGS+=(--no-cache) ;;
    --pull)     BUILD_ARGS+=(--pull) ;;
    -h|--help)  sed -n '3,14p' "$0" | sed 's/^#\s\?//'; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

# docker often needs sudo on this host; fall back only if the daemon IS up but
# we lack permission — if it's genuinely down, say so.
DC=(docker compose)
if ! docker info >/dev/null 2>&1; then
  if sudo -n docker info >/dev/null 2>&1; then
    DC=(sudo -n docker compose)
  else
    echo "!! can't reach the docker daemon (down, or sudo needs a password)" >&2
    exit 1
  fi
fi

if [ ! -f .env ]; then
  echo "!! no .env file — copy .env.example and set GEMINI_API_KEY" >&2
  exit 1
fi

echo ">> building image ${BUILD_ARGS[*]:-}"
"${DC[@]}" build "${BUILD_ARGS[@]}"

echo ">> recreating BOTH services (so nginx re-resolves the app IP)"
"${DC[@]}" down --remove-orphans
"${DC[@]}" up -d

echo ">> waiting for the app to report healthy"
healthy=""
for _ in $(seq 1 30); do
  if "${DC[@]}" ps 2>/dev/null | grep -q 'aegis-ctf-app.*healthy'; then
    healthy=1
    break
  fi
  sleep 2
done
if [ -z "$healthy" ]; then
  echo "!! app did not become healthy" >&2
  "${DC[@]}" ps
  "${DC[@]}" logs --tail 40 aegis-ctf
  exit 1
fi

echo ">> smoke test (through nginx)"
code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost/healthz || echo 000)
if [ "$code" != "200" ]; then
  echo "!! http://localhost/healthz returned $code" >&2
  "${DC[@]}" ps
  "${DC[@]}" logs --tail 40
  exit 1
fi

echo ">> deployed OK"
"${DC[@]}" ps
