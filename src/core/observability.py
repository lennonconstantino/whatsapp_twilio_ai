from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from .config import settings
from .utils import get_logger

logger = get_logger(__name__)

def setup_observability(app=None):
    """
    Sets up OpenTelemetry observability.
    """
    if not settings.otel.exporter_otlp_endpoint:
        logger.info("OTEL_EXPORTER_OTLP_ENDPOINT not set. Skipping OpenTelemetry setup.")
        return

    logger.info(f"Setting up OpenTelemetry for service: {settings.otel.service_name}")

    resource = Resource.create({
        SERVICE_NAME: settings.otel.service_name,
        SERVICE_VERSION: "4.1.0", # Hardcoded to match main.py for now
    })

    # Trace Provider
    provider = TracerProvider(resource=resource)
    
    # OTLP Exporter
    # Note: endpoint usually comes as http://host:port, but grpc exporter might expect host:port
    # The library handles parsing often, but let's be safe.
    endpoint = settings.otel.exporter_otlp_endpoint.replace("http://", "").replace("https://", "")
    
    otlp_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    
    # Span Processor
    processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(processor)
    
    # Set global TracerProvider
    trace.set_tracer_provider(provider)

    # Instrumentations
    # LoggingInstrumentor().instrument(set_logging_format=True) # structlog handles formatting, skipping to avoid mess
    HTTPXClientInstrumentor().instrument()
    RequestsInstrumentor().instrument()

    if app:
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    
    logger.info("OpenTelemetry setup complete.")
