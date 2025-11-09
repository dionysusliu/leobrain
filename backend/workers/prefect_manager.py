"""Prefect task and flow management"""
try:
    import common.prefect_config
except ImportError:
    import os
    os.environ.setdefault("PREFECT_API_URL", "http://localhost:4200/api")

import logging
import time
import os
from typing import Dict, Optional
from prefect import flow, task, get_client
from prefect.context import get_run_context
from prefect.schedules import Schedule
from prefect.client.schemas.filters import (
    DeploymentFilter,
    DeploymentFilterTags,
    DeploymentFilterName,
    FlowRunFilter,
    FlowRunFilterTags,
)

from workers.crawler_task import crawl_site
from crawlers.core.engine import load_site_configs
from common.metrics import (
    task_runs_total,
    task_duration,
    active_tasks,
    crawler_errors_total
)

logger = logging.getLogger(__name__)

# Ensure Prefect API URL is set to use Docker server
# This prevents Prefect from creating a temporary server
_prefect_api_url = os.getenv("PREFECT_API_URL", "http://localhost:4200/api")
if "PREFECT_API_URL" not in os.environ:
    os.environ["PREFECT_API_URL"] = _prefect_api_url
    logger.info("Set Prefect API URL to: %s", _prefect_api_url)


@task(name="crawl_site_task", log_prints=True)
async def crawl_site_task(site_name: str, config: Dict):
    """
    Prefect task wrapper for crawl_site
    
    Args:
        site_name: Name of the site to crawl
        config: Site configuration
    """
    task_start_time = time.time()
    active_tasks.labels(task_name=f"crawl_{site_name}").inc()
    
    try:
        logger.info("Starting Prefect task for %s", site_name)
        task_runs_total.labels(task_name=f"crawl_{site_name}", status="started").inc()
        
        await crawl_site(site_name, config)
        
        task_runs_total.labels(task_name=f"crawl_{site_name}", status="success").inc()
        logger.info("Completed Prefect task for %s", site_name)
        
    except Exception as e:
        task_runs_total.labels(task_name=f"crawl_{site_name}", status="error").inc()
        crawler_errors_total.labels(site_name=site_name, error_type=type(e).__name__).inc()
        logger.error("Error in Prefect task for %s: %s", site_name, e, exc_info=True)
        raise
    finally:
        duration = time.time() - task_start_time
        task_duration.labels(task_name=f"crawl_{site_name}").observe(duration)
        active_tasks.labels(task_name=f"crawl_{site_name}").dec()


@flow(name="crawl_site_flow", log_prints=True)
async def crawl_site_flow(site_name: str, config: Dict):
    """Prefect flow for crawling a site"""
    # Add tags to flow run using context manager
    from prefect import tags
    with tags("crawler", site_name):
        await crawl_site_task(site_name, config)
    # Return flow run ID for tracking
    try:
        run_context = get_run_context()
        if run_context and hasattr(run_context, 'flow_run'):
            return run_context.flow_run.id
    except Exception:
        pass
    return None


def parse_cron_to_prefect(cron_expr: str) -> Schedule:
    """Parse cron expression to Prefect Schedule"""
    return Schedule(cron=cron_expr, timezone="UTC")


async def create_prefect_deployments():
    """
    Create Prefect deployment configurations for all configured sites.
    
    Note: In Prefect 3.0+, deployments are created using flow.serve() or
    via the Prefect CLI. This function returns deployment metadata for
    reference purposes only.
    """
    configs = load_site_configs()
    deployments = []
    
    for site_name, config in configs.items():
        cron_expr = config.get('cron', '*/10 * * * *')
        schedule = parse_cron_to_prefect(cron_expr)
        
        # Create deployment metadata (for reference)
        deployment_info = {
            "name": f"crawl-{site_name}",
            "flow_name": "crawl_site_flow",
            "work_queue_name": "default",
            "parameters": {"site_name": site_name, "config": config},
            "schedule": schedule,
            "tags": ["crawler", site_name],
        }
        
        deployments.append(deployment_info)
        logger.info("Created Prefect deployment config for %s", site_name)
    
    return deployments


async def apply_deployments():
    """
    Apply all deployments to Prefect server.
    
    Note: In Prefect 3.0+, deployments should be created using:
    - `flow.serve()` for local development
    - `prefect deploy` CLI command
    - Or programmatically using the Prefect client API
    
    This function logs deployment information but actual deployment
    should be done via the Prefect CLI or UI.
    """
    deployments = await create_prefect_deployments()
    
    for deployment_info in deployments:
        try:
            logger.info("Deployment config ready: %s", deployment_info['name'])
            logger.info(
                "To apply this deployment, use: prefect deploy --name %s --work-queue-name %s",
                deployment_info['name'],
                deployment_info['work_queue_name']
            )
        except (KeyError, TypeError) as e:
            logger.error("Error processing deployment %s: %s", deployment_info.get('name', 'unknown'), e)


async def trigger_manual_crawl(site_name: str) -> str:
    """
    Manually trigger a crawl via Prefect
    
    This function ensures the flow run is created on the configured Prefect server
    (Docker server) rather than creating a temporary server.
    
    Returns:
        Flow run ID
    """
    configs = load_site_configs()
    if site_name not in configs:
        raise ValueError(f"Site {site_name} not found")
    
    config = configs[site_name]
    
    # Ensure PREFECT_API_URL is set to use Docker server
    prefect_api_url = os.getenv("PREFECT_API_URL", "http://localhost:4200/api")
    if "PREFECT_API_URL" not in os.environ:
        os.environ["PREFECT_API_URL"] = prefect_api_url
    
    logger.info("Triggering crawl for %s via Prefect server at %s", site_name, prefect_api_url)
    
    # Run flow immediately and get flow run ID from the result
    # The flow will use the configured PREFECT_API_URL to connect to Docker server
    # Note: Tags should be added via flow decorator or using tags context manager
    try:
        flow_run_id = await crawl_site_flow.with_options(
            name=f"manual-crawl-{site_name}"
        )(
            site_name=site_name,
            config=config
        )
        
        # flow_run_id is returned from the flow itself
        if flow_run_id is None:
            # Fallback: try to get from context
            try:
                run_context = get_run_context()
                if run_context and hasattr(run_context, 'flow_run'):
                    flow_run_id = str(run_context.flow_run.id)
                    logger.info("Got flow run ID from context: %s", flow_run_id)
                    return flow_run_id
            except Exception as e:
                logger.warning("Could not get flow run ID from context: %s", e)
        
        if flow_run_id:
            logger.info("Flow run created with ID: %s", flow_run_id)
            return str(flow_run_id)
        else:
            raise RuntimeError("Failed to get flow run ID from flow execution")
            
    except Exception as e:
        logger.error("Error triggering crawl for %s: %s", site_name, e, exc_info=True)
        # Check if it's a connection issue
        if "connection" in str(e).lower() or "refused" in str(e).lower():
            raise RuntimeError(
                f"Cannot connect to Prefect server at {prefect_api_url}. "
                f"Make sure Prefect server is running: docker compose up -d prefect-server"
            ) from e
        raise


async def get_deployments():
    """Get all deployments from Prefect server"""
    async with get_client() as client:
        # Use Prefect 3.0 filter objects instead of dict
        deployment_filter = DeploymentFilter(
            tags=DeploymentFilterTags(all_=["crawler"])
        )
        deployments = await client.read_deployments(
            deployment_filter=deployment_filter
        )
        
        return [
            {
                "id": str(deployment.id),
                "name": deployment.name,
                "schedule": str(deployment.schedule) if deployment.schedule else None,
                "tags": deployment.tags,
                "flow_name": deployment.flow_name,
                "work_queue_name": deployment.work_queue_name,
                "is_schedule_active": deployment.is_schedule_active if hasattr(deployment, 'is_schedule_active') else None,
            }
            for deployment in deployments
        ]


async def get_deployment_by_name(deployment_name: str):
    """Get a specific deployment by name from Prefect server"""
    async with get_client() as client:
        # Use Prefect 3.0 filter objects instead of dict
        deployment_filter = DeploymentFilter(
            name=DeploymentFilterName(any_=[deployment_name])
        )
        deployments = await client.read_deployments(
            deployment_filter=deployment_filter
        )
        
        if not deployments:
            return None
        
        deployment = deployments[0]
        return {
            "id": str(deployment.id),
            "name": deployment.name,
            "schedule": str(deployment.schedule) if deployment.schedule else None,
            "tags": deployment.tags,
            "flow_name": deployment.flow_name,
            "work_queue_name": deployment.work_queue_name,
            "is_schedule_active": deployment.is_schedule_active if hasattr(deployment, 'is_schedule_active') else None,
        }


async def get_flow_runs(site_name: Optional[str] = None, limit: int = 20):
    """Get recent flow runs"""
    async with get_client() as client:
        # Use Prefect 3.0 FlowRunFilter with correct parameter name (flow_run_filter, not flow_filter)
        if site_name:
            # If site_name is provided, flow run must have both "crawler" and site_name tags
            flow_run_filter = FlowRunFilter(
                tags=FlowRunFilterTags(all_=["crawler", site_name])
            )
        else:
            # Otherwise, just filter by "crawler" tag
            flow_run_filter = FlowRunFilter(
                tags=FlowRunFilterTags(all_=["crawler"])
            )
        
        runs = await client.read_flow_runs(
            flow_run_filter=flow_run_filter,  # Correct parameter name for Prefect 3.0
            limit=limit,
            sort="START_TIME_DESC"  # Prefect 3.0 uses START_TIME_DESC instead of CREATED_DESC
        )
        
        return [
            {
                "id": str(run.id),
                "name": run.name,
                "status": run.state_type.value if run.state_type else "unknown",
                "start_time": run.start_time.isoformat() if run.start_time else None,
                "end_time": run.end_time.isoformat() if run.end_time else None,
                "tags": run.tags,
            }
            for run in runs
        ]
