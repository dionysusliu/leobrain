"""Job management API"""
from fastapi import APIRouter, HTTPException
import logging

from workers.prefect_manager import get_flow_runs, get_deployments, get_deployment_by_name

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def get_jobs():
    """Get all scheduled jobs (Prefect deployments) from Prefect server"""
    try:
        # Try to get deployments from Prefect server first
        try:
            deployments = await get_deployments()
            return {"jobs": deployments}
        except (ConnectionError, TimeoutError, OSError) as server_error:
            # If server is not available, fall back to local config
            logger.warning("Could not connect to Prefect server: %s. Using local config.", server_error)
            from workers.prefect_manager import create_prefect_deployments
            deployment_configs = await create_prefect_deployments()
            return {
                "jobs": [
                    {
                        "id": config["name"],
                        "name": config["name"],
                        "schedule": str(config["schedule"]) if config.get("schedule") else None,
                        "tags": config["tags"],
                    }
                    for config in deployment_configs
                ]
            }
    except Exception as e:
        logger.error("Error getting jobs: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{job_id}")
async def get_job(job_id: str):
    """Get a specific job and its recent runs from Prefect server"""
    try:
        # Try to get deployment from Prefect server first
        deployment = await get_deployment_by_name(job_id)
        
        if not deployment:
            # Fall back to local config if not found on server
            logger.warning("Deployment %s not found on server, checking local config", job_id)
            from workers.prefect_manager import create_prefect_deployments
            deployment_configs = await create_prefect_deployments()
            deployment_config = next(
                (d for d in deployment_configs if d["name"] == job_id),
                None
            )
            if not deployment_config:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
            
            deployment = {
                "id": deployment_config["name"],
                "name": deployment_config["name"],
                "schedule": str(deployment_config["schedule"]) if deployment_config.get("schedule") else None,
                "tags": deployment_config["tags"],
            }
        
        # Get recent flow runs for this job
        site_name = job_id.replace("crawl-", "")
        runs = await get_flow_runs(site_name=site_name, limit=5)
        
        return {
            **deployment,
            "recent_runs": runs
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting job: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e
