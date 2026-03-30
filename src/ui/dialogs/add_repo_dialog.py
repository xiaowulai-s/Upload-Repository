"""添加仓库对话框"""

from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFileDialog, QCheckBox
)


class AddRepoDialog(QDialog):
    """添加仓库对话框"""
    
    def __init__(self, parent=None):
        super().__init__()
        self.setWindowTitle("添加仓库")
        self.setMinimumSize(500, 400)
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        folder_label = QLabel("本地文件夹:")
        layout.addWidget(folder_label)
        
        folder_layout = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("选择本地文件夹...")
        folder_layout.addWidget(self.folder_edit)
        
        self.btn_browse = QPushButton("浏览...")
        self.btn_browse.clicked.connect(self._browse_folder)
        folder_layout.addWidget(self.btn_browse)
        
        layout.addLayout(folder_layout)
        
        remote_label = QLabel("远程仓库 URL (可选):")
        layout.addWidget(remote_label)
        
        self.remote_edit = QLineEdit()
        self.remote_edit.setPlaceholderText("https://github.com/user/repo.git")
        layout.addWidget(self.remote_edit)
        
        self.auto_sync_check = QCheckBox("自动同步")
        layout.addWidget(self.auto_sync_check)
        
        button_layout = QHBoxLayout()
        
        self.btn_ok = QPushButton("确定")
        self.btn_ok.clicked.connect(self.accept)
        button_layout.addWidget(self.btn_ok)
        
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(button_layout)
    
    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            self.folder_edit.setText(folder)
    
    def get_values(self) -> Tuple[Path, str, bool]:
        return (
            Path(self.folder_edit.text()),
            self.remote_edit.text().strip() or None,
            self.auto_sync_check.isChecked()
        )
    
    def accept(self):
        self.done(1, self.get_values())
    
    def reject(self):
        self.done(0, self.get_values())
