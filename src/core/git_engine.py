"""Git 操作引擎"""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import os

from ..utils.logger import logger
from ..models.repository import GitStatus, FileDiff, CommitInfo, ChangeType


@dataclass
class Result:
    success: bool
    data: Any = None
    error: Optional[str] = None

    @classmethod
    def ok(cls, data: Any = None) -> "Result":
        return cls(success=True, data=data)

    @classmethod
    def error(cls, error: str) -> "Result":
        return cls(success=False, error=error)


class GitEngine:
    """Git 操作引擎 - 底层 Git 命令封装"""

    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path)
        self._git_dir = self.repo_path / ".git"

    @property
    def is_git_repo(self) -> bool:
        return self._git_dir.exists()

    async def _run_git_command(
        self, 
        *args: str, 
        check: bool = True,
        env: Optional[Dict[str, str]] = None
    ) -> Tuple[int, str, str]:
        cmd = ["git"] + list(args)
        
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=process_env
        )
        
        stdout, stderr = await process.communicate()
        
        return process.returncode, stdout.decode('utf-8', errors='replace'), stderr.decode('utf-8', errors='replace')

    def init(self) -> Result:
        logger.debug(f"Initializing git repository at {self.repo_path}")
        if self.is_git_repo:
            logger.info(f"Repository already initialized at {self.repo_path}")
            return Result.ok("Already a git repository")
        
        try:
            subprocess.run(
                ["git", "init"],
                cwd=str(self.repo_path),
                check=True,
                capture_output=True
            )
            logger.info(f"Repository initialized successfully at {self.repo_path}")
            return Result.ok("Repository initialized")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to initialize repository at {self.repo_path}: {e.stderr.decode()}")
            return Result.error(f"Init failed: {e.stderr.decode()}")

    async def clone(self, url: str, branch: Optional[str] = None) -> Result:
        logger.debug(f"Cloning repository from {url} to {self.repo_path}")
        if self.repo_path.exists() and any(self.repo_path.iterdir()):
            logger.warning(f"Directory {self.repo_path} is not empty, cannot clone")
            return Result.error("Directory is not empty")
        
        self.repo_path.parent.mkdir(parents=True, exist_ok=True)
        
        args = ["git", "clone"]
        if branch:
            args.extend(["-b", branch])
        args.extend([url, str(self.repo_path)])
        
        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"Repository cloned successfully from {url} to {self.repo_path}")
                return Result.ok("Repository cloned")
            else:
                logger.error(f"Failed to clone repository from {url} to {self.repo_path}: {stderr.decode()}")
                return Result.error(f"Clone failed: {stderr.decode()}")
        except Exception as e:
            logger.error(f"Exception occurred while cloning repository: {str(e)}")
            return Result.error(f"Clone failed: {str(e)}")

    async def get_status(self) -> Result:
        if not self.is_git_repo:
            return Result.error("Not a git repository")
        
        returncode, stdout, stderr = await self._run_git_command(
            "status", "--porcelain=v1", "--branch"
        )
        
        if returncode != 0:
            return Result.error(f"Status failed: {stderr}")
        
        lines = stdout.strip().split('\n')
        
        branch = "HEAD"
        ahead = 0
        behind = 0
        staged = []
        unstaged = []
        untracked = []
        conflicts = []
        
        for line in lines:
            if line.startswith("## "):
                branch_info = line[3:]
                if "..." in branch_info:
                    parts = branch_info.split("...")
                    branch = parts[0]
                    tracking = parts[1]
                    
                    if "[ahead " in tracking:
                        ahead = int(tracking.split("[ahead ")[1].split("]")[0])
                    if "[behind " in tracking:
                        behind = int(tracking.split("[behind ")[1].split("]")[0])
                else:
                    branch = branch_info.split("...")[0]
            elif line:
                index_status = line[0]
                work_tree_status = line[1] if len(line) > 1 else ' '
                file_path = line[3:]
                
                if index_status in ('M', 'A', 'D', 'R', 'C'):
                    staged.append(file_path)
                if work_tree_status in ('M', 'D'):
                    unstaged.append(file_path)
                if index_status == '?' and work_tree_status == '?':
                    untracked.append(file_path)
                if index_status == 'U' or work_tree_status == 'U':
                    conflicts.append(file_path)
        
        status = GitStatus(
            branch=branch,
            ahead=ahead,
            behind=behind,
            staged=staged,
            unstaged=unstaged,
            untracked=untracked,
            conflicts=conflicts
        )
        
        return Result.ok(status)

    async def add(self, files: Optional[List[str]] = None) -> Result:
        if not self.is_git_repo:
            return Result.error("Not a git repository")
        
        if files is None:
            args = ["add", "-A"]
        else:
            args = ["add"] + files
        
        returncode, stdout, stderr = await self._run_git_command(*args)
        
        if returncode == 0:
            return Result.ok("Files staged")
        else:
            return Result.error(f"Add failed: {stderr}")

    async def commit(self, message: str, author: Optional[str] = None) -> Result:
        logger.debug(f"Committing changes to {self.repo_path} with message: {message[:50]}...")
        if not self.is_git_repo:
            logger.error(f"Cannot commit, {self.repo_path} is not a git repository")
            return Result.error("Not a git repository")
        
        if not message or not message.strip():
            logger.error("Cannot commit with empty message")
            return Result.error("Commit message cannot be empty")
        
        args = ["commit", "-m", message]
        if author:
            args.extend(["--author", author])
        
        returncode, stdout, stderr = await self._run_git_command(*args)
        
        if returncode == 0:
            hash_result = await self._run_git_command("rev-parse", "HEAD")
            commit_hash = hash_result[1].strip() if hash_result[0] == 0 else None
            logger.info(f"Successfully committed to {self.repo_path} with hash: {commit_hash}")
            return Result.ok({"hash": commit_hash, "message": message})
        else:
            if "nothing to commit" in stderr:
                logger.info(f"Nothing to commit in {self.repo_path}")
                return Result.ok({"hash": None, "message": "Nothing to commit"})
            logger.error(f"Failed to commit to {self.repo_path}: {stderr}")
            return Result.error(f"Commit failed: {stderr}")

    async def pull(
        self, 
        remote: str = "origin", 
        branch: Optional[str] = None
    ) -> Result:
        logger.debug(f"Pulling from remote {remote} branch {branch} to {self.repo_path}")
        if not self.is_git_repo:
            logger.error(f"Cannot pull, {self.repo_path} is not a git repository")
            return Result.error("Not a git repository")
        
        args = ["pull", remote]
        if branch:
            args.append(branch)
        
        returncode, stdout, stderr = await self._run_git_command(*args)
        
        if returncode == 0:
            logger.info(f"Successfully pulled from {remote} to {self.repo_path}")
            return Result.ok({
                "output": stdout,
                "message": "Pull successful"
            })
        else:
            logger.error(f"Failed to pull from {remote} to {self.repo_path}: {stderr}")
            if "CONFLICT" in stderr:
                logger.warning(f"Merge conflict detected during pull from {remote} to {self.repo_path}")
                return Result.error(f"Merge conflict: {stderr}")
            return Result.error(f"Pull failed: {stderr}")

    async def push(
        self, 
        remote: str = "origin", 
        branch: Optional[str] = None,
        set_upstream: bool = False
    ) -> Result:
        logger.debug(f"Pushing to remote {remote} branch {branch} from {self.repo_path}")
        if not self.is_git_repo:
            logger.error(f"Cannot push, {self.repo_path} is not a git repository")
            return Result.error("Not a git repository")
        
        args = ["push", remote]
        if branch:
            args.append(branch)
        if set_upstream:
            args.insert(1, "-u")
        
        returncode, stdout, stderr = await self._run_git_command(*args)
        
        if returncode == 0:
            logger.info(f"Successfully pushed to {remote} from {self.repo_path}")
            return Result.ok({
                "output": stdout,
                "message": "Push successful"
            })
        else:
            logger.error(f"Failed to push to {remote} from {self.repo_path}: {stderr}")
            return Result.error(f"Push failed: {stderr}")

    async def fetch(self, remote: str = "origin") -> Result:
        logger.debug(f"Fetching from remote {remote} to {self.repo_path}")
        if not self.is_git_repo:
            logger.error(f"Cannot fetch, {self.repo_path} is not a git repository")
            return Result.error("Not a git repository")
        
        returncode, stdout, stderr = await self._run_git_command("fetch", remote)
        
        if returncode == 0:
            logger.info(f"Successfully fetched from {remote} to {self.repo_path}")
            return Result.ok("Fetch successful")
        else:
            logger.error(f"Failed to fetch from {remote} to {self.repo_path}: {stderr}")
            return Result.error(f"Fetch failed: {stderr}")

    async def get_current_branch(self) -> Result:
        if not self.is_git_repo:
            return Result.error("Not a git repository")
        
        returncode, stdout, stderr = await self._run_git_command(
            "branch", "--show-current"
        )
        
        if returncode == 0:
            return Result.ok(stdout.strip())
        else:
            return Result.error(f"Get branch failed: {stderr}")

    async def get_branches(self) -> Result:
        if not self.is_git_repo:
            return Result.error("Not a git repository")
        
        returncode, stdout, stderr = await self._run_git_command(
            "branch", "-a"
        )
        
        if returncode == 0:
            branches = []
            for line in stdout.strip().split('\n'):
                line = line.strip()
                if line:
                    current = line.startswith('*')
                    name = line.lstrip('* ').strip()
                    branches.append({
                        "name": name,
                        "current": current,
                        "is_remote": name.startswith("remotes/")
                    })
            return Result.ok(branches)
        else:
            return Result.error(f"Get branches failed: {stderr}")

    async def create_branch(self, name: str) -> Result:
        if not self.is_git_repo:
            return Result.error("Not a git repository")
        
        returncode, stdout, stderr = await self._run_git_command(
            "checkout", "-b", name
        )
        
        if returncode == 0:
            return Result.ok(f"Branch '{name}' created")
        else:
            return Result.error(f"Create branch failed: {stderr}")

    async def switch_branch(self, name: str) -> Result:
        if not self.is_git_repo:
            return Result.error("Not a git repository")
        
        returncode, stdout, stderr = await self._run_git_command(
            "checkout", name
        )
        
        if returncode == 0:
            return Result.ok(f"Switched to branch '{name}'")
        else:
            return Result.error(f"Switch branch failed: {stderr}")

    async def get_diff(self, staged: bool = False) -> Result:
        if not self.is_git_repo:
            return Result.error("Not a git repository")
        
        args = ["diff"]
        if staged:
            args.append("--staged")
        args.append("--stat")
        
        returncode, stdout, stderr = await self._run_git_command(*args)
        
        if returncode == 0:
            diffs = []
            for line in stdout.strip().split('\n'):
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        file_path = parts[0].strip()
                        stats = parts[1].strip()
                        
                        additions = 0
                        deletions = 0
                        if '+' in stats:
                            additions = stats.count('+')
                        if '-' in stats:
                            deletions = stats.count('-')
                        
                        diffs.append(FileDiff(
                            path=file_path,
                            change_type=ChangeType.MODIFIED,
                            additions=additions,
                            deletions=deletions
                        ))
            return Result.ok(diffs)
        else:
            return Result.error(f"Get diff failed: {stderr}")

    async def get_log(
        self, 
        limit: int = 50, 
        since: Optional[datetime] = None
    ) -> Result:
        if not self.is_git_repo:
            return Result.error("Not a git repository")
        
        args = [
            "log",
            f"--max-count={limit}",
            "--pretty=format:%H|%an|%ai|%s",
            "--name-only"
        ]
        
        if since:
            args.append(f"--since={since.isoformat()}")
        
        returncode, stdout, stderr = await self._run_git_command(*args)
        
        if returncode == 0:
            commits = []
            current_commit = None
            
            for line in stdout.strip().split('\n'):
                if '|' in line and line.count('|') >= 3:
                    parts = line.split('|')
                    if current_commit:
                        commits.append(current_commit)
                    
                    date_str = parts[2].strip()
                    try:
                        if ' ' in date_str:
                            date_str = date_str.replace(' ', 'T', 1)
                        if '+' in date_str:
                            date_str = date_str.split('+')[0]
                        if date_str.endswith('T'):
                            date_str = date_str[:-1]
                        commit_date = datetime.fromisoformat(date_str)
                    except ValueError:
                        commit_date = datetime.now()
                    
                    current_commit = CommitInfo(
                        hash=parts[0],
                        author=parts[1],
                        date=commit_date,
                        message='|'.join(parts[3:]),
                        files=[]
                    )
                elif current_commit and line.strip():
                    current_commit.files.append(line.strip())
            
            if current_commit:
                commits.append(current_commit)
            
            return Result.ok(commits)
        else:
            return Result.error(f"Get log failed: {stderr}")

    async def get_remote_url(self, remote: str = "origin") -> Result:
        if not self.is_git_repo:
            return Result.error("Not a git repository")
        
        returncode, stdout, stderr = await self._run_git_command(
            "remote", "get-url", remote
        )
        
        if returncode == 0:
            return Result.ok(stdout.strip())
        else:
            return Result.error(f"Get remote URL failed: {stderr}")

    async def add_remote(self, name: str, url: str) -> Result:
        if not self.is_git_repo:
            return Result.error("Not a git repository")
        
        returncode, stdout, stderr = await self._run_git_command(
            "remote", "add", name, url
        )
        
        if returncode == 0:
            return Result.ok(f"Remote '{name}' added")
        else:
            return Result.error(f"Add remote failed: {stderr}")

    async def reset(self, ref: str, mode: str = "mixed") -> Result:
        if not self.is_git_repo:
            return Result.error("Not a git repository")
        
        returncode, stdout, stderr = await self._run_git_command(
            "reset", f"--{mode}", ref
        )
        
        if returncode == 0:
            return Result.ok(f"Reset to {ref}")
        else:
            return Result.error(f"Reset failed: {stderr}")
