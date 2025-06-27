# CI/CD Pipeline Plan for Hindsight AI with GitHub Actions and Kubernetes

This document outlines the detailed plan for setting up a Continuous Integration/Continuous Deployment (CI/CD) pipeline for the Hindsight AI project. The pipeline will automate the building of Docker images for the `hindsight-service` (FastAPI backend), `hindsight-dashboard` (React frontend), and deploy them along with PostgreSQL to a K3s cluster using GitHub Actions.

## 1. Create Dockerfiles

A `Dockerfile` will be created for each application to define how its Docker image should be built.

### 1.1. `apps/hindsight-service/Dockerfile`

This Dockerfile will be placed in the `apps/hindsight-service/` directory.

```dockerfile
# Use a lightweight Python base image
FROM python:3.13-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Install uv (or pip if uv is not preferred for production builds)
# For uv, ensure it's installed globally or in a way accessible by the build process
# For simplicity, we'll assume uv is available or use pip directly.
# Given pyproject.toml, uv is the package manager.
# Install uv and then use it to install dependencies
RUN pip install uv

# Copy pyproject.toml and uv.lock first to leverage Docker cache
COPY apps/hindsight-service/pyproject.toml apps/hindsight-service/uv.lock ./

# Install dependencies using uv
RUN uv pip install --system .

# Copy the rest of the application code
COPY apps/hindsight-service/ ./

# Expose the port the FastAPI application listens on
EXPOSE 8000

# Define the command to run the FastAPI application with Uvicorn
# The app is located in core/api/main.py and the FastAPI instance is named 'app'
CMD ["uvicorn", "core.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 1.2. `apps/hindsight-dashboard/Dockerfile`

This Dockerfile will be placed in the `apps/hindsight-dashboard/` directory.

```dockerfile
# Stage 1: Build the React application
FROM node:20-alpine AS build

WORKDIR /app

# Copy package.json and package-lock.json to install dependencies
COPY apps/hindsight-dashboard/package*.json ./

# Install Node.js dependencies
RUN npm install

# Copy the rest of the application code
COPY apps/hindsight-dashboard/ ./

# Build the React application for production
RUN npm run build

# Stage 2: Serve the React application with Nginx
FROM nginx:alpine

# Copy the Nginx configuration
# Create a custom nginx.conf if needed, otherwise use default
# For a simple React app, default might be sufficient or a minimal one
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built React app from the build stage to Nginx's public directory
COPY --from=build /app/build /usr/share/nginx/html

# Expose port 80 for the web server
EXPOSE 80

# Command to run Nginx
CMD ["nginx", "-g", "daemon off;"]
```

**Note for `apps/hindsight-dashboard/Dockerfile`**: You might need to create a simple `nginx.conf` file in `apps/hindsight-dashboard/` if the default Nginx configuration doesn't correctly serve your React app's routing (e.g., for client-side routing). A basic `nginx.conf` might look like this:

```nginx
server {
  listen 80;
  location / {
    root /usr/share/nginx/html;
    index index.html index.htm;
    try_files $uri $uri/ /index.html;
  }
}
```

## 2. Create Kubernetes Manifests

A new `k8s/` directory will be created at the root of the repository (`/home/jean/git/hindsight-ai/k8s/`). All Kubernetes manifest files will be placed inside this directory.

### 2.1. `k8s/postgres-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-deployment
  labels:
    app: postgres
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:13
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_DB
              value: "hindsight_db"
            - name: POSTGRES_USER
              value: "user"
            - name: POSTGRES_PASSWORD
              value: "password"
          volumeMounts:
            - name: postgres-storage
              mountPath: /var/lib/postgresql/data
      volumes:
        - name: postgres-storage
          persistentVolumeClaim:
            claimName: postgres-pvc
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi # Adjust storage size as needed
```

### 2.2. `k8s/postgres-service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  labels:
    app: postgres
spec:
  selector:
    app: postgres
  ports:
    - protocol: TCP
      port: 5432
      targetPort: 5432
  type: ClusterIP
```

### 2.3. `k8s/hindsight-service-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hindsight-service-deployment
  labels:
    app: hindsight-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: hindsight-service
  template:
    metadata:
      labels:
        app: hindsight-service
    spec:
      containers:
        - name: hindsight-service
          image: ghcr.io/YOUR_GITHUB_USERNAME/hindsight-service:latest # This will be updated by GitHub Actions
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              value: "postgresql://user:password@postgres-service:5432/hindsight_db"
            # Add other necessary environment variables here, e.g., LLM_API_KEY
            # For production, consider using Kubernetes Secrets for sensitive data
            - name: LLM_API_KEY
              valueFrom:
                secretKeyRef:
                  name: hindsight-secrets
                  key: LLM_API_KEY
          imagePullPolicy: Always # Ensure the latest image is pulled
```

**Note for `hindsight-service-deployment.yaml`**: You will need to create a Kubernetes Secret named `hindsight-secrets` containing your `LLM_API_KEY` (and any other sensitive environment variables) before deploying. Example:

```bash
kubectl create secret generic hindsight-secrets --from-literal=LLM_API_KEY='your_llm_api_key_here'
```

### 2.4. `k8s/hindsight-service-service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: hindsight-service-service
  labels:
    app: hindsight-service
spec:
  selector:
    app: hindsight-service
  ports:
    - protocol: TCP
      port: 8000
      targetPort: 8000
  type: ClusterIP
```

### 2.5. `k8s/hindsight-service-ingress.yaml`

```yaml
apiVersion: traefik.containo.us/v1alpha1
kind: IngressRoute
metadata:
  name: hindsight-service-ingress
spec:
  entryPoints:
    - websecure # Assuming Traefik is configured for HTTPS
  routes:
    - match: Host(`your-domain.com`) && PathPrefix(`/api`) # Replace your-domain.com
      kind: Rule
      services:
        - name: hindsight-service-service
          port: 8000
```

**Note for `hindsight-service-ingress.yaml`**: Replace `your-domain.com` with your actual domain. If you are not using HTTPS or Traefik's `websecure` entrypoint, adjust `entryPoints` accordingly (e.g., `web`).

### 2.6. `k8s/hindsight-dashboard-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hindsight-dashboard-deployment
  labels:
    app: hindsight-dashboard
spec:
  replicas: 1
  selector:
    matchLabels:
      app: hindsight-dashboard
  template:
    metadata:
      labels:
        app: hindsight-dashboard
    spec:
      containers:
        - name: hindsight-dashboard
          image: ghcr.io/YOUR_GITHUB_USERNAME/hindsight-dashboard:latest # This will be updated by GitHub Actions
          ports:
            - containerPort: 80
          imagePullPolicy: Always # Ensure the latest image is pulled
```

### 2.7. `k8s/hindsight-dashboard-service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: hindsight-dashboard-service
  labels:
    app: hindsight-dashboard
spec:
  selector:
    app: hindsight-dashboard
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: ClusterIP
```

### 2.8. `k8s/hindsight-dashboard-ingress.yaml`

```yaml
apiVersion: traefik.containo.us/v1alpha1
kind: IngressRoute
metadata:
  name: hindsight-dashboard-ingress
spec:
  entryPoints:
    - websecure # Assuming Traefik is configured for HTTPS
  routes:
    - match: Host(`your-domain.com`) && PathPrefix(`/`) # Replace your-domain.com
      kind: Rule
      services:
        - name: hindsight-dashboard-service
          port: 80
```

**Note for `hindsight-dashboard-ingress.yaml`**: Replace `your-domain.com` with your actual domain. If you are not using HTTPS or Traefik's `websecure` entrypoint, adjust `entryPoints` accordingly (e.g., `web`). Ensure this Ingress has a lower priority or more specific rule than the `/api` ingress if both are on the same domain, or use different subdomains.

## 3. Create GitHub Actions Workflow

The GitHub Actions workflow file will be created at `.github/workflows/deploy.yml`.

```yaml
name: Build, Push, and Deploy Hindsight AI to K3s

on:
  push:
    branches: [ main ] # Triggers the workflow on every push to the main branch

jobs:
  # --- JOB 1: Build and Push Hindsight Service Docker Image ---
  build-and-push-hindsight-service:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write # Permission needed to push images to GHCR

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }} # Automatically generated by GitHub

      - name: Build and push Hindsight Service Docker image
        id: build-push-service
        uses: docker/build-push-action@v5
        with:
          context: apps/hindsight-service # Context is the hindsight-service directory
          push: true
          tags: |
            ghcr.io/${{ github.repository_owner }}/hindsight-service:${{ github.sha }}
            ghcr.io/${{ github.repository_owner }}/hindsight-service:latest
          file: apps/hindsight-service/Dockerfile # Specify the Dockerfile path

  # --- JOB 2: Build and Push Hindsight Dashboard Docker Image ---
  build-and-push-hindsight-dashboard:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Hindsight Dashboard Docker image
        id: build-push-dashboard
        uses: docker/build-push-action@v5
        with:
          context: apps/hindsight-dashboard # Context is the hindsight-dashboard directory
          push: true
          tags: |
            ghcr.io/${{ github.repository_owner }}/hindsight-dashboard:${{ github.sha }}
            ghcr.io/${{ github.repository_owner }}/hindsight-dashboard:latest
          file: apps/hindsight-dashboard/Dockerfile # Specify the Dockerfile path

  # --- JOB 3: Deploy Images to K3s Server ---
  deploy:
    needs: [build-and-push-hindsight-service, build-and-push-hindsight-dashboard] # Waits for both build jobs to complete
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Deploy to Server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          port: ${{ secrets.SSH_PORT }}
          script: |
            echo "Connection successful, deployment in progress..."
            
            # Apply Kubernetes manifests
            # Ensure the k8s directory is present on the server or clone the repo
            # For simplicity, we assume the k8s directory is available or will be cloned.
            # A better approach for production might be to use kustomize or helm.
            
            # Apply all manifests in the k8s directory
            kubectl apply -f k8s/
            
            # Update the image of the hindsight-service deployment
            kubectl set image deployment/hindsight-service-deployment hindsight-service=ghcr.io/${{ github.repository_owner }}/hindsight-service:latest
            
            # Update the image of the hindsight-dashboard deployment
            kubectl set image deployment/hindsight-dashboard-deployment hindsight-dashboard=ghcr.io/${{ github.repository_owner }}/hindsight-dashboard:latest
            
            echo "Deployment completed!"
```

**Note on `github.repository_owner`**: This variable automatically resolves to your GitHub username or organization name.

## 4. Configure GitHub Secrets

These secrets must be configured in your GitHub repository settings under `Settings` > `Secrets and variables` > `Actions`.

*   **`SSH_HOST`**: The IP address of your server (`46.62.141.65`).
*   **`SSH_USERNAME`**: Your SSH username (`jean`).
*   **`SSH_PORT`**: Your SSH port (`2222`).
*   **`SSH_KEY`**: The complete content of your **private SSH key** (`hertzner_builder_os` file, without the `.pub` extension).

Once all these files are in place and secrets are configured, a `git push` to your `main` branch will trigger the automated build and deployment process. You can monitor the workflow execution in the "Actions" tab of your GitHub repository.

## 5. Networking and Port Exposure

It is crucial to understand how networking works with Kubernetes and Traefik Ingress.

*   **External Access:** Your Hetzner server should only have standard web ports (like 80 for HTTP and 443 for HTTPS) open to the internet.
*   **Traefik Ingress:** Traefik, your Ingress controller, listens on these external ports. It then routes incoming traffic to the correct internal Kubernetes Services (like `hindsight-dashboard-service` on port 80 and `hindsight-service-service` on port 8000) based on the domain and path rules defined in your `IngressRoute` manifests.
*   **Internal Communication:** Services within your Kubernetes cluster (e.g., `hindsight-dashboard` communicating with `hindsight-service`, or `hindsight-service` communicating with `postgres-service`) use internal ClusterIP services and do not require external port exposure.
*   **Local MCP Server Interaction:** If your local MCP server needs to interact with the deployed `hindsight-service`, it should do so via the public domain and the `/api` path (e.g., `https://your-domain.com/api/memory-blocks`), not by directly accessing internal Kubernetes service IPs or ports.

Therefore, you **do not need to open ports 3000 or 8000** on your Hetzner server's firewall. Your existing port 80 (and 443 if configured for HTTPS) is sufficient, with Traefik handling the internal routing.
