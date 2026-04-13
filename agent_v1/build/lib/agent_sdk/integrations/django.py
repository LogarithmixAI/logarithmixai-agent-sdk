import time
from ..queue import EventQueue
from ..metrics import EndpointMetrics

class AgentDjangoMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        try:
            response = self.get_response(request)
            duration = time.time() - start_time

            EventQueue.push({
                "type": "INCOMING_REQUEST",
                "framework": "django",
                "path": request.path,
                "method": request.method,
                "status": response.status_code,
                "duration": duration
            })
            EndpointMetrics.record(
                path=request.path,
                status=response.status_code,
                duration=duration
            )
            return response

        except Exception as e:
            duration = time.time() - start_time

            EventQueue.push({
                "type": "DJANGO_ERROR",
                "path": request.path,
                "method": request.method,
                "message": str(e),
                "duration": duration
            })

            raise e


def init_django():
    """
    Django middleware must be added manually to settings.py
    """
    pass
