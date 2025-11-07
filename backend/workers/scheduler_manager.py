"""Scheduler manager for managing crawler jobs"""
import logging
from typing import Optional
import asyncio
from datetime import datetime

from crawlers.core.scheduler import APSchedulerScheduler
from workers.crawler_task import crawl_site
from workers.crawler_task import create_crawl_jobs
from crawlers.core.engine import load_site_configs

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[APSchedulerScheduler] = None


def get_scheduler() -> Optional[APSchedulerScheduler]:
    """Get the global scheduler instance"""
    return _scheduler


def start_scheduler():
    """Start the scheduler and load all jobs"""
    global _scheduler
    
    if _scheduler is not None:
        logger.warning("Scheduler already started")
        return
    
    _scheduler = APSchedulerScheduler()
    
    # Load and add all crawl jobs
    jobs = create_crawl_jobs()
    
    for job_config in jobs:
        try:
            # Create a wrapper function that handles async
            async def job_wrapper(site_name, config):
                await crawl_site(site_name, config)
            
            _scheduler.add_job(
                func=lambda sn=job_config['args'][0], cfg=job_config['args'][1]: job_wrapper(sn, cfg),
                trigger=job_config['trigger'],
                job_id=job_config['id'],
                cron=job_config.get('cron')
            )
            logger.info(f"Added scheduled job: {job_config['id']}")
        except Exception as e:
            logger.error(f"Error adding job {job_config.get('id')}: {e}")
    
    _scheduler.start()
    logger.info(f"Scheduler started with {len(jobs)} scheduled jobs")


def stop_scheduler():
    """Stop the scheduler"""
    global _scheduler
    
    if _scheduler is None:
        return
    
    _scheduler.shutdown()
    _scheduler = None
    logger.info("Scheduler stopped")


async def trigger_manual_crawl(site_name: str) -> str:
    """
    Manually trigger a crawl for a site (immediate execution)
    
    Args:
        site_name: Name of the site to crawl
        
    Returns:
        Job ID of the created task
        
    Raises:
        ValueError: If site not found or scheduler not started
        RuntimeError: If task is already running
    """
    if _scheduler is None:
        raise RuntimeError("Scheduler not started")
    
    # Check if scheduled job exists and is running
    scheduled_job_id = f"crawl_{site_name}"
    if _scheduler.is_running(scheduled_job_id):
        raise RuntimeError(f"Crawl task for {site_name} is already running")
    
    # Load site config
    configs = load_site_configs()
    if site_name not in configs:
        raise ValueError(f"Site {site_name} not found")
    
    config = configs[site_name]
    
    # Create one-time job for immediate execution
    manual_job_id = f"manual_crawl_{site_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    async def manual_crawl_wrapper():
        await crawl_site(site_name, config)
    
    _scheduler.add_job(
        func=manual_crawl_wrapper,
        trigger='date',
        job_id=manual_job_id,
        run_date=datetime.now()  # Execute immediately
    )
    
    logger.info(f"Triggered manual crawl for {site_name} (job_id: {manual_job_id})")
    return manual_job_id
