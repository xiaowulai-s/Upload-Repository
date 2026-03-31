"""日志工具类"""

import os
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger
from typing import Optional, Union


class Logger:
    """日志管理器"""
    
    def __init__(self):
        self._log_dir = Path.home() / ".git_sync_tool" / "logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logger()
    
    def _setup_logger(self):
        """配置日志器"""
        # 移除默认处理器
        logger.remove()
        
        # 定义日志格式
        log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        audit_format = "{time:YYYY-MM-DD HH:mm:ss} | AUDIT | {user} | {action} | {repo_id} | {details}"
        
        # 控制台输出 - 只显示INFO及以上级别
        logger.add(
            sys.stdout,
            level="INFO",
            format=log_format,
            colorize=True
        )
        
        # 文件输出 - 所有级别
        logger.add(
            str(self._log_dir / "app.log"),
            level="DEBUG",
            format=log_format,
            rotation="1 week",
            retention="1 month",
            compression="zip"
        )
        
        # 错误日志 - 只记录ERROR及以上级别
        logger.add(
            str(self._log_dir / "error.log"),
            level="ERROR",
            format=log_format,
            rotation="1 day",
            retention="1 month",
            compression="zip"
        )
        
        # 审计日志
        logger.add(
            str(self._log_dir / "audit.log"),
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | AUDIT | {extra[user]} | {extra[action]} | {extra[repo_id]} | {extra[details]}",
            rotation="1 day",
            retention="6 months",
            compression="zip",
            filter=lambda record: record["extra"].get("audit") is True
        )
    
    @property
    def log(self):
        """获取日志器实例"""
        return logger
    
    def debug(self, message: str, **kwargs):
        """DEBUG级别日志"""
        self.log.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """INFO级别日志"""
        self.log.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """WARNING级别日志"""
        self.log.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """ERROR级别日志"""
        self.log.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """CRITICAL级别日志"""
        self.log.critical(message, **kwargs)
    
    def audit(self, user: str, action: str, repo_id: Optional[str] = None, details: str = ""):
        """审计日志"""
        self.log.info(
            "",
            user=user,
            action=action,
            repo_id=repo_id or "-",
            details=details,
            audit=True
        )
    
    def get_log_path(self) -> Path:
        """获取日志目录路径"""
        return self._log_dir


# 创建全局日志实例
logger_instance = Logger()
logger = logger_instance.log
