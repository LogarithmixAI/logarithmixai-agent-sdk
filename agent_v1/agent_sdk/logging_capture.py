import logging
import traceback
from .queue import EventQueue

_installed = False


class SDKLogHandler(logging.Handler):
    def emit(self, record):
        try:
            log_entry = {
                "type": "LOG",
                "level": record.levelname,
                "message": record.getMessage(),
                "logger": record.name,
                "file": record.pathname,
                "line": record.lineno,
            }

            # If exception info present
            if record.exc_info:
                log_entry["exception"] = "".join(
                    traceback.format_exception(*record.exc_info)
                )

            EventQueue.push(log_entry)

        except Exception:
            # NEVER break client logging
            pass


def install_logging(level=logging.ERROR):
    global _installed

    if _installed:
        return

    handler = SDKLogHandler()
    handler.setLevel(level)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    _installed = True
