from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

from langfuse import Langfuse
from .state import RuntimeContext


class TraceProxy:
    """
    Fallback trace object used when Langfuse is unavailable
    or trace creation fails.
    """

    def __init__(self, trace_id: str | None = None):
        self.id = trace_id or "local-trace"

    def span(self, *args, **kwargs):
        return self

    def generation(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return None

    def end(self, *args, **kwargs):
        return None


class SpanProxy:
    """
    Fallback span object when Langfuse is unavailable.
    """
    
    def __init__(self, span_id: str = "local-span"):
        self.id = span_id
    
    def update(self, *args, **kwargs):
        return None
    
    def end(self, *args, **kwargs):
        return None


def get_langfuse_client() -> Optional[Langfuse]:
    """
    Returns Langfuse client if env vars are present, otherwise None.
    """
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    host = os.environ.get("LANGFUSE_HOST")

    if not public_key or not secret_key:
        return None

    try:
        return Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
    except Exception:
        return None


def create_langfuse_trace(
    job_data: Dict[str, Any],
    context: RuntimeContext
):
    """
    Creates a Langfuse trace with fallback to TraceProxy.
    """

    client = get_langfuse_client()

    if client is None:
        return TraceProxy()

    try:
        # type: ignore[attr-defined] because Langfuse SDK is weakly typed
        return client.trace(
            name="refactor_workflow",
            user_id="user-placeholder",
            session_id=context.run_id,
            metadata=job_data,
        )
    except Exception:
        # fallback if Langfuse is misconfigured or request fails
        return TraceProxy()


@asynccontextmanager
async def create_span(trace, name: str, metadata: Optional[Dict[str, Any]] = None):
    """
    Context manager for creating and ending Langfuse spans.
    
    Usage:
        async with create_span(trace, "generate", {"iteration": 1}) as span:
            # do work
            span.update(output={"code": "..."})
    """
    start_time = time.time()
    
    if hasattr(trace, 'span'):
        try:
            span = trace.span(
                name=name,
                metadata=metadata or {},
            )
        except Exception:
            span = SpanProxy()
    else:
        span = SpanProxy()
    
    try:
        yield span
    finally:
        elapsed = time.time() - start_time
        try:
            if hasattr(span, 'end'):
                span.end(metadata={"duration_seconds": elapsed})
        except Exception:
            pass
