"""配置管理模块"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
import threading
import shutil
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


@dataclass
class AppConfig:
    name: str = "Git Sync Tool"
    version: str = "1.0.0"
    language: str = "zh_CN"
    
    auto_sync: bool = True
    sync_interval: int = 300
    conflict_strategy: str = "ask"
    
    watch_enabled: bool = True
    debounce_interval: int = 1000
    ignore_patterns: List[str] = field(default_factory=lambda: [
        ".git/*",
        "__pycache__/*",
        "*.pyc",
        ".DS_Store",
        "node_modules/*",
        "*.log",
    ])
    
    github_api_url: str = "https://api.github.com"
    github_timeout: int = 30
    
    ui_theme: str = "dark"
    window_width: int = 1200
    window_height: int = 800
    show_tray_icon: bool = True
    
    log_level: str = "INFO"
    log_max_size: int = 10 * 1024 * 1024
    log_backup_count: int = 5
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


class ConfigFileHandler(FileSystemEventHandler):
    """配置文件变更处理器"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self._last_modified = 0
    
    def on_modified(self, event):
        if event.src_path == str(self.config_manager.config_path):
            current_time = time.time()
            # 防止重复触发
            if current_time - self._last_modified > 0.5:
                self._last_modified = current_time
                self.config_manager._load()
                self.config_manager._notify_listeners()


class ConfigManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, config_path: Optional[Path] = None, env: str = "default"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Optional[Path] = None, env: str = "default"):
        if self._initialized:
            return

        self.env = env
        self._listeners = []
        self._hot_reload_enabled = True
        
        if config_path is None:
            # 支持多环境配置
            config_dir = Path.home() / ".git-sync-tool"
            config_file = f"config.{env}.json"
            self.config_path = config_dir / config_file
        else:
            self.config_path = Path(config_path)

        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        self.config = AppConfig()
        self._load()
        
        # 启动配置文件监控
        self._observer = Observer()
        self._event_handler = ConfigFileHandler(self)
        self._observer.schedule(self._event_handler, str(self.config_path.parent), recursive=False)
        self._observer.start()
        
        self._initialized = True

    def _load(self):
        """加载配置"""
        from ..utils.logger import logger
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.config = AppConfig.from_dict(data)
                logger.info(f"配置文件加载成功: {self.config_path}")
            except Exception as e:
                logger.error(f"加载配置失败: {e}, 使用默认配置")
                self._save()
        else:
            logger.info(f"配置文件不存在，创建默认配置: {self.config_path}")
            self._save()

    def _save(self):
        """保存配置"""
        from ..utils.logger import logger
        
        try:
            self.config.updated_at = datetime.now()
            
            # 支持多种格式
            ext = self.config_path.suffix.lower()
            content = None
            
            if ext == '.json':
                content = json.dumps(self.config.to_dict(), indent=2, ensure_ascii=False)
            elif ext in ['.yaml', '.yml']:
                content = yaml.dump(self.config.to_dict(), allow_unicode=True, indent=2)
            
            if content:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.debug(f"配置保存成功: {self.config_path}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self.config, key, default)

    def set(self, key: str, value: Any):
        if hasattr(self.config, key):
            setattr(self.config, key, value)
            self._save()
        else:
            from ..utils.logger import logger
            logger.error(f"配置项 '{key}' 不存在")
            raise AttributeError(f"配置项 '{key}' 不存在")

    def update(self, updates: Dict[str, Any]):
        for key, value in updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self._save()

    def reset(self):
        self.config = AppConfig()
        self._save()

    def export_config(self, export_path: Path):
        shutil.copy(self.config_path, export_path)

    def import_config(self, import_path: Path):
        from ..utils.logger import logger
        
        try:
            ext = import_path.suffix.lower()
            data = None
            
            with open(import_path, 'r', encoding='utf-8') as f:
                if ext == '.json':
                    data = json.load(f)
                elif ext in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
            
            if data:
                self.config = AppConfig.from_dict(data)
                self._save()
                logger.info(f"配置导入成功: {import_path}")
        except Exception as e:
            logger.error(f"配置导入失败: {e}")
            raise

    @property
    def ignore_patterns(self) -> List[str]:
        return self.config.ignore_patterns

    def add_ignore_pattern(self, pattern: str):
        if pattern not in self.config.ignore_patterns:
            self.config.ignore_patterns.append(pattern)
            self._save()

    def remove_ignore_pattern(self, pattern: str):
        if pattern in self.config.ignore_patterns:
            self.config.ignore_patterns.remove(pattern)
            self._save()
    
    def add_listener(self, listener: Callable[[], None]):
        """添加配置变更监听器"""
        self._listeners.append(listener)
    
    def remove_listener(self, listener: Callable[[], None]):
        """移除配置变更监听器"""
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    def _notify_listeners(self):
        """通知配置变更监听器"""
        for listener in self._listeners:
            try:
                listener()
            except Exception as e:
                from ..utils.logger import logger
                logger.error(f"配置变更通知失败: {e}")
    
    def enable_hot_reload(self, enable: bool = True):
        """启用或禁用热重载"""
        self._hot_reload_enabled = enable
        if enable:
            self._observer.start()
        else:
            self._observer.stop()
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, '_observer'):
            self._observer.stop()
            self._observer.join()
