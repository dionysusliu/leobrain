"""Crawler management API"""
from fastapi import APIRouter, HTTPException
import logging

from crawlers.core.engine import load_site_configs
from workers.prefect_manager import trigger_manual_crawl, get_flow_runs

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/sites")
async def get_sites():
    """Get all configured sites"""
    try:
        configs = load_site_configs()
        
        # Get recent flow runs for status
        sites_info = {}
        for site_name, config in configs.items():
            # Get most recent run for this site
            try:
                runs = await get_flow_runs(site_name=site_name, limit=1)
                latest_run = runs[0] if runs else None
                is_running = bool(latest_run and latest_run.get("status") in ["RUNNING", "PENDING"])
            except Exception:
                # If Prefect server is unavailable, set defaults
                latest_run = None
                is_running = False
            
            sites_info[site_name] = {
                "config": config,
                "is_running": is_running,
                "latest_run": latest_run
            }
        
        return {
            "sites": list(configs.keys()),
            "sites_info": sites_info
        }
    except Exception as e:
        logger.error("Error loading sites: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/sites/{site_name}/crawl")
async def trigger_crawl(site_name: str):
    """Manually trigger a crawl for a specific site (immediate execution)"""
    try:
        # Trigger manual crawl through Prefect
        flow_run_id = await trigger_manual_crawl(site_name)
        
        return {
            "message": f"Crawl task started for {site_name}",
            "site": site_name,
            "flow_run_id": flow_run_id
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error triggering crawl: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sites/{site_name}")
async def get_site_config(site_name: str):
    """Get configuration for a specific site"""
    try:
        configs = load_site_configs()
        
        if site_name not in configs:
            raise HTTPException(status_code=404, detail=f"Site {site_name} not found")
        
        # Get recent flow runs
        try:
            runs = await get_flow_runs(site_name=site_name, limit=5)
            latest_run = runs[0] if runs else None
            is_running = bool(latest_run and latest_run.get("status") in ["RUNNING", "PENDING"])
        except Exception:
            runs = []
            latest_run = None
            is_running = False
        
        return {
            "site": site_name,
            "config": configs[site_name],
            "is_running": is_running,
            "recent_runs": runs
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting site config: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sites/{site_name}/status")
async def get_site_status(site_name: str):
    """Get running status for a specific site"""
    try:
        configs = load_site_configs()
        if site_name not in configs:
            raise HTTPException(status_code=404, detail=f"Site {site_name} not found")
        
        # Get recent flow runs
        try:
            runs = await get_flow_runs(site_name=site_name, limit=1)
            latest_run = runs[0] if runs else None
            is_running = bool(latest_run and latest_run.get("status") in ["RUNNING", "PENDING"])
        except Exception:
            latest_run = None
            is_running = False
        
        return {
            "site": site_name,
            "is_running": is_running,
            "latest_run": latest_run
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting site status: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e
