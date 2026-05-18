#!/usr/bin/env bash
# airgap-preflight.sh — verify all required images are locally available
# Exits 0 if all images present, 1 if any are missing.
set -euo pipefail

REQUIRED_IMAGES=(
  "postgres:16-alpine"
  "redis:7-alpine"
  "qdrant/qdrant:v1.9.2"
  "neo4j:5.19-community"
  "ollama/ollama:0.1.44"
)

MISSING=()
for img in "${REQUIRED_IMAGES[@]}"; do
  if docker image inspect "$img" > /dev/null 2>&1; then
    echo "  ✓  $img"
  else
    echo "  ✗  $img  (missing)"
    MISSING+=("$img")
  fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
  echo ""
  echo "❌ Preflight failed — ${#MISSING[@]} image(s) missing."
  echo "   Run 'make airgap-load' to load from .airgap-images/*.tar"
  exit 1
fi

echo ""
echo "✓ Preflight passed — all images available."
