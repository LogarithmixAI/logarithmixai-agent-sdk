import sqlite3
import time
import threading
import traceback

from agent_sdk.core.sanitizer import SanitizerEngine
from agent_sdk.core.pipeline import Pipeline

# reuse existing
sanitizer = SanitizerEngine()
pipeline = Pipeline()

_original_connect = None


# ----------------------------
# Helper functions (reuse yours if already defined)
# ----------------------------
def extract_query_type(statement):
    try:
        return statement.strip().split()[0].upper()
    except:
        return "UNKNOWN"


def extract_table_name(statement):
    try:
        tokens = statement.strip().split()
        if tokens[0].upper() == "SELECT":
            if "FROM" in [t.upper() for t in tokens]:
                idx = [t.upper() for t in tokens].index("FROM")
                return tokens[idx + 1]

        elif tokens[0].upper() in ("INSERT", "UPDATE", "DELETE"):
            return tokens[2]
    except:
        pass
    return "UNKNOWN"


def classify_db(duration, error, exception_type=None, message=None,
                slow_threshold=500, timeout_threshold=4000):

    if error:
        return "DB_FAILED"
    if duration and duration >= slow_threshold:
        return "DB_SLOW"
    return "DB_SUCCESS"


# ----------------------------
# Wrapper Classes
# ----------------------------

class TrackedCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, statement, parameters=None):
        start_time = time.time()
        pipeline.start("Database_operation", "db_query")

        exc = None

        try:
            return self._cursor.execute(statement, parameters or ())
        except Exception as e:
            exc = e
            raise
        finally:
            duration_ms = int((time.time() - start_time) * 1000)

            try:
                query_type = extract_query_type(statement)
                table = extract_table_name(statement)

                safe_params = sanitizer.sanitize(parameters) if parameters else None

                if exc:
                    event_type = classify_db(duration_ms, True, type(exc).__name__, str(exc))
                else:
                    event_type = classify_db(duration_ms, False)

                pipeline.process(
                    event_type=event_type,
                    category="DATABASE",
                    status="FAILURE" if exc else "SUCCESS",
                    metrics={
                        "rowcount": getattr(self._cursor, "rowcount", None)
                    },
                    data={
                        "query_type": query_type,
                        "table": table,
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
                        "rowcount": getattr(self._cursor, "rowcount", None),
                        "error": True if exc else False
                    }
                )

            except Exception as e:
                print(f"[SDK][DB] sqlite wrapper error: {e}")
                traceback.print_exc()

    def executemany(self, statement, seq_of_parameters):
        return self._cursor.executemany(statement, seq_of_parameters)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class TrackedConnection:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self, *args, **kwargs):
        return TrackedCursor(self._conn.cursor(*args, **kwargs))

    def __getattr__(self, name):
        return getattr(self._conn, name)


# ----------------------------
# Installer
# ----------------------------

def install_sqlite3_monitor():

    global _original_connect

    if _original_connect:
        return  # already installed

    _original_connect = sqlite3.connect

    def patched_connect(*args, **kwargs):
        conn = _original_connect(*args, **kwargs)
        return TrackedConnection(conn)

    sqlite3.connect = patched_connect

    print("[SDK] sqlite3 monitoring enabled (wrapper mode)")