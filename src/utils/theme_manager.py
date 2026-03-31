"""主题管理器"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

from .logger import logger
from ..data.config_manager import ConfigManager


class ThemeType(Enum):
    """主题类型"""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


@dataclass
class ThemeConfig:
    """主题配置"""
    type: ThemeType
    stylesheet: str
    palette: Dict[str, str]


class ThemeManager:
    """主题管理器"""
    
    def __init__(self):
        self._config_manager = ConfigManager()
        self._current_theme: ThemeType = ThemeType(self._config_manager.get("ui_theme", "light"))
        self._app: Optional[QApplication] = None
        self._stylesheets: Dict[ThemeType, str] = {
            ThemeType.LIGHT: self._get_light_stylesheet(),
            ThemeType.DARK: self._get_dark_stylesheet(),
            ThemeType.SYSTEM: ""
        }
    
    def initialize(self, app: QApplication):
        """初始化主题管理器"""
        self._app = app
        # 设置初始主题
        self.set_theme(self._current_theme)
    
    def _get_light_stylesheet(self) -> str:
        """获取亮色主题样式表"""
        return """
            QMainWindow {
                background-color: #f5f5f5;
            }
            
            QWidget {
                background-color: #ffffff;
                color: #333333;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 10pt;
            }
            
            /* ===== 按钮系统 ===== */
            QPushButton {
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 10pt;
                color: #333333;
            }
            
            /* 主按钮 */
            QPushButton#primary {
                background-color: #3B82F6;
                color: #ffffff;
                border: none;
            }
            QPushButton#primary:hover {
                background-color: #2563EB;
            }
            
            /* 次要按钮 */
            QPushButton#secondary {
                background-color: transparent;
                border: 1px solid #374151;
                color: #333333;
            }
            QPushButton#secondary:hover {
                border-color: #6B7280;
            }
            
            /* 危险按钮 */
            QPushButton#danger {
                background-color: #EF4444;
                color: #ffffff;
                border: none;
            }
            QPushButton#danger:hover {
                background-color: #DC2626;
            }
            
            /* 成功按钮 */
            QPushButton#success {
                background-color: #22C55E;
                color: #ffffff;
                border: none;
            }
            QPushButton#success:hover {
                background-color: #16A34A;
            }
            
            /* 幽灵按钮 */
            QPushButton#ghost {
                background-color: transparent;
                border: none;
                color: #6B7280;
            }
            QPushButton#ghost:hover {
                color: #3B82F6;
            }
            
            /* 禁用状态 */
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #9CA3AF;
                border-color: #E5E7EB;
            }
            
            /* ===== 输入控件 ===== */
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 8px;
                color: #333333;
            }
            QLineEdit:hover {
                border-color: #9CA3AF;
            }
            QLineEdit:focus {
                border-color: #3B82F6;
                outline: none;
            }
            
            /* 下拉框 */
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 8px;
                color: #333333;
                min-width: 120px;
            }
            QComboBox:hover {
                border-color: #9CA3AF;
            }
            QComboBox:focus {
                border-color: #3B82F6;
                outline: none;
            }
            QComboBox::drop-down {
                background-color: transparent;
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: url(:/icons/down_arrow.png);
                width: 12px;
                height: 12px;
            }
            
            /* 文本编辑区 */
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 8px;
                color: #333333;
            }
            QTextEdit:hover {
                border-color: #9CA3AF;
            }
            QTextEdit:focus {
                border-color: #3B82F6;
                outline: none;
            }
            
            /* 复选框 */
            QCheckBox {
                color: #333333;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #E5E7EB;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #3B82F6;
                border-color: #3B82F6;
                image: url(:/icons/check.png);
            }
            
            /* 树控件 */
            QTreeWidget {
                background-color: #ffffff;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                selection-background-color: #E0F2FE;
                selection-color: #0369A1;
            }
            
            QTreeWidget::item {
                height: 28px;
                padding: 2px 5px;
            }
            
            QTreeWidget::header {
                background-color: #F3F4F6;
                border-bottom: 1px solid #E5E7EB;
                height: 32px;
                font-weight: bold;
            }
            
            QTreeWidget::header::section {
                border: 1px solid #E5E7EB;
                background-color: #F3F4F6;
                padding: 5px;
            }
            
            /* 标签页 */
            QTabWidget::pane {
                border: 1px solid #E5E7EB;
                background-color: #ffffff;
                border-radius: 8px;
                padding: 10px;
            }
            
            QTabBar::tab {
                background-color: #F3F4F6;
                border: 1px solid #E5E7EB;
                border-bottom-color: transparent;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                color: #6B7280;
            }
            
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #333333;
                font-weight: bold;
            }
            
            QTabBar::tab:hover {
                background-color: #E5E7EB;
            }
            
            /* 状态栏 */
            QStatusBar {
                background-color: #F3F4F6;
                border-top: 1px solid #E5E7EB;
                color: #6B7280;
            }
            
            /* 标签 */
            QLabel {
                color: #333333;
            }
            
            /* 分割器 */
            QSplitter::handle {
                background-color: #E5E7EB;
            }
            QSplitter::handle:hover {
                background-color: #9CA3AF;
            }
            
            /* 菜单 */
            QMenuBar {
                background-color: #F3F4F6;
                border-bottom: 1px solid #E5E7EB;
                color: #333333;
            }
            
            QMenu {
                background-color: #ffffff;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                color: #333333;
            }
            
            QMenu::item {
                padding: 6px 16px;
            }
            
            QMenu::item:selected {
                background-color: #E0F2FE;
                color: #0369A1;
            }
            
            /* 进度条 */
            QProgressBar {
                background-color: #F3F4F6;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3B82F6;
                border-radius: 5px;
            }
            
            /* 滚动条 */
            QScrollBar:vertical {
                background-color: #F3F4F6;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #9CA3AF;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #6B7280;
            }
            QScrollBar:horizontal {
                background-color: #F3F4F6;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #9CA3AF;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #6B7280;
            }
        """
    
    def _get_dark_stylesheet(self) -> str:
        """获取暗色主题样式表"""
        return """
            QMainWindow {
                background-color: #0B1220;
            }
            
            QWidget {
                background-color: #111827;
                color: #E6EDF3;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 10pt;
            }
            
            /* ===== 按钮系统 ===== */
            QPushButton {
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 10pt;
                color: #E6EDF3;
            }
            
            /* 主按钮 */
            QPushButton#primary {
                background-color: #3B82F6;
                color: #ffffff;
                border: none;
            }
            QPushButton#primary:hover {
                background-color: #2563EB;
            }
            
            /* 次要按钮 */
            QPushButton#secondary {
                background-color: transparent;
                border: 1px solid #374151;
                color: #E6EDF3;
            }
            QPushButton#secondary:hover {
                border-color: #6B7280;
            }
            
            /* 危险按钮 */
            QPushButton#danger {
                background-color: #EF4444;
                color: #ffffff;
                border: none;
            }
            QPushButton#danger:hover {
                background-color: #DC2626;
            }
            
            /* 成功按钮 */
            QPushButton#success {
                background-color: #22C55E;
                color: #ffffff;
                border: none;
            }
            QPushButton#success:hover {
                background-color: #16A34A;
            }
            
            /* 幽灵按钮 */
            QPushButton#ghost {
                background-color: transparent;
                border: none;
                color: #9CA3AF;
            }
            QPushButton#ghost:hover {
                color: #3B82F6;
            }
            
            /* 禁用状态 */
            QPushButton:disabled {
                background-color: #1F2937;
                color: #4B5563;
                border-color: #374151;
            }
            
            /* ===== 输入控件 ===== */
            QLineEdit {
                background-color: #1F2937;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 8px;
                color: #E6EDF3;
            }
            QLineEdit:hover {
                border-color: #6B7280;
            }
            QLineEdit:focus {
                border-color: #3B82F6;
                outline: none;
            }
            
            QTextEdit {
                background-color: #1F2937;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 8px;
                color: #E6EDF3;
            }
            QTextEdit:hover {
                border-color: #6B7280;
            }
            QTextEdit:focus {
                border-color: #3B82F6;
                outline: none;
            }
            
            /* ===== 树控件 ===== */
            QTreeWidget {
                background-color: #111827;
                border: 1px solid #374151;
                border-radius: 8px;
                selection-background-color: #1E40AF;
                selection-color: #ffffff;
            }
            
            QTreeWidget::item {
                height: 28px;
                padding: 2px 5px;
            }
            
            QTreeWidget::header {
                background-color: #1F2937;
                border-bottom: 1px solid #374151;
                height: 32px;
                font-weight: bold;
            }
            
            QTreeWidget::header::section {
                border: 1px solid #374151;
                background-color: #1F2937;
                padding: 5px;
            }
            
            /* ===== 标签页 ===== */
            QTabWidget::pane {
                border: 1px solid #374151;
                background-color: #111827;
                border-radius: 8px;
                padding: 10px;
            }
            
            QTabBar::tab {
                background-color: #1F2937;
                border: 1px solid #374151;
                border-bottom-color: transparent;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                color: #9CA3AF;
            }
            
            QTabBar::tab:selected {
                background-color: #111827;
                color: #E6EDF3;
                font-weight: bold;
            }
            
            QTabBar::tab:hover {
                background-color: #374151;
            }
            
            /* ===== 状态栏 ===== */
            QStatusBar {
                background-color: #1F2937;
                border-top: 1px solid #374151;
                color: #9CA3AF;
            }
            
            /* ===== 标签 ===== */
            QLabel {
                color: #E6EDF3;
            }
            
            /* ===== 分割器 ===== */
            QSplitter::handle {
                background-color: #374151;
            }
            QSplitter::handle:hover {
                background-color: #6B7280;
            }
            
            /* ===== 菜单 ===== */
            QMenuBar {
                background-color: #1F2937;
                border-bottom: 1px solid #374151;
                color: #E6EDF3;
            }
            
            QMenu {
                background-color: #111827;
                border: 1px solid #374151;
                border-radius: 8px;
                color: #E6EDF3;
            }
            
            QMenu::item {
                padding: 6px 16px;
            }
            
            QMenu::item:selected {
                background-color: #1E40AF;
                color: #ffffff;
            }
        """
    
    def set_theme(self, theme_type: ThemeType):
        """设置主题"""
        if not self._app:
            logger.warning("ThemeManager not initialized, call initialize() first")
            return
        
        self._current_theme = theme_type
        
        # 保存主题配置
        self._config_manager.set("ui_theme", theme_type.value)
        
        # 设置样式
        if theme_type == ThemeType.SYSTEM:
            # 系统主题
            self._app.setStyleSheet("")
            self._app.setStyle(QStyleFactory.create("Fusion"))
        else:
            # 自定义主题
            self._app.setStyle(QStyleFactory.create("Fusion"))
            self._app.setStyleSheet(self._stylesheets[theme_type])
        
        logger.info(f"Theme set to {theme_type.value}")
    
    def get_current_theme(self) -> ThemeType:
        """获取当前主题"""
        return self._current_theme
    
    def toggle_theme(self):
        """切换主题"""
        if self._current_theme == ThemeType.LIGHT:
            self.set_theme(ThemeType.DARK)
        else:
            self.set_theme(ThemeType.LIGHT)
    
    def get_available_themes(self) -> Dict[str, str]:
        """获取可用主题列表"""
        return {
            ThemeType.LIGHT.value: "亮色",
            ThemeType.DARK.value: "暗色",
            ThemeType.SYSTEM.value: "系统"
        }
    
    def apply_theme_to_widget(self, widget):
        """将当前主题应用到指定控件"""
        if not self._app:
            return
        
        widget.setStyleSheet(self._stylesheets[self._current_theme])
