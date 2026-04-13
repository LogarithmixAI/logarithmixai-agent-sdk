import threading


class EventQueue:

    _queue = []
    _lock = threading.Lock()

    @classmethod
    def push(cls, event):
        with cls._lock:
            cls._queue.append(event)

    @classmethod
    def flush(cls):
        with cls._lock:
            batch = cls._queue[:]
            cls._queue.clear()
        return batch
