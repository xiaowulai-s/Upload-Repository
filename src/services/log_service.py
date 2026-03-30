"""日志服务"""

import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import re

from ..models.repository import Repository, CommitInfo
from ..core.git_engine import GitEngine
from ..core.changelog_gen import ChangelogGenerator, ChangelogEntry, ChangeItem
from ..data.database import Database


class LogService:
    """日志服务"""
    
    CHANGELOG_FILE = "CHANGELOG.md"
    
    def __init__(self):
        self.db = Database()
        self.generator = ChangelogGenerator()
        self._git_engines: Dict[str, GitEngine] = {}
    
    def _get_git_engine(self, repo_id: str) -> Optional[GitEngine]:
        if repo_id not in self._git_engines:
            repo = self.db.get_repository(repo_id)
            if repo:
                self._git_engines[repo_id] = GitEngine(Path(repo.local_path))
        return self._git_engines.get(repo_id)
    
    async def generate_commit_message(
        self,
        repo_id: str,
        style: str = "conventional"
    ) -> str:
        """根据当前变更生成 commit message"""
        git_engine = self._get_git_engine(repo_id)
        if not git_engine:
            return "chore: update files"
        
        diff_result = await git_engine.get_diff()
        
        if not diff_result.success:
            return "chore: update files"
        
        diffs = diff_result.data
        
        diff_content = ""
        for diff in diffs:
            diff_content += f"diff --git a/{diff.path} b/{diff.path}\n"
            diff_content += f"{diff.diff_content}\n"
        
        if not diff_content.strip():
            status_result = await git_engine.get_status()
            if status_result.success:
                status = status_result.data
                files = status.staged + status.unstaged + status.untracked
                if files:
                    return f"chore: update {len(files)} files"
        
        return self.generator.generate_commit_message(diff_content, style)
    
    async def generate_changelog(
        self,
        repo_id: str,
        version: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 50
    ) -> str:
        """生成 CHANGELOG"""
        git_engine = self._get_git_engine(repo_id)
        if not git_engine:
            return ""
        
        log_result = await git_engine.get_log(limit=limit, since=since)
        
        if not log_result.success:
            return ""
        
        commits = log_result.data
        
        commit_dicts = []
        for commit in commits:
            commit_dicts.append({
                "hash": commit.hash,
                "author": commit.author,
                "date": commit.date.isoformat(),
                "message": commit.message,
                "files": commit.files
            })
        
        if version is None:
            version = "Unreleased"
        
        return self.generator.generate_changelog(commit_dicts, version)
    
    async def sync_changelog(
        self,
        repo_id: str,
        version: Optional[str] = None
    ) -> bool:
        """同步 CHANGELOG 到仓库"""
        repo = self.db.get_repository(repo_id)
        if not repo:
            return False
        
        changelog_path = Path(repo.local_path) / self.CHANGELOG_FILE
        
        new_content = await self.generate_changelog(repo_id, version)
        
        if not new_content:
            return False
        
        if changelog_path.exists():
            existing_content = changelog_path.read_text(encoding="utf-8")
            merged = self.generator.merge_changelog(existing_content, new_content)
            changelog_path.write_text(merged, encoding="utf-8")
        else:
            header = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"
            changelog_path.write_text(header + new_content, encoding="utf-8")
        
        return True
    
    async def get_changelog(self, repo_id: str) -> Optional[str]:
        """获取仓库的 CHANGELOG 内容"""
        repo = self.db.get_repository(repo_id)
        if not repo:
            return None
        
        changelog_path = Path(repo.local_path) / self.CHANGELOG_FILE
        
        if not changelog_path.exists():
            return None
        
        return changelog_path.read_text(encoding="utf-8")
    
    async def get_commit_history(
        self,
        repo_id: str,
        limit: int = 50,
        since: Optional[datetime] = None
    ) -> List[CommitInfo]:
        """获取提交历史"""
        git_engine = self._get_git_engine(repo_id)
        if not git_engine:
            return []
        
        result = await git_engine.get_log(limit=limit, since=since)
        
        if result.success:
            return result.data
        return []
    
    async def analyze_changes(
        self,
        repo_id: str
    ) -> Dict[str, Any]:
        """分析当前变更"""
        git_engine = self._get_git_engine(repo_id)
        if not git_engine:
            return {"error": "Git engine not available"}
        
        status_result = await git_engine.get_status()
        if not status_result.success:
            return {"error": status_result.error}
        
        status = status_result.data
        
        diff_result = await git_engine.get_diff()
        diffs = diff_result.data if diff_result.success else []
        
        staged_files = status.staged
        unstaged_files = status.unstaged
        untracked_files = status.untracked
        
        file_categories = self.generator.categorize_files(
            staged_files + unstaged_files + untracked_files
        )
        
        diff_content = ""
        for diff in diffs:
            diff_content += diff.diff_content + "\n"
        
        suggested_message = self.generator.generate_commit_message(diff_content)
        
        return {
            "status": status.to_dict(),
            "diffs": [d.to_dict() for d in diffs],
            "file_categories": file_categories,
            "suggested_message": suggested_message,
            "summary": {
                "staged_count": len(staged_files),
                "unstaged_count": len(unstaged_files),
                "untracked_count": len(untracked_files),
                "total_changes": len(staged_files) + len(unstaged_files) + len(untracked_files)
            }
        }
    
    async def generate_version_notes(
        self,
        repo_id: str,
        from_commit: str,
        to_commit: str = "HEAD"
    ) -> str:
        """生成两个版本之间的变更说明"""
        git_engine = self._get_git_engine(repo_id)
        if not git_engine:
            return ""
        
        log_result = await git_engine.get_log(limit=100)
        if not log_result.success:
            return ""
        
        commits = log_result.data
        
        in_range = False
        range_commits = []
        
        for commit in commits:
            if commit.hash == to_commit or commit.hash.startswith(to_commit):
                in_range = True
            
            if in_range:
                range_commits.append(commit)
            
            if commit.hash == from_commit or commit.hash.startswith(from_commit):
                break
        
        commit_dicts = []
        for commit in range_commits:
            commit_dicts.append({
                "hash": commit.hash,
                "author": commit.author,
                "date": commit.date.isoformat(),
                "message": commit.message,
                "files": commit.files
            })
        
        return self.generator.generate_changelog(commit_dicts, "Version Notes")
    
    def format_commit_for_display(
        self,
        commit: CommitInfo,
        format_type: str = "short"
    ) -> str:
        """格式化提交信息用于显示"""
        if format_type == "short":
            return f"{commit.hash[:8]} {commit.message.split(chr(10))[0][:50]}"
        elif format_type == "medium":
            return (
                f"commit {commit.hash}\n"
                f"Author: {commit.author}\n"
                f"Date: {commit.date.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"    {commit.message}\n"
            )
        elif format_type == "full":
            files_str = "\n".join(f"    {f}" for f in commit.files)
            return (
                f"commit {commit.hash}\n"
                f"Author: {commit.author}\n"
                f"Date: {commit.date.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"    {commit.message}\n\n"
                f"Files:\n{files_str}\n"
            )
        else:
            return commit.message
