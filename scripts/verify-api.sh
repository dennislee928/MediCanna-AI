#!/usr/bin/env bash
# 驗證生產環境 API：先啟動 docker-compose，再執行此腳本
set -euo pipefail
GATEWAY="${GATEWAY_URL:-http://localhost:8080}"
echo "Testing Gateway: $GATEWAY"
curl -sS -X POST "$GATEWAY/api/v1/recommend" \
  -H "x-request-id: smoke-test-001" \
  -H "Content-Type: application/json" \
  -d '{"symptoms":"pain relief relaxed","avoid_effects":[]}' | head -c 500
echo ""
echo "Done."
