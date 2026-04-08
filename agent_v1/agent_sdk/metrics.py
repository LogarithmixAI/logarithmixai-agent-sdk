import time
import threading
from collections import defaultdict


class EndpointMetrics:

    _lock = threading.Lock()
    _data = defaultdict(lambda: {
        "total": 0,
        "errors": 0,
        "total_duration": 0.0
    })

    @classmethod
    def record(cls, path, status, duration):
        with cls._lock:
            cls._data[path]["total"] += 1
            cls._data[path]["total_duration"] += duration

            if status >= 400:
                cls._data[path]["errors"] += 1

    @classmethod
    def snapshot(cls):
        with cls._lock:
            snapshot = dict(cls._data)
            cls._data.clear()
        return snapshot
