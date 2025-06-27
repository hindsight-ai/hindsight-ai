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
COPY apps/hindsight-dashboard/nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built React app from the build stage to Nginx's public directory
COPY --from=build /app/build /usr/share/nginx/html

# Expose port 80 for the web server
EXPOSE 80

# Command to run Nginx
CMD ["nginx", "-g", "daemon off;"]
