#!/bin/sh
set -eu

CONFIG_PATH="/usr/share/nginx/html/assets/app-config.json"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8080/api/v1/recommend}"

mkdir -p "$(dirname "$CONFIG_PATH")"
cat > "$CONFIG_PATH" <<EOF
{
  "gatewayUrl": "$GATEWAY_URL"
}
EOF

echo "[entrypoint] wrote runtime gateway config to $CONFIG_PATH"
