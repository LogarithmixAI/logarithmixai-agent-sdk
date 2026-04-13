import sys
import traceback
from .queue import EventQueue

class ExceptionTracker:
    @staticmethod
    def install():
        sys.excepthook = ExceptionTracker.handle

    @staticmethod
    def handle(exc_type, exc, tb):
        EventQueue.push({
            "type": "EXCEPTION",
            "error_type": exc_type.__name__,
            "message": str(exc),
            "stacktrace": "".join(traceback.format_tb(tb))
        })

