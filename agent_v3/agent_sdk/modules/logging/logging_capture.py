import logging
import traceback
import re
import threading

from agent_sdk.core.sanitizer import SanitizerEngine
from agent_sdk.core.pipeline import Pipeline
from agent_sdk.config.setting import AgentConfig

pipeline = Pipeline()
DEBUG = AgentConfig().DEBUG

# 🔐 sanitizer engine (reuse)
sanitizer = SanitizerEngine()

def classify_log(message, level):

    msg = (message or "").lower()

    # 🔴 infra / network
    if "timeout" in msg:
        return "LOG_TIMEOUT"

    if "connection refused" in msg or "connection error" in msg:
        return "LOG_CONNECTION_ERROR"

    # 🔴 database
    if "deadlock" in msg:
        return "LOG_DB_DEADLOCK"

    if "duplicate" in msg or "constraint" in msg:
        return "LOG_DB_INTEGRITY"

    # 🔴 auth
    if "unauthorized" in msg or "token" in msg:
        return "LOG_AUTH_ERROR"

    if "permission denied" in msg:
        return "LOG_PERMISSION_DENIED"

    # 🔴 code issues
    if level >= logging.CRITICAL:
        return "LOG_CRITICAL"

    if level >= logging.ERROR:
        return "LOG_ERROR"

    if level >= logging.WARNING:
        return "LOG_WARNING"

    return "LOG_INFO"


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
            if record.name == "werkzeug" and not DEBUG:
                return

            stacktrace = None
            if record.exc_info:
                stacktrace = "".join(
                    traceback.format_exception(*record.exc_info)
                )[:500]
                stacktrace = sanitizer.mask_by_pattern(stacktrace)

            message = sanitize_message(record.getMessage())

            event_type = classify_log(message, record.levelno)

            exception_type = None
            if record.exc_info and record.exc_info[0]:
                exception_type = record.exc_info[0].__name__

            pipeline.process(
                event_type=event_type,
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
                    "exception_type": exception_type,
                    "has_stacktrace": bool(stacktrace),
                }
            )

        except Exception as e:
            print(f"Error in log instrumentation: {e}")
            traceback.print_exc()


def install_logging(level=logging.INFO):

    root_logger = logging.getLogger()

    # ⚠️ avoid duplicate handlers
    for h in root_logger.handlers:
        if isinstance(h, AgentLogHandler):
            return

    handler = AgentLogHandler()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)