# Stage 1: Build the React application
FROM node:20-alpine AS build

WORKDIR /app

# Build-time variables for Vite (only variables prefixed with VITE_ are embedded)
ARG VITE_HINDSIGHT_SERVICE_API_URL
ARG VITE_VERSION
ARG VITE_BUILD_SHA
ARG VITE_BUILD_TIMESTAMP
ARG VITE_DASHBOARD_IMAGE_TAG

# Make them available during build
ENV VITE_HINDSIGHT_SERVICE_API_URL=$VITE_HINDSIGHT_SERVICE_API_URL \
    VITE_VERSION=$VITE_VERSION \
    VITE_BUILD_SHA=$VITE_BUILD_SHA \
    VITE_BUILD_TIMESTAMP=$VITE_BUILD_TIMESTAMP \
    VITE_DASHBOARD_IMAGE_TAG=$VITE_DASHBOARD_IMAGE_TAG

# Copy package.json and package-lock.json to install dependencies
COPY package*.json ./

# Install Node.js dependencies
RUN npm install

# Copy the rest of the application code
COPY . ./

# Build the Vite app for production
RUN npm run build

# Stage 2: Serve the React application with Nginx
FROM nginx:alpine

# Copy the Nginx configuration for SPA fallback routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built app to Nginx's web root (Vite outputs to dist)
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port 80 for the web server
EXPOSE 80

# Command to run Nginx
CMD ["nginx", "-g", "daemon off;"]
