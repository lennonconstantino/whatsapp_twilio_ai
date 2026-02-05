"""
Main FastAPI application.
"""

from dotenv import load_dotenv

# Carrega variáveis de ambiente ANTES de qualquer outro import que use settings
# load_dotenv() - Moved to explicit initialization or entry point check


from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.di.container import Container
from .core.utils import get_logger
from .core.observability import setup_observability
from .core.api.exception_handlers import setup_exception_handlers
from .modules.channels.twilio.api import router as twilio_router
from .modules.conversation.api import router as conversation_router
from .modules.identity.api import router as identity_router
from .modules.billing.api import router as billing_router

logger = get_logger(__name__)

# Initialize DI Container
container = Container()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting Owner API application")
    logger.info(f"API running on {settings.api.host}:{settings.api.port}")

    yield

    # Shutdown
    logger.info("Shutting down Owner API application")


# Create FastAPI app
is_production = settings.api.environment == "production"

app = FastAPI(
    title="Owner API",
    description="Multi-tenant conversation management system with Twilio integration",
    version="4.1.0",
    lifespan=lifespan,
    debug=settings.api.debug,
    docs_url=None if is_production else "/docs",
    redoc_url=None,  # Disable default Redoc to use custom CDN
    openapi_url=None if is_production else "/openapi.json",
)

# Setup Observability
setup_observability(app)

# Setup Exception Handlers
setup_exception_handlers(app)

# Attach container to app
app.container = container

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(conversation_router.router)
app.include_router(twilio_router.router)
app.include_router(identity_router.router)
app.include_router(billing_router.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"name": "Owner API", "version": "4.1.0", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "owner-api"}


if not is_production:
    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        """Redoc documentation."""
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=app.title + " - ReDoc",
            redoc_js_url="https://unpkg.com/redoc@latest/bundles/redoc.standalone.js",
        )


if __name__ == "__main__":
    load_dotenv()
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.debug,
    )
