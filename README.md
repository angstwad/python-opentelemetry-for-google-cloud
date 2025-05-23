# OpenTelemetry with Google Cloud Monitoring Demo

[//]: # (**Note:** This repository is a supplement to the blog post: <TODO: INSERT LINK TO BLOG POST HERE>.)

## Why This Project Exists

This project demonstrates the best known configuration for OpenTelemetry with Google Cloud
Monitoring in Python. It uses a FastAPI application as a device for demonstration.

Setting up these libraries can be incredibly confusing. This project aims to provide a clear,
working example.

The most important file here is [ops.py](src/fastapi_tracing/ops.py). This file contains the core
logic for setting up
OpenTelemetry to work seamlessly with GCP. It's opinionated because the world of OpenTelemetry
configuration is vast. This setup makes specific choices to get you up and running efficiently with
traces, metrics, and logs in Google Cloud.

For instance, `ops.py` programmatically configures:

* Trace, metric, and log exporters (e.g., `OTLPSpanExporter`, `OTLPMetricExporter`,
  `OTLPLogExporter`) to send telemetry data to an OpenTelemetry collector.
* A `SpanToMetricProcessor`, which is a custom processor that converts span information into
  metrics—a common and useful pattern.
* Structured logging using `python-json-logger`. This ensures that logs are machine-readable and
  automatically include trace context (like trace IDs and span IDs). This is vital for correlating
  logs with traces in GCP.

**Important Note on Logging:** This application supports two methods for exporting logs:

1. **Via the OpenTelemetry Collector**: Logs are sent using the OTLPLogExporter.
2. **Via `stdout` as structured JSON**: The application is also configured to write logs in JSON
   format to `stdout`. Many Google Cloud services (like Cloud Run, Google Kubernetes Engine (GKE),
   Cloud Functions, and App Engine Flexible Environment) can automatically parse these JSON logs
   from `stdout`/`stderr`, making them viewable and searchable in Cloud Logging with proper
   indexing of JSON fields.

The `otel-collector-config.yaml` file is also opinionated. It's designed to run
the [OpenTelemetry collector](https://opentelemetry.io/docs/collector/installation/) in a specific
way, optimized for this demo. We expect the OpenTelemetry collector to be deployed as a sidecar in
any environment where this application is installed.

The API code in this project is purely for demonstration purposes. Its sole function is to showcase
this definitive OpenTelemetry configuration.

## How to Run

This project uses `uv` for dependency management and as a runner.

### Using `uv`

1. **Install `uv`**:
   If you don't have `uv` installed, follow the instructions on the [official
   `uv` website](https://github.com/astral-sh/uv).

2. **Create a virtual environment**:
   ```bash
   uv venv
   ```

3. **Activate the virtual environment**:
   ```bash
   source .venv/bin/activate
   ```

4. **Install dependencies**:
   ```bash
   uv pip install -r requirements.txt
   ```
   (Or, if you have a `pyproject.toml` and prefer to install from that):
   ```bash
   uv pip install .
   ```

5. **Run the application**:
   The command below is derived from the `Dockerfile` and is suitable for local development.
   ```bash
   uv run uvicorn --host 0.0.0.0 --port 8000 --workers 2 --factory src.fastapi_tracing.app:get_or_create_app --reload
   ```

### Using Docker (for GCP or other containerized environments)

This project includes a `Dockerfile` that you can use to build an image and run it.
This is suitable for environments like Google Cloud Run or Google Kubernetes Engine.

1. **Build the Docker image**:
   ```bash
   docker build -t your-image-name .
   ```

2. **Run the Docker container**:
   ```bash
   docker run -p 8000:8000 your-image-name
   ```
   Remember to configure your GCP environment to run the OpenTelemetry collector as a sidecar to
   this application container.
   The `otel-collector-config.yaml` should be used to configure this sidecar.