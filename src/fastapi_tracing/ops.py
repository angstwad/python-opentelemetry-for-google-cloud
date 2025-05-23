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
""" Configures OpenTelemetry and structured logging for FastAPI applications. """
import logging
import os
from datetime import datetime
from typing import Optional

import fastapi
from opentelemetry import _events as events
from opentelemetry import _logs as logs
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk._events import EventLoggerProvider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler as OtelLoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_INSTANCE_ID, SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pythonjsonlogger import json as jsonlogger

from . import __version__

_RESOURCE = Resource.create(
    attributes={
        # Use the PID as the service.instance.id to avoid duplicate timeseries
        # from different worker processes
        SERVICE_NAME: "fastapi-tracing",
        SERVICE_INSTANCE_ID: f"worker-{os.getpid()}",
    }
)

from opentelemetry import metrics, trace
from opentelemetry.sdk.trace import Span, SpanProcessor
from opentelemetry.semconv.trace import SpanAttributes  # Standard attribute keys

# Get a meter to create metric instruments
# It's good practice to get it once and reuse it.
meter = metrics.get_meter("fastapi.instrumentation.spans-to-metrics")


class SpanToMetricProcessor(SpanProcessor):
    """
    A custom SpanProcessor that converts span data into metrics.

    This processor will create a latency histogram for completed spans
    that match a given set of criteria.

    Use: SpanToMetricProcessor(span_names={"GET /", "POST /foo"})
    """

    def __init__(self, span_names: set[str]):
        super().__init__()
        self.span_names = set(span_names)
        self.request_latency_histogram = meter.create_histogram(
            name="http.server.request.latency",
            description="Measures the duration of inbound HTTP requests from spans.",
            unit="ms",
        )

    def on_end(self, span: Span) -> None:
        """Called when a span is ended."""
        # 1. Filter for the spans you want to turn into metrics.
        # FastAPIInstrumentor creates spans with names like "HTTP GET", "HTTP POST", etc.
        if span.name not in self.span_names:
            return

        # 2. Calculate latency directly and precisely from the span.
        start_time_ns = span._start_time
        end_time_ns = span._end_time
        if not start_time_ns or not end_time_ns:
            return

        latency_ms = (end_time_ns - start_time_ns) / 1_000_000  # nanoseconds to milliseconds

        # 3. Extract attributes from the span to use as metric dimensions.
        # Use the standard semantic convention keys that FastAPIInstrumentor provides.
        metric_attributes = {
            "http.method": span.attributes.get(SpanAttributes.HTTP_METHOD),
            "http.route": span.attributes.get(SpanAttributes.HTTP_ROUTE),
            "http.status_code": span.attributes.get(SpanAttributes.HTTP_STATUS_CODE),
            "http.flavor": span.attributes.get(SpanAttributes.HTTP_FLAVOR),
        }

        # 5. Record the metric with its attributes and the exemplar.
        self.request_latency_histogram.record(
            amount=latency_ms,
            attributes=metric_attributes,
        )


def setup_otel(app: fastapi.FastAPI, span_metrics_names: set[str] | None = None) -> None:
    # Set up OpenTelemetry Python SDK
    tracer_provider = TracerProvider(resource=_RESOURCE)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)
    if span_metrics_names:
        metric_processor = SpanToMetricProcessor(span_names=span_metrics_names)
        tracer_provider.add_span_processor(metric_processor)

    logger_provider = LoggerProvider(resource=_RESOURCE)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    logs.set_logger_provider(logger_provider)

    event_logger_provider = EventLoggerProvider(logger_provider)
    events.set_event_logger_provider(event_logger_provider)

    reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    meter_provider = MeterProvider(metric_readers=[reader], resource=_RESOURCE)
    metrics.set_meter_provider(meter_provider)

    FastAPIInstrumentor.instrument_app(app)


class JsonFormatter(jsonlogger.JsonFormatter):
    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None):
        # Format the timestamp as RFC 3339 with microsecond precision
        isoformat = datetime.fromtimestamp(record.created).isoformat()
        return f"{isoformat}Z"


class AppNameFilter(logging.Filter):
    """ Adds an appname attribute to log records.  This is useful when logs may be commingled
    with other applications and extra filtering is required.
    """

    def __init__(self, appname: str, *args, **kwargs):
        self.appname = appname
        super().__init__(*args, **kwargs)

    def filter(self, record: logging.LogRecord) -> bool:
        record.appname = self.appname
        return True


def setup_structured_logging(app_name: str | None = None,
                             enable_otel: bool = True,
                             enable_json_formatter: bool = False,
                             log_level: int = logging.INFO) -> None:
    # otel-only logging; remove if not using otel logs collector
    otel_handler: logging.Handler | None = None
    if enable_otel:
        log_provider = logs.get_logger_provider()
        otel_handler = OtelLoggingHandler(level=log_level, logger_provider=log_provider)

    # logging to stdout
    stream_handler = logging.StreamHandler()

    app_name_filter = AppNameFilter(app_name)
    stream_handler.addFilter(app_name_filter)
    if otel_handler:
        otel_handler.addFilter(app_name_filter)

    # JSON formatter; intentionally disabled
    # use if logging to stdout on GKE, Cloud Run or equivalent service capable of processing
    # structured logs on stdout
    json_formatter = JsonFormatter(
        "%(asctime)s %(levelname)s %(appname)s %(message)s %(otelTraceID)s %(otelSpanID)s %(otelTraceSampled)s",
        rename_fields={
            "levelname": "severity",
            "asctime": "timestamp",
            "otelTraceID": "logging.googleapis.com/trace",
            "otelSpanID": "logging.googleapis.com/spanId",
            "otelTraceSampled": "logging.googleapis.com/trace_sampled",
        },
    )

    if enable_json_formatter:
        stream_handler.setFormatter(json_formatter)

    handlers = [stream_handler, otel_handler if enable_otel else None]

    logging.basicConfig(
        level=log_level,
        format='%(levelname)-7s %(message)s',
        handlers=handlers,
    )

    LoggingInstrumentor().instrument()


meter = metrics.get_meter("fastapi-tracing", version=__version__)
