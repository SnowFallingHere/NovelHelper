"""
NovelHelper 主窗口类
基于 qframelesswindow.AcrylicWindow —— 原生亚克力、无边框、无白色残影
"""
import os
import sys
import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTabBar, QLabel, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QSettings, QSize
from PyQt5.QtGui import QFont

from qframelesswindow import AcrylicWindow
from qfluentwidgets import FluentTitleBar

from novelhelper.core.config_manager import ConfigManager
from novelhelper.core.language_manager import language_manager
from novelhelper.core.file_manager import get_base_dir, file_manager
from novelhelper.core.theme_manager import theme_manager

from novelhelper.tabs.base_tab import BaseTab, initialize_tab_if_needed
from novelhelper.tabs.create_tab import CreateTab
from novelhelper.tabs.summary_tab import SummaryTab
from novelhelper.tabs.monitor_tab import MonitorTab
from novelhelper.tabs.keyword_tab import KeywordTab
from novelhelper.tabs.config_tab import ConfigTab
from novelhelper.tabs.help_tab import HelpTab
from novelhelper.tabs.stats_tab import StatsTab

from novelhelper.core.animation_manager import (
    HoverBounceEffect, is_animation_enabled
)
from novelhelper.ui.style_theme import apply_global_stylesheet

logger = logging.getLogger(__name__)


def get_log_dir():
    log_dir = os.path.join(get_base_dir(), "log")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    return log_dir


def setup_logging():
    log_dir = get_log_dir()
    log_file = os.path.join(log_dir, f"NovelHelper_{datetime.now().strftime('%Y%m%d')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


setup_logging()
logger = logging.getLogger(__name__)


class NovelHelper(AcrylicWindow):
    """NovelHelper 主窗口 — AcrylicWindow 提供亚克力 + 无边框 + DWM 合成"""

    def __init__(self):
        self.settings = QSettings("NovelHelper", "NovelHelper")
        self.load_config_values()
        self._geometry_restored = False

        theme_name = ConfigManager.get('UI', 'theme', fallback='fluent')
        theme_manager.set_theme(theme_name)

        super().__init__()

        self.setMinimumSize(self.min_width, self.min_height)

        self._tab_instances = {}
        self._tabs_created = set()

        self.setTitleBar(FluentTitleBar(self))
        self.titleBar.setTitle(language_manager.tr("app_title"))
        self.titleBar.minBtn.clicked.disconnect()
        self.titleBar.minBtn.clicked.connect(self.showMinimized)
        self.titleBar.closeBtn.clicked.disconnect()
        self.titleBar.closeBtn.clicked.connect(self.close)

        self._build_content()

        self._tabs_created.add('create')
        self.tabs.currentChanged.connect(self._on_tab_changed)

        first_tab = self.tabs.widget(0)
        if isinstance(first_tab, BaseTab):
            first_tab.initialize()

        self.load_settings()
        if not self._geometry_restored:
            self.apply_adaptive()

        apply_global_stylesheet()

        QTimer.singleShot(100, self._lazy_init_tabs)

        logger.info(f"{language_manager.tr('app_title')} started")

    def load_config_values(self):
        self.base_font_size = ConfigManager.get_int('UI', 'base_font_size', fallback=14)
        self.base_title_size = ConfigManager.get_int('UI', 'base_title_size', fallback=16)
        self.initial_width = ConfigManager.get_int('UI', 'initial_width', fallback=1100)
        self.initial_height = ConfigManager.get_int('UI', 'initial_height', fallback=700)
        self.min_width = ConfigManager.get_int('UI', 'min_width', fallback=800)
        self.min_height = ConfigManager.get_int('UI', 'min_height', fallback=550)

    def _build_content(self):
        # AcrylicWindow 的标题栏是独立悬浮控件（不在布局中）
        # 需要创建布局时留出顶部空间给标题栏
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        layout.addWidget(self.tabs, 1)

        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(44)
        bottom_bar.setObjectName('bottomBar')
        bottom_bar.setStyleSheet(f"""
            #bottomBar {{
                background-color: {theme_manager.get('card_bg', '#F8F9FA')};
                border-top: 1px solid {theme_manager.get('border_color', '#DEE2E6')};
            }}
        """)

        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(16, 4, 16, 4)
        bottom_layout.addStretch()

        self._save_exit_btn = QPushButton(language_manager.tr("save_and_exit_btn"))
        self._save_exit_btn.setFixedHeight(34)
        self._save_exit_btn.setMinimumWidth(120)
        self._save_exit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_manager.get('accent_color', '#0078D4')};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 20px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.get('accent_color', '#0078D4')}CC;
            }}
        """)
        HoverBounceEffect.apply(self._save_exit_btn)
        self._save_exit_btn.clicked.connect(self._save_and_exit)
        bottom_layout.addWidget(self._save_exit_btn)
        layout.addWidget(bottom_bar)

        win_layout = QVBoxLayout(self)
        win_layout.setContentsMargins(0, self.titleBar.height(), 0, 0)
        win_layout.setSpacing(0)
        win_layout.addWidget(content)
        self.create_tab()

    def create_tab(self):
        logger.info("创建标签页: create")
        tab = CreateTab(self)
        self._tab_instances['create'] = tab
        self.tabs.addTab(tab, language_manager.tr("init_and_create_tab"))

    def _lazy_init_tabs(self):
        init_queue = ['summary', 'monitor', 'keyword', 'stats', 'config', 'help']
        self._init_queue = list(init_queue)
        self._process_init_queue()

    def _process_init_queue(self):
        if not self._init_queue:
            logger.info("所有标签页已延迟加载完成")
            return
        tab_name = self._init_queue.pop(0)
        self._create_tab_by_name(tab_name)
        self._tabs_created.add(tab_name)
        current_idx = self.tabs.currentIndex()
        for i in range(self.tabs.count()):
            if self._get_tab_name_by_index(i) == tab_name and i == current_idx:
                tab = self.tabs.widget(i)
                if isinstance(tab, BaseTab):
                    initialize_tab_if_needed(tab)
        if self._init_queue:
            QTimer.singleShot(50, self._process_init_queue)

    def _create_tab_by_name(self, tab_name):
        method_map = {
            'summary': self.summary_tab,
            'monitor': self.monitor_tab,
            'keyword': self.keyword_tab,
            'stats': self.stats_tab,
            'config': self.config_tab,
            'help': self.help_tab,
        }
        method = method_map.get(tab_name)
        if method:
            method()

    def summary_tab(self):
        tab = SummaryTab(self)
        self._tab_instances['summary'] = tab
        self.tabs.addTab(tab, language_manager.tr("summary_merge_tool"))

    def monitor_tab(self):
        tab = MonitorTab(self)
        self._tab_instances['monitor'] = tab
        self.tabs.addTab(tab, language_manager.tr("monitor_management"))
        tab.new_chapter_detected.connect(self._on_monitor_new_chapter)

    def keyword_tab(self):
        tab = KeywordTab(self)
        self._tab_instances['keyword'] = tab
        self.tabs.addTab(tab, language_manager.tr("keyword_manager"))

    def stats_tab(self):
        tab = StatsTab(self)
        self._tab_instances['stats'] = tab
        self.tabs.addTab(tab, language_manager.tr("stats_analysis"))

    def config_tab(self):
        tab = ConfigTab(self)
        self._tab_instances['config'] = tab
        self.tabs.addTab(tab, language_manager.tr("parameter_config"))
        tab.config_saved.connect(self._on_config_saved)
        tab.config_applied.connect(self._on_config_applied)
        tab.overlay_pos_changed.connect(self._on_overlay_pos_changed)
        tab.legend_config_changed.connect(self._on_legend_config_changed)
        tab.glow_config_changed.connect(self._on_glow_config_changed)
        tab.size_sort_config_changed.connect(self._on_size_sort_config_changed)

    def help_tab(self):
        tab = HelpTab(self)
        self._tab_instances['help'] = tab
        self.tabs.addTab(tab, language_manager.tr("user_guide"))

    def _on_tab_changed(self, index):
        tab_name = self._get_tab_name_by_index(index)
        if tab_name and tab_name not in self._tabs_created:
            self._create_tab_lazy(tab_name)
        tab = self.tabs.widget(index)
        if isinstance(tab, BaseTab):
            initialize_tab_if_needed(tab)

    def _get_tab_name_by_index(self, index):
        names = {0: 'create', 1: 'summary', 2: 'monitor', 3: 'keyword',
                 4: 'stats', 5: 'config', 6: 'help'}
        return names.get(index)

    def _create_tab_lazy(self, tab_name):
        if tab_name in self._tabs_created:
            return
        self._create_tab_by_name(tab_name)
        self._tabs_created.add(tab_name)

    def _on_monitor_new_chapter(self):
        """监控检测到新章节时刷新统计页"""
        if 'stats' in self._tab_instances:
            try:
                self._tab_instances['stats'].refresh()
            except Exception:
                pass

    def _on_config_saved(self):
        file_manager._load_custom_formats()
        self.update_ui_language()
        if 'config' in self._tab_instances:
            self._tab_instances['config'].reload_config()

    def _on_config_applied(self):
        theme_name = ConfigManager.get('UI', 'theme', fallback='fluent')
        theme_manager.set_theme(theme_name)
        self.load_config_values()
        apply_global_stylesheet()
        self.update_ui_language()
        # 跨标签页刷新
        if 'create' in self._tab_instances:
            self._tab_instances['create']._load_data()
        if 'keyword' in self._tab_instances:
            self._tab_instances['keyword'].update_config()
        if 'config' in self._tab_instances:
            self._tab_instances['config'].reload_config()
        if 'keyword' in self._tab_instances:
            view = getattr(self._tab_instances['keyword'], 'network_graph_view', None)
            if view:
                follow = ConfigManager.get('Theme', 'graph_bg_follow_theme', fallback='1') == '1'
                if follow:
                    bg = theme_manager.get('graph_bg', '#F8F9FA')
                else:
                    bg = ConfigManager.get('Theme', 'graph_bg_color', fallback='#F8F9FA')
                view.update_graph_background(bg_color=bg)
        if 'summary' in self._tab_instances:
            try:
                self._tab_instances['summary']._load_data()
            except Exception:
                pass
        if 'monitor' in self._tab_instances:
            try:
                self._tab_instances['monitor'].load_data()
            except Exception:
                pass
        if 'stats' in self._tab_instances:
            try:
                self._tab_instances['stats'].reload_data()
            except Exception:
                pass

    def _on_overlay_pos_changed(self, pos):
        if 'keyword' in self._tab_instances:
            self._tab_instances['keyword'].set_overlay_position(pos)

    def _on_legend_config_changed(self, visible, font_name, font_size):
        if 'keyword' in self._tab_instances:
            self._tab_instances['keyword'].update_legend_config(visible, font_name, font_size)

    def _on_glow_config_changed(self, enabled):
        if 'keyword' in self._tab_instances:
            self._tab_instances['keyword'].update_glow_config(enabled)

    def _on_size_sort_config_changed(self, enabled):
        if 'keyword' in self._tab_instances:
            self._tab_instances['keyword'].update_size_sort_config(enabled)

    def update_ui_language(self):
        if hasattr(self, 'titleBar'):
            self.titleBar.setTitle(language_manager.tr("app_title"))
        tab_titles = {
            0: language_manager.tr("init_and_create_tab"),
            1: language_manager.tr("summary_merge_tool"),
            2: language_manager.tr("monitor_management"),
            3: language_manager.tr("keyword_manager"),
            4: language_manager.tr("stats_analysis"),
            5: language_manager.tr("parameter_config"),
            6: language_manager.tr("user_guide"),
        }
        for idx, title in tab_titles.items():
            if idx < self.tabs.count():
                self.tabs.setTabText(idx, title)
        if hasattr(self, '_save_exit_btn'):
            self._save_exit_btn.setText(language_manager.tr("save_and_exit_btn"))
        if 'help' in self._tab_instances:
            self._tab_instances['help'].refresh_help()
        for tab_name, tab_instance in self._tab_instances.items():
            if hasattr(tab_instance, 'retranslate_ui'):
                tab_instance.retranslate_ui()

    def apply_adaptive(self):
        """首次启动时自适应窗口尺寸，不覆盖用户已保存的几何设置"""
        screen = QApplication.primaryScreen()
        if screen:
            ag = screen.availableGeometry()

            if self.initial_width > int(ag.width() * 0.8):
                self.initial_width = int(ag.width() * 0.8)
            if self.initial_height > int(ag.height() * 0.8):
                self.initial_height = int(ag.height() * 0.8)

            if self.initial_width < self.min_width:
                self.initial_width = self.min_width
            if self.initial_height < self.min_height:
                self.initial_height = self.min_height

            x = (ag.width() - self.initial_width) // 2
            y = (ag.height() - self.initial_height) // 2
            self.setGeometry(x, y, self.initial_width, self.initial_height)

    def load_settings(self):
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            self._geometry_restored = True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.isVisible():
            self.settings.setValue("geometry", self.saveGeometry())
            self._enforce_window_visible()

    def _enforce_window_visible(self):
        """确保窗口至少标题栏区域始终可见"""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        ag = screen.availableGeometry()
        x, y = self.x(), self.y()
        w, h = self.width(), self.height()
        title_bar_h = self.titleBar.height() if hasattr(self, 'titleBar') else 30

        clamped = False
        if x + w < ag.x() + 80:
            x = ag.x() + 20
            clamped = True
        if y + h < ag.y() + title_bar_h + 10:
            y = ag.y() + 20
            clamped = True
        if x > ag.right() - 80:
            x = ag.right() - 80
            clamped = True

        if clamped:
            self.move(x, y)

    def _save_and_exit(self):
        reply = QMessageBox.question(
            self, language_manager.tr("confirm_exit"),
            language_manager.tr("exit_confirm_message"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.settings.setValue("geometry", self.saveGeometry())
            self._cleanup_resources()
            QApplication.quit()

    def _cleanup_resources(self):
        if 'monitor' in self._tab_instances:
            self._tab_instances['monitor'].cleanup()
        for tab_name, tab_instance in self._tab_instances.items():
            if hasattr(tab_instance, 'cleanup'):
                try:
                    tab_instance.cleanup()
                except Exception as e:
                    logger.warning(f"清理标签页 [{tab_name}] 时出错: {e}")

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self._cleanup_resources()
        event.accept()
