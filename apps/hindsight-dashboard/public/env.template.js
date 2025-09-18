// This file is turned into /env.js at container startup by docker-entrypoint.sh
// Only expose safe, non-secret public config here.
window.__ENV__ = {
  HINDSIGHT_SERVICE_API_URL: "${HINDSIGHT_SERVICE_API_URL:-/api}"
};

