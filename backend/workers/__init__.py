"""Workers package"""
from workers.crawler_task import crawl_site, create_crawl_jobs
from workers.prefect_manager import (
    trigger_manual_crawl,
    get_flow_runs,
    get_deployments,
    get_deployment_by_name,
    apply_deployments,
    create_prefect_deployments,
)

__all__ = [
    "crawl_site",
    "create_crawl_jobs",
    "trigger_manual_crawl",
    "get_flow_runs",
    "get_deployments",
    "get_deployment_by_name",
    "apply_deployments",
    "create_prefect_deployments",
]
