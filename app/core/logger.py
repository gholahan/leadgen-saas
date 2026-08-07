import logging
from logging.config import dictConfig

from app.core.config import settings

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": LOG_FORMAT,
            "datefmt": LOG_DATEFMT,
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        }
    },
    "root": {
        "level": settings.LOG_LEVEL,
        "handlers": ["console"],
    },
    "loggers": {
        "uvicorn": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console"],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console"],
            "propagate": False,
        },
    },
}


def configure_logging() -> None:
    dictConfig(LOGGING_CONFIG)
    logging.getLogger(__name__).debug("Logging configured at %s", settings.LOG_LEVEL)
