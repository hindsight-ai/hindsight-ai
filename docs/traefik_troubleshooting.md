# Traefik and Ingress Troubleshooting Guide for Hindsight AI

This document summarizes common issues encountered during the deployment of Hindsight AI with Traefik Ingress and OAuth2 Proxy, along with their resolutions. This serves as a quick reference for future troubleshooting and onboarding.

## 1. TLS Secret Double-Encoding in GitHub Actions

**Problem:** When creating Kubernetes TLS secrets from GitHub Secrets in the CI/CD pipeline, the certificate (`TLS_CRT`) and key (`TLS_KEY`) were being double-encoded with `base64 -w 0`. This resulted in invalid PEM data in the Kubernetes secret, causing Traefik to fail to use the TLS certificate.

**Error Symptom:** `Warning: tls: failed to find any PEM data in certificate input` in deployment logs.

**Resolution:** Removed the `base64 -w 0` encoding from the `kubectl create secret generic hindsight-tls-secret` command in `.github/workflows/deploy.yml`. GitHub Secrets already provide base64-encoded values, so direct use is sufficient.

**Relevant Change (in `.github/workflows/deploy.yml`):**
```diff
--- a/.github/workflows/deploy.yml
+++ b/.github/workflows/deploy.yml
@@ -124,8 +124,8 @@ jobs:
             # Create TLS secret from GitHub Secrets
             echo "Creating TLS secret from GitHub Secrets..."
             sudo kubectl create secret generic hindsight-tls-secret \
-              --from-literal=tls.crt=$(echo -n "${{ secrets.TLS_CRT }}" | base64 -w 0) \
-              --from-literal=tls.key=$(echo -n "${{ secrets.TLS_KEY }}" | base64 -w 0) \
+              --from-literal=tls.crt="${{ secrets.TLS_CRT }}" \
+              --from-literal=tls.key="${{ secrets.TLS_KEY }}" \
               --type=kubernetes.io/tls \
               --dry-run=client -o yaml | sudo kubectl apply -f -
             echo "TLS secret created."
```

## 2. OAuth2 Proxy Client Secrets Double-Encoding

**Problem:** Similar to TLS secrets, the `OAUTH2_PROXY_CLIENT_ID` and `OAUTH2_PROXY_CLIENT_SECRET` were also being double-encoded when passed to the `oauth2-proxy-secret`.

**Resolution:** Removed the `base64 -w 0` encoding from the `printf` command used to construct the `oauth2-proxy-secret` in `.github/workflows/deploy.yml`.

**Relevant Change (in `.github/workflows/deploy.yml`):**
```diff
--- a/.github/workflows/deploy.yml
+++ b/.github/workflows/deploy.yml
@@ -134,8 +134,8 @@ jobs:
             echo "Creating oauth2-proxy secret from GitHub Secrets..."
             # Use printf and --from-env-file=/dev/stdin for robustness
             printf "OAUTH2_PROXY_CLIENT_ID=%s\nOAUTH2_PROXY_CLIENT_SECRET=%s\nOAUTH2_PROXY_COOKIE_SECRET=%s" \
-              "$(echo -n "${{ secrets.OAUTH2_PROXY_CLIENT_ID }}" | base64 -w 0)" \
-              "$(echo -n "${{ secrets.OAUTH2_PROXY_CLIENT_SECRET }}" | base64 -w 0)" \
+              "${{ secrets.OAUTH2_PROXY_CLIENT_ID }}" \
+              "${{ secrets.OAUTH2_PROXY_CLIENT_SECRET }}" \
               "${{ secrets.OAUTH2_PROXY_COOKIE_SECRET }}" \
               | sudo kubectl create secret generic oauth2-proxy-secret --from-env-file=/dev/stdin --dry-run=client -o yaml | sudo kubectl apply -f -
             echo "oauth2-proxy secret created."
```

## 3. OAuth2 Proxy Redirect URL and Cookie Domain Configuration

**Problem:** Initial `oauth2-proxy` configuration had a single `redirect-url` and no explicit `cookie-domain`, which could lead to authentication issues or 404s when accessing the application via different domains (e.g., `hindsight-ai.com` vs. `www.hindsight-ai.com`).

**Resolution:** Added multiple `redirect-url` arguments to cover all expected domains and explicitly set the `--cookie-domain` to the base domain (`hindsight-ai.com`) in `k8s/oauth2-proxy-deployment.yaml`.

**Relevant Change (in `k8s/oauth2-proxy-deployment.yaml`):**
```diff
--- a/k8s/oauth2-proxy-deployment.yaml
+++ b/k8s/oauth2-proxy-deployment.yaml
@@ -22,7 +22,9 @@ spec:
           - --email-domain=* # Allow any email domain initially, will restrict later
           - --upstream=static:200 # Dummy upstream, Traefik will handle actual routing
           - --http-address=0.0.0.0:4180
-          - --redirect-url=https://hindsight-ai.com/oauth2/callback # IMPORTANT: Update with your actual domain
+          - --redirect-url=https://hindsight-ai.com/oauth2/callback
+          - --redirect-url=https://www.hindsight-ai.com/oauth2/callback
+          - --cookie-domain=hindsight-ai.com # Set cookie for the base domain
           - --cookie-secure=true
           - --cookie-expire=168h # 7 days
           - --cookie-refresh=1h # Refresh cookie every hour
```

## 4. Traefik Middleware Reference Syntax

**Problem:** Traefik logs showed "middleware \"oauth2-proxy-auth@default@kubernetescrd\" does not exist" or "invalid reference to middleware oauth2-proxy-auth@kubernetescrd: with crossnamespace disallowed, the namespace field needs to be explicitly specified". This was due to incorrect syntax for referencing middlewares in `IngressRoute` definitions. The `@kubernetescrd` suffix should not be explicitly included in the `name` field, and the namespace should be specified in a separate `namespace` field.

**Resolution:** Modified `k8s/hindsight-dashboard-ingress.yaml` and `k8s/hindsight-service-ingress.yaml` to use the correct middleware reference syntax: `name: oauth2-proxy-auth` with `namespace: default` as a separate field.

**Relevant Change (example from `k8s/hindsight-dashboard-ingress.yaml`):**
```diff
--- a/k8s/hindsight-dashboard-ingress.yaml
+++ b/k8s/hindsight-dashboard-ingress.yaml
@@ -13,7 +13,8 @@ spec:
         - name: hindsight-dashboard-service
           port: 80
       middlewares:
-        - name: oauth2-proxy-auth@default@kubernetescrd # Apply oauth2-proxy authentication
+        - name: oauth2-proxy-auth
+          namespace: default # Apply oauth2-proxy authentication
         - name: redirect-to-https
   tls:
     secretName: hindsight-tls-secret # Name of the secret containing your TLS certificate and key
```

## 5. Traefik Middleware Definition Namespace

**Problem:** Even after correcting the middleware reference syntax in IngressRoutes, Traefik still reported the middleware as non-existent. This was because the `oauth2-proxy-auth` middleware itself did not explicitly define its namespace in its `metadata`, leading to Traefik's strict cross-namespace rules preventing its discovery.

**Resolution:** Explicitly added `namespace: default` to the `metadata` section of `k8s/oauth2-proxy-middleware.yaml`.

**Relevant Change (in `k8s/oauth2-proxy-middleware.yaml`):**
```diff
--- a/k8s/oauth2-proxy-middleware.yaml
+++ b/k8s/oauth2-proxy-middleware.yaml
@@ -2,7 +2,6 @@ apiVersion: traefik.io/v1alpha1 (actually this is not ok, the correct apiVersion is traefik.containo.us/v1alpha1)
 kind: Middleware
 metadata:
   name: oauth2-proxy-auth
-  namespace: default # Explicitly define namespace for strict Traefik referencing
 spec:
   forwardAuth:
     address: http://oauth2-proxy-service:4180/oauth2/auth
```

## 6. Traefik Host Rule Syntax for Multiple Domains

**Problem:** Traefik logs showed "error while adding rule Host(`hindsight-ai.com`, `www.hindsight-ai.com`): unexpected number of parameters; got 2, expected one of [1]". This indicates that Traefik's `Host()` rule does not accept multiple hostnames as comma-separated values within a single function call.

**Resolution:** Split the `Host()` rule for multiple domains into separate `match` rules within the `IngressRoute`.

**Relevant Change (example from `k8s/hindsight-dashboard-ingress.yaml`):**
```diff
--- a/k8s/hindsight-dashboard-ingress.yaml
+++ b/k8s/hindsight-dashboard-ingress.yaml
@@ -37,7 +37,16 @@ spec:
     - web # HTTP entry point for redirection
     - websecure # HTTPS entry point
   routes:
-    - match: Host(`hindsight-ai.com`, `www.hindsight-ai.com`) && PathPrefix(`/`)
+    - match: Host(`hindsight-ai.com`) && PathPrefix(`/`)
+      kind: Rule
+      services:
+        - name: hindsight-dashboard-service
+          port: 80
+      middlewares:
+        - name: oauth2-proxy-auth
+          namespace: default # Apply oauth2-proxy authentication
+        - name: redirect-to-https
+    - match: Host(`www.hindsight-ai.com`) && PathPrefix(`/`)
       kind: Rule
       services:
         - name: hindsight-dashboard-service
```
```

## 7. Traefik Cross-Namespace Discovery Configuration

**Problem:** Even after explicitly defining namespaces for middlewares and using correct referencing syntax, Traefik (running in `kube-system`) still couldn't discover middlewares in the `default` namespace. This is because Traefik's default configuration disallows cross-namespace resource discovery for security reasons.

**Resolution:** The Traefik deployment itself needs to be configured to allow cross-namespace referencing. This is done by adding the argument `--providers.kubernetescrd.allowCrossNamespace=true` to Traefik's command-line arguments in its deployment YAML (e.g., `kubectl edit deployment traefik -n kube-system`).

**Relevant Change (example in Traefik's Deployment YAML, not in this repository):**
```yaml
spec:
  template:
    spec:
      containers:
        - name: traefik
          args:
            - --providers.kubernetescrd.allowCrossNamespace=true # Add this line
            # ... other Traefik arguments
```

## 8. CI/CD Robustness for CRD Application

**Problem:** A race condition could occur where `oauth2-proxy-middleware.yaml` was applied before the `middlewares.traefik.io` CRD was fully established in the cluster, leading to the middleware not being created correctly.

**Resolution:** Added a `kubectl wait` command to the `.github/workflows/deploy.yml` script to explicitly wait for the `middlewares.traefik.io` CRD to be established before applying the `oauth2-proxy-middleware.yaml`. Also added a file existence check for the middleware YAML.

**Relevant Change (in `.github/workflows/deploy.yml`):**
```diff
--- a/.github/workflows/deploy.yml
+++ b/.github/workflows/deploy.yml
@@ -103,11 +103,13 @@ jobs:
             
             # Install Traefik Resource Definitions and RBAC for Traefik
             echo "Applying Traefik CRDs..."
+            # Apply CRDs
             sudo kubectl apply -f https://raw.githubusercontent.com/traefik/traefik/v3.3/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml
             sudo kubectl apply -f https://raw.githubusercontent.com/traefik/traefik/v3.3/docs/content/reference/dynamic-configuration/kubernetes-crd-rbac.yml
-            
-            echo "Waiting for CRDs to be registered..."
-            sleep 10 # Give Kubernetes time to register the CRDs
+
+            # Wait for CRDs to be established
+            echo "Waiting for Middleware CRD..."
+            sudo kubectl wait --for=condition=established crd/middlewares.traefik.io --timeout=60s
             
             # Replace placeholder in k8s manifests with actual GitHub username
             echo "Replacing YOUR_GITHUB_USERNAME placeholder in k8s manifests..."
@@ -140,9 +142,13 @@ jobs:
               | sudo kubectl create secret generic oauth2-proxy-secret --from-env-file=/dev/stdin --dry-run=client -o yaml | sudo kubectl apply -f -
             echo "oauth2-proxy secret created."
 
-            # Apply oauth2-proxy deployment and middleware
-            echo "Applying oauth2-proxy deployment and middleware..."
+            # Apply oauth2-proxy deployment
+            echo "Applying oauth2-proxy deployment..."
             sudo kubectl apply -f k8s/oauth2-proxy-deployment.yaml
+            
+            # Apply oauth2-proxy middleware after CRD is established
+            echo "Applying oauth2-proxy middleware..."
+            test -f k8s/oauth2-proxy-middleware.yaml && echo "Middleware file found" || echo "Middleware file missing"
             sudo kubectl apply -f k8s/oauth2-proxy-middleware.yaml
