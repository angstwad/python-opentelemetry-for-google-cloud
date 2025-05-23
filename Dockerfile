# Copyright 2025 Paul Durivage <durivage+github@google.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Use an official Python runtime as a parent image
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory in the container
WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --verbose

# Copy the content of the local src directory to the working directory
COPY src .

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --verbose

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable (optional, can be removed if not used by the app)
ENV NAME FastAPI

# Run main.py when the container launches
# The application is started with uvicorn directly as per main.py's if __name__ == "__main__": block
CMD ["uv", "run", "uvicorn", "--host", "0.0.0.0", "--port", "8000", "--workers", "8", "--factory", "src.fastapi_tracing.app:get_or_create_app", "--reload"]
