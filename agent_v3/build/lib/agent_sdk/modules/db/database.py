import time
import threading
import sqlite3
from agent_sdk.core.sanitizer import SanitizerEngine
from agent_sdk.core.pipeline import Pipeline
from agent_sdk.modules.db.sqlite_monitor import install_sqlite3_monitor

try:
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
except Exception:
    event = None
    Engine = None

# 🔐 sanitizer
sanitizer = SanitizerEngine()
pipeline = Pipeline()

_original_execute = None
_original_executemany = None

def classify_db(duration, error, exception_type=None, message=None,
                slow_threshold=500, timeout_threshold=4000):

    is_slow = duration and duration >= slow_threshold
    is_timeout = duration and duration >= timeout_threshold

    msg = (message or "").lower()
    exc = (exception_type or "").lower()

    # 🔴 1. Timeout
    if is_timeout or "timeout" in msg:
        return "DB_TIMEOUT"

    # 🔴 2. Deadlock
    if "deadlock" in msg:
        return "DB_DEADLOCK"

    # 🔴 3. Connection issues
    if any(x in msg for x in ["connection refused", "could not connect", "connection error"]):
        return "DB_CONNECTION_FAILED"

    # 🔴 4. Integrity issues
    if "integrity" in exc or "duplicate" in msg or "constraint" in msg:
        return "DB_INTEGRITY_ERROR"

    # 🔴 5. Syntax / programming
    if "syntax" in msg or "programmingerror" in exc:
        return "DB_SYNTAX_ERROR"

    # 🔴 6. Generic failure
    if error:
        if is_slow:
            return "DB_SLOW_FAILURE"
        return "DB_FAILED"

    # 🟢 7. Success
    if is_slow:
        return "DB_SLOW"

    return "DB_SUCCESS"

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


def install_db_monitor(db_engine=None):

    # 🔴 Case 1: SQLAlchemy engine passed
    if db_engine and Engine and isinstance(db_engine, Engine):
        print("[SDK] SQLAlchemy detected → installing monitor")
        install_sqlalchemy_monitor(db_engine)
        return "sqlalchemy"

    # 🔴 Case 2: sqlite3 fallback (auto patch)
    try:
        print("[SDK] No SQLAlchemy engine → using sqlite3 patch")
        install_sqlite3_monitor()
        return "sqlite3"
    except Exception as e:
        print(f"[SDK] DB monitor install failed: {e}")
        return None

def install_sqlalchemy_monitor(engine):
    if event is None:
        raise RuntimeError("SQLAlchemy monitoring requested but SQLAlchemy is not installed")

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time() 
        pipeline.start("Database_operation", "db_query") # start db query span

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):

        duration_ms = int((time.time() - context._query_start_time) * 1000)
        query_type = extract_query_type(statement)
        table = extract_table_name(statement)

        # 🔐 sanitize parameters (important)
        safe_params = sanitizer.sanitize(parameters) if parameters else None

        event_type = classify_db(duration_ms, error=False)

        pipeline.process(
            event_type = event_type,
            category="DATABASE",
            status="SUCCESS" if event_type == "DB_SUCCESS" else "WARNING",
            metrics={
                "rowcount": getattr(cursor, "rowcount", None)
            },
            data={
                "query_type": query_type,
                "table": table,
                "executemany": executemany,
                "params": safe_params,
                "thread": threading.current_thread().name,
                "is_slow": duration_ms >= 500,
                "is_timeout": duration_ms >= 4000
            }
        )

        pipeline.end(
            span_extra_data={
                "query_type": query_type,
                "table": table,
                "duration_ms": duration_ms,
                "rowcount": getattr(cursor, "rowcount", None),
                "is_slow": duration_ms >= 500,
            }
        ) # end db_query span

    @event.listens_for(engine, "handle_error")
    def handle_error(context):
        duration_ms = int((time.time() - context._query_start_time) * 1000) if hasattr(context, "_query_start_time") else None
        query_type = extract_query_type(context.statement)
        table = extract_table_name(context.statement)

        # 🔐 sanitize message
        error_message = sanitizer.mask_by_pattern(str(context.original_exception))
        exception_type = type(context.original_exception).__name__

        event_type = classify_db(
            duration=duration_ms,
            error=True,
            exception_type=exception_type,
            message=error_message
        )

        pipeline.process(
            event_type=event_type,
            category="DATABASE",
            status="FAILURE",
            metrics={},
            data={
                "query_type": query_type,
                "table": table,
                "exception_type": type(context.original_exception).__name__,
                "message": error_message,
                "thread": threading.current_thread().name,
                "is_slow": duration_ms and duration_ms >= 500,
                "is_timeout": duration_ms and duration_ms >= 4000
            }
        )


        pipeline.end(
            span_extra_data={
                "query_type": query_type,
                "table": table,
                "duration_ms": duration_ms,
                "exception_type": exception_type,
                "error": True
            }
        ) # end db_query span

