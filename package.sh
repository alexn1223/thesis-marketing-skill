#!/bin/sh
# Builds dist/thesis-marketing.zip for upload at claude.ai → Settings → Capabilities → Skills.
set -eu
ROOT="$(cd "$(dirname "$0")" && pwd)"
SKILL="$ROOT/plugins/thesis-marketing/skills/thesis-marketing"
STAGE="$(mktemp -d)"
cp -R "$SKILL" "$STAGE/thesis-marketing"
rm -rf "$STAGE/thesis-marketing/agents"
find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} +
mkdir -p "$ROOT/dist"
rm -f "$ROOT/dist/thesis-marketing.zip"
( cd "$STAGE" && zip -r -X "$ROOT/dist/thesis-marketing.zip" thesis-marketing ) >/dev/null
rm -rf "$STAGE"
echo "dist/thesis-marketing.zip"
