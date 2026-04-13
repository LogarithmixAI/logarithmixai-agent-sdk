import time
from flask import request, g
from ..queue import EventQueue
from ..metrics import EndpointMetrics

def init_flask(app):

    @app.before_request
    def start_timer():
        g._agent_start_time = time.time()

    @app.after_request
    def log_request(response):
        try:
            duration = time.time() - g._agent_start_time
            
            EventQueue.push({
                "type": "INCOMING_REQUEST",
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

        except Exception:
            pass

        return response

    @app.errorhandler(Exception)
    def handle_error(e):
        EventQueue.push({
            "type": "FLASK_ERROR",
            "message": str(e),
            "path": request.path
        })
        raise e

