#!/bin/bash

echo "--- Checking Pod Logs for Errors ---"

# Define common error patterns
ERROR_PATTERNS="error|fail|denied|refused|unauthorized|forbidden|crash|exception|panic|timeout|unreachable|no such host|connection refused|bad gateway|service unavailable|500 Internal Server Error|400 Bad Request|401 Unauthorized|403 Forbidden|404 Not Found|502 Bad Gateway|503 Service Unavailable|504 Gateway Timeout"

# Get all pod names in the default namespace
PODS=$(kubectl get pods -n default -o jsonpath='{.items[*].metadata.name}')

if [ -z "$PODS" ]; then
    echo "No pods found in the default namespace."
else
    for POD_NAME in $PODS; do
        echo -e "\n--- Logs for Pod: $POD_NAME ---"
        # Get container names within the pod
        CONTAINERS=$(kubectl get pod "$POD_NAME" -n default -o jsonpath='{.spec.containers[*].name}')
        
        if [ -z "$CONTAINERS" ]; then
            echo "  No containers found in pod $POD_NAME."
        else
            for CONTAINER_NAME in $CONTAINERS; do
                echo -e "\n  Checking container: $CONTAINER_NAME"
                # Fetch logs for the last 1 hour (3600 seconds) and filter for errors
                # Using --since=1h might not be supported on all kubectl versions,
                # so falling back to a simpler tail if it fails.
                if kubectl logs "$POD_NAME" -c "$CONTAINER_NAME" -n default --since=1h 2>/dev/null | grep -iE "$ERROR_PATTERNS"; then
                    echo "  Errors found in logs for $POD_NAME/$CONTAINER_NAME."
                elif kubectl logs "$POD_NAME" -c "$CONTAINER_NAME" -n default 2>/dev/null | tail -n 200 | grep -iE "$ERROR_PATTERNS"; then
                    echo "  Errors found in recent logs (last 200 lines) for $POD_NAME/$CONTAINER_NAME."
                else
                    echo "  No common error patterns found in recent logs for $POD_NAME/$CONTAINER_NAME."
                fi
            done
        fi
    done
fi

echo -e "\n--- End of Pod Log Error Check ---"
