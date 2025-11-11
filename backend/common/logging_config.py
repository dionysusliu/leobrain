"""Structured logging configuration for JSON output to file"""
import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pathlib import Path
import os


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


def setup_logging(level: str = "INFO", log_dir: Optional[str] = None):
    """
    Setup structured JSON logging
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files (default: /var/log/leobrain or from LOG_DIR env)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    formatter = JSONFormatter()
    
    # Determine log directory
    # Default to project logs directory for development, or system directory if LOG_DIR is set
    if log_dir is None:
        # Check if we're in a project directory (has backend/ or is backend/)
        project_root = Path(__file__).parent.parent.parent
        default_log_dir = project_root / "logs" if (project_root / "backend").exists() or (project_root / "backend").name == "backend" else "/var/log/leobrain"
        log_dir = os.getenv("LOG_DIR", str(default_log_dir))
    log_path = Path(log_dir)
    try:
        log_path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Fallback to current directory if system directory is not accessible
        log_path = Path("./logs")
        log_path.mkdir(parents=True, exist_ok=True)
        log_dir = str(log_path)
    
    # File handler for Promtail collection
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_path / "leobrain-api.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Only output ERROR and above to stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.ERROR)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    logging.info("Logging configured: level=%s, log_dir=%s", level, log_path)

