"""配置类型定义"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from prefect.schedules import Schedule
from datetime import datetime


class SiteConfig(BaseModel):
    """站点配置模型"""
    spider: str = Field(
        ...,
        description="爬虫类型（如 'rss'），字符串类型以支持未来扩展"
    )
    source_name: str = Field(
        ...,
        description="源名称，用于标识站点"
    )
    feed_url: str = Field(
        ...,
        description="RSS Feed URL"
    )
    cron: str = Field(
        ...,
        description="Cron 表达式，定义爬取频率（必填，无默认值）"
    )
    work_pool: str = Field(
        default="default",
        description="Work Pool 名称，用于指定执行环境"
    )
    qps: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="每秒请求数限制 (0.1-10.0)"
    )
    concurrency: int = Field(
        default=2,
        ge=1,
        le=10,
        description="并发数 (1-10)"
    )
    max_items: Optional[int] = Field(
        default=None,
        ge=1,
        description="最大抓取数量，None 表示无限制"
    )
    fetch_full_content: bool = Field(
        default=False,
        description="是否获取完整内容（需要额外 HTTP 请求）"
    )
    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="HTTP 请求头"
    )
    use_render: bool = Field(
        default=False,
        description="是否使用浏览器渲染（需要 Playwright）"
    )
    
    @field_validator('feed_url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """验证 URL 格式"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("feed_url must start with http:// or https://")
        return v
    
    @field_validator('cron')
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """
        验证 Cron 表达式有效性
        
        使用 Prefect 的 Schedule 来验证 cron 表达式是否有效
        """
        try:
            # 尝试创建 Schedule 对象来验证 cron 表达式
            Schedule(cron=v, timezone="UTC")
        except Exception as e:
            raise ValueError(
                f"Invalid cron expression '{v}': {e}. "
                f"Cron expression must have 5 parts: minute hour day month weekday"
            ) from e
        return v
    
    class Config:
        """Pydantic 配置"""
        json_schema_extra = {
            "example": {
                "spider": "rss",
                "source_name": "bbc",
                "feed_url": "http://feeds.bbci.co.uk/news/rss.xml",
                "cron": "*/10 * * * *",
                "work_pool": "default",
                "qps": 1.0,
                "concurrency": 2,
                "max_items": 50,
                "fetch_full_content": False,
                "headers": {
                    "User-Agent": "LeoBrain/1.0"
                },
                "use_render": False
            }
        }

    

class WorkPoolConfig(BaseModel):
    """
    Work Pool 配置模型
    
    注意：base_job_template 是 Prefect Work Pool 的内部配置，
    对于 process 类型的 Work Pool，通常使用默认配置即可。
    如果需要自定义，可以通过 Prefect UI 或 CLI 配置。
    """
    name: str = Field(
        ...,
        description="Work Pool 名称"
    )
    type: Literal["process", "docker", "kubernetes", "ecs", "cloud-run"] = Field(
        default="process",
        description="Work Pool 类型"
    )
    description: str = Field(
        default="",
        description="Work Pool 描述"
    )
    concurrency_limit: Optional[int] = Field(
        default=None,
        ge=1,
        description="并发限制，None 表示无限制"
    )
    is_paused: bool = Field(
        default=False,
        description="是否暂停"
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证 Work Pool 名称"""
        if not v or len(v) < 3:
            raise ValueError("Work Pool name must be at least 3 characters")
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError(
                "Work Pool name can only contain alphanumeric characters, "
                "hyphens, and underscores"
            )
        return v
    
    class Config:
        """Pydantic 配置"""
        json_schema_extra = {
            "example": {
                "name": "default",
                "type": "process",
                "description": "Default work pool for crawler tasks",
                "concurrency_limit": 10,
                "is_paused": False
            }
        }
        
        
