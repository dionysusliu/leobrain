"""Prefect 相关类型定义"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from prefect.schedules import Schedule

from configs.types import SiteConfig  # 从 configs 导入


class DeploymentParameters(BaseModel):
    """Deployment 参数模型"""
    site_name: str = Field(
        ...,
        description="站点名称"
    )
    config: SiteConfig = Field(
        ...,
        description="站点配置"
    )
    
    class Config:
        """Pydantic 配置"""
        json_schema_extra = {
            "example": {
                "site_name": "bbc",
                "config": {
                    "spider": "rss",
                    "source_name": "bbc",
                    "feed_url": "http://feeds.bbci.co.uk/news/rss.xml",
                    "cron": "*/10 * * * *",
                    "work_pool": "default"
                }
            }
        }
        
        

class DeploymentConfig(BaseModel):
    """
    Deployment 配置模型
    
    用于生成 Prefect Deployment 的配置。
    实际部署时使用 flow.deploy() 方法。
    
    只包含必要的和推荐的参数，遵循"如无必要，勿增实体"原则。
    """
    flow_name: str = Field(
        ...,
        description="Flow 名称（必须与 @flow 装饰器中的 name 一致）"
    )
    name: str = Field(
        ...,
        description="Deployment 名称"
    )
    parameters: DeploymentParameters = Field(
        ...,
        description="Deployment 参数"
    )
    cron: str = Field(
        ...,
        description="Cron 表达式，定义执行时间（必填）"
    )
    work_pool_name: str = Field(
        default="default",
        description="Work Pool 名称"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="标签列表，用于筛选和分组"
    )
    description: Optional[str] = Field(
        default=None,
        description="Deployment 描述"
    )
    enforce_parameter_schema: bool = Field(
        default=True,
        description="是否强制参数模式验证"
    )
    paused: bool = Field(
        default=False,
        description="是否暂停部署（创建后可通过 Prefect UI 管理）"
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证 Deployment 名称"""
        if not v or len(v) < 3:
            raise ValueError("Deployment name must be at least 3 characters")
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError(
                "Deployment name can only contain alphanumeric characters, "
                "hyphens, and underscores"
            )
        return v
    
    @field_validator('cron')
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """
        验证 Cron 表达式有效性
        
        使用 Prefect 的 Schedule 来验证 cron 表达式是否有效
        """
        try:
            Schedule(cron=v, timezone="UTC")
        except Exception as e:
            raise ValueError(
                f"Invalid cron expression '{v}': {e}. "
                f"Cron expression must have 5 parts: minute hour day month weekday"
            ) from e
        return v
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """验证标签"""
        if len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")
        return v
    
    class Config:
        """Pydantic 配置"""
        json_schema_extra = {
            "example": {
                "flow_name": "crawl_site_flow",
                "name": "crawl-bbc",
                "parameters": {
                    "site_name": "bbc",
                    "config": {
                        "spider": "rss",
                        "source_name": "bbc",
                        "feed_url": "http://feeds.bbci.co.uk/news/rss.xml",
                        "cron": "*/10 * * * *"
                    }
                },
                "cron": "*/10 * * * *",
                "work_pool_name": "default",
                "tags": ["crawler", "bbc"],
                "description": "Crawl deployment for bbc",
                "enforce_parameter_schema": True,
                "paused": False
            }
        }