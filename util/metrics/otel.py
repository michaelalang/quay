from functools import wraps
import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON, TraceIdRatioBased

from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter,
)


import features

def init_exporter(app_config, span_exporter_factory=None):

    otel_config = app_config.get("OTEL_CONFIG", {})

    service_name = otel_config.get("service_name", "quay")
    DT_API_URL = otel_config.get("dt_api_url", None)
    DT_API_TOKEN = otel_config.get("dt_api_token", None)
    service_namespace = otel_config.get("service_namespace", "standalone")
    service_version = otel_config.get("service_version", "unknown")
    resource = Resource.create(attributes={SERVICE_NAME: service_name, "service.namespace": service_namespace, "service.version": service_version})

    sampler_rate = otel_config.get("OTEL_TRACES_SAMPLER_ARG", 1 / 1000)
    sampler = TraceIdRatioBased(sampler_rate)
    tracerProvider = TracerProvider(resource=resource, sampler=sampler)

    import os

    is_test = os.environ.get("TEST") == "true"

    sampler_rate = otel_config.get("OTEL_TRACES_SAMPLER_ARG", 1 / 1000)
    sampler = ALWAYS_ON if is_test else TraceIdRatioBased(sampler_rate)
    tracerProvider = TracerProvider(resource=resource, sampler=sampler)

    processor_type = SimpleSpanProcessor if is_test else BatchSpanProcessor

    if DT_API_URL is not None and DT_API_TOKEN is not None:
        exporter_instance = (span_exporter_factory or OTLPSpanExporter)(
            endpoint=DT_API_URL + "/v1/traces",
            headers={
                "Authorization": "Api-Token " + DT_API_TOKEN,
                "Tenant-Id": otel_config.get("OTEL_EXPORTER_OTLP_HEADERS", {}).get("Tenant-Id"),
            },
        )
        processor = processor_type(exporter_instance)
    else:
        exporter_instance = (span_exporter_factory or OTLPSpanExporter)(endpoint="http://jaeger:4317")
        processor = processor_type(exporter_instance)

    tracerProvider.add_span_processor(processor)
    trace.set_tracer_provider(tracerProvider)


def init_logging(app_config, log_exporter_factory=None):
    otel_config = app_config.get("OTEL_CONFIG", {})

    service_name = otel_config.get("service_name", "quay")
    DT_API_URL = otel_config.get("dt_api_url", None)
    DT_API_TOKEN = otel_config.get("dt_api_token", None)
    service_namespace = otel_config.get("service_namespace", "standalone")
    service_version = otel_config.get("service_version", "unknown")
    resource = Resource.create(attributes={SERVICE_NAME: service_name, "service.namespace": service_namespace, "service.version": service_version})

    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)
    import requests
    import urllib3

    # Optional but recommended: Suppress the console warnings that 'requests' throws when SSL is disabled
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # 1. Create a custom session and disable TLS/SSL verification
    insecure_session = requests.Session()
    insecure_session.verify = False
    if DT_API_URL is not None and DT_API_TOKEN is not None:
        exporter_instance = (log_exporter_factory or OTLPLogExporter)(
            endpoint=DT_API_URL + "/v1/logs",
            headers={
                "Authorization": "Api-Token " + DT_API_TOKEN,
                "Tenant-Id": otel_config.get("OTEL_EXPORTER_OTLP_HEADERS", {}).get("Tenant-Id"),
            },
            session=insecure_session
        )
        processor = BatchLogRecordProcessor(exporter_instance)
    else:
        exporter_instance = (log_exporter_factory or OTLPLogExporter)(endpoint="http://jaeger:4318")
        processor = BatchLogRecordProcessor(exporter_instance)

    logger_provider.add_log_record_processor(processor)

    # Attach the OpenTelemetry handler to the root logger
    logging.getLogger().addHandler(LoggingHandler(logger_provider=logger_provider))


def get_otel_logging_handler():
    return LoggingHandler(level=logging.NOTSET)


def traced(span_name=None):
    """
    Decorator for tracing function calls using OpenTelemetry.
    """

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if features.OTEL_TRACING:
                tracer = trace.get_tracer(__name__)
                name = span_name if span_name else func.__name__
                with tracer.start_as_current_span(name) as span:
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(trace.Status(trace.StatusCode.ERROR))
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorate
