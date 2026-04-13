import time
import requests
from urllib.parse import urlparse
from .queue import EventQueue
from .config import AgentConfig

_original_request = None


def install_http_patch():
    global _original_request

    if _original_request is not None:
        return  # Already patched

    _original_request = requests.Session.request

    def patched_request(self, method, url, **kwargs):

        # 🔥 1️⃣ Ignore SDK internal endpoint
        if AgentConfig.endpoint:
            try:
                if urlparse(url).netloc == urlparse(AgentConfig.endpoint).netloc:
                    return _original_request(self, method, url, **kwargs)
            except Exception:
                pass

        start = time.time()

        try:
            response = _original_request(self, method, url, **kwargs)
            duration = time.time() - start

            EventQueue.push({
                "type": "HTTP_CALL",
                "method": method,
                "url": url,
                "status": response.status_code,
                "duration": duration
            })

            return response

        except Exception as e:
            duration = time.time() - start

            EventQueue.push({
                "type": "HTTP_EXCEPTION",
                "method": method,
                "url": url,
                "message": str(e),
                "duration": duration
            })

            raise

    requests.Session.request = patched_request


# Optional manual wrapper (still supported)
def monitored_request(method, url, **kwargs):
    start = time.time()
    try:
        response = requests.request(method, url, **kwargs)
        duration = time.time() - start

        if response.status_code >= 400:
            EventQueue.push({
                "type": "HTTP_ERROR",
                "method": method,
                "url": url,
                "status": response.status_code,
                "duration": duration
            })

        return response

    except Exception as e:
        duration = time.time() - start

        EventQueue.push({
            "type": "HTTP_EXCEPTION",
            "method": method,
            "url": url,
            "message": str(e),
            "duration": duration
        })
        raise
