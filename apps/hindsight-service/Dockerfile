# Use a lightweight Python base image
FROM python:3.13.5-slim

# Define build arguments
ARG BUILD_SHA
ARG BUILD_TIMESTAMP
ARG IMAGE_TAG
ARG VERSION

# Set environment variables from build arguments
ENV BUILD_SHA=${BUILD_SHA}
ENV BUILD_TIMESTAMP=${BUILD_TIMESTAMP}
ENV IMAGE_TAG=${IMAGE_TAG}
ENV VERSION=${VERSION}

# Set the working directory inside the container
WORKDIR /app

# Install PostgreSQL client tools and upgrade pip
RUN apt-get update && apt-get install -y postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --upgrade pip setuptools wheel

# Copy project files and install dependencies using pip
COPY . ./
RUN pip install --no-cache-dir .

# Expose the port the FastAPI application listens on
EXPOSE 8000

# Make the entrypoint script executable
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Define the entrypoint to run migrations and then start the FastAPI application
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "core.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
