# fast api application

from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST
from starlette.responses import Response
import time
import logging

from common.database import init_db
from common.logging_config import setup_logging
from common.metrics import get_metrics, api_requests_total, api_request_duration
from app.api.v1 import router as api_router
from workers.prefect_manager import apply_deployments

# Setup structured logging
setup_logging(level="INFO")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting up application...")
    init_db()
    
    # Apply Prefect deployments
    try:
        await apply_deployments()
        logger.info("Prefect deployments applied")
    except Exception as e:
        logger.error(f"Error applying Prefect deployments: {e}", exc_info=True)
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


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

# API metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect API metrics"""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    endpoint = request.url.path
    method = request.method
    status = response.status_code
    
    # Record metrics
    api_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    api_request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    return response

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
    return Response(content=get_metrics(), media_type=CONTENT_TYPE_LATEST)
