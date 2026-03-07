# gunicorn.conf.py

# Basic Gunicorn settings
bind = "0.0.0.0:8000"
workers = 2

# The logging configuration dictionary
logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "otel_handler": {
            # Notice the "()" syntax from our previous fix!
            "()": "util.metrics.otel.get_otel_logging_handler", 
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
