from contextvars import ContextVar
from typing import Optional

trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
trace_source_var: ContextVar[Optional[str]] = ContextVar('trace_source', default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
request_source_var: ContextVar[Optional[str]] = ContextVar('request_source', default=None)
order_id_var: ContextVar[Optional[str]] = ContextVar('order_id', default=None)


def set_trace_context(
    trace_id: Optional[str] = None,
    trace_source: Optional[str] = None,
    request_id: Optional[str] = None,
    request_source: Optional[str] = None,
    order_id: Optional[str] = None
):
    if trace_id:
        trace_id_var.set(trace_id)
    if trace_source:
        trace_source_var.set(trace_source)
    if request_id:
        request_id_var.set(request_id)
    if request_source:
        request_source_var.set(request_source)
    if order_id:
        order_id_var.set(order_id)


def get_trace_context() -> dict:
    return {
        'trace_id': trace_id_var.get(),
        'trace_source': trace_source_var.get(),
        'request_id': request_id_var.get(),
        'request_source': request_source_var.get(),
        'order_id': order_id_var.get()
    }


def clear_trace_context():
    trace_id_var.set(None)
    trace_source_var.set(None)
    request_id_var.set(None)
    request_source_var.set(None)
    order_id_var.set(None)

