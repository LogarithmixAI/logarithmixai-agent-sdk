from agent_sdk.core.event_builder import build_event
from agent_sdk.transport.queue import EventQueue
from agent_sdk.core.span.trace_summary_event import build_trace_event
from agent_sdk.core.context import Trace
from agent_sdk.core.span.span_engine import SpanEngine
from contextvars import ContextVar
# from rich import print_json
import json

_pipeline_ctx = ContextVar("pipeline_ctx", default=None)

import time


class Pipeline:

    def __init__(self):
        self.engine = SpanEngine()
        _pipeline_ctx.set(False)

    # ----------------------------
    # 🔥 TRACE CONTROL
    # ----------------------------

    def create_trace(self, reset=False):
        current_trace = Trace.get()

        if reset:

            if current_trace:
                # print("MESSAGE: Active trace found in reset Mode. Clearing and creating new trace.")
                self.clear_trace()
                Trace.create()
                return
            # print("MESSAGE: No active trace found in reset Mode. Creating new trace.")
            Trace.create()
        
        else:
            if not current_trace:
                Trace.create()
                _pipeline_ctx.set(True)
    

    def clear_trace(self, force_clear=False):
        current_trace = Trace.get()
        if current_trace and _pipeline_ctx.get():
            # print("MESSAGE: Clearing trace at own pipeline's request.")
            ## for debugging: print trace graph before clearing

            graph = self.engine._get_graph()
            if not graph:
                # print("No graph found to clear.")
                pass

            else:
                # print(json.dumps(graph.to_dict(), indent=2))
                trace_summary_event = build_trace_event(graph.to_dict())
                trace_summary_event["event"]["context_mode"] = "trace_summary"
                self._dispatch(trace_summary_event)

            # print("MESSAGE: Clearing trace context.")
            self.engine.clear()
            _pipeline_ctx.set(False)

        elif current_trace and force_clear:

            graph = self.engine._get_graph()
            if not graph:
                # print("No graph found to clear.")
                pass

            else:

               # print(json.dumps(graph.to_dict(), indent=2))
                trace_summary_event = build_trace_event(graph.to_dict())
                trace_summary_event["event"]["context_mode"] = "trace_summary"
                self._dispatch(trace_summary_event)

            # # print("MESSAGE: Forcing clear of main trace context.")
            self.engine.clear()

    # ----------------------------
    # 🔥 START SPAN
    # ----------------------------
    def start(self, name, span_type):

        # 🔥 ensure trace exists
        if not Trace.get():
            Trace.create()

        span = self.engine.add_span(name, span_type)
        self.engine.start_span()

        return span

    # ----------------------------
    # 🔥 PROCESS EVENT (multi-safe)
    # ----------------------------
    def process(
        self,
        event_type,
        category,
        status,
        data,
        metrics=None,
        span_extra_data=None,
        severity=None
    ):

        try:
            event = build_event(event_type, category, status, data, metrics)

            if severity:
                event['event']['severity'] = severity

            # 🔥 attach to current span 
            if self.has_active_trace() :  
                span = self.engine.get_current_span()

            else:
                event["event"]["span_id"] = None
                event["event"]["context_mode"] = "standalone"
                event["event"]["metrics"]["duration_ms"] = None
                event["event"]["metrics"]["duration_us"] = None
                self._dispatch(event)
                return

            duration = (time.time() - span.start_time) * 1000

            event['event']["metrics"]["duration_ms"] = round(duration, 3)
            event['event']["metrics"]["duration_us"] = int(duration*1000)
            event['event']["span_id"] = span.span_id
            event["event"]["context_mode"] = "trace"

            span.event_ids.append( event.get("event", {}).get("event_id") )
            if event.get("event", {}).get("type") != "REQUEST_VERDICT":
                span.event_flow.append(event.get("event", {}).get("type"))

            graph = self.engine._get_graph()
            if graph:
                parent_span = graph.get_span(span.parent_span_id) if span.parent_span_id else None
                if parent_span and event.get("event", {}).get("type") != "REQUEST_VERDICT":
                    parent_span.event_flow.append(event.get("event", {}).get("type"))



            # 🔥 optional: immediate dispatch
            self._dispatch(event)

        except Exception as e:
            print(f"[Pipeline Error]: {str(e) } | Event Type: {event_type}|data: {data}| Span: {span.name if span else 'No Span'}")

    # ----------------------------
    # 🔥 END SPAN
    # ----------------------------
    def end(self, span_extra_data=None):

        span = self.engine.end_span(span_extra_data)

        if not span:
            return
    

        return span

    # ----------------------------
    # 🔥 DISPATCH
    # ----------------------------
    def _dispatch(self, event: dict):
        EventQueue.push(event)

        
    def has_active_trace(self):
        return Trace.get() is not None

    def get_trace_id(self):
        return Trace.get()


    

    
