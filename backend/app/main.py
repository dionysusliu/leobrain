# fast api application

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import logging

from common.database import init_db
from app.api.v1 import router as api_router
from workers.scheduler_manager import get_scheduler, start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting up application...")
    init_db()
    
    # Start scheduler
    start_scheduler()
    logger.info("Scheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    stop_scheduler()
    logger.info("Scheduler stopped")


app = FastAPI(
    title="LeoBrain API",
    description="Personal Web Intelligence & ML Pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "LeoBrain API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
