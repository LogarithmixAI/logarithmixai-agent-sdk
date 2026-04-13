import time
import threading

from sqlalchemy import event
from .event_builder import build_event
from .queue import EventQueue
from .context import get_trace_id
from .sanitizer import SanitizerEngine
from .span_context import start_span, end_span
from .span_event import build_span_event

# 🔐 sanitizer
sanitizer = SanitizerEngine()


def extract_query_type(statement):
    if not statement:
        return "UNKNOWN"
    return statement.strip().split()[0].upper()


def extract_table_name(statement):
    try:
        tokens = statement.strip().split()

        # handle SELECT, INSERT, UPDATE, DELETE
        if tokens[0].upper() == "SELECT":
            if "FROM" in [t.upper() for t in tokens]:
                idx = [t.upper() for t in tokens].index("FROM")
                return tokens[idx + 1]

        elif tokens[0].upper() in ("INSERT", "UPDATE", "DELETE"):
            return tokens[2]

    except Exception:
        pass

    return "UNKNOWN"


def install_sqlalchemy_monitor(engine):

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._span = start_span("db_query", "DB")
        context._query_start_time = time.time()

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):


        duration_ms = int(
            (time.time() - getattr(context, "_query_start_time", time.time())) * 1000
        )

        query_type = extract_query_type(statement)
        table = extract_table_name(statement)


        # 🔐 sanitize parameters (important)
        safe_params = sanitizer.sanitize(parameters) if parameters else None

        event_obj = build_event(
            event_type="DB_QUERY",
            category="DATABASE",
            status="SUCCESS",
            metrics={
                "duration_ms": duration_ms,
                "rowcount": getattr(cursor, "rowcount", None)
            },
            data={
                "query_type": query_type,
                "table": table,
                "executemany": executemany,
                "params": safe_params,
                "thread": threading.current_thread().name,
            }
        )

        span = end_span({"table": table})
        EventQueue.push(build_span_event(span))
        EventQueue.push(event_obj)

    @event.listens_for(engine, "handle_error")
    def handle_error(context):

        duration_ms = 0
        if hasattr(context, "_query_start_time"):
            duration_ms = int(
                (time.time() - context._query_start_time) * 1000
            )

        query_type = extract_query_type(context.statement)
        table = extract_table_name(context.statement)


        # 🔐 sanitize message
        error_message = sanitizer.mask_by_pattern(str(context.original_exception))

        event_obj = build_event(
            event_type="DB_ERROR",
            category="DATABASE",
            status="FAILURE",
            metrics={
                "duration_ms": duration_ms
            },
            data={
                "query_type": query_type,
                "table": table,
                "exception_type": type(context.original_exception).__name__,
                "message": error_message,
                "thread": threading.current_thread().name,
            }
        )

        EventQueue.push(event_obj)