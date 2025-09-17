#!/usr/bin/env sh
set -eu

HTML_DIR="/usr/share/nginx/html"

bool_from_env() {
  local raw_value="${1:-}"
  local normalized="$(printf '%s' "$raw_value" | tr '[:upper:]' '[:lower:]')"
  case "$normalized" in
    ""|"0"|"false"|"no"|"off")
      printf 'false'
      ;;
    *)
      printf 'true'
      ;;
  esac
}

API_URL=${HINDSIGHT_SERVICE_API_URL:-/api}
LLM_ENABLED=$(bool_from_env "$LLM_FEATURES_ENABLED")
FEATURE_CONSOLIDATION=$(bool_from_env "$FEATURE_CONSOLIDATION_ENABLED")
FEATURE_PRUNING=$(bool_from_env "$FEATURE_PRUNING_ENABLED")
FEATURE_ARCHIVED=$(bool_from_env "$FEATURE_ARCHIVED_ENABLED")

cat > "$HTML_DIR/env.js" <<EOF
// Generated at container start; do not edit manually.
window.__ENV__ = {
  HINDSIGHT_SERVICE_API_URL: '${API_URL}',
  LLM_FEATURES_ENABLED: ${LLM_ENABLED},
  FEATURE_CONSOLIDATION_ENABLED: ${FEATURE_CONSOLIDATION},
  FEATURE_PRUNING_ENABLED: ${FEATURE_PRUNING},
  FEATURE_ARCHIVED_ENABLED: ${FEATURE_ARCHIVED}
};
EOF

exec nginx -g 'daemon off;'
