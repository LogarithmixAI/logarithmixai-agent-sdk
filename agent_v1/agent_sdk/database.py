import time
from sqlalchemy import event
from .queue import EventQueue

def install_sqlalchemy_monitor(engine):

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        duration = time.time() - context._query_start_time

        EventQueue.push({
            "type": "DB_QUERY",
            "query": statement[:200],  # limit length
            "duration": duration
        })
