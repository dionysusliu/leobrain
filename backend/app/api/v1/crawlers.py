"""Crawler management API"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import logging

from crawlers.core.engine import load_site_configs
from workers.scheduler_manager import get_scheduler, trigger_manual_crawl

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/sites")
async def get_sites():
    """Get all configured sites"""
    try:
        configs = load_site_configs()
        scheduler = get_scheduler()
        
        # Get running status for each site
        sites_info = {}
        for site_name, config in configs.items():
            job_id = f"crawl_{site_name}"
            is_running = False
            next_run = None
            
            if scheduler:
                is_running = scheduler.is_running(job_id)
                job = scheduler.get_job(job_id)
                if job and job.next_run_time:
                    next_run = job.next_run_time.isoformat()
            
            sites_info[site_name] = {
                "config": config,
                "is_running": is_running,
                "next_run_time": next_run
            }
        
        return {
            "sites": list(configs.keys()),
            "sites_info": sites_info
        }
    except Exception as e:
        logger.error(f"Error loading sites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sites/{site_name}/crawl")
async def trigger_crawl(site_name: str):
    """Manually trigger a crawl for a specific site (immediate execution)"""
    try:
        scheduler = get_scheduler()
        if not scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not started")
        
        # Check if scheduled task is already running
        scheduled_job_id = f"crawl_{site_name}"
        if scheduler.is_running(scheduled_job_id):
            raise HTTPException(
                status_code=409,
                detail=f"Crawl task for {site_name} is already running"
            )
        
        # Trigger manual crawl through scheduler
        job_id = await trigger_manual_crawl(site_name)
        
        return {
            "message": f"Crawl task started for {site_name}",
            "site": site_name,
            "job_id": job_id
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering crawl: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sites/{site_name}")
async def get_site_config(site_name: str):
    """Get configuration for a specific site"""
    try:
        configs = load_site_configs()
        
        if site_name not in configs:
            raise HTTPException(status_code=404, detail=f"Site {site_name} not found")
        
        scheduler = get_scheduler()
        job_id = f"crawl_{site_name}"
        is_running = False
        next_run = None
        
        if scheduler:
            is_running = scheduler.is_running(job_id)
            job = scheduler.get_job(job_id)
            if job and job.next_run_time:
                next_run = job.next_run_time.isoformat()
        
        return {
            "site": site_name,
            "config": configs[site_name],
            "is_running": is_running,
            "next_run_time": next_run
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting site config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sites/{site_name}/status")
async def get_site_status(site_name: str):
    """Get running status for a specific site"""
    try:
        scheduler = get_scheduler()
        if not scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not started")
        
        job_id = f"crawl_{site_name}"
        is_running = scheduler.is_running(job_id)
        job = scheduler.get_job(job_id)
        
        return {
            "site": site_name,
            "is_running": is_running,
            "next_run_time": job.next_run_time.isoformat() if job and job.next_run_time else None,
            "job_id": job_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting site status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
