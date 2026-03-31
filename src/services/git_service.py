"""Git 操作服务"""

import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import time

from ..models.repository import Repository, SyncRecord, SyncStatus, GitStatus, CommitInfo
from ..data.database import Database
from ..core.git_engine import GitEngine, Result
from ..utils.exceptions import GitOperationError, RepositoryNotFoundError, ConflictError


class GitService:
    """Git 操作服务"""

    def __init__(self):
        self.db = Database()
        self._git_engines: Dict[str, GitEngine] = {}

    def _get_git_engine(self, repo_id: str) -> Optional[GitEngine]:
        if repo_id not in self._git_engines:
            repo = self.db.get_repository(repo_id)
            if repo:
                self._git_engines[repo_id] = GitEngine(Path(repo.local_path))
        return self._git_engines.get(repo_id)

    async def pull(
        self, 
        repo_id: str, 
        remote: str = "origin",
        branch: Optional[str] = None
    ) -> SyncRecord:
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine or not git_engine.is_git_repo:
            raise GitOperationError("不是有效的 Git 仓库")
        
        start_time = time.time()
        record = SyncRecord.create(
            repo_id=repo_id,
            action="pull",
            status=SyncStatus.SYNCING
        )
        
        result = await git_engine.pull(remote, branch or repo.branch)
        
        record.duration = time.time() - start_time
        
        if result.success:
            record.status = SyncStatus.SUCCESS
            record.message = "Pull successful"
            
            repo.last_sync = datetime.now()
            self.db.update_repository(repo)
        else:
            if "CONFLICT" in (result.error or ""):
                record.status = SyncStatus.CONFLICT
                record.message = result.error
                raise ConflictError(result.error)
            else:
                record.status = SyncStatus.ERROR
                record.message = result.error
                raise GitOperationError(result.error)
        
        self.db.insert_sync_record(record)
        return record

    async def push(
        self, 
        repo_id: str,
        remote: str = "origin",
        branch: Optional[str] = None,
        set_upstream: bool = False
    ) -> SyncRecord:
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine or not git_engine.is_git_repo:
            raise GitOperationError("不是有效的 Git 仓库")
        
        start_time = time.time()
        record = SyncRecord.create(
            repo_id=repo_id,
            action="push",
            status=SyncStatus.SYNCING
        )
        
        result = await git_engine.push(
            remote, 
            branch or repo.branch,
            set_upstream
        )
        
        record.duration = time.time() - start_time
        
        if result.success:
            record.status = SyncStatus.SUCCESS
            record.message = "Push successful"
            
            repo.last_sync = datetime.now()
            self.db.update_repository(repo)
        else:
            record.status = SyncStatus.ERROR
            record.message = result.error
            raise GitOperationError(result.error)
        
        self.db.insert_sync_record(record)
        return record

    async def commit(
        self, 
        repo_id: str, 
        message: Optional[str] = None,
        files: Optional[List[str]] = None,
        author: Optional[str] = None
    ) -> SyncRecord:
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine or not git_engine.is_git_repo:
            raise GitOperationError("不是有效的 Git 仓库")
        
        start_time = time.time()
        record = SyncRecord.create(
            repo_id=repo_id,
            action="commit",
            status=SyncStatus.SYNCING
        )
        
        # 自动生成提交信息
        if not message or not message.strip():
            status_result = await git_engine.get_status()
            if status_result.success:
                status = status_result.data
                # 根据文件变化自动生成提交信息
                changed_files = len(status.staged) + len(status.unstaged)
                message = f"Auto commit: {changed_files} file(s) changed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                message = f"Auto commit at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        if files:
            add_result = await git_engine.add(files)
        else:
            add_result = await git_engine.add()
        
        if not add_result.success:
            record.status = SyncStatus.ERROR
            record.message = add_result.error
            self.db.insert_sync_record(record)
            raise GitOperationError(f"添加文件失败: {add_result.error}")
        
        result = await git_engine.commit(message, author)
        
        record.duration = time.time() - start_time
        
        if result.success:
            record.status = SyncStatus.SUCCESS
            record.message = f"Commit: {result.data.get('hash', '')[:8]}"
            record.files_count = len(files) if files else 1
        else:
            record.status = SyncStatus.ERROR
            record.message = result.error
            raise GitOperationError(result.error)
        
        self.db.insert_sync_record(record)
        return result

    async def sync(
        self, 
        repo_id: str,
        commit_message: Optional[str] = None,
        auto_commit: bool = True,
        retry_count: int = 1
    ) -> SyncRecord:
        """同步仓库，包含自动拉取、自动提交和自动推送"""
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine or not git_engine.is_git_repo:
            raise GitOperationError("不是有效的 Git 仓库")
        
        start_time = time.time()
        record = SyncRecord.create(
            repo_id=repo_id,
            action="sync",
            status=SyncStatus.SYNCING
        )
        
        try:
            # 1. 拉取远程代码，带重试机制
            pull_result = None
            for attempt in range(retry_count + 1):
                pull_result = await git_engine.pull()
                if pull_result.success:
                    break
                elif "CONFLICT" in (pull_result.error or ""):
                    # 冲突情况，不重试
                    record.status = SyncStatus.CONFLICT
                    record.message = f"合并冲突: {pull_result.error}"
                    self.db.insert_sync_record(record)
                    raise ConflictError(pull_result.error)
                elif attempt < retry_count:
                    # 临时网络问题，重试
                    logger.warning(f"拉取失败，{attempt + 1}秒后重试: {pull_result.error}")
                    await asyncio.sleep(1)
            
            if not pull_result.success:
                record.status = SyncStatus.ERROR
                record.message = f"拉取失败: {pull_result.error}"
                self.db.insert_sync_record(record)
                raise GitOperationError(pull_result.error)
            
            # 2. 检查本地状态
            status_result = await git_engine.get_status()
            
            if status_result.success:
                status: GitStatus = status_result.data
                
                if status.has_changes and auto_commit:
                    # 3. 自动生成智能提交信息
                    if not commit_message or not commit_message.strip():
                        changed_files = len(status.staged) + len(status.unstaged)
                        if status.untracked:
                            changed_files += len(status.untracked)
                        commit_message = f"Auto sync: {changed_files} file(s) changed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    # 4. 自动提交
                    commit_result = await git_engine.commit(commit_message)
                    
                    if not commit_result.success:
                        record.status = SyncStatus.ERROR
                        record.message = f"提交失败: {commit_result.error}"
                        self.db.insert_sync_record(record)
                        raise GitOperationError(commit_result.error)
                    
                    # 5. 自动推送
                    push_result = None
                    for attempt in range(retry_count + 1):
                        push_result = await git_engine.push()
                        if push_result.success:
                            break
                        elif attempt < retry_count:
                            # 临时网络问题，重试
                            logger.warning(f"推送失败，{attempt + 1}秒后重试: {push_result.error}")
                            await asyncio.sleep(1)
                    
                    if not push_result.success:
                        record.status = SyncStatus.ERROR
                        record.message = f"推送失败: {push_result.error}"
                        self.db.insert_sync_record(record)
                        raise GitOperationError(push_result.error)
                    
                    record.files_count = len(status.staged) + len(status.unstaged) + len(status.untracked)
            
            record.status = SyncStatus.SUCCESS
            record.message = "同步完成"
            record.duration = time.time() - start_time
            
            repo.last_sync = datetime.now()
            repo.status = RepoStatus.SYNCED
            self.db.update_repository(repo)
            
        except Exception as e:
            record.status = SyncStatus.ERROR
            record.message = str(e)
            record.duration = time.time() - start_time
            self.db.insert_sync_record(record)
            raise
        
        self.db.insert_sync_record(record)
        return record

    async def get_status(self, repo_id: str) -> GitStatus:
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine or not git_engine.is_git_repo:
            raise GitOperationError("不是有效的 Git 仓库")
        
        result = await git_engine.get_status()
        
        if result.success:
            return result.data
        else:
            raise GitOperationError(result.error)

    async def get_diff(self, repo_id: str, staged: bool = False) -> List[Dict[str, Any]]:
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine or not git_engine.is_git_repo:
            raise GitOperationError("不是有效的 Git 仓库")
        
        result = await git_engine.get_diff(staged)
        
        if result.success:
            return [d.to_dict() for d in result.data]
        else:
            raise GitOperationError(result.error)

    async def get_log(
        self, 
        repo_id: str, 
        limit: int = 50,
        since: Optional[datetime] = None
    ) -> List[CommitInfo]:
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine or not git_engine.is_git_repo:
            raise GitOperationError("不是有效的 Git 仓库")
        
        result = await git_engine.get_log(limit, since)
        
        if result.success:
            return result.data
        else:
            raise GitOperationError(result.error)

    async def fetch(self, repo_id: str, remote: str = "origin") -> Result:
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine or not git_engine.is_git_repo:
            raise GitOperationError("不是有效的 Git 仓库")
        
        return await git_engine.fetch(remote)

    async def reset(
        self, 
        repo_id: str, 
        ref: str = "HEAD",
        mode: str = "mixed"
    ) -> Result:
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine or not git_engine.is_git_repo:
            raise GitOperationError("不是有效的 Git 仓库")
        
        return await git_engine.reset(ref, mode)
    
    async def get_current_branch(self, repo_id: str) -> str:
        """获取当前分支"""
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine or not git_engine.is_git_repo:
            raise GitOperationError("不是有效的 Git 仓库")
        
        result = await git_engine.get_current_branch()
        if result.success:
            return result.data
        raise GitOperationError(result.error)
    
    async def get_branches(self, repo_id: str) -> List[Dict[str, Any]]:
        """获取所有分支"""
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine or not git_engine.is_git_repo:
            raise GitOperationError("不是有效的 Git 仓库")
        
        result = await git_engine.get_branches()
        if result.success:
            return result.data
        raise GitOperationError(result.error)
    
    async def create_branch(self, repo_id: str, branch_name: str) -> str:
        """创建新分支"""
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine or not git_engine.is_git_repo:
            raise GitOperationError("不是有效的 Git 仓库")
        
        result = await git_engine.create_branch(branch_name)
        if result.success:
            # 更新仓库当前分支
            repo.branch = branch_name
            self.db.update_repository(repo)
            return result.data
        raise GitOperationError(result.error)
    
    async def switch_branch(self, repo_id: str, branch_name: str) -> str:
        """切换分支"""
        repo = self.db.get_repository(repo_id)
        if not repo:
            raise RepositoryNotFoundError(f"仓库不存在: {repo_id}")
        
        git_engine = self._get_git_engine(repo_id)
        if not git_engine or not git_engine.is_git_repo:
            raise GitOperationError("不是有效的 Git 仓库")
        
        result = await git_engine.switch_branch(branch_name)
        if result.success:
            # 更新仓库当前分支
            repo.branch = branch_name
            self.db.update_repository(repo)
            return result.data
        raise GitOperationError(result.error)
