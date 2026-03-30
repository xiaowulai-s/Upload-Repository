"""配置管理模块"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
import threading
import shutil


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


class ConfigManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, config_path: Optional[Path] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Optional[Path] = None):
        if self._initialized:
            return

        if config_path is None:
            config_path = Path.home() / ".git-sync-tool" / "config.json"

        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        self.config = AppConfig()
        self._load()
        self._initialized = True

    def _load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.config = AppConfig.from_dict(data)
            except Exception as e:
                print(f"加载配置失败: {e}")
                self._save()

    def _save(self):
        try:
            self.config.updated_at = datetime.now()
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self.config, key, default)

    def set(self, key: str, value: Any):
        if hasattr(self.config, key):
            setattr(self.config, key, value)
            self._save()
        else:
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
        with open(import_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.config = AppConfig.from_dict(data)
        self._save()

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
