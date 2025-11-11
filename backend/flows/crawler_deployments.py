"""爬虫 Flow 的部署逻辑"""
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from prefect import get_client
from prefect.client.schemas.actions import WorkPoolCreate

from flows.crawler_flows import pf_flow_crawl_site_by_name
from configs.loaders import load_site_configs, load_work_pool_configs
from common.prefect_types import DeploymentConfig, DeploymentParameters
from common.prefect_utils import helper_deployment_config_to_kwargs

logger = logging.getLogger(__name__)


def get_crawler_deployment_configs() -> List[DeploymentConfig]:
    """
    从配置文件生成所有爬虫部署配置
    
    Returns:
        类型化的部署配置列表
        
    示例:
        >>> configs = get_crawler_deployment_configs()
        >>> for config in configs:
        ...     print(config.name)  # IDE 自动补全
    """
    site_configs = load_site_configs()
    
    deployments = []
    for site_name, site_config in site_configs.items():
        # 创建类型化的部署配置
        deployment = DeploymentConfig(
            flow_name="crawl_site_by_name",  # 与 flow 定义中的 name 一致
            name=f"crawl-{site_name}",
            parameters=DeploymentParameters(
                site_name=site_name,
                config=site_config,
            ),
            cron=site_config.cron,
            work_pool_name=site_config.work_pool,
            tags=["crawler", site_name],
            description=f"Crawl deployment for {site_name}",
        )
        
        deployments.append(deployment)
    
    logger.info(f"Generated {len(deployments)} deployment configurations")
    return deployments


async def ensure_work_pools() -> int:
    """
    确保 Work Pools 存在，如果不存在则创建
    
    Returns:
        创建的 Work Pool 数量
    """
    pool_configs = load_work_pool_configs()
    
    if not pool_configs:
        logger.info("No work pool configurations found, skipping work pool creation")
        return 0
    
    created_count = 0
    
    async with get_client() as client:
        for pool_id, pool_config in pool_configs.items():
            try:
                # 检查 Work Pool 是否已存在
                existing_pool = await client.read_work_pool(pool_config.name)
                if existing_pool:
                    logger.info(f"Work Pool '{pool_config.name}' already exists, skipping")
                    continue
            except Exception:
                # Work Pool 不存在，需要创建
                pass
            
            try:
                # 创建 Work Pool
                work_pool = await client.create_work_pool(
                    WorkPoolCreate(
                        name=pool_config.name,
                        type=pool_config.type,
                        description=pool_config.description,
                        is_paused=pool_config.is_paused,
                        concurrency_limit=pool_config.concurrency_limit,
                    )
                )
                logger.info(f"✓ Created Work Pool: {pool_config.name} (type: {pool_config.type})")
                created_count += 1
            except Exception as e:
                logger.error(f"Failed to create Work Pool '{pool_config.name}': {e}")
    
    return created_count


async def deploy_crawler_flows(
    deployment_configs: Optional[List[DeploymentConfig]] = None,
    ensure_work_pools_first: bool = True
) -> Dict[str, Any]:
    """
    部署所有爬虫 flow 的部署配置
    
    Args:
        deployment_configs: 部署配置列表，如果为 None 则从配置文件加载
        ensure_work_pools_first: 是否在部署前确保 Work Pools 存在
        
    Returns:
        部署结果统计字典，包含:
        - total: 总部署数量
        - deployed: 成功部署数量
        - errors: 错误数量
        - error_details: 错误详情列表
        
    示例:
        >>> result = await deploy_crawler_flows()
        >>> print(f"Deployed {result['deployed']}/{result['total']} deployments")
    """
    if deployment_configs is None:
        deployment_configs = get_crawler_deployment_configs()
    
    # 确保 Work Pools 存在
    if ensure_work_pools_first:
        logger.info("Ensuring Work Pools exist...")
        await ensure_work_pools()

    # 代码源路径
    # docker容器中，挂载到 /app/backend
    flow_source_path="/app/backend"
    # flow 的入口
    flow_entrypoint = "flows/crawler_flows.py:pf_flow_crawl_site_by_name"

    # 使用 crawler flow
    flow = pf_flow_crawl_site_by_name
    
    deployed_count = 0
    error_count = 0
    errors = []
    
    logger.info(f"Starting deployment of {len(deployment_configs)} crawler deployments...")
    
    for deployment_config in deployment_configs:
        try:
            # 加载flow
            flow_from_source = await pf_flow_crawl_site_by_name.from_source(
                source=flow_source_path,
                entrypoint=flow_entrypoint,
            )

            # 验证 flow 名称匹配
            if deployment_config.flow_name != flow.name:
                raise ValueError(
                    f"Flow name mismatch: deployment expects '{deployment_config.flow_name}', "
                    f"but flow is named '{flow.name}'"
                )
            
            # 转换为 deploy 参数
            deploy_kwargs = helper_deployment_config_to_kwargs(deployment_config)
            
            # 执行部署
            deployment = await flow_from_source.deploy(**deploy_kwargs)
            
            logger.info(
                f"✓ Deployed: {deployment_config.name} "
                f"(work_pool: {deployment_config.work_pool_name}, "
                f"cron: {deployment_config.cron})"
            )
            deployed_count += 1
            
        except Exception as e:
            error_msg = f"Failed to deploy '{deployment_config.name}': {e}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
            error_count += 1
    
    result = {
        "total": len(deployment_configs),
        "deployed": deployed_count,
        "errors": error_count,
        "error_details": errors,
    }
    
    logger.info(
        f"Deployment complete: {deployed_count}/{len(deployment_configs)} successful, "
        f"{error_count} errors"
    )
    
    return result

    
async def trigger_manual_crawl(site_name: str) -> str:
    """
    手动触发爬虫 flow
    
    Args:
        site_name: 站点名称
        
    Returns:
        Flow run ID
    """
    from configs import load_site_configs
    
    site_configs = load_site_configs()
    if site_name not in site_configs:
        raise ValueError(f"Site {site_name} not found")
    
    config = site_configs[site_name]
    
    # 使用新的 flow
    flow_run = await pf_flow_crawl_site_by_name.with_options(
        name=f"manual-crawl-{site_name}"
    )(
        site_name=site_name,
        config=config
    )
    
    return str(flow_run) if flow_run else None


async def get_flow_runs(site_name: Optional[str] = None, limit: int = 20):
    """获取最近的 flow runs"""
    from prefect.client.schemas.filters import FlowRunFilter, FlowRunFilterTags
    
    async with get_client() as client:
        if site_name:
            flow_run_filter = FlowRunFilter(
                tags=FlowRunFilterTags(all_=["crawler", site_name])
            )
        else:
            flow_run_filter = FlowRunFilter(
                tags=FlowRunFilterTags(all_=["crawler"])
            )
        
        runs = await client.read_flow_runs(
            flow_run_filter=flow_run_filter,
            limit=limit,
            sort="START_TIME_DESC"
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


async def get_deployments():
    """获取所有部署"""
    from prefect.client.schemas.filters import DeploymentFilter, DeploymentFilterTags
    
    async with get_client() as client:
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
            }
            for deployment in deployments
        ]


async def get_deployment_by_name(deployment_name: str):
    """根据名称获取部署"""
    from prefect.client.schemas.filters import DeploymentFilter, DeploymentFilterName
    
    async with get_client() as client:
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
        }