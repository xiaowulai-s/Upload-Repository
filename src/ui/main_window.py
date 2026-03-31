"""主窗口"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStatusBar, QTreeWidget, QTreeWidgetItem,
    QSplitter, QTabWidget, QMessageBox, QFileDialog, QInputDialog,
    QTextEdit, QProgressBar, QLineEdit
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QActionGroup

from ..services.repo_service import RepoService
from ..services.git_service import GitService
from ..services.schedule_service import ScheduleService
from ..models.repository import Repository, RepoStatus, SyncStatus


class AsyncWorker(QThread):
    finished = Signal(object)
    error = Signal(str)
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._stop_flag = False
    
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.func(*self.args, **self.kwargs))
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
    
    def stop(self):
        self._stop_flag = True
        self.quit()
        self.wait()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.repo_service = RepoService()
        self.git_service = GitService()
        self.schedule_service = ScheduleService()  # 添加定时任务服务
        self.current_repo: Optional[Repository] = None
        self._workers = []  # 用于跟踪所有运行的线程
        
        self._init_ui()
        self._load_repositories()
        
        # 启动定时任务服务和自动同步
        self.schedule_service.start()
        self.schedule_service.start_auto_sync()
    
    def closeEvent(self, event):
        """窗口关闭时停止所有运行的线程和服务"""
        for worker in self._workers:
            if worker.isRunning():
                worker.stop()
        
        # 停止定时任务服务
        self.schedule_service.stop()
        
        event.accept()
    
    def _add_worker(self, worker):
        """添加线程到跟踪列表"""
        self._workers.append(worker)
        worker.finished.connect(lambda: self._remove_worker(worker))
        worker.error.connect(lambda: self._remove_worker(worker))
    
    def _remove_worker(self, worker):
        """从跟踪列表中移除线程"""
        if worker in self._workers:
            self._workers.remove(worker)
            worker.deleteLater()
    
    def _get_status_icon(self, status: str):
        """获取状态图标"""
        from PySide6.QtGui import QPixmap
        
        # 使用简单的文字图标作为占位符
        # 在实际应用中，可以替换为真实的图标文件
        if status == "synced":
            # 绿色对勾
            return QPixmap()
        elif status == "conflict":
            # 红色冲突图标
            return QPixmap()
        elif status == "initialized":
            # 蓝色初始化图标
            return QPixmap()
        else:
            # 灰色未初始化图标
            return QPixmap()
    
    def _init_ui(self):
        self.setWindowTitle("Git 同步工具")
        self.setMinimumSize(1200, 800)
        
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([300, 900])
        
        self._create_status_bar()
        self._create_menu_bar()  # 创建菜单栏，用于主题切换
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        from ..utils.theme_manager import ThemeType, ThemeManager
        
        menu_bar = self.menuBar()
        
        # 主题菜单
        theme_menu = menu_bar.addMenu("主题")
        
        # 主题选项
        self.light_action = theme_menu.addAction("亮色主题")
        self.light_action.triggered.connect(lambda: self.theme_manager.set_theme(ThemeType.LIGHT))
        self.light_action.setCheckable(True)
        
        self.dark_action = theme_menu.addAction("暗色主题")
        self.dark_action.triggered.connect(lambda: self.theme_manager.set_theme(ThemeType.DARK))
        self.dark_action.setCheckable(True)
        
        self.system_action = theme_menu.addAction("系统主题")
        self.system_action.triggered.connect(lambda: self.theme_manager.set_theme(ThemeType.SYSTEM))
        self.system_action.setCheckable(True)
        
        # 单选组
        theme_group = QActionGroup(self)
        theme_group.addAction(self.light_action)
        theme_group.addAction(self.dark_action)
        theme_group.addAction(self.system_action)
        theme_group.setExclusive(True)
        
        # 设置当前主题的选中状态 - 只有当theme_manager被赋值后才执行
        if hasattr(self, 'theme_manager'):
            current_theme = self.theme_manager.get_current_theme()
            if current_theme == ThemeType.LIGHT:
                self.light_action.setChecked(True)
            elif current_theme == ThemeType.DARK:
                self.dark_action.setChecked(True)
            else:
                self.system_action.setChecked(True)
    
    def _create_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        title = QLabel("仓库列表")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setStyleSheet("margin-bottom: 8px; color: #333333;")
        layout.addWidget(title)
        
        self.repo_tree = QTreeWidget()
        self.repo_tree.setHeaderLabels(["名称", "状态", "最后同步"])
        self.repo_tree.setIndentation(15)
        self.repo_tree.setMinimumHeight(300)
        self.repo_tree.setAlternatingRowColors(True)
        self.repo_tree.itemClicked.connect(self._on_repo_selected)
        layout.addWidget(self.repo_tree)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_add = QPushButton("添加")
        self.btn_add.setObjectName("primary")
        self.btn_add.clicked.connect(self._add_repository)
        btn_layout.addWidget(self.btn_add)
        
        self.btn_remove = QPushButton("移除")
        self.btn_remove.setObjectName("danger")
        self.btn_remove.clicked.connect(self._remove_repository)
        btn_layout.addWidget(self.btn_remove)
        
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.setObjectName("secondary")
        self.btn_refresh.clicked.connect(self._refresh)
        btn_layout.addWidget(self.btn_refresh)
        
        layout.addLayout(btn_layout)
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # 创建统一的操作工具栏
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)
        toolbar_layout.setObjectName("toolbar")
        
        self.btn_pull = QPushButton("拉取")
        self.btn_pull.setObjectName("secondary")
        self.btn_pull.clicked.connect(self._pull)
        self.btn_pull.setEnabled(False)
        toolbar_layout.addWidget(self.btn_pull)
        
        self.btn_push = QPushButton("推送")
        self.btn_push.setObjectName("primary")
        self.btn_push.clicked.connect(self._push)
        self.btn_push.setEnabled(False)
        toolbar_layout.addWidget(self.btn_push)
        
        self.btn_sync = QPushButton("同步")
        self.btn_sync.setObjectName("success")
        self.btn_sync.clicked.connect(self._sync)
        self.btn_sync.setEnabled(False)
        toolbar_layout.addWidget(self.btn_sync)
        
        self.btn_commit = QPushButton("提交")
        self.btn_commit.setObjectName("secondary")
        self.btn_commit.clicked.connect(self._commit)
        self.btn_commit.setEnabled(False)
        toolbar_layout.addWidget(self.btn_commit)
        
        toolbar_layout.addStretch()
        
        # 添加自动同步开关
        auto_sync_layout = QHBoxLayout()
        auto_sync_label = QLabel("自动同步:")
        self.auto_sync_switch = QPushButton("开启")
        self.auto_sync_switch.setObjectName("secondary")
        self.auto_sync_switch.clicked.connect(self._toggle_auto_sync)
        auto_sync_layout.addWidget(auto_sync_label)
        auto_sync_layout.addWidget(self.auto_sync_switch)
        toolbar_layout.addLayout(auto_sync_layout)
        
        layout.addLayout(toolbar_layout)
        
        self.tabs = QTabWidget()
        
        # 文件状态标签页 - 整合常用的文件操作
        file_tab = self._create_file_tab()
        self.tabs.addTab(file_tab, "文件状态")
        
        # 分支管理标签页
        branch_tab = self._create_branch_tab()
        self.tabs.addTab(branch_tab, "分支管理")
        
        # 同步历史标签页
        history_tab = self._create_history_tab()
        self.tabs.addTab(history_tab, "同步历史")
        
        layout.addWidget(self.tabs)
        
        return panel
    
    def _create_file_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        label = QLabel("文件状态")
        label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        label.setStyleSheet("color: #333333;")
        layout.addWidget(label)
        
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["文件", "状态"])
        self.file_tree.setIndentation(15)
        self.file_tree.setMinimumHeight(200)
        self.file_tree.setAlternatingRowColors(True)
        layout.addWidget(self.file_tree)
        
        commit_label = QLabel("提交信息:")
        commit_label.setStyleSheet("font-weight: bold; color: #333333;")
        layout.addWidget(commit_label)
        
        self.commit_edit = QTextEdit()
        self.commit_edit.setMaximumHeight(100)
        self.commit_edit.setPlaceholderText("输入提交信息...")
        layout.addWidget(self.commit_edit)
        
        return tab
    
    def _create_history_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        label = QLabel("同步历史")
        label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        label.setStyleSheet("color: #333333;")
        layout.addWidget(label)
        
        self.history_tree = QTreeWidget()
        self.history_tree.setHeaderLabels(["时间", "操作", "状态", "描述"])
        self.history_tree.setIndentation(15)
        self.history_tree.setMinimumHeight(300)
        self.history_tree.setAlternatingRowColors(True)
        layout.addWidget(self.history_tree)
        
        return tab
    
    def _create_branch_tab(self) -> QWidget:
        """创建分支管理标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # 标题
        label = QLabel("分支管理")
        label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        label.setStyleSheet("color: #333333;")
        layout.addWidget(label)
        
        # 分支列表
        self.branch_tree = QTreeWidget()
        self.branch_tree.setHeaderLabels(["分支名称", "状态", "类型"])
        self.branch_tree.setIndentation(15)
        self.branch_tree.setMinimumHeight(200)
        self.branch_tree.setAlternatingRowColors(True)
        self.branch_tree.itemDoubleClicked.connect(self._on_branch_double_clicked)
        layout.addWidget(self.branch_tree)
        
        # 当前分支信息
        branch_info_layout = QHBoxLayout()
        branch_info_layout.setSpacing(10)
        branch_info_label = QLabel("当前分支:")
        branch_info_label.setStyleSheet("font-weight: bold; color: #333333;")
        branch_info_layout.addWidget(branch_info_label)
        
        self.current_branch_label = QLabel("- 未选择 -", styleSheet="font-weight: bold; color: #333333;")
        branch_info_layout.addWidget(self.current_branch_label)
        branch_info_layout.addStretch()
        layout.addLayout(branch_info_layout)
        
        # 创建分支区域
        create_branch_layout = QHBoxLayout()
        create_branch_layout.setSpacing(10)
        
        branch_name_label = QLabel("新分支名称:")
        branch_name_label.setStyleSheet("color: #333333;")
        create_branch_layout.addWidget(branch_name_label)
        
        self.new_branch_edit = QLineEdit()
        self.new_branch_edit.setPlaceholderText("输入新分支名称...")
        create_branch_layout.addWidget(self.new_branch_edit)
        
        self.btn_create_branch = QPushButton("创建分支")
        self.btn_create_branch.setObjectName("success")
        self.btn_create_branch.clicked.connect(self._create_branch)
        self.btn_create_branch.setEnabled(False)
        create_branch_layout.addWidget(self.btn_create_branch)
        
        layout.addLayout(create_branch_layout)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_switch_branch = QPushButton("切换分支")
        self.btn_switch_branch.setObjectName("primary")
        self.btn_switch_branch.clicked.connect(self._switch_branch)
        self.btn_switch_branch.setEnabled(False)
        btn_layout.addWidget(self.btn_switch_branch)
        
        self.btn_refresh_branches = QPushButton("刷新分支")
        self.btn_refresh_branches.setObjectName("secondary")
        self.btn_refresh_branches.clicked.connect(self._refresh_branches)
        self.btn_refresh_branches.setEnabled(False)
        btn_layout.addWidget(self.btn_refresh_branches)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return tab
    
    def _create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        self.status_bar.setStyleSheet("color: #333333;")
    
    def _load_repositories(self):
        repos = self.repo_service.get_all_repositories()
        self.repo_tree.clear()
        
        for repo in repos:
            item = QTreeWidgetItem(self.repo_tree)
            item.setText(0, repo.name)
            
            # 状态显示优化，使用颜色和图标增强视觉反馈
            status = repo.status.value
            if repo.status == RepoStatus.SYNCED:
                status_text = f"<span style='color: green; font-weight: bold;'>{status}</span>"
            elif repo.status == RepoStatus.CONFLICT:
                status_text = f"<span style='color: red; font-weight: bold;'>{status}</span>"
            elif repo.status == RepoStatus.INITIALIZED:
                status_text = f"<span style='color: blue; font-weight: bold;'>{status}</span>"
            else:
                status_text = f"<span style='color: gray;'>{status}</span>"
            
            item.setText(1, status)
            item.setToolTip(1, f"状态: {status}")
            
            last_sync = repo.last_sync.strftime("%Y-%m-%d %H:%M") if repo.last_sync else "从未"
            item.setText(2, last_sync)
            item.setData(0, Qt.UserRole, repo.id)
            
            # 添加图标
            if repo.status == RepoStatus.SYNCED:
                item.setIcon(1, self._get_status_icon("synced"))
            elif repo.status == RepoStatus.CONFLICT:
                item.setIcon(1, self._get_status_icon("conflict"))
            elif repo.status == RepoStatus.INITIALIZED:
                item.setIcon(1, self._get_status_icon("initialized"))
            else:
                item.setIcon(1, self._get_status_icon("uninitialized"))
    
    def _on_repo_selected(self, item: QTreeWidgetItem):
        repo_id = item.data(0, Qt.UserRole)
        repos = self.repo_service.get_all_repositories()
        self.current_repo = next((r for r in repos if r.id == repo_id), None)
        
        if self.current_repo:
            self.btn_pull.setEnabled(True)
            self.btn_push.setEnabled(True)
            self.btn_sync.setEnabled(True)
            self.btn_commit.setEnabled(True)
            # 分支管理相关按钮启用
            self.btn_create_branch.setEnabled(True)
            self.btn_switch_branch.setEnabled(True)
            self.btn_refresh_branches.setEnabled(True)
            # 加载数据
            self._load_repo_status()
            self._load_history()
            self._load_branches()  # 加载分支列表
    
    def _load_repo_status(self):
        if not self.current_repo:
            return
        
        async def load():
            result = await self.repo_service.get_repo_status(self.current_repo.id)
            return result
        
        def on_finished(result):
            if result and result.get("git_status"):
                self._update_file_tree(result["git_status"])
            self.status_bar.showMessage("状态已更新")
        
        def on_error(err):
            self.status_bar.showMessage(f"加载失败: {err}")
        
        worker = AsyncWorker(load)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        self._add_worker(worker)
        worker.start()
    
    def _load_branches(self):
        """加载分支列表"""
        if not self.current_repo:
            return
        
        async def load():
            # 获取当前分支
            current_branch = await self.git_service.get_current_branch(self.current_repo.id)
            # 获取所有分支
            branches = await self.git_service.get_branches(self.current_repo.id)
            return {
                "current_branch": current_branch,
                "branches": branches
            }
        
        def on_finished(result):
            if result:
                # 更新当前分支显示
                self.current_branch_label.setText(result["current_branch"])
                # 更新分支列表
                self.branch_tree.clear()
                for branch in result["branches"]:
                    item = QTreeWidgetItem(self.branch_tree)
                    branch_name = branch["name"]
                    if branch["is_remote"]:
                        branch_name = branch["name"].replace("remotes/", "")
                    item.setText(0, branch_name)
                    item.setText(1, "当前分支" if branch["current"] else "")
                    item.setText(2, "远程" if branch["is_remote"] else "本地")
                    item.setData(0, Qt.UserRole, branch["name"])
                self.status_bar.showMessage("分支列表已更新")
        
        def on_error(err):
            self.status_bar.showMessage(f"加载分支失败: {err}")
        
        worker = AsyncWorker(load)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        self._add_worker(worker)
        worker.start()
    
    def _on_branch_double_clicked(self, item: QTreeWidgetItem):
        """双击分支事件处理"""
        self._switch_branch()
    
    def _create_branch(self):
        """创建分支"""
        if not self.current_repo:
            return
        
        branch_name = self.new_branch_edit.text().strip()
        if not branch_name:
            QMessageBox.warning(self, "警告", "请输入新分支名称")
            return
        
        async def create():
            return await self.git_service.create_branch(self.current_repo.id, branch_name)
        
        def on_finished(result):
            QMessageBox.information(self, "成功", f"分支 '{branch_name}' 已创建")
            self.new_branch_edit.clear()
            self._load_branches()
            self.status_bar.showMessage(f"分支 '{branch_name}' 已创建")
        
        def on_error(err):
            QMessageBox.critical(self, "错误", f"创建分支失败: {err}")
            self.status_bar.showMessage(f"创建分支失败: {err}")
        
        worker = AsyncWorker(create)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        self._add_worker(worker)
        worker.start()
    
    def _switch_branch(self):
        """切换分支"""
        if not self.current_repo:
            return
        
        selected_items = self.branch_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个分支")
            return
        
        item = selected_items[0]
        branch_name = item.data(0, Qt.UserRole)
        
        async def switch():
            return await self.git_service.switch_branch(self.current_repo.id, branch_name)
        
        def on_finished(result):
            QMessageBox.information(self, "成功", f"已切换到分支 '{branch_name}'")
            self._load_branches()
            self._load_repo_status()  # 切换分支后重新加载状态
            self.status_bar.showMessage(f"已切换到分支 '{branch_name}'")
        
        def on_error(err):
            QMessageBox.critical(self, "错误", f"切换分支失败: {err}")
            self.status_bar.showMessage(f"切换分支失败: {err}")
        
        worker = AsyncWorker(switch)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        self._add_worker(worker)
        worker.start()
    
    def _refresh_branches(self):
        """刷新分支列表"""
        self._load_branches()
    
    def _update_file_tree(self, status: dict):
        self.file_tree.clear()
        
        for f in status.get("staged", []):
            item = QTreeWidgetItem(self.file_tree)
            item.setText(0, f)
            item.setText(1, "已暂存")
        
        for f in status.get("unstaged", []):
            item = QTreeWidgetItem(self.file_tree)
            item.setText(0, f)
            item.setText(1, "已修改")
        
        for f in status.get("untracked", []):
            item = QTreeWidgetItem(self.file_tree)
            item.setText(0, f)
            item.setText(1, "未跟踪")
    
    def _load_history(self):
        if not self.current_repo:
            return
        
        records = self.repo_service.get_sync_history(self.current_repo.id)
        self.history_tree.clear()
        
        for r in records:
            item = QTreeWidgetItem(self.history_tree)
            item.setText(0, r.created_at.strftime("%Y-%m-%d %H:%M:%S"))
            item.setText(1, r.action)
            item.setText(2, r.status.value)
            item.setText(3, r.message or "-")
    
    def _add_repository(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if not folder:
            return
        
        name, ok = QInputDialog.getText(self, "仓库名称", "输入名称:", text=Path(folder).name)
        if not ok:
            name = Path(folder).name
        
        try:
            self.repo_service.bind_local_folder(Path(folder), name)
            self._load_repositories()
            QMessageBox.information(self, "成功", f"已添加: {name}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加失败: {e}")
    
    def _remove_repository(self):
        if not self.current_repo:
            return
        
        if QMessageBox.question(self, "确认", f"移除 {self.current_repo.name}?") == QMessageBox.Yes:
            self.repo_service.remove_repository(self.current_repo.id)
            self.current_repo = None
            self._load_repositories()
            self.file_tree.clear()
            self.history_tree.clear()
            self.btn_pull.setEnabled(False)
            self.btn_push.setEnabled(False)
            self.btn_sync.setEnabled(False)
            self.btn_commit.setEnabled(False)
    
    def _refresh(self):
        self._load_repositories()
        if self.current_repo:
            self._load_repo_status()
            self._load_history()
    
    def _toggle_auto_sync(self):
        """切换自动同步状态"""
        if self.auto_sync_switch.text() == "开启":
            # 开启自动同步
            self.auto_sync_switch.setText("关闭")
            self.auto_sync_switch.setObjectName("success")
            self.schedule_service.start_auto_sync()
            self.status_bar.showMessage("自动同步已开启")
        else:
            # 关闭自动同步
            self.auto_sync_switch.setText("开启")
            self.auto_sync_switch.setObjectName("secondary")
            self.schedule_service.stop_auto_sync()
            self.status_bar.showMessage("自动同步已关闭")
    
    def _pull(self):
        if not self.current_repo:
            return
        
        self.status_bar.showMessage("正在拉取...")
        
        async def do_pull():
            return await self.git_service.pull(self.current_repo.id)
        
        def on_finished(result):
            self.status_bar.showMessage("拉取完成")
            QMessageBox.information(self, "完成", "拉取成功")
            self._load_repo_status()
            self._load_history()
        
        def on_error(err):
            self.status_bar.showMessage(f"拉取失败: {err}")
            QMessageBox.critical(self, "错误", f"拉取失败: {err}")
        
        worker = AsyncWorker(do_pull)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        self._add_worker(worker)
        worker.start()
    
    def _push(self):
        if not self.current_repo:
            return
        
        self.status_bar.showMessage("正在推送...")
        
        async def do_push():
            return await self.git_service.push(self.current_repo.id)
        
        def on_finished(result):
            self.status_bar.showMessage("推送完成")
            QMessageBox.information(self, "完成", "推送成功")
            self._load_repo_status()
            self._load_history()
        
        def on_error(err):
            self.status_bar.showMessage(f"推送失败: {err}")
            QMessageBox.critical(self, "错误", f"推送失败: {err}")
        
        worker = AsyncWorker(do_push)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        self._add_worker(worker)
        worker.start()
    
    def _sync(self):
        if not self.current_repo:
            return
        
        self.status_bar.showMessage("正在同步...")
        
        async def do_sync():
            return await self.git_service.sync(self.current_repo.id)
        
        def on_finished(result):
            self.status_bar.showMessage("同步完成")
            QMessageBox.information(self, "完成", "同步成功")
            self._load_repo_status()
            self._load_history()
        
        def on_error(err):
            self.status_bar.showMessage(f"同步失败: {err}")
            QMessageBox.critical(self, "错误", f"同步失败: {err}")
        
        worker = AsyncWorker(do_sync)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        self._add_worker(worker)
        worker.start()
    
    def _commit(self):
        if not self.current_repo:
            return
        
        message = self.commit_edit.toPlainText().strip()
        
        self.status_bar.showMessage("正在提交...")
        
        async def do_commit():
            return await self.git_service.commit(self.current_repo.id, message)
        
        def on_finished(result):
            self.status_bar.showMessage("提交完成")
            self.commit_edit.clear()
            QMessageBox.information(self, "完成", "提交成功")
            self._load_repo_status()
            self._load_history()
        
        def on_error(err):
            self.status_bar.showMessage(f"提交失败: {err}")
            QMessageBox.critical(self, "错误", f"提交失败: {err}")
        
        worker = AsyncWorker(do_commit)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        self._add_worker(worker)
        worker.start()


def run_gui():
    app = QApplication(sys.argv)
    
    # 初始化主题管理器
    from ..utils.theme_manager import ThemeManager
    theme_manager = ThemeManager()
    theme_manager.initialize(app)
    
    window = MainWindow()
    # 将主题管理器实例传递给主窗口
    window.theme_manager = theme_manager
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
