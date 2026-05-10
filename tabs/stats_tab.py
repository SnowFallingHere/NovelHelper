"""
统计与分析标签页
集成写作数据仪表板和大纲时间线视图

功能：
- 实时写作数据展示（总字数、章节数、日均速度等）
- 各卷进度可视化
- 关键词覆盖率分析
- 写作趋势图表
- 章节时间线导航
- 最近更新追踪
"""

import os
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QMessageBox, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QEvent

from .base_tab import BaseTab
from ..core.config_manager import ConfigManager
from ..core.language_manager import language_manager
from ..core.file_manager import get_novel_dir
from ..widgets.writing_dashboard import WritingDashboard
from ..widgets.timeline_view import TimelineView, MiniTimelineWidget

logger = logging.getLogger(__name__)


class StatsTab(BaseTab):
    """统计与分析标签页"""
    
    # 信号定义
    data_exported = pyqtSignal(str)  # 数据导出时发出
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_name = "统计与分析"
        
        # 配置属性
        self.base_title_size = int(ConfigManager.get('UI', 'title_size', fallback='18'))
        self._collapsed = {}
        
        logger.info(f"[{self.tab_name}] 创建实例")
    
    def _build_ui(self):
        """构建UI界面"""
        from ..ui.widget_factory import create_button, create_group_box

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        scroll_content = QWidget()
        main_layout = QVBoxLayout(scroll_content)
        main_layout.setContentsMargins(16, 10, 16, 10)
        main_layout.setSpacing(14)

        from ..core.theme_manager import theme_manager as tm

        # ====== 标题栏 ======
        header = QHBoxLayout()
        self._title_label = QLabel("统计与分析中心")
        self._title_label.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {tm.get('accent_color', '#0078D4')};"
        )
        header.addWidget(self._title_label)
        header.addStretch()

        self._refresh_all_btn = create_button(
            language_manager.tr("refresh_all_btn"), kind='primary', min_height=36, min_width=120,
            on_click=self._refresh_all_data
        )
        header.addWidget(self._refresh_all_btn)

        self._export_btn = create_button(
            language_manager.tr("export_report_btn"), kind='secondary', min_height=36, min_width=120,
            on_click=self._export_full_report
        )
        header.addWidget(self._export_btn)
        main_layout.addLayout(header)

        # ====== 写作数据仪表板 ======
        self._dash_group_box = create_group_box("写作数据仪表板")
        dash_layout = QVBoxLayout(self._dash_group_box)
        dash_layout.setSpacing(8)
        dash_layout.setContentsMargins(20, 32, 20, 20)
        self.dashboard = WritingDashboard(self)
        dash_layout.addWidget(self.dashboard, 1)
        self._dash_group = self._dash_group_box
        self._make_collapsible(self._dash_group_box, 'dashboard')
        main_layout.addWidget(self._dash_group_box, 1)

        # ====== 大纲时间线 ======
        self._timeline_group_box = create_group_box("大纲时间线")
        self._timeline_group_box.setMinimumHeight(600)
        timeline_layout = QVBoxLayout(self._timeline_group_box)
        timeline_layout.setSpacing(6)
        timeline_layout.setContentsMargins(12, 28, 12, 12)
        self.timeline_view = TimelineView(self)
        self.timeline_view.node_clicked.connect(self._on_timeline_node_clicked)
        self.timeline_view.node_double_clicked.connect(self._on_timeline_node_double_clicked)
        timeline_layout.addWidget(self.timeline_view, 1)
        self._timeline_group = self._timeline_group_box
        self._make_collapsible(self._timeline_group_box, 'timeline')
        main_layout.addWidget(self._timeline_group_box, 5)

        # ====== 最近更新 ======
        self._recent_group_box = create_group_box("最近更新的章节")
        self._recent_group_box.setMinimumHeight(400)
        recent_layout = QVBoxLayout(self._recent_group_box)
        recent_layout.setSpacing(4)
        recent_layout.setContentsMargins(12, 28, 12, 12)
        self.mini_timeline = MiniTimelineWidget(max_items=12)
        self.mini_timeline.node_selected.connect(self._on_timeline_node_selected)
        recent_layout.addWidget(self.mini_timeline, 1)
        self._recent_group = self._recent_group_box
        self._make_collapsible(self._recent_group_box, 'recent')
        main_layout.addWidget(self._recent_group_box, 4)

        scroll.setWidget(scroll_content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # 底部状态栏（固定在底部）
        status_frame = QFrame()
        status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {tm.get('card_bg', '#FFFFFF')};
                border-top: 1px solid {tm.get('border_color', '#DEE2E6')};
            }}
        """)
        status = QHBoxLayout(status_frame)
        status.setContentsMargins(16, 4, 16, 4)
        status.setSpacing(12)
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet(
            f"color: {tm.get('fg_color', '#212529')}; font-size: 11px; border: none;"
        )
        status.addWidget(self.status_label)
        sep = QLabel("|")
        sep.setStyleSheet(
            f"color: {tm.get('border_color', '#DEE2E6')}; font-size: 10px; border: none;"
        )
        status.addWidget(sep)
        self._auto_label = QLabel("自动刷新: 5分钟")
        self._auto_label.setStyleSheet(
            f"color: {tm.get('text_secondary', '#6C757D')}; font-size: 11px; border: none;"
        )
        status.addWidget(self._auto_label)
        status.addStretch()
        outer.addWidget(status_frame)

        logger.debug(f"[{self.tab_name}] UI构建完成")

    def retranslate_ui(self):
        lm = language_manager.tr
        if hasattr(self, '_title_label'):
            self._title_label.setText("统计与分析中心")
        if hasattr(self, '_refresh_all_btn'):
            self._refresh_all_btn.setText(lm("refresh_all_btn"))
        if hasattr(self, '_export_btn'):
            self._export_btn.setText(lm("export_report_btn"))
        if hasattr(self, '_dash_group_box'):
            self._dash_group_box.setTitle("写作数据仪表板")
        if hasattr(self, '_timeline_group_box'):
            self._timeline_group_box.setTitle("大纲时间线")
        if hasattr(self, '_recent_group_box'):
            self._recent_group_box.setTitle("最近更新的章节")
        if hasattr(self, 'status_label'):
            self.status_label.setText("就绪")
        if hasattr(self, '_auto_label'):
            self._auto_label.setText("自动刷新: 5分钟")

    def _make_collapsible(self, group_box: QGroupBox, key: str):
        """使QGroupBox支持点击标题折叠/展开"""
        group_box.setProperty('_collapse_key', key)
        group_box.installEventFilter(self)
        self._collapsed.setdefault(key, False)

    def eventFilter(self, obj, event):
        if isinstance(obj, QGroupBox) and event.type() == QEvent.MouseButtonPress:
            key = obj.property('_collapse_key')
            if key and event.pos().y() < 32:
                self._toggle_collapse(obj, key)
                return True
        return super().eventFilter(obj, event)

    def _toggle_collapse(self, group_box: QGroupBox, key: str):
        self._collapsed[key] = not self._collapsed[key]
        collapsed = self._collapsed[key]
        for child in group_box.findChildren(QWidget, '', Qt.FindDirectChildrenOnly):
            child.setVisible(not collapsed)
        title = group_box.title().rstrip(' ▶').strip()
        group_box.setTitle(f"{title}  {'▶' if collapsed else '▼'}")

    def _load_data(self):
        """加载数据"""
        # 延迟到首次显示或手动刷新时加载
        pass
    
    def initialize(self):
        """延迟初始化（首次显示时调用）"""
        if not super().initialize():
            return False
        
        # 自动检测并加载小说目录
        novel_dir = get_novel_dir()
        if novel_dir and os.path.exists(novel_dir):
            self._load_novel_data(novel_dir)
        
        return True
    
    def _load_novel_data(self, novel_dir: str):
        """加载小说数据"""
        try:
            # 设置仪表板数据源
            self.dashboard.set_novel_dir(novel_dir)
            
            # 加载时间线数据
            self._load_timeline_from_cache(novel_dir)
            
            # 更新状态
            self.status_label.setText(f"已加载目录: {novel_dir}")
            
            # 自动刷新一次
            self._refresh_all_data()
            
            logger.info(f"[{self.tab_name}]: {novel_dir}")
            
        except Exception as e:
            logger.error(f"[{self.tab_name}] 加载数据失败: {e}", exc_info=True)
            self.status_label.setText(f"加载失败: {str(e)}")
    
    def _load_timeline_from_cache(self, novel_dir: str):
        """从章节缓存加载时间线数据"""
        try:
            cache = self.dashboard.get_chapter_cache()
            if not cache:
                from core.chapter_index_cache import ChapterIndexCache
                cache = ChapterIndexCache(novel_dir)
            self.timeline_view.load_from_chapter_cache(cache)
            
            # 同时填充迷你时间线
            recent_items = cache.get_recently_modified(hours=24 * 7)  # 最近7天
            timeline_data = []
            for item in recent_items[:8]:
                timeline_data.append({
                    'title': item.get('chapter', '?'),
                    'subtitle': f"{item.get('word_count', 0)}字 | {item.get('modified_at', '')}",
                    'volume': item.get('volume', ''),
                    'path': item.get('path', '')
                })
            
            if timeline_data:
                self.mini_timeline.set_items(timeline_data)
                
        except Exception as e:
            logger.warning(f"[{self.tab_name}] 时间线加载失败: {e}")

    def reload_data(self):
        """重新加载数据（小说路径变更时调用）"""
        novel_dir = get_novel_dir()
        if novel_dir and os.path.exists(novel_dir):
            self._load_novel_data(novel_dir)

    def _refresh_all_data(self):
        """刷新所有数据"""
        self.status_label.setText("正在刷新数据...")
        
        try:
            # 刷新仪表板数据
            self.dashboard.refresh_data()
            
            # 刷新时间线
            novel_dir = get_novel_dir()
            if novel_dir and os.path.exists(novel_dir):
                self._load_timeline_from_cache(novel_dir)
            
            self.status_label.setText("数据刷新完成")
            
        except Exception as e:
            logger.error(f"[{self.tab_name}] 刷新失败: {e}", exc_info=True)
            self.status_label.setText(f"刷新失败: {str(e)}")
    
    def _export_full_report(self):
        """导出完整报告"""
        try:
            # 导出仪表板报告
            self.dashboard._export_report()
            
            # 发出信号
            self.data_exported.emit("full_report")
            
        except Exception as e:
            QMessageBox.warning(
                self, 
                "导出失败", 
                f"无法导出报告:\n{str(e)}"
            )
    
    def _on_timeline_node_selected(self, path: str):
        """时间线节点选中事件"""
        if path and os.path.isfile(path):
            try:
                os.startfile(path)
                logger.debug(f"[{self.tab_name}] 打开文件: {path}")
            except Exception:
                pass
    
    def _on_timeline_node_clicked(self, node_data: dict):
        """时间线节点点击事件"""
        chapter_name = node_data.get('title', '')
        volume = node_data.get('volume', '')
        self.status_label.setText(
            f"当前选择: 【{volume}】{chapter_name}"
        )
    
    def _on_timeline_node_double_clicked(self, path: str):
        """时间线节点双击事件"""
        self._on_timeline_node_selected(path)
    
    def refresh(self, force=False):
        """外部调用刷新接口"""
        if force or not self._initialized:
            self.initialize()
        else:
            self._refresh_all_data()
    
    def update_config(self):
        """配置变更时调用"""
        pass  # 暂无配置项需要响应
