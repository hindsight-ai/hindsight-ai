# Use a lightweight Python base image
FROM python:3.13.5-slim

# Set the working directory inside the container
WORKDIR /app

# Install PostgreSQL client tools and uv
RUN apt-get update && apt-get install -y postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv (or pip if uv is not preferred for production builds)
# For uv, ensure it's installed globally or in a way accessible by the build process
# For simplicity, we'll assume uv is available or use pip directly.
# Given pyproject.toml, uv is the package manager.
# Install uv and then use it to install dependencies
RUN pip install uv

# Copy pyproject.toml and uv.lock first to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv pip install --system .

# Copy the rest of the application code
COPY . ./

# Expose the port the FastAPI application listens on
EXPOSE 8000

# Define the command to run the FastAPI application with Uvicorn
# The app is located in core/api/main.py and the FastAPI instance is named 'app'
CMD ["uvicorn", "core.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
