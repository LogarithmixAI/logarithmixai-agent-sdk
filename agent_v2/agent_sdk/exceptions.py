import sys
import traceback
import threading
import time

from .event_builder import build_event
from .queue import EventQueue
from .context import get_trace_id
from .sanitizer import SanitizerEngine



# 🔥 globals (dedup + rate limit)
_recent_errors = set()
_last_exception_time = 0

# 🔐 sanitizer instance (reuse)
sanitizer = SanitizerEngine()


class ExceptionTracker:

    @staticmethod
    def install():
        sys.excepthook = ExceptionTracker.handle_exception
        print("ExceptionTracker installed: global exception hook set.") 
        # Python 3.8+ thread exception support
        if hasattr(threading, "excepthook"):
            threading.excepthook = ExceptionTracker.handle_thread_exception

    @staticmethod
    def handle_exception(exc_type, exc_value, exc_traceback):
        print("🔥 excepthook triggered")
        try:
            ExceptionTracker._process_exception(
                exc_type,
                exc_value,
                exc_traceback,
                handled=False
            )
        except Exception:
            print("Error in exception handler:", file=sys.stderr)
            traceback.print_exc()   

    @staticmethod
    def handle_thread_exception(args):
        print("🔥 thread exception triggered")
        try:
            ExceptionTracker._process_exception(
                args.exc_type,
                args.exc_value,
                args.exc_traceback,
                handled=False
            )
        except Exception:
            print("Error in thread exception handler:", file=sys.stderr)
            traceback.print_exc()

    @staticmethod
    def _process_exception(exc_type, exc_value, exc_traceback, handled):

        global _last_exception_time

        # ❌ ignore system exit events
        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            return

        # ⏱️ rate limiting (avoid spam)
        now = time.time()
        if now - _last_exception_time < 1:   # 1 sec window
            return
        _last_exception_time = now

        # 🔁 deduplication
        error_key = f"{exc_type.__name__}:{str(exc_value)}"
        if error_key in _recent_errors:
            return
        _recent_errors.add(error_key)

        # 📜 stacktrace
        stack = "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )

        # 🔐 sanitize stacktrace (important)
        stack = sanitizer.mask_by_pattern(stack)

        # 📍 last frame info
        last_trace = traceback.extract_tb(exc_traceback)[-1] if exc_traceback else None

        file_name = last_trace.filename if last_trace else None
        line_number = last_trace.lineno if last_trace else None
        function_name = last_trace.name if last_trace else None

        payload = {
            "error_type": exc_type.__name__,
            "message": str(exc_value),
            "file": file_name,
            "line": line_number,
            "function": function_name,
            "thread": threading.current_thread().name,
            "stacktrace": stack,
            "handled": handled,
          }

        event = build_event(
            event_type="EXCEPTION",
            category="APPLICATION",
            status="FAILURE",
            data=payload,
            metrics={}
        )

        EventQueue.push(event)

