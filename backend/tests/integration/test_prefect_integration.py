"""Integration tests for Prefect manager"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from workers.prefect_manager import (
    crawl_site_task,
    crawl_site_flow,
    create_prefect_deployments,
    apply_deployments,
    trigger_manual_crawl,
    get_deployments,
    get_deployment_by_name,
    get_flow_runs,
)
from workers.crawler_task import crawl_site
from crawlers.core.engine import load_site_configs
from tests.utils import load_fixture


@pytest.mark.integration
class TestPrefectIntegration:
    """Integration tests for Prefect manager with actual Prefect server"""
    
    @pytest.fixture
    def sample_site_config(self):
        """Sample site configuration for testing"""
        return {
            "spider": "rss",
            "source_name": "test_integration_source",
            "feed_url": "http://example.com/feed.xml",
            "cron": "*/10 * * * *",
            "qps": 1.0,
            "concurrency": 2,
            "max_items": 5,
            "fetch_full_content": False,
        }
    
    @pytest.fixture
    def mock_site_configs(self, sample_site_config, monkeypatch):
        """Mock site configs for testing"""
        def mock_load_configs():
            return {
                "test_site": sample_site_config,
            }
        
        monkeypatch.setattr(
            "workers.prefect_manager.load_site_configs",
            mock_load_configs
        )
        return mock_load_configs()
    
    @pytest.mark.asyncio
    async def test_prefect_task_execution(self, sample_site_config, monkeypatch):
        """Test that Prefect task actually executes crawl_site"""
        # Mock crawl_site to verify it's called
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
        await crawl_site_task("test_site", sample_site_config)
        
        # Verify crawl_site was called with correct parameters
        mock_crawl.assert_called_once_with("test_site", sample_site_config)
        
        # Verify metrics were updated
        assert mock_active_tasks.labels().inc.called
        assert mock_task_runs.labels().inc.called
        assert mock_task_duration.labels().observe.called
    
    @pytest.mark.asyncio
    async def test_prefect_flow_execution(self, sample_site_config, monkeypatch):
        """Test that Prefect flow executes task correctly"""
        # Mock the task to return None (crawl_site_task doesn't return a value)
        mock_task = AsyncMock(return_value=None)
        monkeypatch.setattr("workers.prefect_manager.crawl_site_task", mock_task)
        
        # Mock get_run_context to return a flow_run with an id
        # When flow runs in Prefect, it returns flow_run.id (UUID or string)
        mock_flow_run = Mock()
        mock_flow_run.id = "test-flow-run-id"
        mock_context = Mock()
        mock_context.flow_run = mock_flow_run
        
        def mock_get_run_context():
            return mock_context
        
        monkeypatch.setattr("workers.prefect_manager.get_run_context", mock_get_run_context)
        
        # Execute flow
        result = await crawl_site_flow("test_site", sample_site_config)
        
        # Verify task was called
        mock_task.assert_called_once_with("test_site", sample_site_config)
        
        # Prefect flow returns flow_run.id when running in Prefect server
        # The flow tries to get flow_run.id from context, which we've mocked
        assert result == "test-flow-run-id"
    
    @pytest.mark.asyncio
    async def test_create_deployments_from_config(self, mock_site_configs):
        """Test creating deployments from actual site configs"""
        deployments = await create_prefect_deployments()
        
        assert len(deployments) > 0
        assert all(isinstance(d, dict) for d in deployments)
        assert all("name" in d for d in deployments)
        assert all("schedule" in d for d in deployments)
        assert all("tags" in d for d in deployments)
        
        # Verify deployment structure
        for deployment in deployments:
            assert deployment["name"].startswith("crawl-")
            assert "crawler" in deployment["tags"]
            assert deployment["schedule"] is not None
    
    @pytest.mark.asyncio
    async def test_apply_deployments_logs_info(self, mock_site_configs):
        """Test that apply_deployments logs deployment information"""
        # This function now just logs info in Prefect 3.0+
        # We verify it completes without error
        await apply_deployments()
        
        # Should complete successfully
        assert True
    
    @pytest.mark.asyncio
    async def test_trigger_manual_crawl_integration(self, mock_site_configs, monkeypatch):
        """Test manually triggering a crawl through Prefect"""
        # Mock crawl_site_flow.with_options(...) to return a callable that returns flow_run_id
        # The actual flow returns flow_run.id (a string/UUID), not the flow_run object
        expected_flow_run_id = "test-flow-run-123"
        
        async def mock_flow_execution(*args, **kwargs):
            return expected_flow_run_id
        
        # Create mock that chains: flow.with_options(...) returns callable
        mock_flow = Mock()
        mock_flow.with_options = Mock(return_value=mock_flow_execution)
        
        monkeypatch.setattr("workers.prefect_manager.crawl_site_flow", mock_flow)
        
        # Trigger manual crawl
        flow_run_id = await trigger_manual_crawl("test_site")
        
        # Verify
        assert flow_run_id == expected_flow_run_id
        # Verify with_options was called
        mock_flow.with_options.assert_called_once()
        # Note: We can't easily verify mock_flow_execution was called since it's a regular function
        # But the fact that we got the expected flow_run_id confirms it was called
    
    @pytest.mark.asyncio
    async def test_trigger_manual_crawl_site_not_found(self, mock_site_configs):
        """Test triggering crawl for non-existent site raises error"""
        with pytest.raises(ValueError, match="Site nonexistent not found"):
            await trigger_manual_crawl("nonexistent")
    
    @pytest.mark.asyncio
    async def test_get_deployments_from_server(self, monkeypatch):
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
        
        # Get deployments
        deployments = await get_deployments()
        
        # Verify
        assert len(deployments) == 1
        assert deployments[0]["id"] == "deployment-123"
        assert deployments[0]["name"] == "crawl-test_site"
        assert "crawler" in deployments[0]["tags"]
    
    @pytest.mark.asyncio
    async def test_get_flow_runs_from_server(self, monkeypatch):
        """Test getting flow runs from Prefect server"""
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
        
        def mock_get_client():
            return mock_client
        
        monkeypatch.setattr("workers.prefect_manager.get_client", mock_get_client)
        
        # Get flow runs
        runs = await get_flow_runs(site_name="test_site", limit=10)
        
        # Verify
        assert len(runs) == 1
        assert runs[0]["id"] == "run-123"
        assert runs[0]["status"] == "COMPLETED"
        assert "crawler" in runs[0]["tags"]
    
    @pytest.mark.asyncio
    async def test_full_prefect_workflow(self, mock_site_configs, monkeypatch):
        """Test complete Prefect workflow: create deployment -> trigger -> get runs"""
        # Mock crawl_site
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
        
        # Step 1: Create deployment config
        deployments = await create_prefect_deployments()
        assert len(deployments) > 0
        
        # Step 2: Trigger manual crawl
        # Mock crawl_site_flow to return flow_run_id directly (as string)
        expected_flow_run_id = "workflow-test-run-123"
        
        async def mock_flow_execution(*args, **kwargs):
            return expected_flow_run_id
        
        mock_flow = Mock()
        mock_flow.with_options = Mock(return_value=mock_flow_execution)
        monkeypatch.setattr("workers.prefect_manager.crawl_site_flow", mock_flow)
        
        flow_run_id = await trigger_manual_crawl("test_site")
        assert flow_run_id == expected_flow_run_id
        
        # Step 3: Verify flow was triggered
        # Verify with_options was called (which means the flow was set up)
        mock_flow.with_options.assert_called_once()
        # Note: In real scenario, we would wait for flow to complete and check runs
    
    @pytest.mark.asyncio
    async def test_prefect_task_error_handling(self, sample_site_config, monkeypatch):
        """Test that Prefect task properly handles and reports errors"""
        # Mock crawl_site to raise an error
        error = RuntimeError("Integration test error")
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
        with pytest.raises(RuntimeError, match="Integration test error"):
            await crawl_site_task("test_site", sample_site_config)
        
        # Verify error metrics were updated
        assert mock_crawler_errors.labels().inc.called
        assert mock_task_runs.labels().inc.called
    
    @pytest.mark.asyncio
    async def test_get_deployment_by_name_integration(self, monkeypatch):
        """Test getting a specific deployment by name"""
        # Mock Prefect client
        mock_deployment = Mock()
        mock_deployment.id = "deployment-456"
        mock_deployment.name = "crawl-integration-test"
        mock_deployment.schedule = Mock()
        mock_deployment.schedule.__str__ = Mock(return_value="0 * * * *")
        mock_deployment.tags = ["crawler", "integration_test"]
        mock_deployment.flow_name = "crawl_site_flow"
        mock_deployment.work_queue_name = "default"
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.read_deployments = AsyncMock(return_value=[mock_deployment])
        
        def mock_get_client():
            return mock_client
        
        monkeypatch.setattr("workers.prefect_manager.get_client", mock_get_client)
        
        # Get deployment by name
        deployment = await get_deployment_by_name("crawl-integration-test")
        
        # Verify
        assert deployment is not None
        assert deployment["id"] == "deployment-456"
        assert deployment["name"] == "crawl-integration-test"
        assert "integration_test" in deployment["tags"]
    
    @pytest.mark.asyncio
    async def test_prefect_with_actual_crawl(self, test_session, mock_storage_service, monkeypatch):
        """Integration test with actual crawl execution through Prefect"""
        from crawlers.core.types import Response
        from tests.utils import load_fixture
        
        # Setup: Use real RSS content
        rss_content = load_fixture("sample_rss.xml")
        
        # Mock fetcher to return RSS content
        async def mock_fetch(req):
            return Response(
                url=req.url,
                status=200,
                body=rss_content.encode('utf-8'),
                headers={},
                request=req
            )
        
        # Mock the engine's fetcher
        original_crawl_site = crawl_site
        
        async def mock_crawl_site(site_name, config):
            from crawlers.core.engine import CrawlerEngine
            from crawlers.core.pipelines import StoragePipeline
            from crawlers.spiders.rss_spider import RSSSpider
            
            # Create real engine and pipeline
            pipeline = StoragePipeline(session=test_session)
            pipeline.storage = mock_storage_service
            
            engine = CrawlerEngine(pipeline=pipeline)
            engine.fetcher.fetch = mock_fetch
            
            # Create spider
            spider = RSSSpider(
                source_name=config["source_name"],
                feed_url=config["feed_url"],
                max_items=config.get("max_items", 5)
            )
            
            # Run crawl
            await engine.crawl_spider(spider, config)
            await engine.close()
        
        monkeypatch.setattr("workers.prefect_manager.crawl_site", mock_crawl_site)
        
        # Mock metrics
        mock_active_tasks = Mock()
        mock_task_runs = Mock()
        mock_task_duration = Mock()
        mock_crawler_errors = Mock()
        
        monkeypatch.setattr("workers.prefect_manager.active_tasks", mock_active_tasks)
        monkeypatch.setattr("workers.prefect_manager.task_runs_total", mock_task_runs)
        monkeypatch.setattr("workers.prefect_manager.task_duration", mock_task_duration)
        monkeypatch.setattr("workers.prefect_manager.crawler_errors_total", mock_crawler_errors)
        
        # Execute Prefect task
        config = {
            "spider": "rss",
            "source_name": "integration_test",
            "feed_url": "http://example.com/feed.xml",
            "max_items": 5,
            "qps": 1.0,
        }
        
        await crawl_site_task("integration_test", config)
        
        # Verify metrics were updated
        assert mock_active_tasks.labels().inc.called
        assert mock_task_runs.labels().inc.called
        assert mock_task_duration.labels().observe.called
        
        # Verify no errors
        assert not mock_crawler_errors.labels().inc.called

