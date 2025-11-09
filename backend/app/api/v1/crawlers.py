"""Crawler management API"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import logging
import asyncio

from crawlers.core.engine import load_site_configs
from workers.prefect_manager import trigger_manual_crawl, get_flow_runs

logger = logging.getLogger(__name__)

router = APIRouter()


class BatchCrawlRequest(BaseModel):
    """Request model for batch crawl"""
    sites: Optional[List[str]] = None  # If None, crawl all sites
    parallel: bool = False  # Whether to run in parallel


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


@router.post("/sites/batch-crawl")
async def batch_trigger_crawl(request: BatchCrawlRequest):
    """
    Trigger crawl tasks for multiple sites
    
    Args:
        request: BatchCrawlRequest with sites list and parallel flag
            - sites: List of site names to crawl. If None, crawl all sites
            - parallel: If True, trigger all tasks in parallel; if False, trigger sequentially
    
    Returns:
        Dictionary with results for each site
    """
    try:
        configs = load_site_configs()
        
        # Determine which sites to crawl
        if request.sites is None:
            # Crawl all sites
            sites_to_crawl = list(configs.keys())
        else:
            # Validate sites
            invalid_sites = [s for s in request.sites if s not in configs]
            if invalid_sites:
                raise HTTPException(
                    status_code=404,
                    detail=f"Sites not found: {', '.join(invalid_sites)}"
                )
            sites_to_crawl = request.sites
        
        if not sites_to_crawl:
            raise HTTPException(status_code=400, detail="No sites to crawl")
        
        results = {}
        
        async def trigger_single(site_name: str):
            """Trigger crawl for a single site"""
            try:
                flow_run_id = await trigger_manual_crawl(site_name)
                return {
                    "success": True,
                    "site": site_name,
                    "flow_run_id": flow_run_id,
                    "message": f"Crawl task started for {site_name}"
                }
            except Exception as e:
                logger.error(f"Error triggering crawl for {site_name}: {e}")
                return {
                    "success": False,
                    "site": site_name,
                    "error": str(e)
                }
        
        # Trigger crawls
        if request.parallel:
            # Trigger all in parallel
            tasks = [trigger_single(site) for site in sites_to_crawl]
            results_list = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results_list):
                site_name = sites_to_crawl[i]
                if isinstance(result, Exception):
                    results[site_name] = {
                        "success": False,
                        "error": str(result)
                    }
                else:
                    results[site_name] = result
        else:
            # Trigger sequentially
            for site_name in sites_to_crawl:
                result = await trigger_single(site_name)
                results[site_name] = result
        
        # Count successes and failures
        success_count = sum(1 for r in results.values() if r.get("success", False))
        failure_count = len(results) - success_count
        
        return {
            "message": f"Triggered {len(sites_to_crawl)} crawl tasks",
            "total": len(sites_to_crawl),
            "success": success_count,
            "failed": failure_count,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in batch trigger crawl: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e
