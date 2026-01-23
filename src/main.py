"""
Main FastAPI application.
"""
from dotenv import load_dotenv

# Carrega variáveis de ambiente ANTES de qualquer outro import que use settings
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .modules.conversation.api import conversations
from .modules.channels.twilio.api import webhooks
from .core.utils import configure_logging, get_logger
from .core.config import settings
from .core.di.container import Container

configure_logging()
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
app = FastAPI(
    title="Owner API",
    description="Multi-tenant conversation management system with Twilio integration",
    version="3.1.0",
    lifespan=lifespan,
    debug=settings.api.debug
)

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
app.include_router(conversations.router)
app.include_router(webhooks.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Owner API",
        "version": "3.1.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "owner-api"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.debug
    )
