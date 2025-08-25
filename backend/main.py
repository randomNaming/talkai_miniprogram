"""
TalkAI Mini Program Backend
Main application entry point
"""
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.core.config import settings, get_log_path
from app.core.database import create_tables
from app.api.v1.auth import router as auth_router
from app.api.v1.dict import router as dict_router
from app.api.v1.chat import router as chat_router
from app.api.v1.vocab import router as vocab_router
from app.api.v1.learning_vocab import router as learning_vocab_router
from app.api.v1.user import router as user_router
from app.api.v1.sync import router as sync_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting TalkAI Backend...")
    
    # Configure logging
    logger.add(
        get_log_path(),
        rotation="1 day",
        retention="30 days",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    )
    
    # Create database tables
    try:
        create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    
    # Copy dictionary database if needed
    await setup_dictionary_db()
    
    # Start learning analysis scheduler
    from app.services.learning_analysis import start_learning_analysis_scheduler
    await start_learning_analysis_scheduler()
    
    logger.info("TalkAI Backend started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down TalkAI Backend...")


async def setup_dictionary_db():
    """Setup dictionary database"""
    import shutil
    from pathlib import Path
    
    # Source dictionary path from original project
    source_dict = Path("../dictionary400k.db")
    target_dict = Path(settings.dictionary_db_path)
    
    # Create directory if not exists
    target_dict.parent.mkdir(parents=True, exist_ok=True)
    
    # Copy dictionary if not exists
    if source_dict.exists() and not target_dict.exists():
        try:
            shutil.copy2(source_dict, target_dict)
            logger.info(f"Dictionary database copied to {target_dict}")
        except Exception as e:
            logger.warning(f"Failed to copy dictionary database: {e}")
    elif target_dict.exists():
        logger.info(f"Dictionary database already exists at {target_dict}")
    else:
        logger.warning(f"Dictionary database not found at {source_dict}")


# Create FastAPI app
app = FastAPI(
    title="TalkAI API",
    description="English Learning Assistant with AI-powered conversation and grammar correction",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware for production
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure this properly for production
    )

# Include API routers
api_prefix = f"/api/{settings.api_version}"

app.include_router(auth_router, prefix=f"{api_prefix}/auth", tags=["authentication"])
app.include_router(dict_router, prefix=f"{api_prefix}/dict", tags=["dictionary"])
app.include_router(chat_router, prefix=f"{api_prefix}/chat", tags=["chat"])
app.include_router(vocab_router, prefix=f"{api_prefix}/vocab", tags=["vocabulary"])
app.include_router(learning_vocab_router, prefix=f"{api_prefix}/learning-vocab", tags=["learning-vocabulary"])
app.include_router(user_router, prefix=f"{api_prefix}/user", tags=["user"])
app.include_router(sync_router, prefix=f"{api_prefix}/sync", tags=["synchronization"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "TalkAI API",
        "version": "1.0.0",
        "status": "running",
        "docs_url": "/docs" if settings.debug else None
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )