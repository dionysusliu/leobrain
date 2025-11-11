"""Prefect 工具函数"""
from typing import Dict, Any
from common.prefect_types import DeploymentConfig

import logging

logger = logging.getLogger(__name__)


def helper_deployment_config_to_kwargs(deployment_config: DeploymentConfig) -> Dict[str, Any]:
    """
    将 DeploymentConfig 转换为 flow.deploy() 的参数
    
    Args:
        deployment_config: 类型化的部署配置
    """
    kwargs = {
        "name": deployment_config.name,
        "work_pool_name": deployment_config.work_pool_name,
        "parameters": deployment_config.parameters.model_dump(),
        "cron": deployment_config.cron,
        "tags": deployment_config.tags,
        "enforce_parameter_schema": deployment_config.enforce_parameter_schema,
        "paused": deployment_config.paused,
    }
    
    # 添加可选参数
    if deployment_config.description:
        kwargs["description"] = deployment_config.description
    
    return kwargs