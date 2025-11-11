"""爬虫相关的 Prefect Tasks"""
from prefect import task
from typing import Dict
import time
import logging

from crawlers.core.service import crawl_site
from configs.types import SiteConfig
from common.metrics import (
    task_runs_total,
    task_duration,
    active_tasks,
    crawler_errors_total
)

logger = logging.getLogger(__name__)


@task(name="crawl_one_site", log_prints=True, retries=2, retry_delay_seconds=60)
async def pf_task_crawl_one_site(site_name: str, config: SiteConfig):
    """
    Prefect Task 包装爬虫业务逻辑
    
    Args:
        site_name: 站点名称
        config: 站点配置（类型化的 SiteConfig）
    """
    task_start_time = time.time()
    active_tasks.labels(task_name=f"crawl_{site_name}").inc()

    try:
        task_runs_total.labels(task_name=f"crawl_{site_name}", status="started").inc()

        # 业务逻辑
        config_dict = config.model_dump()
        await crawl_site(site_name, config_dict)

        task_runs_total.labels(task_name=f"crawl_{site_name}", status="success").inc()
    
    except Exception as e:
        task_runs_total.labels(task_name=f"crawl_{site_name}", status="error").inc()
        crawler_errors_total.labels(site_name=site_name, error_type=type(e).__name__).inc()
        raise

    finally:
        duration = time.time() - task_start_time
        task_duration.labels(task_name=f"crawl_{site_name}").observe(duration)
        active_tasks.labels(task_name=f"crawl_{site_name}").dec()
        
    