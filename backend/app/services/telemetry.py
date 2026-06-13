import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Try importing opentelemetry, handle gracefully if not available
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter, BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.semconv.resource import ResourceAttributes
    
    # Configure tracer provider with resource
    resource = Resource(attributes={
        ResourceAttributes.SERVICE_NAME: "successcore-backend"
    })
    provider = TracerProvider(resource=resource)
    
    otel_logger = logging.getLogger("successcore.telemetry")
    
    class CustomLogSpanExporter(ConsoleSpanExporter):
        def export(self, spans):
            for span in spans:
                otel_logger.info(
                    f"[SPAN] Name: {span.name} | TraceID: {span.context.trace_id:032x} | "
                    f"SpanID: {span.context.span_id:016x} | ParentID: {f'{span.parent.span_id:016x}' if (span.parent and hasattr(span.parent, 'span_id') and span.parent.span_id) else 'None'} | "
                    f"Attributes: {dict(span.attributes)} | Latency: {span.end_time - span.start_time if span.end_time else 0}ns"
                )
            return super().export(spans)

    provider.add_span_processor(SimpleSpanProcessor(CustomLogSpanExporter()))
    
    # Configure OTLP Exporter if endpoint is provided
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            otel_logger.info(f"OTLP Exporter configured to push traces to {otlp_endpoint}")
        except ImportError:
            otel_logger.warning("opentelemetry-exporter-otlp not installed, skipping OTLP exporter")

    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("successcore")
    OTEL_AVAILABLE = True
except ImportError:
    tracer = None
    OTEL_AVAILABLE = False

logger = logging.getLogger("successcore.telemetry")

@asynccontextmanager
async def trace_span(span_name: str, attributes: dict = None) -> AsyncGenerator[dict, None]:
    """
    Helper async context manager to wrap spans and yield a dict where code can record additional details
    or trace/span IDs.
    """
    span_data = {
        "trace_id": "00000000000000000000000000000000",
        "span_id": "0000000000000000"
    }
    
    if OTEL_AVAILABLE and tracer:
        with tracer.start_as_current_span(span_name) as span:
            if attributes:
                for k, v in attributes.items():
                    span.set_attribute(k, str(v) if v is not None else "")
            
            ctx = span.get_span_context()
            span_data["trace_id"] = f"{ctx.trace_id:032x}"
            span_data["span_id"] = f"{ctx.span_id:016x}"
            
            try:
                yield span_data
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                raise
    else:
        logger.debug(f"[Telemetry MOCK] Start span {span_name} | Attributes: {attributes}")
        yield span_data
        logger.debug(f"[Telemetry MOCK] End span {span_name}")
