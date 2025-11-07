"""Job management API"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict
import logging

from workers.scheduler_manager import get_scheduler

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def get_jobs():
    """Get all scheduled jobs"""
    try:
        scheduler = get_scheduler()
        if not scheduler:
            return {"jobs": [], "message": "Scheduler not started"}
        
        jobs = scheduler.get_jobs()
        return {
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                }
                for job in jobs
            ]
        }
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}")
async def get_job(job_id: str):
    """Get a specific job"""
    try:
        scheduler = get_scheduler()
        if not scheduler:
            raise HTTPException(status_code=404, detail="Scheduler not started")
        
        job = scheduler.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return {
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job: {e}")
        raise HTTPException(status_code=500, detail=str(e))
