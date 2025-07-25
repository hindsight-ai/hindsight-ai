# Stage 1: Build the React application
FROM node:20-alpine AS build

WORKDIR /app

# Declare build arguments for frontend build information
ARG REACT_APP_HINDSIGHT_SERVICE_API_URL
ARG REACT_APP_VERSION
ARG REACT_APP_BUILD_SHA
ARG REACT_APP_BUILD_TIMESTAMP
ARG REACT_APP_DASHBOARD_IMAGE_TAG

# Set them as environment variables for the build process
ENV REACT_APP_HINDSIGHT_SERVICE_API_URL=$REACT_APP_HINDSIGHT_SERVICE_API_URL
ENV REACT_APP_VERSION=$REACT_APP_VERSION
ENV REACT_APP_BUILD_SHA=$REACT_APP_BUILD_SHA
ENV REACT_APP_BUILD_TIMESTAMP=$REACT_APP_BUILD_TIMESTAMP
ENV REACT_APP_DASHBOARD_IMAGE_TAG=$REACT_APP_DASHBOARD_IMAGE_TAG

# Copy package.json and package-lock.json to install dependencies
COPY package*.json ./

# Install Node.js dependencies
RUN npm install

# Copy the rest of the application code
COPY . ./

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
