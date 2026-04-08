import time
from .queue import EventQueue

def monitor(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            EventQueue.push({
                "type": "PERFORMANCE",
                "function": func.__name__,
                "duration": time.time() - start
            })
    return wrapper
