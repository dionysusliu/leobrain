"""Scheduler interface and APScheduler implementation"""
from abc import ABC, abstractmethod
from typing import Callable, Any, Optional
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

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
            func: Function to execute
            trigger: Trigger type ('cron' or 'interval')
            job_id: Optional job ID
            **kwargs: Additional trigger parameters
                    - For cron: minute, hour, day, etc.
                    - For interval: seconds, minutes, hours
        """
        if trigger == 'cron':
            # Parse cron expression: "*/10 * * * *" or dict
            if isinstance(kwargs.get('cron'), str):
                # Parse cron string
                parts = kwargs['cron'].split()
                if len(parts) == 5:
                    trigger_obj = CronTrigger(
                        minute=parts[0],
                        hour=parts[1],
                        day=parts[2],
                        month=parts[3],
                        day_of_week=parts[4]
                    )
                else:
                    raise ValueError(f"Invalid cron expression: {kwargs['cron']}")
            else:
                # Use cron dict
                trigger_obj = CronTrigger(**{k: v for k, v in kwargs.items() if k != 'cron'})
        elif trigger == 'interval':
            # Interval trigger
            trigger_obj = IntervalTrigger(**{k: v for k, v in kwargs.items() if k != 'trigger'})
        else:
            raise ValueError(f"Unknown trigger type: {trigger}")
        
        job = self.scheduler.add_job(
            func,
            trigger=trigger_obj,
            id=job_id,
            replace_existing=True
        )
        
        if job_id:
            self.jobs[job_id] = job
        
        logger.info(f"Added job {job_id or 'unnamed'} with trigger {trigger}")
        return job
    
    def start(self):
        """Start the scheduler"""
        self.scheduler.start()
        logger.info("Scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler shutdown")
    
    def remove_job(self, job_id: str):
        """Remove a job"""
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self.jobs:
                del self.jobs[job_id]
            logger.info(f"Removed job {job_id}")
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {e}")
    
    def get_jobs(self):
        """Get all jobs"""
        return self.scheduler.get_jobs()
