"""
Wallet Service with Paystack Integration
FastAPI Application Entry Point
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from src.db.session import close_db, init_db
from src.routes.api_key_routes import router as keys_router
from src.routes.auth_routes import router as auth_router
from src.routes.wallet_routes import router as wallet_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("app.log")],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    logger.info("Starting up wallet service...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        raise

    yield

    logger.info("Shutting down wallet service...")
    try:
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {str(e)}", exc_info=True)


app = FastAPI(
    title="Wallet Service API",
    description="Wallet service with Paystack, JWT & API Keys",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "super-secret-session-key"),
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to catch unhandled exceptions
    Logs error and returns generic error message to client
    """
    logger.error(
        f"Unhandled exception: {str(exc)} - Path: {request.url.path}", exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal error occurred. Please try again later.",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(keys_router, prefix="/keys", tags=["API Keys"])
app.include_router(wallet_router, prefix="/wallet", tags=["Wallet"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Wallet Service API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
