"""
FastAPI application entry point.

Main application setup with lifespan events, router registration,
and health check endpoints.
"""
import sys
from pathlib import Path
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

# Add project root to Python path (for imports from kök dizin)
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modules.video_processor_agent.core.config import settings
from modules.video_processor_agent.core.database import db
from modules.video_processor_agent.routers import analysis, llm_data

# Logger setup (no global basicConfig)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events:
    - Startup: Connect to MongoDB
    - Shutdown: Close MongoDB connection
    """
    # Startup: Connect to DB
    logger.info("ViralFlow Backend starting...")
    
    try:
        await db.connect()
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        # Re-raise to prevent app from starting with broken DB connection
        raise
    
    yield
    
    # Shutdown: Close DB
    logger.info("Shutting down...")
    
    try:
        await db.close()
        logger.info("Application shutdown completed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)
        # Don't re-raise during shutdown - just log the error


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="High-performance viral marketing agent that analyzes videos sequentially",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Register Routers
app.include_router(
    analysis.router,
    prefix=settings.API_V1_STR,
    tags=["Analysis"]
)

app.include_router(
    llm_data.router,
    prefix=settings.API_V1_STR,
    tags=["LLM Data"]
)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """
    Root endpoint - API information.
    
    Returns:
        API welcome message and documentation links
    """
    return {
        "message": "Welcome to ViralFlow Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "status": "active"
    }


@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    """
    Health check endpoint.
    
    Checks:
    - Database connection status
    
    Returns:
        Health status with HTTP 200 if healthy, 503 if unhealthy
    """
    try:
        # Check database connection
        is_healthy = await db.ping()
        
        if is_healthy:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "healthy",
                    "database": "connected",
                    "service": settings.PROJECT_NAME
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "database": "disconnected",
                    "service": settings.PROJECT_NAME
                }
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "service": settings.PROJECT_NAME
            }
        )


if __name__ == "__main__":
    import uvicorn
    
    # Run server locally
    uvicorn.run(
        "modules.video_processor_agent.video_processor:app",
        host="0.0.0.0",
        port=8001,  # Video processor uses port 8001
        reload=True,
        reload_excludes=["test_*.py", "check_*.py"],
        log_level="info"
    )
