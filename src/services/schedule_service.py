"""定时任务服务"""

import asyncio
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from ..utils.logger import logger
from ..models.repository import Repository
from .repo_service import RepoService
from .git_service import GitService
from ..data.config_manager import ConfigManager


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    repo_id: str
    interval: int  # 秒
    next_run: datetime
    last_run: Optional[datetime] = None
    is_running: bool = False
    is_paused: bool = False
    run_count: int = 0
    last_result: Optional[str] = None


class ScheduleService:
    """定时任务服务"""
    
    def __init__(self):
        self._tasks: Dict[str, TaskInfo] = {}
        self._repo_service = RepoService()
        self._git_service = GitService()
        self._config_manager = ConfigManager()
        self._running = False
        self._lock = threading.Lock()
        self._task_thread: Optional[threading.Thread] = None
    
    def start(self):
        """启动定时任务服务"""
        if not self._running:
            logger.info("启动定时任务服务")
            self._running = True
            self._task_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self._task_thread.start()
    
    def stop(self):
        """停止定时任务服务"""
        logger.info("停止定时任务服务")
        self._running = False
        if self._task_thread:
            self._task_thread.join(timeout=5)
    
    def _run_scheduler(self):
        """调度器主循环"""
        while self._running:
            try:
                self._check_tasks()
            except Exception as e:
                logger.error(f"调度器执行错误: {e}")
            time.sleep(1)
    
    def _check_tasks(self):
        """检查并执行到期的任务"""
        current_time = datetime.now()
        
        with self._lock:
            for task_id, task in list(self._tasks.items()):
                if not task.is_paused and task.next_run <= current_time and not task.is_running:
                    self._execute_task(task)
    
    def _execute_task(self, task: TaskInfo):
        """执行任务"""
        logger.info(f"执行任务 {task.task_id} 用于仓库 {task.repo_id}")
        task.is_running = True
        
        # 在独立的线程中执行任务
        def run_task():
            try:
                result = asyncio.run(self._git_service.sync(task.repo_id))
                task.last_result = f"Success: {result.message}"
                logger.info(f"任务 {task.task_id} 执行成功: {result.message}")
            except Exception as e:
                task.last_result = f"Error: {str(e)}"
                logger.error(f"任务 {task.task_id} 执行失败: {e}")
            finally:
                with self._lock:
                    task.is_running = False
                    task.last_run = datetime.now()
                    task.next_run = task.last_run + timedelta(seconds=task.interval)
                    task.run_count += 1
        
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
    
    def add_task(self, repo_id: str, interval: int = 300) -> str:
        """添加定时任务"""
        import uuid
        task_id = str(uuid.uuid4())
        
        with self._lock:
            # 检查是否已存在该仓库的任务
            for existing_task in self._tasks.values():
                if existing_task.repo_id == repo_id and not existing_task.is_paused:
                    logger.warning(f"仓库 {repo_id} 已存在活跃任务，跳过添加")
                    return existing_task.task_id
            
            task = TaskInfo(
                task_id=task_id,
                repo_id=repo_id,
                interval=interval,
                next_run=datetime.now() + timedelta(seconds=interval)
            )
            self._tasks[task_id] = task
        
        logger.info(f"添加定时任务 {task_id} 用于仓库 {repo_id}，间隔 {interval} 秒")
        return task_id
    
    def remove_task(self, task_id: str) -> bool:
        """移除定时任务"""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                logger.info(f"移除定时任务 {task_id}")
                return True
        logger.warning(f"定时任务 {task_id} 不存在")
        return False
    
    def pause_task(self, task_id: str) -> bool:
        """暂停定时任务"""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].is_paused = True
                logger.info(f"暂停定时任务 {task_id}")
                return True
        logger.warning(f"定时任务 {task_id} 不存在")
        return False
    
    def resume_task(self, task_id: str) -> bool:
        """恢复定时任务"""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].is_paused = False
                self._tasks[task_id].next_run = datetime.now() + timedelta(seconds=self._tasks[task_id].interval)
                logger.info(f"恢复定时任务 {task_id}")
                return True
        logger.warning(f"定时任务 {task_id} 不存在")
        return False
    
    def update_task_interval(self, task_id: str, interval: int) -> bool:
        """更新任务间隔"""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].interval = interval
                self._tasks[task_id].next_run = datetime.now() + timedelta(seconds=interval)
                logger.info(f"更新定时任务 {task_id} 间隔为 {interval} 秒")
                return True
        logger.warning(f"定时任务 {task_id} 不存在")
        return False
    
    def get_tasks(self) -> List[TaskInfo]:
        """获取所有任务"""
        with self._lock:
            return list(self._tasks.values())
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取单个任务"""
        with self._lock:
            return self._tasks.get(task_id)
    
    def get_tasks_by_repo(self, repo_id: str) -> List[TaskInfo]:
        """获取指定仓库的所有任务"""
        with self._lock:
            return [task for task in self._tasks.values() if task.repo_id == repo_id]
    
    def start_auto_sync(self):
        """启动自动同步功能"""
        logger.info("启动自动同步功能")
        
        # 从配置中获取同步间隔
        sync_interval = self._config_manager.get("sync_interval", 300)
        auto_sync_enabled = self._config_manager.get("auto_sync", True)
        
        if not auto_sync_enabled:
            logger.info("自动同步已禁用")
            return
        
        # 获取所有仓库
        repos = self._repo_service.get_all_repositories()
        
        # 为每个仓库添加定时任务
        for repo in repos:
            if repo.status != "uninitialized":
                self.add_task(repo.id, sync_interval)
        
        logger.info(f"自动同步已启动，共添加 {len(repos)} 个任务，间隔 {sync_interval} 秒")
    
    def stop_auto_sync(self):
        """停止自动同步功能"""
        logger.info("停止自动同步功能")
        
        with self._lock:
            self._tasks.clear()
        
        logger.info("所有自动同步任务已停止")
    
    def update_auto_sync_config(self):
        """更新自动同步配置"""
        logger.info("更新自动同步配置")
        
        # 先停止所有任务
        self.stop_auto_sync()
        
        # 根据新配置重新启动
        self.start_auto_sync()
    
    def is_running(self) -> bool:
        """检查服务是否运行"""
        return self._running
    
    def get_stats(self) -> Dict[str, int]:
        """获取任务统计信息"""
        with self._lock:
            total = len(self._tasks)
            running = sum(1 for task in self._tasks.values() if task.is_running)
            paused = sum(1 for task in self._tasks.values() if task.is_paused)
            active = total - paused
        
        return {
            "total": total,
            "running": running,
            "paused": paused,
            "active": active
        }
