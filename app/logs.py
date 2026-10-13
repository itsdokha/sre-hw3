import json
import logging
import os
import sys
from datetime import datetime, timezone


SERVICE_NAME = os.environ.get("SERVICE_NAME", "tasks-app")
SERVICE_VERSION = os.environ.get("SERVICE_VERSION", "local")
ENVIRONMENT = os.environ.get("DEPLOYMENT_ENVIRONMENT", "local")

# Атрибуты, которые есть у любой LogRecord; всё остальное пришло через extra=.
_STANDARD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """Одна запись лога — одна строка JSON в stdout."""

    def format(self, record):
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "message": record.getMessage(),
            "service.name": SERVICE_NAME,
            "service.version": SERVICE_VERSION,
            "deployment.environment": ENVIRONMENT,
            "logger": record.name,
        }
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                entry[key] = value
        if record.exc_info:
            entry["error.type"] = record.exc_info[0].__name__
            entry["error.stack"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())


# Конфиг для gunicorn (gunicorn.conf.py): его собственные логи тоже в JSON.
GUNICORN_LOGCONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": JsonFormatter}},
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        }
    },
    # gunicorn делает неглубокий update своих дефолтов, поэтому root задаём явно.
    "root": {"handlers": ["stdout"], "level": "INFO"},
    "loggers": {
        "gunicorn.error": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
        "gunicorn.access": {"handlers": [], "propagate": False},
    },
}
