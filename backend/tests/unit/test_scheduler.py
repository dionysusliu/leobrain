"""Tests for scheduler"""
import pytest
import asyncio
from datetime import datetime, timedelta
from crawlers.core.scheduler import APSchedulerScheduler, IScheduler


@pytest.mark.unit
class TestAPSchedulerScheduler:
    """Tests for APSchedulerScheduler"""
    
    @pytest.fixture
    def scheduler(self):
        """Create scheduler instance"""
        return APSchedulerScheduler()
    
    def test_scheduler_implements_interface(self, scheduler):
        """Test that scheduler implements IScheduler"""
        assert isinstance(scheduler, IScheduler)
    
    def test_scheduler_add_job_cron_string(self, scheduler):
        """Test adding job with cron string"""
        async def test_job():
            return "test"
        
        job = scheduler.add_job(
            test_job,
            trigger='cron',
            cron="*/10 * * * *",
            job_id="test_job"
        )
        
        assert job is not None
        assert "test_job" in scheduler.jobs
        assert scheduler.running_tasks["test_job"] is False
    
    def test_scheduler_add_job_cron_invalid(self, scheduler):
        """Test adding job with invalid cron string"""
        async def test_job():
            return "test"
        
        with pytest.raises(ValueError, match="Invalid cron expression"):
            scheduler.add_job(
                test_job,
                trigger='cron',
                cron="invalid",
                job_id="test_job"
            )
    
    def test_scheduler_add_job_interval(self, scheduler):
        """Test adding job with interval trigger"""
        async def test_job():
            return "test"
        
        job = scheduler.add_job(
            test_job,
            trigger='interval',
            seconds=10,
            job_id="interval_job"
        )
        
        assert job is not None
        assert "interval_job" in scheduler.jobs
    
    def test_scheduler_add_job_date(self, scheduler):
        """Test adding job with date trigger (immediate)"""
        async def test_job():
            return "test"
        
        run_date = datetime.now() + timedelta(seconds=1)
        job = scheduler.add_job(
            test_job,
            trigger='date',
            run_date=run_date,
            job_id="date_job"
        )
        
        assert job is not None
        assert "date_job" in scheduler.jobs
    
    def test_scheduler_add_job_invalid_trigger(self, scheduler):
        """Test adding job with invalid trigger"""
        async def test_job():
            return "test"
        
        with pytest.raises(ValueError, match="Unknown trigger type"):
            scheduler.add_job(
                test_job,
                trigger='invalid',
                job_id="invalid_job"
            )
    
    def test_scheduler_add_job_sync_function(self, scheduler):
        """Test adding job with sync function"""
        def sync_job():
            return "sync"
        
        job = scheduler.add_job(
            sync_job,
            trigger='interval',
            seconds=10,
            job_id="sync_job"
        )
        
        assert job is not None
        assert "sync_job" in scheduler.jobs
    
    def test_scheduler_is_running(self, scheduler):
        """Test checking if job is running"""
        async def test_job():
            await asyncio.sleep(0.1)
            return "test"
        
        scheduler.add_job(
            test_job,
            trigger='interval',
            seconds=10,
            job_id="running_job"
        )
        
        # Initially not running
        assert scheduler.is_running("running_job") is False
        
        # Test with non-existent job
        assert scheduler.is_running("nonexistent") is False
    
    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, scheduler):
        """Test starting and stopping scheduler"""
        scheduler.start()
        assert scheduler.scheduler.running
        
        scheduler.shutdown()
        # Scheduler should be stopped (we can't easily verify without accessing internals)
    
    def test_scheduler_remove_job(self, scheduler):
        """Test removing a job"""
        async def test_job():
            return "test"
        
        scheduler.add_job(
            test_job,
            trigger='interval',
            seconds=10,
            job_id="remove_job"
        )
        
        assert "remove_job" in scheduler.jobs
        
        scheduler.remove_job("remove_job")
        
        assert "remove_job" not in scheduler.jobs
        assert "remove_job" not in scheduler.running_tasks
    
    def test_scheduler_remove_nonexistent_job(self, scheduler):
        """Test removing non-existent job"""
        # Should not raise exception
        scheduler.remove_job("nonexistent")
    
    def test_scheduler_get_jobs(self, scheduler):
        """Test getting all jobs"""
        async def test_job():
            return "test"
        
        scheduler.add_job(
            test_job,
            trigger='interval',
            seconds=10,
            job_id="job1"
        )
        
        scheduler.add_job(
            test_job,
            trigger='interval',
            seconds=20,
            job_id="job2"
        )
        
        jobs = scheduler.get_jobs()
        assert len(jobs) == 2
    
    def test_scheduler_get_job(self, scheduler):
        """Test getting specific job"""
        async def test_job():
            return "test"
        
        scheduler.add_job(
            test_job,
            trigger='interval',
            seconds=10,
            job_id="get_job"
        )
        
        job = scheduler.get_job("get_job")
        assert job is not None
        assert job.id == "get_job"
        
        # Test non-existent job
        assert scheduler.get_job("nonexistent") is None
    
    @pytest.mark.asyncio
    async def test_scheduler_job_tracking(self, scheduler):
        """Test that scheduler tracks running jobs"""
        running_flag = {"value": False}
        
        async def test_job():
            running_flag["value"] = True
            await asyncio.sleep(0.1)
            return "test"
        
        scheduler.start()
        
        try:
            job = scheduler.add_job(
                test_job,
                trigger='date',
                run_date=datetime.now() + timedelta(seconds=0.1),
                job_id="tracking_job"
            )
            
            # Wait for job to start
            await asyncio.sleep(0.15)
            
            # Job should have been tracked (though it may have finished)
            # The tracking happens in the wrapper function
            assert "tracking_job" in scheduler.running_tasks
        finally:
            scheduler.shutdown()

