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
RUN apt-get update && apt-get install -y \
        curl \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --upgrade pip setuptools wheel

# Copy project files and install the EXACT dependency versions from uv.lock
# (the same versions CI tests). A plain `pip install .` resolves the open-ended
# ranges in pyproject.toml to whatever is newest at build time, which silently
# shipped untested majors (e.g. SQLAlchemy 2.1 switched the default PostgreSQL
# driver to psycopg 3, so the image could not even run migrations).
COPY . ./
RUN pip install --no-cache-dir uv \
    && uv export --frozen --no-dev --no-emit-project --no-hashes -o /tmp/requirements.lock.txt \
    && pip install --no-cache-dir -r /tmp/requirements.lock.txt \
    && pip install --no-cache-dir --no-deps . \
    && rm /tmp/requirements.lock.txt

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:${PATH}"

# Expose the port the FastAPI application listens on
EXPOSE 8000

# Make the entrypoint script executable
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Define the entrypoint to run migrations and then start the FastAPI application
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "core.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
