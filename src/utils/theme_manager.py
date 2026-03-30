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
        self._current_theme: ThemeType = ThemeType(self._config_manager.get("ui_theme", "dark"))
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
                background-color: #f0f0f0;
            }
            
            QWidget {
                background-color: #ffffff;
                color: #333333;
                font-family: Arial, sans-serif;
                font-size: 10pt;
            }
            
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #bdbdbd;
                border-radius: 4px;
                padding: 6px 12px;
                color: #333333;
            }
            
            QPushButton:hover {
                background-color: #d5d5d5;
            }
            
            QPushButton:pressed {
                background-color: #bdbdbd;
            }
            
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #9e9e9e;
                border-color: #e0e0e0;
            }
            
            QTreeWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                selection-background-color: #e3f2fd;
                selection-color: #1976d2;
            }
            
            QTreeWidget::item {
                height: 24px;
            }
            
            QTreeWidget::header {
                background-color: #f5f5f5;
                border-bottom: 1px solid #e0e0e0;
                height: 24px;
            }
            
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 6px;
            }
            
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 6px;
            }
            
            QLabel {
                color: #333333;
            }
            
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                background-color: #ffffff;
            }
            
            QTabBar::tab {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-bottom-color: transparent;
                padding: 8px 16px;
                margin-right: 2px;
            }
            
            QTabBar::tab:selected {
                background-color: #ffffff;
                font-weight: bold;
            }
            
            QStatusBar {
                background-color: #f5f5f5;
                border-top: 1px solid #e0e0e0;
            }
        """
    
    def _get_dark_stylesheet(self) -> str:
        """获取暗色主题样式表"""
        return """
            QMainWindow {
                background-color: #212121;
            }
            
            QWidget {
                background-color: #212121;
                color: #e0e0e0;
                font-family: Arial, sans-serif;
                font-size: 10pt;
            }
            
            QPushButton {
                background-color: #424242;
                border: 1px solid #616161;
                border-radius: 4px;
                padding: 6px 12px;
                color: #e0e0e0;
            }
            
            QPushButton:hover {
                background-color: #4e4e4e;
            }
            
            QPushButton:pressed {
                background-color: #616161;
            }
            
            QPushButton:disabled {
                background-color: #333333;
                color: #757575;
                border-color: #424242;
            }
            
            QTreeWidget {
                background-color: #212121;
                border: 1px solid #424242;
                selection-background-color: #1976d2;
                selection-color: #ffffff;
            }
            
            QTreeWidget::item {
                height: 24px;
            }
            
            QTreeWidget::header {
                background-color: #303030;
                border-bottom: 1px solid #424242;
                height: 24px;
            }
            
            QLineEdit {
                background-color: #303030;
                border: 1px solid #424242;
                border-radius: 4px;
                padding: 6px;
                color: #e0e0e0;
            }
            
            QTextEdit {
                background-color: #303030;
                border: 1px solid #424242;
                border-radius: 4px;
                padding: 6px;
                color: #e0e0e0;
            }
            
            QLabel {
                color: #e0e0e0;
            }
            
            QTabWidget::pane {
                border: 1px solid #424242;
                background-color: #212121;
            }
            
            QTabBar::tab {
                background-color: #303030;
                border: 1px solid #424242;
                border-bottom-color: transparent;
                padding: 8px 16px;
                margin-right: 2px;
                color: #e0e0e0;
            }
            
            QTabBar::tab:selected {
                background-color: #212121;
                font-weight: bold;
            }
            
            QStatusBar {
                background-color: #303030;
                border-top: 1px solid #424242;
                color: #e0e0e0;
            }
            
            QMenuBar {
                background-color: #303030;
                color: #e0e0e0;
            }
            
            QMenu {
                background-color: #303030;
                color: #e0e0e0;
                border: 1px solid #424242;
            }
            
            QMenu::item {
                padding: 6px 16px;
            }
            
            QMenu::item:selected {
                background-color: #1976d2;
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
