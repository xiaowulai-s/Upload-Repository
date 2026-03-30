"""数据模型定义"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import uuid


class RepoStatus(Enum):
    UNINITIALIZED = "uninitialized"
    INITIALIZED = "initialized"
    SYNCED = "synced"
    MODIFIED = "modified"
    CONFLICT = "conflict"
    ERROR = "error"


class SyncStatus(Enum):
    IDLE = "idle"
    SYNCING = "syncing"
    SUCCESS = "success"
    ERROR = "error"
    CONFLICT = "conflict"


class ChangeType(Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass
class Repository:
    id: str
    name: str
    local_path: str
    remote_url: Optional[str] = None
    branch: str = "main"
    status: RepoStatus = RepoStatus.UNINITIALIZED
    auto_sync: bool = True
    sync_interval: int = 300
    last_sync: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(cls, name: str, local_path: str, **kwargs) -> "Repository":
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            local_path=local_path,
            **kwargs
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "local_path": self.local_path,
            "remote_url": self.remote_url,
            "branch": self.branch,
            "status": self.status.value,
            "auto_sync": self.auto_sync,
            "sync_interval": self.sync_interval,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Repository":
        return cls(
            id=data["id"],
            name=data["name"],
            local_path=data["local_path"],
            remote_url=data.get("remote_url"),
            branch=data.get("branch", "main"),
            status=RepoStatus(data.get("status", "uninitialized")),
            auto_sync=data.get("auto_sync", True),
            sync_interval=data.get("sync_interval", 300),
            last_sync=datetime.fromisoformat(data["last_sync"]) if data.get("last_sync") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
        )


@dataclass
class GitStatus:
    branch: str
    ahead: int
    behind: int
    staged: List[str] = field(default_factory=list)
    unstaged: List[str] = field(default_factory=list)
    untracked: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.staged or self.unstaged or self.untracked)

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch": self.branch,
            "ahead": self.ahead,
            "behind": self.behind,
            "staged": self.staged,
            "unstaged": self.unstaged,
            "untracked": self.untracked,
            "conflicts": self.conflicts,
        }


@dataclass
class FileDiff:
    path: str
    change_type: ChangeType
    additions: int = 0
    deletions: int = 0
    diff_content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "change_type": self.change_type.value,
            "additions": self.additions,
            "deletions": self.deletions,
            "diff_content": self.diff_content,
        }


@dataclass
class SyncRecord:
    id: str
    repo_id: str
    action: str
    status: SyncStatus
    message: Optional[str] = None
    files_count: int = 0
    duration: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(cls, repo_id: str, action: str, **kwargs) -> "SyncRecord":
        return cls(
            id=str(uuid.uuid4()),
            repo_id=repo_id,
            action=action,
            **kwargs
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "repo_id": self.repo_id,
            "action": self.action,
            "status": self.status.value,
            "message": self.message,
            "files_count": self.files_count,
            "duration": self.duration,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncRecord":
        return cls(
            id=data["id"],
            repo_id=data["repo_id"],
            action=data["action"],
            status=SyncStatus(data["status"]),
            message=data.get("message"),
            files_count=data.get("files_count", 0),
            duration=data.get("duration", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )


@dataclass
class CommitInfo:
    hash: str
    author: str
    date: datetime
    message: str
    files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hash": self.hash,
            "author": self.author,
            "date": self.date.isoformat(),
            "message": self.message,
            "files": self.files,
        }
