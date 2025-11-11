"""配置文件加载器（带类型验证）"""
import yaml
from pathlib import Path
from typing import Dict
from configs.types import SiteConfig, WorkPoolConfig
import logging

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).parent


def load_site_configs(config_path: Path | None = None) -> Dict[str, SiteConfig]:
    """
    加载并验证站点配置
    
    Args:
        config_path: 配置文件路径，如果为 None 则使用默认路径
        
    Returns:
        验证后的站点配置字典，key 为站点名称，value 为 SiteConfig
        
    Raises:
        FileNotFoundError: 如果配置文件不存在
        ValueError: 如果配置验证失败
        
    示例:
        >>> configs = load_site_configs()
        >>> bbc_config = configs["bbc"]  # 类型: SiteConfig
        >>> print(bbc_config.feed_url)  # IDE 自动补全
    """
    if config_path is None:
        config_path = _CONFIG_DIR / "sites.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Site config not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        raw_config = yaml.safe_load(f)
    
    if not raw_config:
        logger.warning("Site config file is empty")
        return {}
    
    # 验证每个站点配置
    validated_configs = {}
    errors = []
    
    for site_name, site_data in raw_config.items():
        try:
            validated_configs[site_name] = SiteConfig(**site_data)
        except Exception as e:
            error_msg = f"Invalid config for site '{site_name}': {e}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    if errors:
        raise ValueError(
            f"Configuration validation failed for {len(errors)} site(s):\n" +
            "\n".join(f"  - {err}" for err in errors)
        )
    
    logger.info(f"Loaded {len(validated_configs)} site configurations")
    return validated_configs


def load_work_pool_configs(config_path: Path | None = None) -> Dict[str, WorkPoolConfig]:
    """
    加载并验证 Work Pool 配置
    
    Args:
        config_path: 配置文件路径，如果为 None 则使用默认路径
        
    Returns:
        验证后的 Work Pool 配置字典，key 为 Work Pool 名称，value 为 WorkPoolConfig
        
    Raises:
        ValueError: 如果配置验证失败
        
    注意:
        如果配置文件不存在，返回空字典（不报错），因为 Work Pool 可以通过
        Prefect UI 或 CLI 创建，不一定需要配置文件。
        
    示例:
        >>> pools = load_work_pool_configs()
        >>> default_pool = pools.get("default")  # 类型: WorkPoolConfig | None
    """
    if config_path is None:
        config_path = _CONFIG_DIR / "work_pools.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        logger.warning(f"Work pool config not found: {config_path}")
        logger.info("Work pools can be created via Prefect UI or CLI if needed")
        return {}
    
    with open(config_path, 'r', encoding='utf-8') as f:
        raw_config = yaml.safe_load(f)
    
    work_pools = raw_config.get('work_pools', {})
    
    if not work_pools:
        logger.warning("No work pools found in config file")
        return {}
    
    # 验证每个 Work Pool 配置
    validated_configs = {}
    errors = []
    
    for pool_name, pool_data in work_pools.items():
        try:
            validated_configs[pool_name] = WorkPoolConfig(**pool_data)
        except Exception as e:
            error_msg = f"Invalid config for work pool '{pool_name}': {e}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    if errors:
        raise ValueError(
            f"Work pool configuration validation failed for {len(errors)} pool(s):\n" +
            "\n".join(f"  - {err}" for err in errors)
        )
    
    logger.info(f"Loaded {len(validated_configs)} work pool configurations")
    return validated_configs