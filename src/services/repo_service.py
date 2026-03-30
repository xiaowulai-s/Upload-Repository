"""仓库管理服务"""

import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
import shutil

from ..models.repository import Repository, RepoStatus, SyncRecord, SyncStatus
from ..data.database import Database
from ..data.config_manager import ConfigManager
from ..core.git_engine import GitEngine, Result
from ..utils.exceptions import (
    RepositoryNotFoundError, 
    RepositoryExistsError,
    GitOperationError,
    ValidationError
)


class RepoService:
    """仓库管理服务"""

    def __init__(self):
        self.db = Database()
        self.config = ConfigManager()
        self._git_engines: Dict[str, GitEngine] = {}

    def _get_git_engine(self, repo_id: str) -> GitEngine:
        if repo_id not in self._git_engines:
            repo = self.db.get_repository(repo_id)
            if repo:
                self._git_engines[repo_id] = GitEngine(Path(repo.local_path))
        return self._git_engines.get(repo_id)

    def bind_local_folder(
        self, 
        folder_path: Path, 
        name: Optional[str] = None,
        remote_url: Optional[str] = None
    ) -> Repository:
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            raise ValidationError(f"文件夹不存在: {folder_path}")
        
        existing = self.db.get_repository_by_path(str(folder_path))
        if existing:
            raise RepositoryExistsError(f"该文件夹已绑定: {existing.id}")
        
        if name is None:
            name = folder_path.name
        
        git_engine = GitEngine(folder_path)
        
        if git_engine.is_git_repo:
            status = RepoStatus.INITIALIZED
            if remote_url is None:
                result = asyncio.run(git_engine.get_remote_url())
                if result.success:
                    remote_url = result.data
        else:
            status = RepoStatus.UNINITIALIZED
        
        repo = Repository.create(
            name=name,
            local_path=str(folder_path),
            remote_url=remote_url,
            status=status
        )
        
        self.db.insert_repository(repo)
        
        return repo

    async def init_repository(self, repo_id: str) -> Result:
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = GitEngine(Path(repo.local_path))
        
        if git_engine.is_git_repo:
            return Result.ok("仓库已初始化")
        
        result = git_engine.init()
        
        if result.success:
            repo.status = RepoStatus.INITIALIZED
            self.db.update_repository(repo)
            self._git_engines[repo_id] = git_engine
        
        return result

    async def clone_repository(
        self, 
        url: str, 
        target_path: Path,
        name: Optional[str] = None,
        branch: Optional[str] = None
    ) -> Repository:
        target_path = Path(target_path)
        
        if target_path.exists() and any(target_path.iterdir()):
            raise ValidationError(f"目标目录不为空: {target_path}")
        
        git_engine = GitEngine(target_path)
        result = await git_engine.clone(url, branch)
        
        if not result.success:
            raise GitOperationError(result.error)
        
        if name is None:
            name = target_path.name
        
        remote_result = await git_engine.get_remote_url()
        remote_url = remote_result.data if remote_result.success else url
        
        branch_result = await git_engine.get_current_branch()
        current_branch = branch_result.data if branch_result.success else "main"
        
        repo = Repository.create(
            name=name,
            local_path=str(target_path),
            remote_url=remote_url,
            branch=current_branch,
            status=RepoStatus.SYNCED
        )
        
        self.db.insert_repository(repo)
        self._git_engines[repo.id] = git_engine
        
        return repo

    def get_repository(self, repo_id: str) -> Optional[Repository]:
        return self.db.get_repository(repo_id)

    def get_all_repositories(self) -> List[Repository]:
        return self.db.get_all_repositories()

    def remove_repository(self, repo_id: str, delete_local: bool = False) -> bool:
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        if delete_local:
            local_path = Path(repo.local_path)
            if local_path.exists():
                shutil.rmtree(local_path)
        
        if repo_id in self._git_engines:
            del self._git_engines[repo_id]
        
        return self.db.delete_repository(repo_id)

    async def get_repo_status(self, repo_id: str) -> Dict[str, Any]:
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine:
            git_engine = GitEngine(Path(repo.local_path))
            self._git_engines[repo_id] = git_engine
        
        if not git_engine.is_git_repo:
            return {
                "repo": repo.to_dict(),
                "git_status": None,
                "message": "不是 Git 仓库"
            }
        
        status_result = await git_engine.get_status()
        branch_result = await git_engine.get_current_branch()
        
        git_status = status_result.data.to_dict() if status_result.success else None
        current_branch = branch_result.data if branch_result.success else repo.branch
        
        if git_status:
            if git_status.get("has_changes"):
                repo.status = RepoStatus.MODIFIED
            elif git_status.get("has_conflicts"):
                repo.status = RepoStatus.CONFLICT
            else:
                repo.status = RepoStatus.SYNCED
            
            self.db.update_repository(repo)
        
        return {
            "repo": repo.to_dict(),
            "git_status": git_status,
            "current_branch": current_branch
        }

    async def connect_remote(
        self, 
        repo_id: str, 
        remote_url: str,
        remote_name: str = "origin"
    ) -> Result:
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine or not git_engine.is_git_repo:
            raise GitOperationError("不是 Git 仓库，请先初始化")
        
        result = await git_engine.add_remote(remote_name, remote_url)
        
        if result.success:
            repo.remote_url = remote_url
            self.db.update_repository(repo)
        
        return result

    async def switch_branch(self, repo_id: str, branch: str) -> Result:
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine:
            raise GitOperationError("Git 引擎未初始化")
        
        result = await git_engine.switch_branch(branch)
        
        if result.success:
            repo.branch = branch
            self.db.update_repository(repo)
        
        return result

    async def create_branch(self, repo_id: str, branch: str) -> Result:
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine:
            raise GitOperationError("Git 引擎未初始化")
        
        result = await git_engine.create_branch(branch)
        
        if result.success:
            repo.branch = branch
            self.db.update_repository(repo)
        
        return result

    async def get_branches(self, repo_id: str) -> List[Dict[str, Any]]:
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine:
            raise GitOperationError("Git 引擎未初始化")
        
        result = await git_engine.get_branches()
        
        if result.success:
            return result.data
        else:
            raise GitOperationError(result.error)

    def get_sync_history(self, repo_id: str, limit: int = 50) -> List[SyncRecord]:
        return self.db.get_sync_records(repo_id, limit)
