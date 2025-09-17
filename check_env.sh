#!/bin/bash
# check_env.sh - Environment variable validation script

ENV_FILE=".env"
EXAMPLE_FILE=".env.example"
MISSING_VARS=()
EMPTY_VARS=()

# Detect environment
IS_DEPLOYMENT=false
if [[ -n "$CI" || -n "$GITHUB_ACTIONS" || -n "$DEPLOYMENT_ENV" ]]; then
  IS_DEPLOYMENT=true
fi

# Variables that can be empty in local development but required in staging/production
DEPLOYMENT_REQUIRED_VARS=(
  "CLOUDFLARE_DNS_EMAIL"
  "CLOUDFLARE_DNS_API_TOKEN"
  "OAUTH2_PROXY_CLIENT_ID"
  "OAUTH2_PROXY_CLIENT_SECRET"
  "OAUTH2_PROXY_COOKIE_SECRET"
  "ADMIN_EMAILS"
  "BETA_ACCESS_ADMINS"
)

# Variables that must have specific values in deployment
DEPLOYMENT_SPECIFIC_VARS=(
  "DEV_MODE=false"
)

# Arrays to track validation issues
MISSING_VARS=()
EMPTY_VARS=()
INVALID_VARS=()

if [[ "$IS_DEPLOYMENT" == "true" ]]; then
  echo "🔍 Running in deployment environment (staging/production) - all variables required"
else
  echo "🔍 Running in local development - some production variables can be empty"
fi

# Check if .env.example exists
if [[ ! -f "$EXAMPLE_FILE" ]]; then
  echo "❌ Error: $EXAMPLE_FILE not found!"
  exit 1
fi

# Check if .env exists
if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ Error: $ENV_FILE not found!"
  exit 1
fi

while IFS= read -r line; do
  # Skip comments and empty lines
  [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue

  VAR_NAME=$(echo "$line" | cut -d= -f1)

  # In local development, skip deployment-required variables if they're empty
  if [[ "$IS_DEPLOYMENT" == "false" && " ${DEPLOYMENT_REQUIRED_VARS[@]} " =~ " ${VAR_NAME} " ]]; then
    continue
  fi

  VAR_VALUE=$(grep "^$VAR_NAME=" "$ENV_FILE" | cut -d= -f2-)

  # Check if variable exists in .env
  if ! grep -q "^$VAR_NAME=" "$ENV_FILE"; then
    MISSING_VARS+=("$VAR_NAME")
  # Check if variable is empty
  elif [[ -z "$VAR_VALUE" ]]; then
    EMPTY_VARS+=("$VAR_NAME")
  fi
done < "$EXAMPLE_FILE"

# Validate deployment-specific variables
if [[ "$IS_DEPLOYMENT" == "true" ]]; then
  for spec in "${DEPLOYMENT_SPECIFIC_VARS[@]}"; do
    VAR_NAME=$(echo "$spec" | cut -d= -f1)
    EXPECTED_VALUE=$(echo "$spec" | cut -d= -f2-)
    VAR_VALUE=$(grep "^$VAR_NAME=" "$ENV_FILE" | cut -d= -f2-)
    
    if ! grep -q "^$VAR_NAME=" "$ENV_FILE"; then
      MISSING_VARS+=("$VAR_NAME")
    elif [[ "$VAR_VALUE" != "$EXPECTED_VALUE" ]]; then
      INVALID_VARS+=("$VAR_NAME (expected: $EXPECTED_VALUE, got: $VAR_VALUE)")
    fi
  done
fi

# Additional guardrails for DEV_MODE irrespective of deployment detection
DEV_MODE_VALUE=$(grep '^DEV_MODE=' "$ENV_FILE" | cut -d= -f2-)
if [[ -n "$DEV_MODE_VALUE" && "${DEV_MODE_VALUE,,}" == "true" ]]; then
  APP_BASE_URL_VALUE=$(grep '^APP_BASE_URL=' "$ENV_FILE" | cut -d= -f2-)
  ALLOW_DEV_MODE_VALUE=$(grep '^ALLOW_DEV_MODE=' "$ENV_FILE" | cut -d= -f2-)
  if [[ -n "$APP_BASE_URL_VALUE" ]]; then
    if [[ "$APP_BASE_URL_VALUE" != *localhost* && "$APP_BASE_URL_VALUE" != *127.0.0.1* && "$APP_BASE_URL_VALUE" != *::1* ]]; then
      INVALID_VARS+=("DEV_MODE (requires APP_BASE_URL pointing at localhost when true)")
    fi
  elif [[ "${ALLOW_DEV_MODE_VALUE,,}" != "true" ]]; then
    INVALID_VARS+=("DEV_MODE (requires APP_BASE_URL or ALLOW_DEV_MODE=true when enabling dev impersonation)")
  fi
fi

# Report results
if [ ${#MISSING_VARS[@]} -ne 0 ]; then
  echo "❌ Missing environment variables:"
  for var in "${MISSING_VARS[@]}"; do
    echo "  - $var"
  done
fi

if [ ${#EMPTY_VARS[@]} -ne 0 ]; then
  echo "⚠️  Empty environment variables:"
  for var in "${EMPTY_VARS[@]}"; do
    echo "  - $var"
  done
fi

if [ ${#INVALID_VARS[@]} -ne 0 ]; then
  echo "❌ Invalid environment variables:"
  for var in "${INVALID_VARS[@]}"; do
    echo "  - $var"
  done
fi

if [ ${#MISSING_VARS[@]} -eq 0 ] && [ ${#EMPTY_VARS[@]} -eq 0 ] && [ ${#INVALID_VARS[@]} -eq 0 ]; then
  echo "✅ All required environment variables are set and non-empty!"
  exit 0
else
  echo "❌ Environment validation failed!"
  exit 1
fi
