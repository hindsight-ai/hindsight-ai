#!/usr/bin/env sh
set -eu

HTML_DIR="/usr/share/nginx/html"

# Generate env.js from template. If variable not set, default to /api.
API_URL=${HINDSIGHT_SERVICE_API_URL:-/api}

if [ -f "$HTML_DIR/env.template.js" ]; then
  sed "s|\${HINDSIGHT_SERVICE_API_URL:-/api}|${API_URL}|g" "$HTML_DIR/env.template.js" > "$HTML_DIR/env.js"
else
  echo "window.__ENV__ = { HINDSIGHT_SERVICE_API_URL: '${API_URL}' };" > "$HTML_DIR/env.js"
fi

exec nginx -g 'daemon off;'

