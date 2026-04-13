import logging
import traceback
import re
import threading

from .event_builder import build_event
from .queue import EventQueue
from .context import get_trace_id
from .sanitizer import SanitizerEngine


LOG_LEVEL_SEVERITY = {
    logging.DEBUG: "LOW",
    logging.INFO: "LOW",
    logging.WARNING: "MEDIUM",
    logging.ERROR: "HIGH",
    logging.CRITICAL: "CRITICAL",
}

# 🔐 sanitizer engine (reuse)
sanitizer = SanitizerEngine()


# ✅ message sanitizer (IP + truncate + pattern)
def sanitize_message(msg: str):
    try:
        msg = str(msg)

        # mask IPv4
        msg = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "x.x.x.x", msg)

        # 🔐 pattern-based masking (email/token etc.)
        msg = sanitizer.mask_by_pattern(msg)

        return msg[:500]

    except Exception:
        return "log_sanitization_failed"


class AgentLogHandler(logging.Handler):

    def emit(self, record):

        try:
            # ❌ ignore noisy logs (extendable)
            if record.name == "werkzeug":
                return

            # 🧠 severity
            severity = LOG_LEVEL_SEVERITY.get(record.levelno, "LOW")


            # 📜 stacktrace
            stacktrace = None
            if record.exc_info:
                stacktrace = "".join(
                    traceback.format_exception(*record.exc_info)
                )[:1000]

                # 🔐 sanitize stacktrace
                stacktrace = sanitizer.mask_by_pattern(stacktrace)

            # 🧾 message
            message = sanitize_message(record.getMessage())

            event = build_event(
                event_type="LOG",
                category="APPLICATION",
                status="FAILURE" if record.levelno >= logging.ERROR else "SUCCESS",
                metrics={},
                data={
                    "logger_name": record.name,
                    "level": record.levelname,
                    "message": message,
                    "file": record.pathname,
                    "line": record.lineno,
                    "function": record.funcName,
                    "thread": threading.current_thread().name,
                }
            )

            # override severity
            event["event"]["severity"] = severity

            EventQueue.push(event)

        except Exception:
            pass


def install_logging(level=logging.WARNING):

    root_logger = logging.getLogger()

    # ⚠️ avoid duplicate handlers
    for h in root_logger.handlers:
        if isinstance(h, AgentLogHandler):
            return

    handler = AgentLogHandler()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)