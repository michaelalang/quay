import opentelemetry.exporter.otlp.proto.grpc.trace_exporter
import opentelemetry.exporter.otlp.proto.http.trace_exporter
import pytest
from opentelemetry import context, trace
from opentelemetry._logs import get_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter,
)
from flask import Flask
import unittest.mock
import logging
import os
import time

from util.metrics.otel import init_exporter, init_logging
from features import import_features

app = Flask(__name__)

# check various configuration options
app_configs = [
    {
        "OTEL_CONFIG": {
            "service_name": "unittest",
            "OTEL_EXPORTER_OTLP_HEADERS": {
                "Authorization": "Api-Token abcdef",
                "Tenant-Id": "Tenant 1",
            },
            "OTEL_EXPORTER_OTLP_ENDPOINT": "https://otlp.example.com",
            "OTEL_EXPORTER_OTLP_INSECURE": False,
            "OTEL_EXPORTER_OTLP_PROTOCOL": "http",
            "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
            "OTEL_TRACES_SAMPLER_ARG": 0.005,
            "dt_api_url": "https://otlp.example.com",
            "dt_api_token": "abcdef",
        },
        "FEATURE_ENABLE_OTEL": True,
    },
]


@pytest.fixture()
@unittest.mock.patch('util.metrics.otel.OTLPSpanExporter')
def test_otel_config(MockSpanExporter, request):
    # Clear any interfering environment variables
    original_otel_endpoint = os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
    original_otel_traces_endpoint = os.environ.pop("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", None)
    original_otel_protocol = os.environ.pop("OTEL_EXPORTER_OTLP_PROTOCOL", None)

    app.config["OTEL_CONFIG"] = request.param["OTEL_CONFIG"]
    app.config["FEATURE_OTEL_TRACING"] = True
    import_features(app.config)

    real_mock_span_exporter_instance = unittest.mock.Mock()
    real_mock_span_exporter_instance.export.return_value = 0 # SUCCESS

    init_exporter(app.config, span_exporter_factory=lambda **kwargs: (
        setattr(real_mock_span_exporter_instance, "_endpoint", kwargs.get("endpoint")),
        setattr(real_mock_span_exporter_instance, "_headers", kwargs.get("headers")),
        real_mock_span_exporter_instance
    )[2])
    tracerProvider = trace.get_tracer_provider()

    return real_mock_span_exporter_instance, MockSpanExporter

    # Restore environment variables after the test
    if original_otel_endpoint is not None:
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = original_otel_endpoint
    if original_otel_traces_endpoint is not None:
        os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = original_otel_traces_endpoint
    if original_otel_protocol is not None:
        os.environ["OTEL_EXPORTER_OTLP_PROTOCOL"] = original_otel_protocol


@pytest.mark.parametrize("test_otel_config", app_configs, indirect=True)
def test_traced_decorator(test_otel_config):
    from util.metrics.otel import traced

    mock_span_exporter_instance, MockSpanExporter = test_otel_config
    tracerProvider = trace.get_tracer_provider()
    tracer = tracerProvider.get_tracer("unittest")

    # Assertions for tracer configuration
    assert tracer.resource.attributes.get("service.name") == "unittest"
    assert tracer.resource.attributes.get("service.namespace") == "standalone"
    assert tracer.resource.attributes.get("service.version", False)

    # Assert headers passed to the OTLPSpanExporter constructor
    assert mock_span_exporter_instance._endpoint == "https://otlp.example.com/v1/traces"
    assert mock_span_exporter_instance._headers.get("Authorization") == "Api-Token abcdef"
    assert mock_span_exporter_instance._headers.get("Tenant-Id") == "Tenant 1"

    @traced(span_name="test_span")
    def test_function():
        return "hello"

    # Call the decorated function
    test_function()

    # Force flush the tracer provider to ensure spans are exported
    assert isinstance(tracerProvider, TracerProvider)

    tracerProvider.force_flush()
    tracerProvider.shutdown()

    # Verify that the exporter's export method was called
    mock_span_exporter_instance.export.assert_called_once()

def test_otel_logging_handler():
    mock_log_exporter_instance = unittest.mock.Mock()
    mock_log_exporter_instance.export.return_value = 0 # SUCCESS

    # Initialize logging with a specific config
    app.config["OTEL_CONFIG"] = app_configs[0]["OTEL_CONFIG"]
    init_logging(app.config, log_exporter_factory=lambda **kwargs: mock_log_exporter_instance)

    # Get a logger and emit a log message
    logger = logging.getLogger(__name__)
    logger.info("Test log message")

    # Force flush the logger provider to ensure logs are exported
    logger_provider = get_logger_provider()
    logger_provider.force_flush()

    # Verify that the exporter's export method was called
    mock_log_exporter_instance.export.assert_called_once()
