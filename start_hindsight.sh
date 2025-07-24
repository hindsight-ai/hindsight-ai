#!/bin/bash

set -e

echo "Starting Hindsight AI services for local development..."
echo "Using Docker Compose with development profile..."

# Check if services are already running
if docker compose -f docker-compose.yml -f docker-compose.dev.yml ps | grep -q "Up"; then
    echo "Hindsight AI services are already running."
    echo "To stop them, run: ./stop_hindsight.sh"
    exit 0
fi

# Start all services using Docker Compose with development profile
echo "Building and starting services..."
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 5

# Check if services are running
if docker compose -f docker-compose.yml -f docker-compose.dev.yml ps | grep -q "Up"; then
    echo ""
    echo "✅ All Hindsight AI services started successfully!"
    echo ""
    echo "Services are accessible at:"
    echo "  🌐 Frontend Dashboard: http://localhost:3000"
    echo "  🔧 Backend API: http://localhost:8000"
    echo "  🗄️  Database: localhost:5432"
    echo ""
    echo "To view logs: docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f"
    echo "To stop services: ./stop_hindsight.sh"
else
    echo "❌ Failed to start services. Check logs with:"
    echo "docker compose -f docker-compose.yml -f docker-compose.dev.yml logs"
    exit 1
fi

exit 0
