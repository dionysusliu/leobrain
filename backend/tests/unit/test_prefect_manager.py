"""Tests for Prefect manager"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict

from workers.prefect_manager import (
    crawl_site_task,
    crawl_site_flow,
    parse_cron_to_prefect,
    create_prefect_deployments,
    apply_deployments,
    trigger_manual_crawl,
    get_flow_runs,
    get_deployments,
    get_deployment_by_name,
)
from workers.crawler_task import crawl_site
from crawlers.core.engine import load_site_configs


@pytest.mark.unit
class TestPrefectManager:
    """Tests for Prefect manager"""
    
    @pytest.fixture
    def sample_config(self):
        """Sample site configuration"""
        return {
            "spider": "rss",
            "source_name": "test_source",
            "feed_url": "http://example.com/feed.xml",
            "cron": "*/10 * * * *",
            "qps": 1.0,
            "concurrency": 2,
            "max_items": 10,
            "fetch_full_content": False,
        }
    
    @pytest.fixture
    def mock_site_configs(self, sample_config, monkeypatch):
        """Mock site configs"""
        def mock_load_configs():
            return {
                "test_site": sample_config,
                "another_site": {**sample_config, "source_name": "another_source"}
            }
        
        monkeypatch.setattr(
            "workers.prefect_manager.load_site_configs",
            mock_load_configs
        )
        return mock_load_configs()
    
    @pytest.mark.asyncio
    async def test_crawl_site_task_success(self, sample_config, monkeypatch):
        """Test crawl_site_task successfully executes"""
        # Mock crawl_site to avoid actual crawling
        mock_crawl = AsyncMock()
        monkeypatch.setattr("workers.prefect_manager.crawl_site", mock_crawl)
        
        # Mock metrics
        mock_active_tasks = Mock()
        mock_task_runs = Mock()
        mock_task_duration = Mock()
        mock_crawler_errors = Mock()
        
        monkeypatch.setattr("workers.prefect_manager.active_tasks", mock_active_tasks)
        monkeypatch.setattr("workers.prefect_manager.task_runs_total", mock_task_runs)
        monkeypatch.setattr("workers.prefect_manager.task_duration", mock_task_duration)
        monkeypatch.setattr("workers.prefect_manager.crawler_errors_total", mock_crawler_errors)
        
        # Execute task
        await crawl_site_task("test_site", sample_config)
        
        # Verify crawl_site was called
        mock_crawl.assert_called_once_with("test_site", sample_config)
        
        # Verify metrics were updated
        assert mock_active_tasks.labels().inc.called
        assert mock_task_runs.labels().inc.called
        assert mock_task_duration.labels().observe.called
    
    @pytest.mark.asyncio
    async def test_crawl_site_task_error(self, sample_config, monkeypatch):
        """Test crawl_site_task handles errors correctly"""
        # Mock crawl_site to raise an error
        error = ValueError("Test error")
        mock_crawl = AsyncMock(side_effect=error)
        monkeypatch.setattr("workers.prefect_manager.crawl_site", mock_crawl)
        
        # Mock metrics
        mock_active_tasks = Mock()
        mock_task_runs = Mock()
        mock_task_duration = Mock()
        mock_crawler_errors = Mock()
        
        monkeypatch.setattr("workers.prefect_manager.active_tasks", mock_active_tasks)
        monkeypatch.setattr("workers.prefect_manager.task_runs_total", mock_task_runs)
        monkeypatch.setattr("workers.prefect_manager.task_duration", mock_task_duration)
        monkeypatch.setattr("workers.prefect_manager.crawler_errors_total", mock_crawler_errors)
        
        # Execute task and expect error
        with pytest.raises(ValueError, match="Test error"):
            await crawl_site_task("test_site", sample_config)
        
        # Verify error metrics were updated
        assert mock_crawler_errors.labels().inc.called
        assert mock_task_runs.labels().inc.called
    
    @pytest.mark.asyncio
    async def test_crawl_site_flow(self, sample_config, monkeypatch):
        """Test crawl_site_flow calls the task"""
        # Mock the task
        mock_task = AsyncMock()
        monkeypatch.setattr("workers.prefect_manager.crawl_site_task", mock_task)
        
        # Execute flow
        await crawl_site_flow("test_site", sample_config)
        
        # Verify task was called
        mock_task.assert_called_once_with("test_site", sample_config)
    
    def test_parse_cron_to_prefect(self):
        """Test parsing cron expression to Prefect Schedule"""
        cron_expr = "*/10 * * * *"
        schedule = parse_cron_to_prefect(cron_expr)
        
        assert schedule is not None
        assert schedule.cron == cron_expr
        assert schedule.timezone == "UTC"
    
    @pytest.mark.asyncio
    async def test_create_prefect_deployments(self, mock_site_configs):
        """Test creating Prefect deployment configs for all sites"""
        deployments = await create_prefect_deployments()
        
        assert len(deployments) == 2
        assert all(d["name"].startswith("crawl-") for d in deployments)
        assert all("crawler" in d["tags"] for d in deployments)
    
    @pytest.mark.asyncio
    async def test_create_prefect_deployments_with_cron(self, mock_site_configs):
        """Test deployments include cron schedule"""
        deployments = await create_prefect_deployments()
        
        for deployment in deployments:
            assert deployment["schedule"] is not None
            assert deployment["schedule"].cron is not None
    
    @pytest.mark.asyncio
    async def test_apply_deployments(self, mock_site_configs):
        """Test applying deployments logs information"""
        # This function now just logs deployment info
        # It doesn't actually apply deployments in Prefect 3.0+
        await apply_deployments()
        
        # Should complete without error
        assert True
    
    @pytest.mark.asyncio
    async def test_apply_deployments_error_handling(self, mock_site_configs, monkeypatch):
        """Test that errors in applying deployments are handled gracefully"""
        # Mock create_prefect_deployments to return invalid data
        async def mock_create():
            return [{"name": "test", "invalid": "data"}]
        
        monkeypatch.setattr(
            "workers.prefect_manager.create_prefect_deployments",
            mock_create
        )
        
        # Should not raise exception
        await apply_deployments()
    
    @pytest.mark.asyncio
    async def test_trigger_manual_crawl(self, mock_site_configs, monkeypatch):
        """Test manually triggering a crawl"""
        # Mock crawl_site_flow
        mock_flow_run = Mock()
        mock_flow_run.id = "test-flow-run-id"
        
        mock_flow = AsyncMock(return_value=mock_flow_run)
        mock_flow.with_options = Mock(return_value=mock_flow)
        
        monkeypatch.setattr("workers.prefect_manager.crawl_site_flow", mock_flow)
        
        # Execute
        flow_run_id = await trigger_manual_crawl("test_site")
        
        # Verify
        assert flow_run_id == "test-flow-run-id"
        mock_flow.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_trigger_manual_crawl_site_not_found(self, mock_site_configs):
        """Test triggering crawl for non-existent site"""
        with pytest.raises(ValueError, match="Site nonexistent not found"):
            await trigger_manual_crawl("nonexistent")
    
    @pytest.mark.asyncio
    async def test_get_flow_runs(self, monkeypatch):
        """Test getting flow runs from Prefect"""
        # Mock Prefect client
        mock_run = Mock()
        mock_run.id = "run-123"
        mock_run.name = "crawl-test_site"
        mock_run.state_type = Mock(value="COMPLETED")
        mock_run.start_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_run.end_time = datetime(2024, 1, 1, 12, 5, 0)
        mock_run.tags = ["crawler", "test_site"]
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.read_flow_runs = AsyncMock(return_value=[mock_run])
        
        # Mock get_client
        def mock_get_client():
            return mock_client
        
        monkeypatch.setattr("workers.prefect_manager.get_client", mock_get_client)
        
        # Execute
        runs = await get_flow_runs(site_name="test_site", limit=20)
        
        # Verify
        assert len(runs) == 1
        assert runs[0]["id"] == "run-123"
        assert runs[0]["name"] == "crawl-test_site"
        assert runs[0]["status"] == "COMPLETED"
        assert runs[0]["tags"] == ["crawler", "test_site"]
    
    @pytest.mark.asyncio
    async def test_get_flow_runs_without_site_name(self, monkeypatch):
        """Test getting flow runs without filtering by site"""
        # Mock Prefect client
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.read_flow_runs = AsyncMock(return_value=[])
        
        def mock_get_client():
            return mock_client
        
        monkeypatch.setattr("workers.prefect_manager.get_client", mock_get_client)
        
        # Execute
        runs = await get_flow_runs(limit=20)
        
        # Verify
        assert isinstance(runs, list)
        mock_client.read_flow_runs.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_flow_runs_handles_missing_fields(self, monkeypatch):
        """Test get_flow_runs handles missing optional fields"""
        # Mock Prefect client with minimal run data
        mock_run = Mock()
        mock_run.id = "run-123"
        mock_run.name = "crawl-test_site"
        mock_run.state_type = None
        mock_run.start_time = None
        mock_run.end_time = None
        mock_run.tags = []
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.read_flow_runs = AsyncMock(return_value=[mock_run])
        
        def mock_get_client():
            return mock_client
        
        monkeypatch.setattr("workers.prefect_manager.get_client", mock_get_client)
        
        # Execute
        runs = await get_flow_runs(limit=20)
        
        # Verify
        assert len(runs) == 1
        assert runs[0]["status"] == "unknown"
        assert runs[0]["start_time"] is None
        assert runs[0]["end_time"] is None
    
    @pytest.mark.asyncio
    async def test_get_deployments(self, monkeypatch):
        """Test getting deployments from Prefect server"""
        # Mock Prefect client
        mock_deployment = Mock()
        mock_deployment.id = "deployment-123"
        mock_deployment.name = "crawl-test_site"
        mock_deployment.schedule = Mock()
        mock_deployment.schedule.__str__ = Mock(return_value="*/10 * * * *")
        mock_deployment.tags = ["crawler", "test_site"]
        mock_deployment.flow_name = "crawl_site_flow"
        mock_deployment.work_queue_name = "default"
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.read_deployments = AsyncMock(return_value=[mock_deployment])
        
        def mock_get_client():
            return mock_client
        
        monkeypatch.setattr("workers.prefect_manager.get_client", mock_get_client)
        
        # Execute
        deployments = await get_deployments()
        
        # Verify
        assert len(deployments) == 1
        assert deployments[0]["id"] == "deployment-123"
        assert deployments[0]["name"] == "crawl-test_site"
        assert deployments[0]["schedule"] == "*/10 * * * *"
        assert deployments[0]["tags"] == ["crawler", "test_site"]
        assert deployments[0]["flow_name"] == "crawl_site_flow"
    
    @pytest.mark.asyncio
    async def test_get_deployment_by_name(self, monkeypatch):
        """Test getting a specific deployment by name"""
        # Mock Prefect client
        mock_deployment = Mock()
        mock_deployment.id = "deployment-123"
        mock_deployment.name = "crawl-test_site"
        mock_deployment.schedule = Mock()
        mock_deployment.schedule.__str__ = Mock(return_value="*/10 * * * *")
        mock_deployment.tags = ["crawler", "test_site"]
        mock_deployment.flow_name = "crawl_site_flow"
        mock_deployment.work_queue_name = "default"
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.read_deployments = AsyncMock(return_value=[mock_deployment])
        
        def mock_get_client():
            return mock_client
        
        monkeypatch.setattr("workers.prefect_manager.get_client", mock_get_client)
        
        # Execute
        deployment = await get_deployment_by_name("crawl-test_site")
        
        # Verify
        assert deployment is not None
        assert deployment["id"] == "deployment-123"
        assert deployment["name"] == "crawl-test_site"
    
    @pytest.mark.asyncio
    async def test_get_deployment_by_name_not_found(self, monkeypatch):
        """Test getting deployment that doesn't exist"""
        # Mock Prefect client returning empty list
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.read_deployments = AsyncMock(return_value=[])
        
        def mock_get_client():
            return mock_client
        
        monkeypatch.setattr("workers.prefect_manager.get_client", mock_get_client)
        
        # Execute
        deployment = await get_deployment_by_name("nonexistent")
        
        # Verify
        assert deployment is None

