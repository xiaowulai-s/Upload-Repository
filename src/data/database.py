"""数据库管理模块"""

import sqlite3
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from contextlib import contextmanager
import threading

from ..models.repository import Repository, SyncRecord, RepoStatus, SyncStatus


class Database:
    _instances = {}
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path.home() / ".git-sync-tool" / "data.db"
        
        db_key = str(db_path)
        
        if db_key not in cls._instances:
            with cls._lock:
                if db_key not in cls._instances:
                    instance = super().__new__(cls)
                    instance._db_path = Path(db_path)
                    instance._local = threading.local()
                    instance._initialized = False
                    cls._instances[db_key] = instance
        return cls._instances[db_key]

    def __init__(self, db_path: Optional[Path] = None):
        if self._initialized:
            return

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()
        self._initialized = True

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(self._db_path),
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    @contextmanager
    def transaction(self):
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_tables(self):
        with self.transaction() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS repositories (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    local_path TEXT NOT NULL UNIQUE,
                    remote_url TEXT,
                    branch TEXT DEFAULT 'main',
                    status TEXT DEFAULT 'uninitialized',
                    auto_sync INTEGER DEFAULT 1,
                    sync_interval INTEGER DEFAULT 300,
                    last_sync TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_records (
                    id TEXT PRIMARY KEY,
                    repo_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    files_count INTEGER DEFAULT 0,
                    duration REAL DEFAULT 0.0,
                    created_at TEXT,
                    FOREIGN KEY (repo_id) REFERENCES repositories(id)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_records_repo_id 
                ON sync_records(repo_id)
            """)

    def insert_repository(self, repo: Repository) -> bool:
        with self.transaction() as conn:
            conn.execute("""
                INSERT INTO repositories 
                (id, name, local_path, remote_url, branch, status, auto_sync, 
                 sync_interval, last_sync, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                repo.id, repo.name, repo.local_path, repo.remote_url,
                repo.branch, repo.status.value, int(repo.auto_sync),
                repo.sync_interval,
                repo.last_sync.isoformat() if repo.last_sync else None,
                repo.created_at.isoformat() if repo.created_at else datetime.now().isoformat(),
                repo.updated_at.isoformat() if repo.updated_at else datetime.now().isoformat()
            ))
        return True

    def update_repository(self, repo: Repository) -> bool:
        repo.updated_at = datetime.now()
        with self.transaction() as conn:
            conn.execute("""
                UPDATE repositories SET
                    name = ?, local_path = ?, remote_url = ?, branch = ?,
                    status = ?, auto_sync = ?, sync_interval = ?,
                    last_sync = ?, updated_at = ?
                WHERE id = ?
            """, (
                repo.name, repo.local_path, repo.remote_url, repo.branch,
                repo.status.value, int(repo.auto_sync), repo.sync_interval,
                repo.last_sync.isoformat() if repo.last_sync else None,
                repo.updated_at.isoformat(), repo.id
            ))
        return True

    def delete_repository(self, repo_id: str) -> bool:
        with self.transaction() as conn:
            conn.execute("DELETE FROM sync_records WHERE repo_id = ?", (repo_id,))
            conn.execute("DELETE FROM repositories WHERE id = ?", (repo_id,))
        return True

    def get_repository(self, repo_id: str) -> Optional[Repository]:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM repositories WHERE id = ?", (repo_id,)
        ).fetchone()

        if row:
            return self._row_to_repository(row)
        return None

    def get_repository_by_path(self, local_path: str) -> Optional[Repository]:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM repositories WHERE local_path = ?", (local_path,)
        ).fetchone()

        if row:
            return self._row_to_repository(row)
        return None

    def get_all_repositories(self) -> List[Repository]:
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM repositories ORDER BY created_at DESC"
        ).fetchall()

        return [self._row_to_repository(row) for row in rows]

    def _row_to_repository(self, row: sqlite3.Row) -> Repository:
        return Repository(
            id=row["id"],
            name=row["name"],
            local_path=row["local_path"],
            remote_url=row["remote_url"],
            branch=row["branch"] or "main",
            status=RepoStatus(row["status"]) if row["status"] else RepoStatus.UNINITIALIZED,
            auto_sync=bool(row["auto_sync"]),
            sync_interval=row["sync_interval"] or 300,
            last_sync=datetime.fromisoformat(row["last_sync"]) if row["last_sync"] else None,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
        )

    def insert_sync_record(self, record: SyncRecord) -> bool:
        with self.transaction() as conn:
            conn.execute("""
                INSERT INTO sync_records
                (id, repo_id, action, status, message, files_count, duration, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id, record.repo_id, record.action, record.status.value,
                record.message, record.files_count, record.duration,
                record.created_at.isoformat() if record.created_at else datetime.now().isoformat()
            ))
        return True

    def get_sync_records(
        self, 
        repo_id: Optional[str] = None, 
        limit: int = 50
    ) -> List[SyncRecord]:
        conn = self._get_connection()

        if repo_id:
            rows = conn.execute("""
                SELECT * FROM sync_records 
                WHERE repo_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (repo_id, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM sync_records 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,)).fetchall()

        return [self._row_to_sync_record(row) for row in rows]

    def _row_to_sync_record(self, row: sqlite3.Row) -> SyncRecord:
        return SyncRecord(
            id=row["id"],
            repo_id=row["repo_id"],
            action=row["action"],
            status=SyncStatus(row["status"]),
            message=row["message"],
            files_count=row["files_count"] or 0,
            duration=row["duration"] or 0.0,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
        )

    def clear_old_records(self, days: int = 30) -> int:
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        with self.transaction() as conn:
            cursor = conn.execute("""
                DELETE FROM sync_records 
                WHERE created_at < ?
            """, (cutoff.isoformat(),))
            return cursor.rowcount

    def close(self):
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None

    @classmethod
    def reset_instance(cls, db_path: Path):
        db_key = str(db_path)
        if db_key in cls._instances:
            instance = cls._instances[db_key]
            instance.close()
            del cls._instances[db_key]
