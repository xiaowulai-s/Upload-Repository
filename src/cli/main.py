"""命令行界面"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="git-sync-tool")
def cli():
    """GitHub 仓库同步工具 - 命令行界面"""
    pass


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--name", "-n", help="仓库名称")
@click.option("--remote", "-r", help="远程仓库 URL")
def bind(path: str, name: Optional[str], remote: Optional[str]):
    """绑定本地文件夹到仓库"""
    from ..services.repo_service import RepoService
    from ..utils.exceptions import RepositoryExistsError
    
    repo_service = RepoService()
    folder_path = Path(path)
    
    try:
        repo = repo_service.bind_local_folder(
            folder_path=folder_path,
            name=name,
            remote_url=remote
        )
        
        console.print(Panel(
            f"[green]✓ 仓库绑定成功[/green]\n\n"
            f"ID: {repo.id}\n"
            f"名称: {repo.name}\n"
            f"路径: {repo.local_path}\n"
            f"状态: {repo.status.value}",
            title="绑定成功"
        ))
    except RepositoryExistsError as e:
        console.print(f"[red]错误: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]绑定失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("url")
@click.argument("path", type=click.Path())
@click.option("--name", "-n", help="仓库名称")
@click.option("--branch", "-b", help="要克隆的分支")
def clone(url: str, path: str, name: Optional[str], branch: Optional[str]):
    """克隆远程仓库"""
    from ..services.repo_service import RepoService
    
    repo_service = RepoService()
    target_path = Path(path)
    
    async def do_clone():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("正在克隆仓库...", total=None)
            
            repo = await repo_service.clone_repository(
                url=url,
                target_path=target_path,
                name=name,
                branch=branch
            )
            
            progress.remove_task(task)
        
        console.print(Panel(
            f"[green]✓ 仓库克隆成功[/green]\n\n"
            f"ID: {repo.id}\n"
            f"名称: {repo.name}\n"
            f"路径: {repo.local_path}\n"
            f"分支: {repo.branch}",
            title="克隆成功"
        ))
    
    try:
        asyncio.run(do_clone())
    except Exception as e:
        console.print(f"[red]克隆失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--all", "-a", "show_all", is_flag=True, help="显示详细信息")
def list(show_all: bool):
    """列出所有绑定的仓库"""
    from ..services.repo_service import RepoService
    
    repo_service = RepoService()
    repos = repo_service.get_all_repositories()
    
    if not repos:
        console.print("[yellow]没有绑定的仓库[/yellow]")
        return
    
    table = Table(title="仓库列表")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("名称", style="green")
    table.add_column("路径", style="blue")
    table.add_column("状态", style="yellow")
    table.add_column("最后同步", style="magenta")
    
    if show_all:
        table.add_column("远程 URL", style="white")
        table.add_column("分支", style="white")
    
    for repo in repos:
        row = [
            repo.id[:8],
            repo.name,
            repo.local_path,
            repo.status.value,
            repo.last_sync.strftime("%Y-%m-%d %H:%M") if repo.last_sync else "从未"
        ]
        
        if show_all:
            row.extend([
                repo.remote_url or "-",
                repo.branch
            ])
        
        table.add_row(*row)
    
    console.print(table)


@cli.command()
@click.argument("repo_id")
def status(repo_id: str):
    """查看仓库状态"""
    from ..services.repo_service import RepoService
    
    repo_service = RepoService()
    
    async def get_status():
        result = await repo_service.get_repo_status(repo_id)
        
        repo = result["repo"]
        git_status = result.get("git_status")
        
        console.print(Panel(
            f"[bold]仓库信息[/bold]\n"
            f"名称: {repo['name']}\n"
            f"路径: {repo['local_path']}\n"
            f"分支: {result.get('current_branch', repo['branch'])}\n"
            f"状态: {repo['status']}",
            title="仓库状态"
        ))
        
        if git_status:
            table = Table(title="Git 状态")
            table.add_column("类型", style="cyan")
            table.add_column("文件数", style="green")
            
            table.add_row("已暂存", str(len(git_status.get("staged", []))))
            table.add_row("未暂存", str(len(git_status.get("unstaged", []))))
            table.add_row("未跟踪", str(len(git_status.get("untracked", []))))
            table.add_row("冲突", str(len(git_status.get("conflicts", []))))
            
            table.add_row("\n领先提交", str(git_status.get("ahead", 0)))
            table.add_row("落后提交", str(git_status.get("behind", 0)))
            
            console.print(table)
            
            if git_status.get("staged"):
                console.print("\n[bold green]已暂存文件:[/bold green]")
                for f in git_status["staged"]:
                    console.print(f"  • {f}")
            
            if git_status.get("unstaged"):
                console.print("\n[bold yellow]未暂存文件:[/bold yellow]")
                for f in git_status["unstaged"]:
                    console.print(f"  • {f}")
            
            if git_status.get("untracked"):
                console.print("\n[bold red]未跟踪文件:[/bold red]")
                for f in git_status["untracked"][:10]:
                    console.print(f"  • {f}")
                if len(git_status["untracked"]) > 10:
                    console.print(f"  ... 还有 {len(git_status['untracked']) - 10} 个文件")
    
    try:
        asyncio.run(get_status())
    except Exception as e:
        console.print(f"[red]获取状态失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("repo_id")
@click.option("--message", "-m", help="提交信息")
def commit(repo_id: str, message: Optional[str]):
    """提交更改"""
    from ..services.git_service import GitService
    
    git_service = GitService()
    
    if not message:
        message = f"Auto commit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    async def do_commit():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("正在提交...", total=None)
            
            result = await git_service.commit(repo_id, message)
            
            progress.remove_task(task)
        
        if hasattr(result, 'data'):
            console.print(f"[green]✓ 提交成功: {result.data.get('hash', '')[:8]}[/green]")
        else:
            console.print(f"[green]✓ 提交成功[/green]")
    
    try:
        asyncio.run(do_commit())
    except Exception as e:
        console.print(f"[red]提交失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("repo_id")
@click.option("--remote", "-r", default="origin", help="远程名称")
@click.option("--branch", "-b", help="分支名称")
def pull(repo_id: str, remote: str, branch: Optional[str]):
    """拉取远程更改"""
    from ..services.git_service import GitService
    
    git_service = GitService()
    
    async def do_pull():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("正在拉取...", total=None)
            
            record = await git_service.pull(repo_id, remote, branch)
            
            progress.remove_task(task)
        
        console.print(f"[green]✓ 拉取成功 (耗时: {record.duration:.2f}s)[/green]")
    
    try:
        asyncio.run(do_pull())
    except Exception as e:
        console.print(f"[red]拉取失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("repo_id")
@click.option("--remote", "-r", default="origin", help="远程名称")
@click.option("--branch", "-b", help="分支名称")
@click.option("--set-upstream", "-u", is_flag=True, help="设置上游分支")
def push(repo_id: str, remote: str, branch: Optional[str], set_upstream: bool):
    """推送本地更改"""
    from ..services.git_service import GitService
    
    git_service = GitService()
    
    async def do_push():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("正在推送...", total=None)
            
            record = await git_service.push(repo_id, remote, branch, set_upstream)
            
            progress.remove_task(task)
        
        console.print(f"[green]✓ 推送成功 (耗时: {record.duration:.2f}s)[/green]")
    
    try:
        asyncio.run(do_push())
    except Exception as e:
        console.print(f"[red]推送失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("repo_id")
@click.option("--message", "-m", help="提交信息")
@click.option("--auto-commit/--no-auto-commit", default=True, help="自动提交")
def sync(repo_id: str, message: Optional[str], auto_commit: bool):
    """同步仓库 (pull + commit + push)"""
    from ..services.git_service import GitService
    
    git_service = GitService()
    
    async def do_sync():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("正在同步...", total=None)
            
            record = await git_service.sync(repo_id, message, auto_commit)
            
            progress.remove_task(task)
        
        console.print(f"[green]✓ 同步成功 (耗时: {record.duration:.2f}s)[/green]")
    
    try:
        asyncio.run(do_sync())
    except Exception as e:
        console.print(f"[red]同步失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("repo_id")
@click.option("--delete-local", is_flag=True, help="同时删除本地文件")
def remove(repo_id: str, delete_local: bool):
    """移除仓库绑定"""
    from ..services.repo_service import RepoService
    
    repo_service = RepoService()
    
    if click.confirm(f"确定要移除仓库 {repo_id} 吗?", default=False):
        try:
            repo_service.remove_repository(repo_id, delete_local)
            console.print(f"[green]✓ 仓库已移除[/green]")
        except Exception as e:
            console.print(f"[red]移除失败: {e}[/red]")
            sys.exit(1)


@cli.command()
@click.argument("repo_id")
def history(repo_id: str):
    """查看同步历史"""
    from ..services.repo_service import RepoService
    
    repo_service = RepoService()
    records = repo_service.get_sync_history(repo_id, limit=20)
    
    if not records:
        console.print("[yellow]没有同步历史记录[/yellow]")
        return
    
    table = Table(title="同步历史")
    table.add_column("时间", style="cyan")
    table.add_column("操作", style="green")
    table.add_column("状态", style="yellow")
    table.add_column("文件数", style="blue")
    table.add_column("耗时", style="magenta")
    table.add_column("消息", style="white")
    
    for record in records:
        status_style = {
            "success": "[green]成功[/green]",
            "error": "[red]失败[/red]",
            "conflict": "[yellow]冲突[/yellow]",
        }.get(record.status.value, record.status.value)
        
        table.add_row(
            record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            record.action,
            status_style,
            str(record.files_count),
            f"{record.duration:.2f}s",
            record.message or "-"
        )
    
    console.print(table)


def main():
    """CLI 入口"""
    cli()


if __name__ == "__main__":
    main()
