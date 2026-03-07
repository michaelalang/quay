# NOTE: Must be before we import or call anything that may be synchronous.
from gevent import monkey

monkey.patch_all()

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

import logging

from util.log import logfile_path
from util.workers import get_worker_connections_count, get_worker_count

import threading
from gunicorn.glogging import Logger
from gunicorn.http.wsgi import Response
from opentelemetry import trace
from opentelemetry.trace import SpanContext, NonRecordingSpan, TraceFlags

# 1. Create a thread-local storage to ferry the IDs across the gap
_otel_ferry = threading.local()

# 2. Intercept Gunicorn's start_response to grab the IDs while the span is still alive
orig_start_response = Response.start_response

def patched_start_response(self, status, headers, exc_info=None):
    # Quay is calling this to send headers. The OTel span is STILL ACTIVE here!
    span = trace.get_current_span()

    if span and span.get_span_context().is_valid:
        ctx = span.get_span_context()
        # Stash the raw integers into our thread-local ferry
        _otel_ferry.trace_id = ctx.trace_id
        _otel_ferry.span_id = ctx.span_id
    else:
        _otel_ferry.trace_id = None
        _otel_ferry.span_id = None

    return orig_start_response(self, status, headers, exc_info)

# Apply the patch to Gunicorn
Response.start_response = patched_start_response

# 3. Use the custom logger to revive the context from the ferry
class OTelContextGunicornLogger(Logger):
    def access(self, resp, req, environ, request_time):
        t_id = getattr(_otel_ferry, 'trace_id', None)
        s_id = getattr(_otel_ferry, 'span_id', None)

        if t_id and s_id:
            # Reconstruct the dummy span using the raw integers we saved
            span_context = SpanContext(
                trace_id=t_id,
                span_id=s_id,
                is_remote=True,
                trace_flags=TraceFlags(1)
            )
            dummy_span = NonRecordingSpan(span_context)

            # Briefly revive the context so the OTel LoggingHandler can see it
            with trace.use_span(dummy_span, end_on_exit=False):
                super().access(resp, req, environ, request_time)

            # Clean up the ferry for the next request on this worker thread
            _otel_ferry.trace_id = None
            _otel_ferry.span_id = None
        else:
            # Fallback if no trace was active
            super().access(resp, req, environ, request_time)

# Tell Gunicorn to use this custom logger
logger_class = OTelContextGunicornLogger

logconfig = logfile_path(debug=False)

bind = "unix:/tmp/gunicorn_web.sock"
workers = get_worker_count("web", 2, minimum=2, maximum=32)
worker_class = "gevent"
worker_connections = get_worker_connections_count("web")
pythonpath = "."
logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "filters": {
        "module_filter": {
            "()": "util.metrics.otel.ModuleAttributeFilter"              
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "otel_handler": {
            "()": "util.metrics.otel.get_otel_logging_handler", 
            "filters": ["module_filter"],
        }
    },
    "loggers": {
        # Gunicorn's main error and lifecycle logger
        "gunicorn.error": {
            "handlers": ["console", "otel_handler"],
            "level": "INFO",
            "propagate": False,
        },
        # Gunicorn's web traffic logger
        "gunicorn.access": {
            "handlers": ["console", "otel_handler"],
            "level": "INFO",
            "propagate": False,
        }
    }
}

if os.getenv("QUAY_HOTRELOAD", "false") == "true":
    reload = True
    reload_engine = "auto"
else:
    preload_app = True


def when_ready(server):
    logger = logging.getLogger(__name__)
    logger.debug("Starting web gunicorn with %s workers and %s worker class", workers, worker_class)
