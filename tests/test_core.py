"""测试核心功能"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from pathlib import Path
from datetime import datetime

from src.models.repository import Repository, RepoStatus, GitStatus, SyncRecord, SyncStatus
from src.data.database import Database
from src.data.config_manager import ConfigManager
from src.core.git_engine import GitEngine, Result


def test_models():
    print("=" * 50)
    print("测试数据模型...")
    print("=" * 50)
    
    repo = Repository.create(
        name="test-repo",
        local_path="/tmp/test"
    )
    print(f"[OK] 创建仓库模型: {repo.name} (ID: {repo.id[:8]}...)")
    
    git_status = GitStatus(
        branch="main",
        ahead=1,
        behind=0,
        staged=["file1.py"],
        unstaged=["file2.py"],
        untracked=["file3.py"]
    )
    print(f"[OK] 创建 Git 状态: 分支={git_status.branch}, 有变更={git_status.has_changes}")
    
    record = SyncRecord.create(
        repo_id=repo.id,
        action="sync",
        status=SyncStatus.SUCCESS
    )
    print(f"[OK] 创建同步记录: {record.action} - {record.status.value}")
    
    print("\n数据模型测试通过!\n")


def test_database():
    print("=" * 50)
    print("测试数据库...")
    print("=" * 50)
    
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        
        db = Database(db_path)
        
        repo = Repository.create(
            name="test-repo",
            local_path="/tmp/test",
            remote_url="https://github.com/user/repo.git"
        )
        
        db.insert_repository(repo)
        print(f"[OK] 插入仓库: {repo.name}")
        
        retrieved = db.get_repository(repo.id)
        assert retrieved is not None
        assert retrieved.name == repo.name
        print(f"[OK] 查询仓库: {retrieved.name}")
        
        all_repos = db.get_all_repositories()
        assert len(all_repos) == 1
        print(f"[OK] 获取所有仓库: {len(all_repos)} 个")
        
        record = SyncRecord.create(
            repo_id=repo.id,
            action="pull",
            status=SyncStatus.SUCCESS,
            message="Pull successful"
        )
        db.insert_sync_record(record)
        print(f"[OK] 插入同步记录")
        
        records = db.get_sync_records(repo.id)
        assert len(records) == 1
        print(f"[OK] 查询同步记录: {len(records)} 条")
        
        db.delete_repository(repo.id)
        assert db.get_repository(repo.id) is None
        print(f"[OK] 删除仓库")
        
        db.close()
        Database.reset_instance(db_path)
        
    print("\n数据库测试通过!\n")


def test_config():
    print("=" * 50)
    print("测试配置管理...")
    print("=" * 50)
    
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        config = ConfigManager(config_path)
        
        print(f"[OK] 创建配置管理器")
        
        assert config.get("language") == "zh_CN"
        print(f"[OK] 读取默认配置: language={config.get('language')}")
        
        config.set("language", "en_US")
        assert config.get("language") == "en_US"
        print(f"[OK] 修改配置: language={config.get('language')}")
        
        patterns = config.ignore_patterns
        assert len(patterns) > 0
        print(f"[OK] 获取忽略模式: {len(patterns)} 个")
        
    print("\n配置管理测试通过!\n")


def test_git_engine():
    print("=" * 50)
    print("测试 Git 引擎...")
    print("=" * 50)
    
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir) / "test_repo"
        repo_path.mkdir()
        
        engine = GitEngine(repo_path)
        
        assert not engine.is_git_repo
        print(f"[OK] 检测非 Git 仓库")
        
        result = engine.init()
        assert result.success
        print(f"[OK] 初始化仓库: {result.data}")
        
        assert engine.is_git_repo
        print(f"[OK] 检测 Git 仓库")
        
        async def test_async_operations():
            status_result = await engine.get_status()
            assert status_result.success
            status = status_result.data
            print(f"[OK] 获取状态: 分支={status.branch}")
            
            branch_result = await engine.get_current_branch()
            assert branch_result.success
            print(f"[OK] 获取当前分支: {branch_result.data}")
            
            test_file = repo_path / "test.txt"
            test_file.write_text("Hello, World!")
            print(f"[OK] 创建测试文件")
            
            add_result = await engine.add()
            assert add_result.success
            print(f"[OK] 添加文件到暂存区")
            
            commit_result = await engine.commit("Initial commit")
            assert commit_result.success
            print(f"[OK] 提交: {commit_result.data.get('hash', '')[:8]}")
            
            log_result = await engine.get_log(limit=1)
            assert log_result.success
            commits = log_result.data
            if commits:
                print(f"[OK] 获取日志: {len(commits)} 条提交")
            
            status_result = await engine.get_status()
            status = status_result.data
            assert not status.has_changes
            print(f"[OK] 验证工作区干净")
        
        asyncio.run(test_async_operations())
        
    print("\nGit 引擎测试通过!\n")


def main():
    print("\n" + "=" * 50)
    print("GitHub 仓库同步工具 - 核心功能测试")
    print("=" * 50 + "\n")
    
    try:
        test_models()
        test_database()
        test_config()
        test_git_engine()
        
        print("=" * 50)
        print("[OK] 所有测试通过!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
