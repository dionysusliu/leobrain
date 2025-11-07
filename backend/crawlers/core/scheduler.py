"""Scheduler interface and APScheduler implementation"""
from abc import ABC, abstractmethod
from typing import Callable, Any, Optional
import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

logger = logging.getLogger(__name__)


class IScheduler(ABC):
    """Scheduler interface"""
    
    @abstractmethod
    def add_job(
        self,
        func: Callable,
        trigger: str,
        **kwargs
    ):
        """Add a scheduled job"""
        pass
    
    @abstractmethod
    def start(self):
        """Start the scheduler"""
        pass
    
    @abstractmethod
    def shutdown(self):
        """Shutdown the scheduler"""
        pass


class APSchedulerScheduler(IScheduler):
    """APScheduler-based scheduler implementation"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.jobs = {}
        self.running_tasks = {}  # Track running tasks: {job_id: True/False}
    
    def add_job(
        self,
        func: Callable,
        trigger: str,
        job_id: Optional[str] = None,
        **kwargs
    ):
        """
        Add a scheduled job
        
        Args:
            func: Async function to execute
            trigger: Trigger type ('cron', 'interval', or 'date' for immediate)
            job_id: Optional job ID
            **kwargs: Additional trigger parameters
                    - For cron: cron string like "*/10 * * * *" or dict
                    - For interval: seconds, minutes, hours
                    - For date: run_date (datetime) for immediate execution
        """
        if trigger == 'cron':
            # Parse cron expression: "*/10 * * * *" or dict
            cron_expr = kwargs.get('cron')
            if isinstance(cron_expr, str):
                # Parse cron string
                parts = cron_expr.split()
                if len(parts) == 5:
                    trigger_obj = CronTrigger(
                        minute=parts[0],
                        hour=parts[1],
                        day=parts[2],
                        month=parts[3],
                        day_of_week=parts[4]
                    )
                else:
                    raise ValueError(f"Invalid cron expression: {cron_expr}")
            else:
                # Use cron dict
                trigger_obj = CronTrigger(**{k: v for k, v in kwargs.items() if k != 'cron' and k != 'trigger'})
        elif trigger == 'interval':
            # Interval trigger
            trigger_obj = IntervalTrigger(**{k: v for k, v in kwargs.items() if k != 'trigger'})
        elif trigger == 'date':
            # Immediate execution trigger
            run_date = kwargs.get('run_date', datetime.now())
            trigger_obj = DateTrigger(run_date=run_date)
        else:
            raise ValueError(f"Unknown trigger type: {trigger}")
        
        # Wrap async function if needed
        if asyncio.iscoroutinefunction(func):
            # Wrap to track running state
            async def tracked_func(*args, **kw):
                if job_id:
                    self.running_tasks[job_id] = True
                try:
                    result = await func(*args, **kw)
                    return result
                finally:
                    if job_id:
                        self.running_tasks[job_id] = False
            job_func = tracked_func
        else:
            # If sync function, wrap it
            async def async_wrapper(*args, **kw):
                if job_id:
                    self.running_tasks[job_id] = True
                try:
                    result = func(*args, **kw)
                    return result
                finally:
                    if job_id:
                        self.running_tasks[job_id] = False
            job_func = async_wrapper
        
        job = self.scheduler.add_job(
            job_func,
            trigger=trigger_obj,
            id=job_id,
            replace_existing=True
        )
        
        if job_id:
            self.jobs[job_id] = job
            self.running_tasks[job_id] = False
        
        logger.info(f"Added job {job_id or 'unnamed'} with trigger {trigger}")
        return job
    
    def is_running(self, job_id: str) -> bool:
        """Check if a job is currently running"""
        return self.running_tasks.get(job_id, False)
    
    def start(self):
        """Start the scheduler"""
        self.scheduler.start()
        logger.info("Scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        self.scheduler.shutdown(wait=True)
        logger.info("Scheduler shutdown")
    
    def remove_job(self, job_id: str):
        """Remove a job"""
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self.jobs:
                del self.jobs[job_id]
            if job_id in self.running_tasks:
                del self.running_tasks[job_id]
            logger.info(f"Removed job {job_id}")
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {e}")
    
    def get_jobs(self):
        """Get all jobs"""
        return self.scheduler.get_jobs()
    
    def get_job(self, job_id: str):
        """Get a specific job"""
        return self.scheduler.get_job(job_id)
