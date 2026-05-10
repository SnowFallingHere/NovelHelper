"""
关键词管理标签页
提供关键词列表、卡片视图、神经网络图、词频分析等功能
"""

import os
import json
import hashlib
import logging
from math import log1p
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextBrowser, QComboBox, QCheckBox, QMenu,
    QDialog, QFormLayout, QDialogButtonBox, QInputDialog,
    QMessageBox, QProgressDialog, QApplication, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont, QFontMetrics

from .base_tab import BaseTab
from ..core.config_manager import ConfigManager
from ..core.language_manager import language_manager
from ..core.file_manager import get_novel_dir, get_novel_config_dir, get_base_dir
from ..core.theme_manager import theme_manager
from ..models.keyword_manager import keyword_manager
from ..ui.network_graph import NetworkGraphView, SciFiNodeItem, NodeIndexOverlay

logger = logging.getLogger(__name__)


class ViewMode:
    """视图模式枚举"""
    LIST = 'list'
    CHARACTER_CARD = 'character_card'
    NETWORK_GRAPH = 'network_graph'
    FREQUENCY_DASHBOARD = 'frequency_dashboard'
    FACTION_CARD = 'faction_card'
    FAMILY_TREE = 'family_tree'


class KeywordTab(BaseTab):
    """关键词管理标签页"""
    
    # 信号定义
    keyword_selected = pyqtSignal(str)  # 选中关键词时发出
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_name = "关键词管理"
        
        # 配置属性（从 ConfigManager 加载）
        self._load_config()
        
        # 状态变量
        self._keyword_tab_initialized = False
        self._neural_graph_built = False
        self._neural_graph_hash = None
        self._card_selected_name = None
        self._freq_page = 'overview'
        self._freq_data = None
        self._selected_rejected_words = set()
        self._selected_freq_words = set()
        self._rejected_confirm_disabled = ConfigManager.get('Frequency', 'reject_confirm_disabled', fallback='0') == '1'

        # 视图管理（组织卡&族谱图）
        self._current_view_mode = ViewMode.LIST
        self._current_faction_name = None
        self._family_tree_widget = None

        logger.info(f"[{self.tab_name}] 创建实例")
    
    def _load_config(self):
        """加载配置参数"""
        # 字体配置
        self.base_font_size = int(ConfigManager.get('UI', 'font_size', fallback='14'))
        self.base_title_size = int(ConfigManager.get('UI', 'title_size', fallback='18'))
        
        # ---- 关键词字体配置 ----
        # 注意：以下 kw_* 值存储在 INI 的 [UI] 节下（如 kw_body_size），
        # 所以从 ConfigManager 读取时必须是 ('UI', 'kw_body_size') 而非 ('Keywords', 'body_size')
        self.kwlist_font_family = ConfigManager.get('UI', 'kwlist_font_family', fallback='Microsoft YaHei')
        self.kwlist_font_color = ConfigManager.get('UI', 'kwlist_font_color', fallback='#212529')
        self.kw_h1_size = int(ConfigManager.get('UI', 'kw_h1_size', fallback='20'))
        self.kw_h2_size = int(ConfigManager.get('UI', 'kw_h2_size', fallback='16'))
        self.kw_body_size = int(ConfigManager.get('UI', 'kw_body_size', fallback='14'))
        self.kw_link_size = int(ConfigManager.get('UI', 'kw_link_size', fallback='14'))
        self.kw_link_color = ConfigManager.get('UI', 'kw_link_color', fallback='#0078D4')
        self.kw_h1_color = ConfigManager.get('UI', 'kw_h1_color', fallback='#212529')
        self.kw_h2_color = ConfigManager.get('UI', 'kw_h2_color', fallback='#6C757D')
        self.kw_body_color = ConfigManager.get('UI', 'kw_body_color', fallback='#212529')
        
        # 链接样式
        self.link_bold = ConfigManager.get('UI', 'link_bold', fallback='false') == 'true'
        self.link_italic = ConfigManager.get('UI', 'link_italic', fallback='false') == 'true'
        
        # 图标字体
        self.graph_font_size = int(ConfigManager.get('Graph', 'graph_font_size', fallback='14'))

        # 行高
        self.line_height = float(ConfigManager.get('UI', 'line_height', fallback='1.25'))
    
    def _build_ui(self):
        """构建UI界面"""
        from ..ui.widget_factory import (create_button, create_input,
                                         create_label, create_combo)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 10)

        # ====== 标题 ======
        self._title_label = QLabel(language_manager.tr("keyword_tab_title"))
        self._title_label.setStyleSheet(f"font-size: {self._s(self.base_title_size)}px; font-weight: bold;")
        main_layout.addWidget(self._title_label)

        # ====== 工具栏 ======
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.keyword_view_combo = create_combo([
            language_manager.tr("view_list"),
            language_manager.tr("view_card"),
            language_manager.tr("view_neural"),
            language_manager.tr("view_frequency"),
            "组织卡",
            "族谱图",
        ])
        self.keyword_view_combo.setMinimumWidth(150)
        # 为每个条目设置 data 值（与原有逻辑兼容）
        combo_data = ["list", "card", "neural", "frequency", "faction_card", "family_tree"]
        for i, data in enumerate(combo_data):
            self.keyword_view_combo.setItemData(i, data)
        self.keyword_view_combo.currentIndexChanged.connect(self.refresh_keywords)
        toolbar.addWidget(self.keyword_view_combo)

        self._refresh_btn = create_button(
            language_manager.tr("refresh_btn"),
            kind='secondary', min_height=32, min_width=80,
            on_click=self.refresh_keywords
        )
        toolbar.addWidget(self._refresh_btn)

        self._layout_save_btn = create_button(
            language_manager.tr("save_layout_btn"),
            kind='secondary', min_height=32, min_width=90,
            on_click=self._save_graph_layout
        )
        self._layout_save_btn.setVisible(False)
        toolbar.addWidget(self._layout_save_btn)

        self._layout_reset_btn = create_button(
            language_manager.tr("reset_layout_btn"),
            kind='secondary', min_height=32, min_width=90,
            on_click=self._reset_graph_layout
        )
        self._layout_reset_btn.setVisible(False)
        toolbar.addWidget(self._layout_reset_btn)

        self._isolated_btn = create_button(
            language_manager.tr("detect_isolated_btn"),
            kind='secondary', min_height=32, min_width=100,
            on_click=self._detect_isolated_nodes
        )
        self._isolated_btn.setVisible(False)
        toolbar.addWidget(self._isolated_btn)

        self._export_png_btn = create_button(
            language_manager.tr("export_png_btn"),
            kind='secondary', min_height=32, min_width=90,
            on_click=self._export_graph_png
        )
        self._export_png_btn.setVisible(False)
        toolbar.addWidget(self._export_png_btn)

        main_layout.addLayout(toolbar)
        
        # ====== 列表类型筛选下拉框 ======
        self._list_type_filter = QComboBox()
        self._list_type_filter.setMinimumWidth(120)
        self._list_type_filter.addItem("全部类型", "all")
        self._list_type_filter.addItem("人物", "character")
        self._list_type_filter.addItem("技法", "skill")
        self._list_type_filter.addItem("地点", "location")
        self._list_type_filter.addItem("物品", "item")
        self._list_type_filter.addItem("伏笔", "foreshadowing")
        self._list_type_filter.addItem("事件", "adventure")
        self._list_type_filter.addItem("势力", "faction")
        self._list_type_filter.addItem("时间点", "time_point")
        self._list_type_filter.addItem("关系", "relationship")
        self._list_type_filter.addItem("自定义", "custom")
        self._list_type_filter.currentIndexChanged.connect(self.refresh_keywords)
        self._list_type_filter.setVisible(False)
        toolbar.addWidget(self._list_type_filter)
        
        # ====== 搜索栏 ======
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(language_manager.tr("search_placeholder"))
        self.search_bar.returnPressed.connect(self._on_graph_search)
        self.search_bar.setVisible(False)
        main_layout.addWidget(self.search_bar)
        
        # ====== 过滤面板 ======
        self._filter_panel = QWidget()
        self._filter_panel.setVisible(False)
        filter_layout = QHBoxLayout(self._filter_panel)
        filter_layout.setContentsMargins(0, 4, 0, 4)
        filter_layout.setSpacing(6)
        self._filter_checkboxes = {}
        node_types = [
            ('character', language_manager.tr('filter_character')),
            ('skill', language_manager.tr('filter_skill')),
            ('location', language_manager.tr('filter_location')),
            ('item', language_manager.tr('filter_item')),
            ('foreshadowing', language_manager.tr('filter_foreshadowing')),
            ('adventure', language_manager.tr('filter_adventure')),
            ('faction', language_manager.tr('filter_faction')),
            ('time_point', language_manager.tr('filter_time_point')),
            ('relationship', language_manager.tr('filter_relationship')),
        ]
        fg = theme_manager.get('fg_color', '#212529')
        accent = theme_manager.get('accent_color', '#0078D4')
        font_family = theme_manager.get('font_family', "'Segoe UI', 'Microsoft YaHei UI', sans-serif")
        for key, label in node_types:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setMinimumWidth(70)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: {fg};
                    font-size: 13px;
                    font-weight: bold;
                    font-family: {font_family};
                    spacing: 6px;
                    padding: 2px 4px;
                }}
                QCheckBox::indicator {{
                    width: 18px; height: 18px;
                    border: 1px solid {theme_manager.get('border_color', '#DEE2E6')};
                    border-radius: 4px;
                    background-color: {theme_manager.get('card_bg', '#FFFFFF')};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {accent};
                    border-color: {accent};
                }}
            """)
            cb.stateChanged.connect(lambda s, k=key: self._on_filter_changed(k, s))
            filter_layout.addWidget(cb)
            self._filter_checkboxes[key] = cb
        filter_layout.addStretch()
        main_layout.addWidget(self._filter_panel)
        
        # ====== 内容区域（QStackedWidget管理多视图） ======
        from PyQt5.QtWidgets import QStackedWidget
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # 页面0: 列表/卡片/词频视图容器
        self._list_card_container = QWidget()
        list_card_layout = QVBoxLayout(self._list_card_container)
        list_card_layout.setContentsMargins(0, 0, 0, 0)

        self.keyword_list_text = QTextBrowser()
        self.keyword_list_text.setOpenLinks(False)
        self.keyword_list_text.anchorClicked.connect(self._on_keyword_clicked)
        self._sync_keyword_browser_font()

        self._freq_tab_bar = QWidget()
        self._freq_tab_bar.setVisible(False)
        freq_tab_layout = QHBoxLayout(self._freq_tab_bar)
        freq_tab_layout.setContentsMargins(0, 0, 0, 8)
        freq_tab_layout.setSpacing(6)

        self._freq_tab_title = QLabel("频度仪表盘")
        self._freq_tab_title.setStyleSheet(
            f"font-size: {self._get_h1_size()}px; font-weight: bold; "
            f"color: {self._t('accent_color', '#0078D4')};"
        )
        freq_tab_layout.addWidget(self._freq_tab_title)
        freq_tab_layout.addSpacing(16)

        from ..ui.widget_factory import create_button
        accent_btn = lambda t, c: create_button(t, kind='primary', min_height=32)
        sec_btn = lambda t, c: create_button(t, kind='secondary', min_height=32)
        self._freq_btn_overview = QPushButton("词频总览")
        self._freq_btn_replace = QPushButton("替换关联")
        self._freq_btn_recycle = QPushButton("回收桶")
        self._freq_btn_scan = QPushButton("▶ 扫描")
        self._freq_btn_clear = QPushButton("清空")
        for b in (self._freq_btn_overview, self._freq_btn_replace, self._freq_btn_recycle):
            b.setMinimumHeight(32)
            b.setCursor(Qt.PointingHandCursor)
        for b in (self._freq_btn_scan, self._freq_btn_clear):
            b.setMinimumHeight(32)
            b.setCursor(Qt.PointingHandCursor)

        freq_tab_layout.addWidget(self._freq_btn_overview)
        freq_tab_layout.addWidget(self._freq_btn_replace)
        freq_tab_layout.addWidget(self._freq_btn_recycle)
        freq_tab_layout.addSpacing(8)
        freq_tab_layout.addWidget(self._freq_btn_scan)
        freq_tab_layout.addWidget(self._freq_btn_clear)
        freq_tab_layout.addStretch()

        self._freq_btn_overview.clicked.connect(lambda: self._switch_freq_page('overview'))
        self._freq_btn_replace.clicked.connect(lambda: self._switch_freq_page('replace'))
        self._freq_btn_recycle.clicked.connect(lambda: self._switch_freq_page('recycle_bin'))
        self._freq_btn_scan.clicked.connect(self._start_frequency_scan)
        self._freq_btn_clear.clicked.connect(self._handle_freq_clear_records)

        list_card_layout.addWidget(self._freq_tab_bar)
        list_card_layout.addWidget(self.keyword_list_text)
        self.stacked_widget.addWidget(self._list_card_container)  # 索引 0

        # 页面1: 网络图谱视图（侧边栏 + 图谱）
        self.network_graph_view = NetworkGraphView()
        follow = ConfigManager.get('Theme', 'graph_bg_follow_theme', fallback='1') == '1'
        if follow:
            bg = theme_manager.get('graph_bg', '#F8F9FA')
        else:
            bg = ConfigManager.get('Theme', 'graph_bg_color', fallback='')
        if bg:
            self.network_graph_view.update_graph_background(bg_color=bg)

        graph_container = QWidget()
        graph_layout = QHBoxLayout(graph_container)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_layout.setSpacing(0)

        self._node_index_sidebar = NodeIndexOverlay(self.network_graph_view, graph_container)
        self.network_graph_view.set_index_overlay(self._node_index_sidebar)
        graph_layout.addWidget(self._node_index_sidebar)
        graph_layout.addWidget(self.network_graph_view, 1)

        self.stacked_widget.addWidget(graph_container)  # 索引 1

        # 页面2: 组织卡视图（包含浏览器+操作按钮）
        self._faction_card_container = QWidget()
        faction_card_layout = QVBoxLayout(self._faction_card_container)
        faction_card_layout.setContentsMargins(0, 0, 0, 0)
        faction_card_layout.setSpacing(6)

        self.faction_card_browser = QTextBrowser()
        self.faction_card_browser.setOpenLinks(False)
        self.faction_card_browser.anchorClicked.connect(self._on_keyword_clicked)
        self._sync_faction_card_font()
        faction_card_layout.addWidget(self.faction_card_browser)

        # 操作按钮栏
        self._faction_action_bar = QHBoxLayout()
        self._faction_action_bar.setSpacing(10)
        
        self._btn_edit_faction = QPushButton("编辑架构")
        self._btn_edit_faction.setFixedSize(120, 36)
        self._btn_edit_faction.clicked.connect(self._on_edit_faction_clicked)
        
        self._btn_export_faction = QPushButton("导出架构图")
        self._btn_export_faction.setFixedSize(120, 36)
        self._btn_export_faction.clicked.connect(self._on_export_faction_clicked)
        
        self._faction_action_bar.addStretch()
        self._faction_action_bar.addWidget(self._btn_edit_faction)
        self._faction_action_bar.addWidget(self._btn_export_faction)
        faction_card_layout.addLayout(self._faction_action_bar)
        
        self.stacked_widget.addWidget(self._faction_card_container)  # 索引 2

        # 页面3: 族谱图视图（完整功能）
        self._family_tree_container = QWidget()
        family_tree_layout = QVBoxLayout(self._family_tree_container)
        family_tree_layout.setContentsMargins(0, 0, 0, 0)
        family_tree_layout.setSpacing(5)

        # 族谱工具栏
        tree_toolbar = QHBoxLayout()
        tree_toolbar.setSpacing(8)

        self._root_label = QLabel("根节点:")
        self._root_label.setStyleSheet(f"color: {self._t('fg_color', '#212529')}; font-size: 13px;")
        tree_toolbar.addWidget(self._root_label)

        self.family_root_combo = create_combo([])
        self.family_root_combo.setMinimumWidth(200)
        self.family_root_combo.currentTextChanged.connect(self._on_family_root_changed)
        tree_toolbar.addWidget(self.family_root_combo)

        self._tree_refresh_btn = create_button(
            "刷新", kind='primary', min_height=30, min_width=70,
            on_click=self._refresh_family_tree
        )
        tree_toolbar.addWidget(self._tree_refresh_btn)

        self._tree_export_btn = create_button(
            "导出PNG", kind='secondary', min_height=30, min_width=80,
            on_click=self._export_family_tree_png
        )
        tree_toolbar.addWidget(self._tree_export_btn)

        tree_toolbar.addStretch()
        family_tree_layout.addLayout(tree_toolbar)

        # 族谱视图容器（延迟初始化）
        self._family_tree_placeholder = QLabel("请选择根节点人物以显示族谱")
        self._family_tree_placeholder.setAlignment(Qt.AlignCenter)
        family_tree_layout.addWidget(self._family_tree_placeholder, 1)

        self.stacked_widget.addWidget(self._family_tree_container)  # 索引 3

        logger.debug(f"[{self.tab_name}] UI构建完成")
    
    def retranslate_ui(self):
        lm = language_manager.tr
        if hasattr(self, '_title_label'):
            self._title_label.setText(lm("keyword_tab_title"))
        if hasattr(self, '_refresh_btn'):
            self._refresh_btn.setText(lm("refresh_btn"))
        if hasattr(self, '_layout_save_btn'):
            self._layout_save_btn.setText(lm("save_layout_btn"))
        if hasattr(self, '_layout_reset_btn'):
            self._layout_reset_btn.setText(lm("reset_layout_btn"))
        if hasattr(self, '_isolated_btn'):
            self._isolated_btn.setText(lm("detect_isolated_btn"))
        if hasattr(self, '_export_png_btn'):
            self._export_png_btn.setText(lm("export_png_btn"))
        if hasattr(self, 'search_bar'):
            self.search_bar.setPlaceholderText(lm("search_placeholder"))
        if hasattr(self, 'keyword_view_combo'):
            self.keyword_view_combo.setItemText(0, lm("view_list"))
            self.keyword_view_combo.setItemText(1, lm("view_card"))
            self.keyword_view_combo.setItemText(2, lm("view_neural"))
            self.keyword_view_combo.setItemText(3, lm("view_frequency"))
        if hasattr(self, '_filter_checkboxes'):
            filter_labels = [
                ('character', 'filter_character'),
                ('skill', 'filter_skill'),
                ('location', 'filter_location'),
                ('item', 'filter_item'),
                ('foreshadowing', 'filter_foreshadowing'),
                ('adventure', 'filter_adventure'),
                ('faction', 'filter_faction'),
                ('time_point', 'filter_time_point'),
                ('relationship', 'filter_relationship'),
            ]
            for key, tr_key in filter_labels:
                if key in self._filter_checkboxes:
                    self._filter_checkboxes[key].setText(lm(tr_key))
        if hasattr(self, '_list_type_filter'):
            self._list_type_filter.setItemText(0, "全部类型")
            self._list_type_filter.setItemText(1, "人物")
            self._list_type_filter.setItemText(2, "技法")
            self._list_type_filter.setItemText(3, "地点")
            self._list_type_filter.setItemText(4, "物品")
            self._list_type_filter.setItemText(5, "伏笔")
            self._list_type_filter.setItemText(6, "事件")
            self._list_type_filter.setItemText(7, "势力")
            self._list_type_filter.setItemText(8, "时间点")
            self._list_type_filter.setItemText(9, "关系")
            self._list_type_filter.setItemText(10, "自定义")
        if hasattr(self, '_freq_tab_title'):
            self._freq_tab_title.setText("频度仪表盘")
        if hasattr(self, '_freq_btn_overview'):
            self._freq_btn_overview.setText("词频总览")
        if hasattr(self, '_freq_btn_replace'):
            self._freq_btn_replace.setText("替换关联")
        if hasattr(self, '_freq_btn_recycle'):
            self._freq_btn_recycle.setText("回收桶")
        if hasattr(self, '_freq_btn_scan'):
            self._freq_btn_scan.setText("▶ 扫描")
        if hasattr(self, '_freq_btn_clear'):
            self._freq_btn_clear.setText("清空")
        if hasattr(self, '_btn_edit_faction'):
            self._btn_edit_faction.setText("编辑架构")
        if hasattr(self, '_btn_export_faction'):
            self._btn_export_faction.setText("导出架构图")
        if hasattr(self, '_root_label'):
            self._root_label.setText("根节点:")
        if hasattr(self, '_family_tree_placeholder'):
            self._family_tree_placeholder.setText("请选择根节点人物以显示族谱")
        if hasattr(self, '_tree_refresh_btn'):
            self._tree_refresh_btn.setText("刷新")
        if hasattr(self, '_tree_export_btn'):
            self._tree_export_btn.setText("导出PNG")
    
    def _load_data(self):
        """加载数据 - 首次打开标签页时自动刷新一次"""
        self.refresh_keywords()
    
    def _s(self, size):
        """缩放尺寸（保留接口）"""
        return size

    def _t(self, key, fallback=''):
        """获取当前主题颜色"""
        return theme_manager.get(key, fallback)

    def _is_dark(self):
        """判断当前是否为暗色主题"""
        bg = self._t('bg_color', '#F8F9FA')
        if bg.startswith('#') and len(bg) >= 7:
            r, g, b = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
            return (r + g + b) < 384
        return False

    def _theme_colors(self):
        """返回当前主题的 HTML 颜色变量字典"""
        t = theme_manager.get
        return {
            'bg': t('bg_color', '#F8F9FA'),
            'fg': t('fg_color', '#212529'),
            'accent': t('accent_color', '#0078D4'),
            'border': t('border_color', '#D0D4D9'),
            'card_bg': t('card_bg', '#FFFFFF'),
            'hover_bg': t('hover_bg', '#E8E8E8'),
            'text_secondary': t('text_secondary', '#6C757D'),
            'input_bg': t('input_bg', '#FFFFFF'),
            'success': t('success_color', '#28A745'),
            'warning': t('warning_color', '#FFC107'),
            'error': t('error_color', '#DC3545'),
            'graph_accent': t('graph_accent', '#0078D4'),
        }
    
    def _set_faction_browser_html(self, html):
        """安全设置组织卡浏览器HTML，确保链接点击始终可用"""
        if not hasattr(self, 'faction_card_browser'):
            return
        self.faction_card_browser.setOpenLinks(False)
        try:
            self.faction_card_browser.anchorClicked.disconnect()
        except Exception:
            pass
        self.faction_card_browser.anchorClicked.connect(self._on_keyword_clicked)
        self.faction_card_browser.setHtml(html)
    
    def _on_edit_faction_clicked(self):
        """编辑架构按钮点击"""
        if self._current_faction_name:
            logger.info(f"编辑架构: {self._current_faction_name}")
            self._edit_faction_structure(self._current_faction_name)
    
    def _on_export_faction_clicked(self):
        """导出架构图按钮点击"""
        if self._current_faction_name:
            logger.info(f"导出架构图: {self._current_faction_name}")
            self._export_faction_structure(self._current_faction_name)
    
    def _set_faction_action_buttons_visible(self, visible):
        """设置组织卡操作按钮的可见性
        
        Args:
            visible: 是否显示按钮栏（仅在详情页显示）
        """
        if not hasattr(self, '_faction_action_bar'):
            return
        for i in range(self._faction_action_bar.count()):
            widget = self._faction_action_bar.itemAt(i).widget()
            if widget:
                widget.setVisible(visible)
        
        if hasattr(self, '_btn_edit_faction') and hasattr(self, '_btn_export_faction'):
            btn_style = f"""
                QPushButton {{
                    background-color: {self._t('accent_color', '#0078D4')};
                    border: none;
                    color: #FFFFFF;
                    font-weight: bold;
                    padding: 6px 18px; border-radius: 6px; font-size: 13px;
                }}
                QPushButton:hover {{ background-color: {self._t('btn_hover_color', '#106EBE')}; }}
            """
            self._btn_edit_faction.setText("编辑架构")
            self._btn_export_faction.setText("导出架构图")
            self._btn_edit_faction.setStyleSheet(btn_style)
            self._btn_export_faction.setStyleSheet(btn_style)
    
    def _sync_keyword_browser_font(self):
        if not hasattr(self, 'keyword_list_text'):
            return
        font = QFont(self.kwlist_font_family, self._s(self.kw_body_size))
        self.keyword_list_text.document().setDefaultFont(font)
        if hasattr(self, 'network_graph_view'):
            self.network_graph_view.set_graph_font_size(self._s(self.graph_font_size))
    
    def _sync_faction_card_font(self):
        if not hasattr(self, 'faction_card_browser'):
            return
        font = QFont(self.kwlist_font_family, self._s(self.kw_body_size))
        self.faction_card_browser.document().setDefaultFont(font)
    
    def refresh_keywords(self):
        """刷新关键词显示"""
        if not self._keyword_tab_initialized:
            self._keyword_tab_initialized = True
            logger.info("首次加载关键词数据...")

        view_mode = self.keyword_view_combo.currentData()

        if view_mode == "list":
            self._switch_to_view(ViewMode.LIST)
            self.render_list_view()
        elif view_mode == "card":
            self._switch_to_view(ViewMode.CHARACTER_CARD)
            self.render_card_view()
        elif view_mode == "neural":
            self._switch_to_view(ViewMode.NETWORK_GRAPH)
            self._render_neural_view_lazy()
        elif view_mode == "frequency":
            self._switch_to_view(ViewMode.FREQUENCY_DASHBOARD)
            self.render_frequency_view()
        elif view_mode == "faction_card":
            if self._current_faction_name:
                self._show_faction_card(self._current_faction_name)
            else:
                self._show_faction_list()
        elif view_mode == "family_tree":
            self._switch_to_view(ViewMode.FAMILY_TREE)
            self._render_family_tree_view()

        self._animate_view_fade()
    
    def _animate_view_fade(self):
        pass
    
    # ====== 列表视图 ======
    
    def render_list_view(self):
        """渲染列表视图"""
        self.search_bar.setVisible(False)
        self._filter_panel.setVisible(False)
        self._layout_save_btn.setVisible(False)
        self._layout_reset_btn.setVisible(False)
        self._isolated_btn.setVisible(False)
        self._export_png_btn.setVisible(False)
        self._freq_tab_bar.setVisible(False)
        self._list_type_filter.setVisible(False)
        self._list_type_filter.setVisible(True)
        
        kw_font = QFont(self.kwlist_font_family, self._s(self.kw_body_size))
        self.keyword_list_text.document().setDefaultFont(kw_font)
        
        keywords = keyword_manager.load_keywords()
        if not keywords:
            guide_msg = (
                "<p style='color:{0};font-size:{1}px;font-family:{2};'>"
                "暂无关键词</p>"
                "<p style='color:{3};font-size:{4}px;font-family:{2};'>"
                "💡 创建关键词可在「神经网络图」可视化创建：<br>"
                "1. 切换视图为「神经网络图」<br>"
                "2. 右键画布 → 创建节点<br>"
                "3. 输入名称、选择类型即可</p>"
            ).format(
                self.kwlist_font_color, self._s(self.kw_body_size),
                self.kwlist_font_family,
                self._t('text_secondary', '#6C757D'),
                self._s(max(10, int(self._get_body_size() * 0.85)))
            )
            self.keyword_list_text.setHtml(guide_msg)
            return
        
        # 获取选中的类型筛选
        selected_type = self._list_type_filter.currentData()
        if selected_type and selected_type != 'all':
            keywords = [kw for kw in keywords if kw.get('type') == selected_type]
        
        if not keywords:
            self.keyword_list_text.setHtml(
                f"<p style='color:{self._t('text_secondary', '#6C757D')};"
                f"font-size:{self._s(self._get_body_size())}px;"
                f"font-family:{self.kwlist_font_family};'>"
                f"没有匹配该类型的关键词</p>"
            )
            return
        
        fs = self._get_body_size()
        fs_small = max(10, int(fs * 0.78))
        fc = self._get_h1_color()
        ff = self.kwlist_font_family
        h1_size = self._get_h1_size()
        body_color = self._get_body_color()
        
        type_colors = {
            'character': theme_manager.get('accent_color', '#0078D4'),
            'skill': theme_manager.get('error_color', '#DC3545'),
            'location': '#00ccff',
            'item': '#ffcc00',
            'foreshadowing': '#ff8c42',
            'adventure': '#ff66cc',
            'faction': '#88ccff',
            'time_point': '#ffd700',
            'relationship': '#cc66ff',
            'custom': theme_manager.get('text_secondary', '#6C757D')
        }
        type_labels = {
            'character': '角色', 'skill': '技法', 'location': '地点',
            'item': '物品', 'foreshadowing': '伏笔', 'adventure': '事件',
            'faction': '势力', 'time_point': '时间点', 'relationship': '关系',
            'custom': '自定义',
        }
        
        border_color = self._t('border_color', '#DEE2E6')
        html = f"<p style='color:{fc};font-size:{h1_size}px;font-family:{ff};font-weight:bold;'>关键词列表</p><ul style='list-style:none;padding-left:0;'>"
        for kw in keywords:
            name = kw.get('name', '?')
            kw_type = kw.get('type', 'custom')
            desc = kw.get('description', '')
            tc = type_colors.get(kw_type, theme_manager.get('text_secondary', '#6C757D'))
            tl = type_labels.get(kw_type, kw_type)
            item_link = self._get_link_style(tc)
            html += f"<li style='padding:3px 0;border-bottom:1px solid {border_color};display:flex;align-items:center;flex-wrap:wrap;'>"
            html += f"<span style='background:{tc};color:#ffffff;padding:1px 8px;border-radius:9px;font-size:{fs_small}px;font-weight:bold;margin-right:6px;display:inline-block;white-space:nowrap;'>{tl}</span>"
            html += f"<a href='card:{name}' style='{item_link}'>{name}</a>"
            if desc:
                html += f"<span style='color:{body_color};font-size:{fs}px;font-family:{ff};margin-left:6px;'> - {desc}</span>"
            html += "</li>"
        html += "</ul>"
        
        self.keyword_list_text.setHtml(html)
    
    # ====== 卡片视图 ======
    
    def render_card_view(self):
        """渲染卡片视图"""
        self.search_bar.setVisible(False)
        self._filter_panel.setVisible(False)
        self._layout_save_btn.setVisible(False)
        self._layout_reset_btn.setVisible(False)
        self._isolated_btn.setVisible(False)
        self._export_png_btn.setVisible(False)
        self._freq_tab_bar.setVisible(False)
        self._list_type_filter.setVisible(False)
        self._card_selected_name = None
        card_font = QFont(self.kwlist_font_family, self._s(self.kw_body_size))
        self.keyword_list_text.document().setDefaultFont(card_font)
        self._render_character_list()
    
    def _render_character_list(self):
        """渲染人物列表"""
        keywords = keyword_manager.load_keywords()
        if not keywords:
            self.keyword_list_text.setHtml("<p>暂无关键词</p>")
            return
        
        characters = [kw for kw in keywords if kw.get('type') == 'character']
        if not characters:
            self.keyword_list_text.setHtml("<p>暂无人物关键词</p>")
            return
        
        fs = self._get_body_size()
        h1_size = self._get_h1_size()
        h1_color = self._get_h1_color()
        fs_small = max(10, int(fs * 0.82))
        link_style = self._get_link_style()
        body_color = self._get_body_color()
        ff = self.kwlist_font_family
        
        text_secondary = self._t('text_secondary', '#6C757D')
        border_color = self._t('border_color', '#DEE2E6')
        html = f"<p style='color:{h1_color};font-size:{h1_size}px;font-family:{ff};font-weight:bold;'>人物列表</p>"
        html += f"<p style='color:{text_secondary};font-size:{fs_small}px;font-family:{ff};'>点击人名查看详细人物卡</p>"
        html += "<ul style='list-style:none;padding-left:0;'>"
        
        for char in characters:
            name = char.get('name', '?')
            desc = char.get('description', '')
            short_desc = desc[:80] + '...' if len(desc) > 80 else desc
            html += f"<li style='padding:4px 0;border-bottom:1px solid {border_color};'>"
            html += f"<a href='card:{name}' style='{link_style}'>{name}</a>"
            if short_desc:
                html += f"<br><span style='color:{body_color};font-size:{fs_small}px;font-family:{ff};padding-left:12px;'>{short_desc}</span>"
            html += "</li>"
        html += "</ul>"
        
        self.keyword_list_text.setHtml(html)
    
    def _render_character_card(self, char_name):
        """渲染人物卡片"""
        keywords = keyword_manager.load_keywords()
        if not keywords:
            self.keyword_list_text.setHtml("<p>暂无关键词</p>")
            return
        
        char_kw = None
        for kw in keywords:
            if kw.get('type') == 'character' and kw.get('name') == char_name:
                char_kw = kw
                break
        
        if not char_kw:
            self._render_character_list()
            return
        
        name = char_kw.get('name', '?')
        desc = char_kw.get('description', '')
        related_names = [rel.get('target') for rel in char_kw.get('relationships', [])]

        belongings = []
        for rel in char_kw.get('relationships', []):
            if rel.get('type') == 'belongs_to':
                belongings.append({
                    'target': rel.get('target', ''),
                    'role': rel.get('role', ''),
                    'description': rel.get('description', '')
                })

        related_skills = []
        related_items = []
        related_locations = []
        related_relations = []
        related_foreshadowing = []
        related_characters = []
        
        for r_name in related_names:
            for kw in keywords:
                if kw.get('name') == r_name:
                    t = kw.get('type', 'custom')
                    entry = (r_name, kw.get('description', ''))
                    if t == 'skill':
                        related_skills.append(entry)
                    elif t == 'item':
                        related_items.append(entry)
                    elif t == 'location':
                        related_locations.append(entry)
                    elif t == 'relationship':
                        related_relations.append(entry)
                    elif t == 'foreshadowing':
                        related_foreshadowing.append(entry)
                    else:
                        related_characters.append(entry)
                    break
        
        referenced_by = []
        for kw in keywords:
            if kw.get('name') == char_name:
                continue
            if kw.get('type') == 'character' and any(rel.get('target') == name for rel in kw.get('relationships', [])):
                referenced_by.append(kw.get('name', '?'))
        
        link_style = self._get_link_style()
        accent_color = self._t('accent_color', '#0078D4')
        border_color = self._t('border_color', '#DEE2E6')
        text_secondary = self._t('text_secondary', '#6C757D')
        link_style_green = self._get_link_style(accent_color)
        h1_size = self._get_h1_size()
        h2_size = self._get_h2_size()
        h2_color = self._get_h2_color()
        body_size = self._get_body_size()
        body_color = self._get_body_color()
        
        fs_desc = max(10, int(body_size * 0.75))
        
        faction_affiliation_html = ""
        if belongings:
            card_bg = self._t('card_bg', '#FFFFFF')
            warning_color = self._t('warning_color', '#FFC107')
            success_color = self._t('success_color', '#28A745')
            faction_html_parts = [f'<div style="margin:15px 0; padding:12px; background-color:{card_bg}; border-left:4px solid {warning_color}; border-radius:4px;">']
            faction_html_parts.append(f'<h4 style="color:{warning_color}; margin:0 0 8px 0; font-size:16px;">所属势力</h4>')

            for belong in belongings:
                target = belong.get('target', '')
                role = belong.get('role', '')
                desc = belong.get('description', '')

                faction_html_parts.append(f'''
        <div style="margin:5px 0; padding:6px 10px; background-color:{self._t("input_bg", "#FFFFFF")}; border-radius:4px;">
          <a href='faction:{target}' style="color:{success_color}; text-decoration:none; font-weight:bold; font-size:15px;">{target}</a>
          {f'<span style="color:{text_secondary}; margin-left:8px;">({role})</span>' if role else ''}
          {f'<br><span style="color:{text_secondary}; font-size:12px; margin-left:8px;">{desc}</span>' if desc else ''}
        </div>
                ''')

            faction_html_parts.append('</div>')
            faction_affiliation_html = '\n'.join(faction_html_parts)

        html = f"""
        <div style='margin-bottom: 0.2em;'>
            <a href="back:list" style='{link_style_green}'> < 返回人物列表</a>
        </div>
        <div style='border: 2px solid {accent_color}; padding: 0.5em; border-radius: 12px; background: rgba(0,120,212,0.03);'>
            <p style='color: {accent_color}; margin: 0 0 0.2em 0; font-size: {h1_size}px; font-weight: bold; font-family: {self.kwlist_font_family};'>{name}</p>
            <hr style='border-color: {border_color}; margin: 0.2em 0;'>
            <p style='color: {body_color}; line-height: {self.line_height}; font-size: {body_size}px;'>{desc}</p>
            <p><a href='edit_desc:{name}' style='color:{text_secondary};font-size:{fs_desc}px;text-decoration:none;'>✏️ 编辑描述</a></p>
        </div>
        {faction_affiliation_html}
        """
        fs = body_size
        fs_small = max(10, int(fs * 0.85))

        sections = [
            ('技 能', related_skills, '#ffe66d'),
            ('物 品', related_items, '#dda0dd'),
            ('地 点', related_locations, '#00ccff'),
            ('关 系', related_relations, '#cc66ff'),
            ('伏 笔', related_foreshadowing, '#ff8c42'),
            ('关联人物', related_characters, self._t('accent_color', '#0078D4')),
        ]
        
        for section_title, items, color in sections:
            if items:
                section_link = self._get_link_style(color)
                html += f"""
                <div style='border: 1px solid {color}40; padding: 0.7em 1em; margin-top: 0.7em; border-radius: 8px; background: rgba(0,0,0,0.05);'>
                    <p style='color: {color}; margin: 0 0 0.5em 0; font-size: {h2_size}px; font-weight: bold; font-family: {self.kwlist_font_family};'>- {section_title}</p>
                """
                for item_name, item_desc in items:
                    html += f"""
                    <div style='padding: 0.25em 0; border-bottom: 1px solid {self._t("border_color", "#DEE2E6")}30;'>
                        <a href="card:{item_name}" style='{section_link}'>{item_name}</a>
                        <span style='color: {text_secondary}; font-size: {fs_desc}px; margin-left: 0.5em;'>{item_desc}</span>
                    </div>"""
                html += "</div>"
        
        if referenced_by:
            accent_color = self._t('accent_color', '#0078D4')
            ref_link = self._get_link_style(accent_color)
            html += f"""
            <div style='border: 1px solid {accent_color}40; padding: 0.7em 1em; margin-top: 0.7em; border-radius: 8px; background: rgba(0,0,0,0.05);'>
                <p style='color: {accent_color}; margin: 0 0 0.5em 0; font-size: {h2_size}px; font-weight: bold; font-family: {self.kwlist_font_family};'>- 被以下人物提及</p>
            """
            for ref_name in referenced_by:
                html += f"""
                <div style='padding: 0.15em 0;'>
                    <a href="card:{ref_name}" style='{ref_link}'>> {ref_name}</a>
                </div>"""
            html += "</div>"
        
        freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
        if os.path.exists(freq_file):
            try:
                with open(freq_file, 'r', encoding='utf-8') as f:
                    freq_data = json.load(f)
                is_replace = freq_data.get('is_replace', {})
                aliases = [alias for alias, target in is_replace.items() if target == char_name]
                if aliases:
                    border_color = self._t('border_color', '#DEE2E6')
                    text_secondary = self._t('text_secondary', '#6C757D')
                    html += f"""
                    <div style='border: 1px solid {border_color}40; padding: 0.7em 1em; margin-top: 0.7em; border-radius: 8px; background: rgba(0,0,0,0.05);'>
                        <p style='color: {text_secondary}; margin: 0 0 0.5em 0; font-size: {h2_size}px; font-weight: bold; font-family: {self.kwlist_font_family};'>- 曾用称谓</p>
                    """
                    for alias in aliases:
                        html += f"""
                        <div style='padding: 0.15em 0;'>
                            <span style='color: {text_secondary}; font-size: {body_size}px;'>{alias}</span>
                        </div>"""
                    html += "</div>"
            except Exception:
                pass
        
        self.keyword_list_text.setHtml(html)
    
    def _render_location_card(self, location_name):
        """渲染地点卡片"""
        keywords = keyword_manager.load_keywords()
        loc_kw = None
        for kw in keywords:
            if kw.get('type') == 'location' and kw.get('name') == location_name:
                loc_kw = kw
                break
        if not loc_kw:
            self._render_character_list()
            return
        
        name = loc_kw.get('name', '?')
        desc = loc_kw.get('description', '')
        region = loc_kw.get('region', '')
        related = [rel.get('target') for rel in loc_kw.get('relationships', []) if isinstance(rel, dict)]
        
        related_chars = []
        related_events = []
        related_others = []
        for kw in keywords:
            r_name = kw.get('name', '')
            if r_name in related:
                t = kw.get('type', '')
                if t == 'character':
                    related_chars.append(r_name)
                elif t == 'adventure':
                    related_events.append(r_name)
                elif t == 'location':
                    related_others.append(r_name)
        
        accent_color = self._t('accent_color', '#0078D4')
        border_color = self._t('border_color', '#DEE2E6')
        text_secondary = self._t('text_secondary', '#6C757D')
        link_green = self._get_link_style(accent_color)
        h1_size = self._get_h1_size()
        h2_size = self._get_h2_size()
        body_size = self._get_body_size()
        body_color = self._get_body_color()
        
        html = f"""
        <div style='margin-bottom: 0.5em;'>
            <a href="back:list" style='{link_green}'>< 返回人物列表</a>
        </div>
        <div style='border: 2px solid #00ccff; padding: 1.2em; border-radius: 12px; background: rgba(0,204,255,0.03);'>
            <p style='color: #00ccff; margin: 0 0 0.3em 0; font-size: {h1_size}px; font-weight: bold; font-family: {self.kwlist_font_family};'>{name}</p>
            <hr style='border-color: {border_color}; margin: 0.6em 0;'>
            <p style='color: {body_color}; line-height: {self.line_height}; font-size: {body_size}px;'>{desc}</p>
        </div>
        """
        if region:
            html += f"<p style='color: {text_secondary}; font-size: {body_size}px;'><b>所属区域:</b> {region}</p>"
        if related_chars:
            char_link = self._get_link_style(accent_color)
            html += f"<div style='border:1px solid {accent_color}40; padding:0.7em 1em; margin-top:0.7em; border-radius:8px;'><p style='color:{accent_color}; font-size: {h2_size}px; font-weight: bold; font-family: {self.kwlist_font_family};'>- 关联人物</p>"
            for c in related_chars:
                html += f"<div style='padding:0.15em 0;'><a href='card:{c}' style='{char_link}'>> {c}</a></div>"
            html += "</div>"
        if related_events:
            html += f"<div style='border:1px solid #ff8c4240; padding:0.7em 1em; margin-top:0.7em; border-radius:8px;'><p style='color:#ff8c42; font-size: {h2_size}px; font-weight: bold; font-family: {self.kwlist_font_family};'>- 关联事件</p>"
            for e in related_events:
                html += f"<div style='padding:0.15em 0;'><span style='color:#ff8c42; font-size: {body_size}px;'>> {e}</span></div>"
            html += "</div>"
        
        self.keyword_list_text.setHtml(html)
    
    def _render_timeline_point_card(self, point_name):
        """渲染时间点卡片"""
        keywords = keyword_manager.load_keywords()
        tp_kw = None
        for kw in keywords:
            if kw.get('type') == 'time_point' and kw.get('name') == point_name:
                tp_kw = kw
                break
        if not tp_kw:
            self._render_character_list()
            return
        
        name = tp_kw.get('name', '?')
        kw_type = tp_kw.get('type', 'time_point')
        desc = tp_kw.get('description', '')
        status = tp_kw.get('status', '')
        related = [rel.get('target') for rel in tp_kw.get('relationships', []) if isinstance(rel, dict)]
        
        related_chars = []
        related_events = []
        related_foreshadowing = []
        for kw in keywords:
            r_name = kw.get('name', '')
            if r_name in related:
                t = kw.get('type', '')
                if t == 'character':
                    related_chars.append(r_name)
                elif t == 'adventure':
                    related_events.append(r_name)
                elif t == 'foreshadowing':
                    related_foreshadowing.append(r_name)
        
        accent_color = self._t('accent_color', '#0078D4')
        border_color = self._t('border_color', '#DEE2E6')
        text_secondary = self._t('text_secondary', '#6C757D')
        link_green = self._get_link_style(accent_color)
        h1_size = self._get_h1_size()
        h2_size = self._get_h2_size()
        body_size = self._get_body_size()
        body_color = self._get_body_color()
        
        html = f"""
        <div style='margin-bottom: 0.5em;'>
            <a href="back:list" style='{link_green}'>< 返回人物列表</a>
        </div>
        <div style='border: 2px solid #ffd700; padding: 1.2em; border-radius: 12px; background: rgba(255,215,0,0.03);'>
            <p style='color: #ffd700; margin: 0 0 0.3em 0; font-size: {h1_size}px; font-weight: bold; font-family: {self.kwlist_font_family};'>{name}</p>
            <hr style='border-color: #5a4a1a; margin: 0.6em 0;'>
            <p style='color: #ccaa88; line-height: {self.line_height}; font-size: {body_size}px;'>{desc}</p>
        </div>
        """
        if status:
            html += f"<p style='color: {text_secondary}; font-size: {body_size}px;'><b>进度状态:</b> {status}</p>"
        if related_chars:
            char_link = self._get_link_style(accent_color)
            html += f"<div style='border:1px solid {accent_color}40; padding:0.7em 1em; margin-top:0.7em; border-radius:8px;'><p style='color:{accent_color}; font-size: {h2_size}px; font-weight: bold; font-family: {self.kwlist_font_family};'>- 关联人物</p>"
            for c in related_chars:
                html += f"<div style='padding:0.15em 0;'><a href='card:{c}' style='{char_link}'>> {c}</a></div>"
            html += "</div>"
        if related_events:
            html += f"<div style='border:1px solid #ff8c4240; padding:0.7em 1em; margin-top:0.7em; border-radius:8px;'><p style='color:#ff8c42; font-size: {h2_size}px; font-weight: bold; font-family: {self.kwlist_font_family};'>- 关联事件</p>"
            for e in related_events:
                html += f"<div style='padding:0.15em 0;'><span style='color:#ff8c42; font-size: {body_size}px;'>> {e}</span></div>"
            html += "</div>"
        if related_foreshadowing:
            html += f"<div style='border:1px solid #ff6b6b40; padding:0.7em 1em; margin-top:0.7em; border-radius:8px;'><p style='color:#ff6b6b; font-size: {h2_size}px; font-weight: bold; font-family: {self.kwlist_font_family};'>- 关联伏笔</p>"
            for f in related_foreshadowing:
                html += f"<div style='padding:0.15em 0;'><span style='color:#ff6b6b; font-size: {body_size}px;'>> {f}</span></div>"
            html += "</div>"
        
        self.keyword_list_text.setHtml(html)
    
    def _render_item_card(self, item_name):
        """渲染物品/武器卡片"""
        keywords = keyword_manager.load_keywords()
        it_kw = None
        for kw in keywords:
            if kw.get('type') in ('item', 'weapon') and kw.get('name') == item_name:
                it_kw = kw
                break
        if not it_kw:
            self._render_character_list()
            return
        
        name = it_kw.get('name', '?')
        kw_type = it_kw.get('type', 'item')
        desc = it_kw.get('description', '')
        owner = it_kw.get('owner', '')
        grade = it_kw.get('grade', '')
        related = [rel.get('target') for rel in it_kw.get('relationships', []) if isinstance(rel, dict)]
        related_chars = []
        related_items = []
        for kw in keywords:
            r_name = kw.get('name', '')
            if r_name in related:
                t = kw.get('type', '')
                if t == 'character':
                    related_chars.append(r_name)
                elif t in ('item', 'weapon'):
                    related_items.append(r_name)
        
        accent_color = self._t('accent_color', '#0078D4')
        border_color_theme = self._t('border_color', '#DEE2E6')
        text_secondary = self._t('text_secondary', '#6C757D')
        link_green = self._get_link_style(accent_color)
        h1_size = self._get_h1_size()
        h2_size = self._get_h2_size()
        body_size = self._get_body_size()
        body_color = self._get_body_color()
        type_label = "武 器" if kw_type == 'weapon' else "物 品"
        border_color = "#ff4466" if kw_type == 'weapon' else "#ffcc00"
        
        html = f"""
        <div style='margin-bottom:0.5em;'><a href="back:list" style='{link_green}'>< 返回列表</a></div>
        <div style='border:2px solid {border_color}; padding:1.2em; border-radius:12px; background: rgba({border_color[1:3]},{border_color[3:5]},{border_color[5:7]},0.03);'>
            <p style='color:{border_color}; margin:0 0 0.3em 0; font-size:{h1_size}px; font-weight: bold; font-family: {self.kwlist_font_family};'>[{type_label}] {name}</p>
            <hr style='border-color:{border_color_theme}; margin:0.6em 0;'>
            <p style='color:{body_color}; line-height:{self.line_height}; font-size:{body_size}px;'>{desc}</p>
        </div>"""
        if owner:
            html += f"<p style='color:{text_secondary}; font-size: {body_size}px;'><b>持有者:</b> {owner}</p>"
        if grade:
            html += f"<p style='color:#ffcc00; font-size: {body_size}px;'><b>等级/品阶:</b> {grade}</p>"
        if related_chars:
            char_link = self._get_link_style(accent_color)
            html += f"<div style='border:1px solid {accent_color}40;padding:0.7em 1em;margin-top:0.7em;border-radius:8px;'><p style='color:{accent_color}; font-size: {h2_size}px; font-weight: bold; font-family: {self.kwlist_font_family};'>- 关联人物</p>"
            for c in related_chars:
                html += f"<div style='padding:0.15em 0;'><a href='card:{c}' style='{char_link}'>> {c}</a></div>"
            html += "</div>"
        if related_items:
            item_link = self._get_link_style('#ffcc00')
            html += f"<div style='border:1px solid #ffcc0040;padding:0.7em 1em;margin-top:0.7em;border-radius:8px;'><p style='color:#ffcc00; font-size: {h2_size}px; font-weight: bold; font-family: {self.kwlist_font_family};'>- 关联物品</p>"
            for i in related_items:
                html += f"<div style='padding:0.15em 0;'><a href='card:{i}' style='{item_link}'>> {i}</a></div>"
            html += "</div>"
        self.keyword_list_text.setHtml(html)
    
    def _render_skill_card(self, skill_name):
        """渲染技能/功法卡片"""
        keywords = keyword_manager.load_keywords()
        sk_kw = None
        for kw in keywords:
            if kw.get('type') in ('skill', 'technique') and kw.get('name') == skill_name:
                sk_kw = kw
                break
        if not sk_kw:
            self._render_character_list()
            return
        
        name = sk_kw.get('name', '?')
        kw_type = sk_kw.get('type', 'skill')
        desc = sk_kw.get('description', '')
        grade = sk_kw.get('grade', '')
        element = sk_kw.get('element', '')
        related = [rel.get('target') for rel in sk_kw.get('relationships', []) if isinstance(rel, dict)]
        related_chars = []
        for kw in keywords:
            r_name = kw.get('name', '')
            if r_name in related and kw.get('type') == 'character':
                related_chars.append(r_name)
        
        accent_color = self._t('accent_color', '#0078D4')
        border_color_theme = self._t('border_color', '#DEE2E6')
        link_green = self._get_link_style(accent_color)
        h1_size = self._get_h1_size()
        h2_size = self._get_h2_size()
        body_size = self._get_body_size()
        body_color = self._get_body_color()
        type_label = "功 法" if kw_type == 'technique' else "技 能"
        border_color = "#ff66cc" if kw_type == 'technique' else "#ffd700"
        
        html = f"""
        <div style='margin-bottom:0.5em;'><a href="back:list" style='{link_green}'>< 返回列表</a></div>
        <div style='border:2px solid {border_color}; padding:1.2em; border-radius:12px; background:rgba(255,102,204,0.03);'>
            <p style='color:{border_color}; margin:0 0 0.3em 0; font-size:{h1_size}px; font-weight: bold; font-family: {self.kwlist_font_family};'>[{type_label}] {name}</p>
            <hr style='border-color:{border_color_theme}; margin:0.6em 0;'>
            <p style='color:{body_color}; line-height:{self.line_height}; font-size:{body_size}px;'>{desc}</p>
        </div>"""
        if grade:
            html += f"<p style='color:#ffcc00; font-size: {body_size}px;'><b>等级/品阶:</b> {grade}</p>"
        if element:
            html += f"<p style='color:#66ccff; font-size: {body_size}px;'><b>属性:</b> {element}</p>"
        if related_chars:
            char_link = self._get_link_style(accent_color)
            html += f"<div style='border:1px solid {accent_color}40;padding:0.7em 1em;margin-top:0.7em;border-radius:8px;'><p style='color:{accent_color}; font-size: {h2_size}px; font-weight: bold; font-family: {self.kwlist_font_family};'>- 修炼/使用者</p>"
            for c in related_chars:
                html += f"<div style='padding:0.15em 0;'><a href='card:{c}' style='{char_link}'>> {c}</a></div>"
            html += "</div>"
        self.keyword_list_text.setHtml(html)
    
    # ====== 辅助方法 ======
    
    def _get_link_style(self, color=None):
        c = color if color else self.kw_link_color
        s = f"font-size: {self._s(self.kw_link_size)}px; "
        s += f"color: {c}; "
        if self.link_bold:
            s += "font-weight: bold; "
        if self.link_italic:
            s += "font-style: italic; "
        s += "text-decoration: none;"
        return s
    
    def _get_h1_size(self):
        return self._s(self.kw_h1_size)
    
    def _get_h2_size(self):
        return self._s(self.kw_h2_size)
    
    def _get_body_size(self):
        return self._s(self.kw_body_size)
    
    def _get_body_color(self):
        return self.kw_body_color
    
    def _get_h1_color(self):
        return self.kw_h1_color
    
    def _get_h2_color(self):
        return self.kw_h2_color
    
    # ====== 词频分析视图 ======

    def _update_freq_tab_styles(self, active_page):
        from ..core.theme_manager import theme_manager
        accent = theme_manager.get('accent_color', '#0078D4')
        bg = theme_manager.get('card_bg', '#FFFFFF')
        bdr = theme_manager.get('border_color', '#DEE2E6')
        btn_r = theme_manager.get('button_radius', '6px')
        tabs = [
            (self._freq_btn_overview, 'overview'),
            (self._freq_btn_replace, 'replace'),
            (self._freq_btn_recycle, 'recycle_bin'),
        ]
        for btn, page in tabs:
            if page == active_page:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {accent};
                        color: #FFFFFF;
                        border: none;
                        border-radius: {btn_r};
                        padding: 6px 18px;
                        font-size: 14px;
                        font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {bg};
                        color: #333333;
                        border: 1px solid {bdr};
                        border-radius: {btn_r};
                        padding: 6px 18px;
                        font-size: 14px;
                    }}
                    QPushButton:hover {{ background-color: #F0F0F0; }}
                """)

    def _switch_freq_page(self, page):
        self._freq_page = page
        self.render_frequency_view()

    def render_frequency_view(self):
        """渲染词频分析视图"""
        self.search_bar.setVisible(False)
        self._filter_panel.setVisible(False)
        self._layout_save_btn.setVisible(False)
        self._layout_reset_btn.setVisible(False)
        self._isolated_btn.setVisible(True)
        self._export_png_btn.setVisible(False)
        self._freq_tab_bar.setVisible(True)
        self._list_type_filter.setVisible(False)
        
        novel_dir = get_novel_dir()
        if not os.path.exists(novel_dir):
            self.keyword_list_text.setHtml("<p style='color:#FFAA00;'>请先设置小说目录</p>")
            return
        
        page = getattr(self, '_freq_page', 'overview')
        self._freq_page = page
        body_size = self._get_body_size()
        self._update_freq_tab_styles(page)
        
        freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
        rejected_count = 0
        if os.path.exists(freq_file):
            try:
                with open(freq_file, 'r', encoding='utf-8') as f:
                    _fdata = json.load(f)
                rejected_count = len(_fdata.get('rejected_words', []))
            except Exception:
                pass
        self._freq_btn_recycle.setText(f"回收桶 ({rejected_count})" if rejected_count else "回收桶")
        
        html = ""
        if os.path.exists(freq_file):
            try:
                with open(freq_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if page == 'overview':
                    html += self._render_freq_overview(data)
                elif page == 'recycle_bin':
                    html += self._render_freq_recycle_bin(data)
                else:
                    html += self._render_freq_replace(data)
            except Exception:
                html += "<p style='color:#FF3333;'>频度文件损坏，请重新扫描</p>"
        else:
            html += "<p style='color:#666;'>暂无频度数据，请先扫描</p>"
        
        self._freq_data = data if os.path.exists(freq_file) else None
        self.keyword_list_text.setHtml(html)
    
    def _freq_heat_color(self, heat_factor):
        """计算热度颜色"""
        r = int(10 + heat_factor * (0 - 10))
        g = int(60 + heat_factor * (255 - 60))
        b = int(40 + heat_factor * (65 - 40))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _render_freq_overview(self, data):
        """渲染词频总览"""
        html = ""
        words = data.get('words', {})
        total_chapters = data.get('total_chapters', 0)
        is_replace = data.get('is_replace', {})
        body_size = self._get_body_size()
        body_color = self._get_body_color()
        fs_small = max(10, int(body_size * 0.8))
        
        max_count = 0
        matched = 0
        for w, info in words.items():
            cnt = info.get('total_occurrences', 0)
            if cnt > max_count:
                max_count = cnt
            if info.get('type', '?') != '?':
                matched += 1
        
        if max_count == 0:
            max_count = 1
        log_max = log1p(max_count)
        
        accent_color = self._t('accent_color', '#0078D4')
        text_secondary = self._t('text_secondary', '#6C757D')
        top5 = sorted(words.items(), key=lambda x: x[1].get('total_occurrences', 0), reverse=True)[:5]
        top5_str = ' | '.join(
            f"<span style='color:{accent_color};'>{w}</span><span style='color:{text_secondary};'>({info.get('total_occurrences',0)})</span>"
            for w, info in top5
        )
        
        card_bg = self._t('card_bg', '#FFFFFF')
        card_border = self._t('card_border', '#E5E5E5')
        warn_color = self._t('warn_color', '#FF8C00')
        html += f"""
        <div style='display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap;'>
            <div style='flex:1; min-width:100px; background:{card_bg}; border:1px solid {card_border}; border-radius:8px; padding:12px 16px;'>
                <p style='color:{text_secondary}; font-size:{fs_small}px; margin:0;'>章节数</p>
                <p style='color:{accent_color}; font-size:{body_size}px; font-weight:bold; margin:4px 0 0;'>{total_chapters}</p>
            </div>
            <div style='flex:1; min-width:100px; background:{card_bg}; border:1px solid {card_border}; border-radius:8px; padding:12px 16px;'>
                <p style='color:{text_secondary}; font-size:{fs_small}px; margin:0;'>词条数</p>
                <p style='color:{accent_color}; font-size:{body_size}px; font-weight:bold; margin:4px 0 0;'>{len(words)}</p>
            </div>
            <div style='flex:1; min-width:100px; background:{card_bg}; border:1px solid {card_border}; border-radius:8px; padding:12px 16px;'>
                <p style='color:{text_secondary}; font-size:{fs_small}px; margin:0;'>已匹配</p>
                <p style='color:{accent_color}; font-size:{body_size}px; font-weight:bold; margin:4px 0 0;'>{matched}</p>
            </div>
            <div style='flex:1; min-width:100px; background:{card_bg}; border:1px solid {card_border}; border-radius:8px; padding:12px 16px;'>
                <p style='color:{text_secondary}; font-size:{fs_small}px; margin:0;'>未匹配</p>
                <p style='color:{warn_color}; font-size:{body_size}px; font-weight:bold; margin:4px 0 0;'>{len(words)-matched}</p>
            </div>
        </div>
        <p style='color:{text_secondary}; font-size:{fs_small}px; margin:0 0 4px 0;'>上次扫描: {data.get('scan_time','?')}</p>
        <p style='color:{accent_color}; font-size:{fs_small}px; margin:0 0 16px 0;'>TOP5: {top5_str}</p>
        """
        
        sorted_words = sorted(words.items(), key=lambda x: x[1].get('total_occurrences', 0), reverse=True)
        rejected_words = set(data.get('rejected_words', []))
        visible_words = [w for w, _ in sorted_words if w not in rejected_words]
        html += "<table style='width:100%;border-collapse:collapse;margin-bottom:24px;'>"
        border_color = self._t('border_color', '#DEE2E6')
        accent_color = self._t('accent_color', '#0078D4')
        all_checked = all(w in self._selected_freq_words for w in visible_words) if visible_words else False
        master_check = '☑' if all_checked else '☐'
        html += f"<tr style='color:{accent_color}; font-size:{body_size}px;'><th style='text-align:center;padding:8px 6px;border-bottom:2px solid {border_color};width:32px;'><a href='freq:overview:toggle_all' style='color:{accent_color};text-decoration:none;font-size:16px;'>{master_check}</a></th><th style='text-align:left;padding:8px 6px;border-bottom:2px solid {border_color};'>词条</th><th style='text-align:center;padding:8px 6px;border-bottom:2px solid {border_color};'>类型</th><th style='text-align:center;padding:8px 6px;border-bottom:2px solid {border_color};'>章数</th><th style='text-align:right;padding:8px 6px;border-bottom:2px solid {border_color};'>次数</th><th style='text-align:right;padding:8px 6px;border-bottom:2px solid {border_color};width:130px;'>热度</th><th style='text-align:center;padding:8px 6px;border-bottom:2px solid {border_color};width:70px;'>操作</th></tr>"

        for word, info in sorted_words:
            if word in rejected_words:
                continue
            wtype = info.get('type', '?')
            ch_count = len(info.get('chapters', {}))
            total = info.get('total_occurrences', 0)
            hf = log1p(total) / log_max
            hc = self._freq_heat_color(hf)

            is_replaced = word in is_replace
            text_secondary = self._t('text_secondary', '#6C757D')
            accent_color = self._t('accent_color', '#0078D4')
            error_color = self._t('error_color', '#DC3545')
            checked = '☑' if word in self._selected_freq_words else '☐'
            if is_replaced:
                target = is_replace[word]
                name_display = f"<span style='color:#555;'>{word}</span> <span style='color:{text_secondary};font-size:{fs_small}px;'>→ {target}</span>"
            else:
                name_display = f"<span style='color:{hc};font-weight:bold;'>{word}</span>"

            bar_pct = int(hf * 100)
            html += f"""<tr style='border-bottom:1px solid {self._t("border_color", "#DEE2E6")}40;'>
                <td style='padding:6px;text-align:center;'><a href='freq:overview:toggle:{word}' style='color:{accent_color};text-decoration:none;font-size:16px;'>{checked}</a></td>
                <td style='padding:6px;font-size:{body_size}px;'>{name_display}</td>
                <td style='padding:6px;text-align:center;color:{body_color};font-size:{fs_small}px;'>{wtype}</td>
                <td style='padding:6px;text-align:center;color:{body_color};font-size:{fs_small}px;'>{ch_count}</td>
                <td style='padding:6px;text-align:right;color:{body_color};font-size:{fs_small}px;'>{total}</td>
                <td style='padding:6px;width:130px;'>
                    <div style='background:rgba(0,120,212,0.08);border-radius:6px;height:14px;overflow:hidden;position:relative;'>
                        <div style='background:linear-gradient(90deg, {hc}80, {hc});height:100%;width:{bar_pct}%;border-radius:6px;transition:width 0.3s;'></div>
                        <span style='position:absolute;right:4px;top:0;font-size:10px;color:{accent_color};line-height:14px;'>{bar_pct}%</span>
                    </div>
                </td>
                <td style='padding:6px;text-align:center;'><a href='freq:reject:{word}' style='color:{error_color};font-size:{fs_small}px;text-decoration:none;border:1px solid {error_color}40;padding:2px 8px;border-radius:4px;'>剔除</a></td>
            </tr>"""
        html += "</table>"

        sel_count = len(self._selected_freq_words)
        if sel_count:
            html += f"<div style='margin-bottom:16px;padding:10px 16px;background:{accent_color}10;border:1px solid {accent_color}40;border-radius:8px;display:flex;align-items:center;gap:12px;'>"
            html += f"<span style='color:{body_color};font-size:{body_size}px;'>已选 {sel_count} 个词</span>"
            html += f"<a href='freq:overview:batch_reject' style='padding:6px 18px;background:{error_color};color:#FFFFFF;border:none;border-radius:6px;text-decoration:none;font-size:{body_size}px;font-weight:bold;'>批量剔除 ({sel_count})</a>"
            html += "</div>"
        return html
    
    def _render_freq_replace(self, data):
        """渲染替换关联页面"""
        html = ""
        words = data.get('words', {})
        total_chapters = data.get('total_chapters', 0)
        is_replace = data.get('is_replace', {})
        split_idx = max(1, total_chapters // 3)
        body_size = self._get_body_size()
        body_color = self._get_body_color()
        fs_small = max(10, int(body_size * 0.8))
        
        keywords_list = keyword_manager.load_keywords()
        kw_names = [kw.get('name', '') for kw in keywords_list if kw.get('type', '?') != '?']
        
        accent_color = self._t('accent_color', '#0078D4')
        text_secondary = self._t('text_secondary', '#6C757D')
        border_color = self._t('border_color', '#DEE2E6')
        stale_candidates = [(w, info) for w, info in words.items() if info.get('is_stale', False) or w in is_replace]
        if not stale_candidates:
            html += f"<p style='color:{text_secondary}; font-size:{body_size}px;'>暂无检测到临时称谓候选。写够章节后扫描即可自动检测。</p>"
            return html
        
        html += f"<p style='color:{body_color}; font-size:{body_size}px; margin-bottom:12px;'>以下词语在前期出现较多、后期骤降，可能是已暴露身份的角色的临时称谓。选择对应的正式关键词进行关联：</p>"
        html += "<table style='width:100%;border-collapse:collapse;'>"
        html += f"<tr style='color:{accent_color}; font-size:{body_size}px;'><th style='text-align:left;padding:8px 6px;border-bottom:2px solid {border_color};'>临时称谓</th><th style='text-align:center;padding:8px 6px;border-bottom:2px solid {border_color};'>前期(1~{split_idx})</th><th style='text-align:center;padding:8px 6px;border-bottom:2px solid {border_color};'>后期({split_idx+1}~{total_chapters})</th><th style='text-align:center;padding:8px 6px;border-bottom:2px solid {border_color};'>最后出现</th><th style='text-align:center;padding:8px 6px;border-bottom:2px solid {border_color};'>替换为</th><th style='text-align:center;padding:8px 6px;border-bottom:2px solid {border_color};'>操作</th></tr>"
        
        for word, info in stale_candidates:
            dist = info.get('chapter_distribution', [])
            front_count = sum(dist[:split_idx]) if dist else 0
            back_count = sum(dist[split_idx:]) if dist else 0
            
            last_ch = "?"
            chapters_dict = info.get('chapters', {})
            if chapters_dict:
                ch_nums = sorted(int(k) for k in chapters_dict.keys())
                if ch_nums:
                    last_ch = f"第{ch_nums[-1]}章"
            
            error_color = self._t('error_color', '#DC3545')
            if word in is_replace:
                target = is_replace[word]
                html += f"""<tr style='border-bottom:1px solid {self._t("border_color", "#DEE2E6")}40;'>
                    <td style='padding:6px; color:#555; font-size:{body_size}px;'>{word}</td>
                    <td style='padding:6px; text-align:center; color:{body_color}; font-size:{fs_small}px;'>{front_count}</td>
                    <td style='padding:6px; text-align:center; color:{body_color}; font-size:{fs_small}px;'>{back_count}</td>
                    <td style='padding:6px; text-align:center; color:{body_color}; font-size:{fs_small}px;'>{last_ch}</td>
                    <td style='padding:6px; text-align:center; color:{accent_color}; font-size:{fs_small}px;'>已关联: {target}</td>
                    <td style='padding:6px; text-align:center;'><a href='freq:unreplace:{word}' style='color:{error_color}; font-size:{fs_small}px; text-decoration:none; border:1px solid {error_color}40; padding:2px 8px; border-radius:4px;'>⊘ 取消</a></td>
                </tr>"""
            else:
                warning_color = self._t('warning_color', '#FFC107')
                html += f"""<tr style='border-bottom:1px solid {self._t("border_color", "#DEE2E6")}40;'>
                    <td style='padding:6px; color:{warning_color}; font-size:{body_size}px; font-weight:bold;'>{word}</td>
                    <td style='padding:6px; text-align:center; color:{body_color}; font-size:{fs_small}px;'>{front_count}</td>
                    <td style='padding:6px; text-align:center; color:{body_color}; font-size:{fs_small}px;'>{back_count}</td>
                    <td style='padding:6px; text-align:center; color:{body_color}; font-size:{fs_small}px;'>{last_ch}</td>
                    <td style='padding:6px;'></td>
                    <td style='padding:6px; text-align:center;'><a href='freq:replace:{word}' style='color:{accent_color}; font-size:{fs_small}px; text-decoration:none; border:1px solid {accent_color}40; padding:2px 8px; border-radius:4px;'>选择目标</a></td>
                </tr>"""
        html += "</table>"
        return html
    
    def _handle_freq_replace(self, stale_word):
        """处理词频替换操作"""
        freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
        if not os.path.exists(freq_file):
            return
        
        with open(freq_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        keywords_list = keyword_manager.load_keywords()
        kw_names = [kw.get('name', '') for kw in keywords_list if kw.get('type', '?') != '?']
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"替换关联: {stale_word}")
        layout = QFormLayout(dialog)
        combo = QComboBox()
        combo.addItems(kw_names)
        layout.addRow(f"将「{stale_word}」替换为:", combo)
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addRow(btn_box)
        
        if dialog.exec_() == QDialog.Accepted:
            target = combo.currentText()
            if target:
                data.setdefault('is_replace', {})[stale_word] = target
                with open(freq_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self.render_frequency_view()
    
    def _handle_freq_unreplace(self, stale_word):
        """取消词频替换"""
        freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
        if not os.path.exists(freq_file):
            return
        
        with open(freq_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'is_replace' in data and stale_word in data['is_replace']:
            del data['is_replace'][stale_word]
            with open(freq_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        self.render_frequency_view()

    def _handle_freq_reject(self, word):
        """剔除关键词（移至回收桶）"""
        if not self._rejected_confirm_disabled:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle("剔除确认")
            msg.setText(f"确定要将「{word}」移入回收桶？")
            cb = QCheckBox("下次不再询问")
            msg.setCheckBox(cb)
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.Yes)
            if msg.exec_() != QMessageBox.Yes:
                return
            if cb.isChecked():
                self._rejected_confirm_disabled = True
                ConfigManager.set('Frequency', 'reject_confirm_disabled', '1')

        freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
        if not os.path.exists(freq_file):
            return

        try:
            with open(freq_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}

        rejected = data.setdefault('rejected_words', [])
        if word not in rejected:
            rejected.append(word)
        with open(freq_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.render_frequency_view()

    def _handle_freq_overview_toggle_all(self):
        """全选/取消全选总览页所有词"""
        freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
        if not os.path.exists(freq_file):
            return
        with open(freq_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        words = data.get('words', {})
        rejected_words = set(data.get('rejected_words', []))
        visible_words = [w for w in words if w not in rejected_words]

        all_checked = all(w in self._selected_freq_words for w in visible_words) if visible_words else False
        if all_checked:
            self._selected_freq_words.clear()
        else:
            for w in visible_words:
                self._selected_freq_words.add(w)
        self.render_frequency_view()

    def _handle_freq_overview_batch_reject(self):
        """批量剔除选中的词"""
        if not self._selected_freq_words:
            return
        freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
        if not os.path.exists(freq_file):
            return
        with open(freq_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        rejected = data.setdefault('rejected_words', [])
        for word in list(self._selected_freq_words):
            if word not in rejected:
                rejected.append(word)
        with open(freq_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._selected_freq_words.clear()
        self.render_frequency_view()

    def _handle_freq_recycle_toggle_all(self):
        """全选/取消全选回收桶"""
        freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
        if not os.path.exists(freq_file):
            return
        with open(freq_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        rejected = data.get('rejected_words', [])
        all_checked = all(w in self._selected_rejected_words for w in rejected) if rejected else False
        if all_checked:
            self._selected_rejected_words.clear()
        else:
            for w in rejected:
                self._selected_rejected_words.add(w)
        self.render_frequency_view()

    def _render_freq_recycle_bin(self, data):
        """渲染回收桶"""
        body_size = self._get_body_size()
        body_color = self._get_body_color()
        fs_small = max(10, int(body_size * 0.8))
        accent_color = self._t('accent_color', '#0078D4')
        border_color = self._t('border_color', '#DEE2E6')
        text_secondary = self._t('text_secondary', '#6C757D')
        card_border = self._t('card_border', '#E5E5E5')

        rejected = data.get('rejected_words', [])
        if not rejected:
            return f"<p style='color:{text_secondary};font-size:{body_size}px;padding:40px 0;text-align:center;'>回收桶为空</p>"

        html = f"<p style='color:{text_secondary};font-size:{fs_small}px;margin:0 0 12px 0;'>已剔除 {len(rejected)} 个词，勾选后可恢复或加入停用词</p>"
        html += "<table style='width:100%;border-collapse:collapse;margin-bottom:24px;'>"
        all_checked_recycle = all(w in self._selected_rejected_words for w in rejected) if rejected else False
        master_check_r = '☑' if all_checked_recycle else '☐'
        html += f"<tr style='color:{accent_color};font-size:{body_size}px;'><th style='text-align:center;padding:8px 6px;border-bottom:2px solid {border_color};width:40px;'><a href='freq:recycle:toggle_all' style='color:{accent_color};text-decoration:none;font-size:16px;'>{master_check_r}</a></th><th style='text-align:left;padding:8px 6px;border-bottom:2px solid {border_color};'>词条</th><th style='text-align:center;padding:8px 6px;border-bottom:2px solid {border_color};width:180px;'>操作</th></tr>"

        for word in rejected:
            checked = '☑' if word in self._selected_rejected_words else '☐'
            html += f"<tr style='border-bottom:1px solid {border_color}40;'>"
            html += f"<td style='padding:6px;text-align:center;'><a href='freq:recycle:toggle:{word}' style='color:{accent_color};text-decoration:none;font-size:16px;'>{checked}</a></td>"
            html += f"<td style='padding:6px;font-size:{body_size}px;color:{body_color};'>{word}</td>"
            html += f"<td style='padding:6px;text-align:center;white-space:nowrap;'>"
            html += f"<a href='freq:recycle:restore:{word}' style='padding:2px 10px;background:transparent;color:{accent_color};border:1px solid {accent_color}40;border-radius:4px;text-decoration:none;font-size:{fs_small}px;margin-right:4px;'>恢复</a>"
            html += f"<a href='freq:recycle:add_stopwords:{word}' style='padding:2px 10px;background:transparent;color:{text_secondary};border:1px solid {card_border};border-radius:4px;text-decoration:none;font-size:{fs_small}px;'>加入停用词</a>"
            html += "</td></tr>"

        html += "</table>"
        sel_count = len(self._selected_rejected_words)
        html += f"<p style='margin-top:12px;line-height:2.4;'>"
        html += f"<a href='freq:recycle:clear' style='padding:6px 16px;background:transparent;color:{text_secondary};border:1px solid {card_border};border-radius:6px;text-decoration:none;font-size:{fs_small}px;margin-right:6px;'>清除全部</a>"
        if sel_count:
            html += f"<a href='freq:recycle:restore_selected' style='padding:6px 16px;background:transparent;color:{accent_color};border:1px solid {accent_color}40;border-radius:6px;text-decoration:none;font-size:{fs_small}px;margin-right:6px;'>恢复选中 ({sel_count})</a>"
            html += f"<a href='freq:recycle:add_stopwords_selected' style='padding:6px 16px;background:transparent;color:{accent_color};border:1px solid {accent_color}40;border-radius:6px;text-decoration:none;font-size:{fs_small}px;'>加入停用词 ({sel_count})</a>"
        html += "</p>"
        return html

    def _handle_freq_recycle_toggle(self, word):
        if word in self._selected_rejected_words:
            self._selected_rejected_words.discard(word)
        else:
            self._selected_rejected_words.add(word)
        self.render_frequency_view()

    def _handle_freq_recycle_restore(self, words):
        freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
        if not os.path.exists(freq_file):
            return
        with open(freq_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        rejected = data.get('rejected_words', [])
        data['rejected_words'] = [w for w in rejected if w not in words]
        with open(freq_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._selected_rejected_words.difference_update(words)
        self.render_frequency_view()

    def _handle_freq_recycle_clear(self):
        freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
        if not os.path.exists(freq_file):
            return
        with open(freq_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['rejected_words'] = []
        with open(freq_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._selected_rejected_words.clear()
        self.render_frequency_view()

    def _handle_freq_recycle_add_stopwords(self, words):
        sw_file = os.path.join(get_novel_config_dir(), "user_stopwords.json")
        existing = []
        if os.path.exists(sw_file):
            try:
                with open(sw_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        changed = False
        for w in words:
            if w not in existing:
                existing.append(w)
                changed = True
        if changed:
            with open(sw_file, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        # 从回收桶移除已加入停用词的词
        freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
        if os.path.exists(freq_file):
            with open(freq_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            rejected = data.get('rejected_words', [])
            data['rejected_words'] = [w for w in rejected if w not in words]
            with open(freq_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        self._selected_rejected_words.difference_update(words)
        self.render_frequency_view()

    def _handle_freq_clear_records(self):
        reply = QMessageBox.question(
            self, "清空确认",
            "确定要清空所有词频扫描记录吗？\n回收桶中的剔除词将保留。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
        if not os.path.exists(freq_file):
            return
        with open(freq_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        rejected = data.get('rejected_words', [])
        keep = {}
        if rejected:
            keep['rejected_words'] = rejected
        with open(freq_file, 'w', encoding='utf-8') as f:
            json.dump(keep, f, ensure_ascii=False, indent=2)
        self.render_frequency_view()

    # ====== 神经网络图视图 ======
    
    def render_neural_view(self):
        """渲染神经网络图视图"""
        self.search_bar.setVisible(False)
        self._filter_panel.setVisible(True)
        self._layout_save_btn.setVisible(True)
        self._layout_reset_btn.setVisible(True)
        self._isolated_btn.setVisible(True)
        self._export_png_btn.setVisible(True)
        self._freq_tab_bar.setVisible(False)
        self._list_type_filter.setVisible(False)
        
        keywords = keyword_manager.load_keywords()
        self.network_graph_view.set_double_click_callback(self._on_graph_node_double_clicked)
        self.network_graph_view.set_right_click_callback(self._on_graph_node_right_click)
        self.network_graph_view.set_edge_right_click_callback(self._on_graph_edge_right_click)
        
        freq_data = None
        freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
        if os.path.exists(freq_file):
            try:
                with open(freq_file, 'r', encoding='utf-8') as f:
                    freq_data = json.load(f)
            except Exception:
                pass
        
        self.network_graph_view.build_graph(keywords, freq_data)
        self.network_graph_view.load_layout(self._get_graph_layout_path())
        logger.info("神经网络图已构建")
    
    def _render_neural_view_lazy(self):
        """延迟渲染神经网络图（带缓存）"""
        self.search_bar.setVisible(False)
        self._filter_panel.setVisible(True)
        self._layout_save_btn.setVisible(True)
        self._layout_reset_btn.setVisible(True)
        self._isolated_btn.setVisible(True)
        self._export_png_btn.setVisible(True)
        
        self.network_graph_view.set_double_click_callback(self._on_graph_node_double_clicked)
        self.network_graph_view.set_right_click_callback(self._on_graph_node_right_click)
        self.network_graph_view.set_edge_right_click_callback(self._on_graph_edge_right_click)
        
        keywords = keyword_manager.load_keywords()
        current_hash = hashlib.md5(str(keywords).encode()).hexdigest()[:16]
        
        if (self._neural_graph_built and 
            self._neural_graph_hash == current_hash and 
            len(self.network_graph_view.node_items) > 0):
            logger.info("使用缓存的网络图，跳过重新构建")
            return
        
        logger.info("数据已变化或首次构建，开始异步构建网络图...")
        self._neural_graph_hash = current_hash
        self._show_graph_loading_hint()
        QTimer.singleShot(50, self._build_graph_async)
    
    def _get_graph_layout_path(self):
        """获取布局文件路径"""
        return os.path.join(get_base_dir(), "graph_layout.json")
    
    def _show_graph_loading_hint(self):
        """显示加载提示"""
        if not hasattr(self, '_loading_label'):
            self._loading_label = QLabel("正在构建网络图...")
            self._loading_label.setAlignment(Qt.AlignCenter)
            self._loading_label.setParent(self.network_graph_view.viewport())
        
        self._loading_label.setGeometry(self.network_graph_view.viewport().rect())
        self._loading_label.raise_()
        self._loading_label.setVisible(True)
        QApplication.processEvents()
    
    def _build_graph_async(self):
        """异步构建网络图"""
        try:
            keywords = keyword_manager.load_keywords()
            freq_data = None
            freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
            if os.path.exists(freq_file):
                try:
                    with open(freq_file, 'r', encoding='utf-8') as f:
                        freq_data = json.load(f)
                except Exception:
                    pass

            progress = QProgressDialog("正在构建网络图...", "取消", 0, 0, self)
            progress.setWindowTitle("神经网络图")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(500)
            progress.show()
            QApplication.processEvents()
            
            self.network_graph_view.build_graph(keywords, freq_data)
            self.network_graph_view.load_layout(self._get_graph_layout_path())
            
            progress.close()
            
            if hasattr(self, '_loading_label'):
                self._loading_label.setVisible(False)
            
            self._neural_graph_built = True
            logger.info("网络图构建完成并已缓存")
        except Exception as e:
            logger.error(f"构建网络图失败: {e}", exc_info=True)
            if hasattr(self, '_loading_label'):
                self._loading_label.setText(f"构建失败: {str(e)}")
    
    def _save_graph_layout(self):
        """保存布局"""
        path = self._get_graph_layout_path()
        if self.network_graph_view.save_layout(path):
            logger.info("[OK] 布局已保存")
    
    def _reset_graph_layout(self):
        """重置布局"""
        path = self._get_graph_layout_path()
        if os.path.exists(path):
            os.remove(path)
        keywords = keyword_manager.load_keywords()
        self.network_graph_view.build_graph(keywords)
        logger.info("[OK] 布局已重置，重新计算力导向位置")
    
    def _detect_isolated_nodes(self):
        """检测孤立节点"""
        isolated = self.network_graph_view.get_isolated_nodes()
        if not isolated:
            logger.info("[OK] 没有孤立节点，所有节点都有连线")
            return
        
        all_kw = keyword_manager.load_keywords()
        kw_map = {k.get('name', ''): k for k in all_kw} if all_kw else {}
        logger.warning(f"[WARN] 发现 {len(isolated)} 个孤立节点:")
        for name in isolated:
            kw = kw_map.get(name, {})
            desc = kw.get('description', '') if kw else ''
            logger.warning(f"  - {name}: {desc}")
    
    def _export_graph_png(self):
        """导出PNG图片"""
        default_name = os.path.join(get_novel_dir(), "graph_export.png")
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出神经网络图为PNG", default_name, "PNG (*.png)"
        )
        if filepath:
            if self.network_graph_view.export_to_png(filepath):
                logger.info(f"[OK] 已导出: {filepath}")
            else:
                logger.error("[ERR] 导出失败")
    
    def _on_filter_changed(self, node_type, state):
        """过滤条件改变"""
        visible = state == Qt.Checked
        self.network_graph_view.toggle_node_filter(node_type, visible)
        self.network_graph_view.apply_filter()
    
    def _on_graph_search(self):
        """搜索节点或路径"""
        text = self.search_bar.text().strip()
        if not text:
            self.network_graph_view.clear_path_highlight()
            return
        
        if "->" in text:
            parts = [p.strip() for p in text.split("->")]
            if len(parts) == 2:
                a, b = parts
                path = self.network_graph_view.find_shortest_path(a, b)
                if path:
                    self.network_graph_view.highlight_path(path)
                    logger.info(f"[OK] 路径: {' → '.join(path)}")
                else:
                    logger.warning(f"[WARN] 未找到 {a} 到 {b} 的路径")
            return
        
        self.network_graph_view.focus_on_node(text)
    
    # ====== 节点和边的事件处理 ======
    
    def _on_graph_node_right_click(self, node_name, screen_pos, scene_pos):
        """节点右键菜单"""
        menu = QMenu()
        
        modify_menu = menu.addMenu("修改")
        rename_action = modify_menu.addAction("命名")
        modify_menu.addSeparator()
        
        type_submenu = modify_menu.addMenu("类别")
        type_map = {
            'character': '人物',
            'skill': '技能',
            'location': '地点',
            'item': '物品',
            'foreshadowing': '伏笔',
            'event': '事件',
            'organization': '组织',
            'time_point': '时间点',
            'relationship': '关系',
            'custom': '自定义'
        }
        
        keywords = keyword_manager.load_keywords()
        current_type = 'custom'
        for kw in keywords:
            if kw.get('name') == node_name:
                current_type = kw.get('type', 'custom')
                break
        
        type_actions = {}
        for type_id, type_name in type_map.items():
            action = type_submenu.addAction(type_name)
            action.setData(type_id)
            if type_id == current_type:
                action.setChecked(True)
                action.setCheckable(True)
                font = action.font()
                font.setBold(True)
                action.setFont(font)
            type_actions[type_id] = action
        
        menu.addSeparator()
        delete_action = menu.addAction("删除")
        
        action = menu.exec_(screen_pos)
        
        if action == rename_action:
            self._rename_graph_node(node_name)
        elif action in type_actions.values():
            new_type = action.data()
            self._change_node_type(node_name, new_type)
        elif action == delete_action:
            self._delete_graph_node(node_name)
    
    def _rename_graph_node(self, node_name):
        """重命名节点"""
        keywords = keyword_manager.load_keywords()
        target_kw = None
        for kw in keywords:
            if kw.get('name') == node_name:
                target_kw = kw
                break
        if not target_kw:
            return
        
        new_name, ok = QInputDialog.getText(
            self, "重命名节点",
            f"请输入新的名称:",
            text=node_name
        )
        if ok and new_name and new_name != node_name:
            if any(kw.get('name') == new_name for kw in keywords):
                QMessageBox.warning(self, "错误", f"节点 '{new_name}' 已存在！")
                return
            
            keyword_manager.rename_keyword(node_name, new_name)
            self._invalidate_neural_cache()
            
            if node_name in self.network_graph_view.node_items:
                old_item_data = self.network_graph_view.node_items.pop(node_name)
                old_item = old_item_data['item']
                
                target_kw['name'] = new_name
                old_item.node_name = new_name
                
                fm = QFontMetrics(old_item._name_font)
                old_item._text_w = fm.horizontalAdvance(new_name)
                max_w = 160
                if old_item._text_w > max_w:
                    smaller_size = SciFiNodeItem.GRAPH_FONT_SIZE
                    while smaller_size > max(8, SciFiNodeItem.GRAPH_FONT_SIZE - 6):
                        smaller_size -= 1
                        test_font = QFont('Microsoft YaHei', smaller_size, QFont.Bold)
                        test_fm = QFontMetrics(test_font)
                        if test_fm.horizontalAdvance(new_name) <= max_w:
                            old_item._name_font = test_font
                            old_item._text_w = test_fm.horizontalAdvance(new_name)
                            break
                
                self.network_graph_view.node_items[new_name] = {'item': old_item, 'keyword': target_kw}
                old_item.update()
            
            self.refresh_keywords()
            logger.info(f"[OK] 节点已重命名: {node_name} → {new_name}")
    
    def _change_node_type(self, node_name, new_type):
        """更改节点类型"""
        keywords = keyword_manager.load_keywords()
        target_kw = None
        for kw in keywords:
            if kw.get('name') == node_name:
                target_kw = kw
                break
        if not target_kw:
            return
        
        type_colors = {
            'character': theme_manager.get('accent_color', '#0078D4'), 'skill': '#ff4466', 'location': '#00ccff',
            'item': '#ffcc00', 'foreshadowing': '#ff8c42', 'relationship': '#cc66ff',
            'custom': theme_manager.get('text_secondary', '#6C757D'), 'adventure': '#ff8c42', 'faction': '#9933ff',
            'time_point': '#ffd700'
        }
        
        old_type = target_kw.get('type', 'custom')
        target_kw['type'] = new_type
        color = type_colors.get(new_type, theme_manager.get('text_secondary', '#6C757D'))
        target_kw['color'] = color
        
        keyword_manager.update_keyword(node_name, new_type, target_kw.get('description', ''), color)
        self._invalidate_neural_cache()
        
        if node_name in self.network_graph_view.node_items:
            item = self.network_graph_view.node_items[node_name]['item']
            item.node_type = new_type
            item.base_color = QColor(color)
            item.update()
        
        logger.info(f"[OK] 节点类型已更改: {node_name} ({old_type} → {new_type})")
    
    def _delete_graph_node(self, node_name):
        """删除节点"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除节点 \"{node_name}\" 及其所有连线吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            keyword_manager.delete_keyword(node_name)
            self.network_graph_view.remove_node(node_name)
            self._invalidate_neural_cache()
            logger.info(f"[OK] 节点已删除: {node_name}")
            self.refresh_keywords()
    
    def _invalidate_neural_cache(self):
        """使神经图缓存失效"""
        self._neural_graph_built = False
        self._neural_graph_hash = None
        logger.info("神经图缓存已失效，下次切换将重新构建")
    
    def _on_graph_edge_right_click(self, edge, screen_pos):
        """边右键菜单"""
        menu = QMenu()
        delete_edge = menu.addAction("删除连线")
        action = menu.exec_(screen_pos)
        
        if action == delete_edge:
            from_name = edge.from_node.node_name
            to_name = edge.to_node.node_name
            rel_type = edge.rel_type
            keyword_manager.remove_relationship(from_name, to_name, rel_type)
            self.network_graph_view.remove_edge(edge)
            self._invalidate_neural_cache()
            logger.info(f"[OK] 连线已删除: {from_name} -- {to_name}")
    
    def _on_graph_node_double_clicked(self, node_name):
        """节点双击事件"""
        keywords = keyword_manager.load_keywords()
        node_type = None
        for kw in keywords:
            if kw.get('name') == node_name:
                node_type = kw.get('type')
                break

        # 切换到卡片视图
        for i in range(self.keyword_view_combo.count()):
            if self.keyword_view_combo.itemData(i) == "card":
                self.keyword_view_combo.setCurrentIndex(i)
                break
        self.refresh_keywords()

        # 根据类型渲染对应卡片或视图
        if node_type == 'faction':
            QTimer.singleShot(300, lambda: self._show_faction_card(node_name))
        elif node_type == 'location':
            QTimer.singleShot(300, lambda: self._render_location_card(node_name))
        elif node_type == 'time_point':
            QTimer.singleShot(300, lambda: self._render_timeline_point_card(node_name))
        elif node_type in ('item', 'weapon'):
            QTimer.singleShot(300, lambda: self._render_item_card(node_name))
        elif node_type in ('skill', 'technique'):
            QTimer.singleShot(300, lambda: self._render_skill_card(node_name))
        elif node_type == 'character':
            QTimer.singleShot(300, lambda: self._render_character_card(node_name))
        else:
            QTimer.singleShot(300, lambda: self._render_character_card(node_name))
    
    def _on_keyword_clicked(self, url):
        """关键词链接点击事件

        根据关键词类型切换到对应视图：
        - character → 人物卡（保持原有逻辑）
        - faction   → 组织卡（新增）
        - 其他类型  → 保持原有行为
        """
        url_str = url.toString()

        if url_str.startswith("card:"):
            target_name = url_str[5:]
            keywords = keyword_manager.load_keywords()
            target_type = None
            for kw in keywords:
                if kw.get('name') == target_name:
                    target_type = kw.get('type')
                    break

            if target_type == 'faction':
                self._show_faction_card(target_name)
            elif target_type == 'location':
                self._render_location_card(target_name)
            elif target_type == 'time_point':
                self._render_timeline_point_card(target_name)
            elif target_type in ('item', 'weapon'):
                self._render_item_card(target_name)
            elif target_type in ('skill', 'technique'):
                self._render_skill_card(target_name)
            else:
                self._render_character_card(target_name)
        
        elif url_str.startswith("edit_desc:"):
            target_name = url_str[10:]
            keywords = keyword_manager.load_keywords()
            for kw in keywords:
                if kw.get('name') == target_name:
                    current_desc = kw.get('description', '')
                    new_desc, ok = QInputDialog.getMultiLineText(
                        self, f"编辑描述 - {target_name}", "请输入新的描述：", current_desc
                    )
                    if ok:
                         kw['description'] = new_desc
                         keyword_manager.save_keywords(keywords)
                         self.refresh_keywords()
                         QMessageBox.information(self, language_manager.tr("success"), f"{language_manager.tr('description_updated')}: 「{target_name}」")
                    break
        
        elif url_str.startswith("back:list"):
            self._card_selected_name = None
            self._render_character_list()
        
        elif url_str.startswith("freq:"):
            parts = url_str[5:].split(':')
            if parts[0] == 'page':
                self._freq_page = parts[1]
                self.render_frequency_view()
            elif parts[0] == 'scan':
                self._start_frequency_scan()
            elif parts[0] == 'replace':
                self._handle_freq_replace(parts[1])
            elif parts[0] == 'unreplace':
                self._handle_freq_unreplace(parts[1])
            elif parts[0] == 'reject':
                self._handle_freq_reject(parts[1])
            elif parts[0] == 'overview':
                sub = parts[1]
                if sub == 'toggle':
                    self._selected_freq_words.symmetric_difference_update({parts[2]})
                    self.render_frequency_view()
                elif sub == 'toggle_all':
                    self._handle_freq_overview_toggle_all()
                elif sub == 'batch_reject':
                    self._handle_freq_overview_batch_reject()
            elif parts[0] == 'recycle':
                sub = parts[1]
                if sub == 'toggle':
                    self._handle_freq_recycle_toggle(parts[2])
                elif sub == 'toggle_all':
                    self._handle_freq_recycle_toggle_all()
                elif sub == 'restore':
                    self._handle_freq_recycle_restore([parts[2]])
                elif sub == 'clear':
                    self._handle_freq_recycle_clear()
                elif sub == 'restore_selected':
                    self._handle_freq_recycle_restore(list(self._selected_rejected_words))
                elif sub == 'add_stopwords':
                    self._handle_freq_recycle_add_stopwords([parts[2]])
                elif sub == 'add_stopwords_selected':
                    self._handle_freq_recycle_add_stopwords(list(self._selected_rejected_words))
            elif parts[0] == 'clear_records':
                self._handle_freq_clear_records()

        elif url_str.startswith("faction:"):
            target_name = url_str[8:]
            self._show_faction_card(target_name)

        elif url_str.startswith("back:factions"):
            self._current_faction_name = None
            self._show_faction_list()
        
        elif url_str.startswith("edit_faction:"):
            target_name = url_str[13:]
            logger.info(f"编辑架构: {target_name}")
            self._edit_faction_structure(target_name)
        
        elif url_str.startswith("export_faction:"):
            target_name = url_str[14:]
            logger.info(f"导出架构图: {target_name}")
            self._export_faction_structure(target_name)
    
    def _start_frequency_scan(self):
        """启动词频扫描（后台线程执行）"""
        from ..models.keyword_manager import KeywordManager

        novel_dir = get_novel_dir()
        if not os.path.exists(novel_dir):
            QMessageBox.warning(self, "提示", "请先设置小说目录")
            return

        if hasattr(self, '_freq_scan_thread') and self._freq_scan_thread is not None and self._freq_scan_thread.isRunning():
            QMessageBox.information(self, "提示", "词频扫描正在进行中，请稍候")
            return

        from PyQt5.QtCore import QThread, QObject, pyqtSignal

        class ScanWorker(QObject):
            finished = pyqtSignal(object)
            error_signal = pyqtSignal(str)

            def __init__(self, novel_dir):
                super().__init__()
                self._novel_dir = novel_dir
                self._cancelled = False

            def cancel(self):
                self._cancelled = True

            def run(self):
                try:
                    result = KeywordManager.scan_frequency(self._novel_dir)
                    if not self._cancelled:
                        self.finished.emit(result)
                except Exception as e:
                    self.error_signal.emit(str(e))

        worker = ScanWorker(novel_dir)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.error_signal.connect(thread.quit)

        progress = QProgressDialog("正在扫描词频...", "取消", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(500)
        progress.setCancelButtonText("取消")
        progress.show()

        progress.canceled.connect(worker.cancel)
        progress.canceled.connect(thread.quit)

        def cleanup():
            self._freq_scan_thread = None
            self._freq_scan_worker = None

        def on_result(data):
            progress.close()
            if data and data.get('words'):
                freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
                try:
                    with open(freq_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    logger.info(f"词频数据已保存: {freq_file}")
                except Exception as e:
                    logger.error(f"保存词频数据失败: {e}")
            self.render_frequency_view()
            cleanup()

        def on_error(err):
            progress.close()
            QMessageBox.critical(self, language_manager.tr("error"), f"{language_manager.tr('freq_scan_failed')}:\n{err}")
            cleanup()

        worker.finished.connect(on_result)
        worker.error_signal.connect(on_error)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._freq_scan_worker = worker
        self._freq_scan_thread = thread
        thread.start()
        logger.info("词频扫描已启动（后台线程）")
    
    # ====== 配置更新方法 ======
    
    def update_config(self):
        """更新配置（当外部配置改变时调用）"""
        self._load_config()
        self._sync_keyword_browser_font()
        self._sync_faction_card_font()
        if hasattr(self, 'keyword_view_combo'):
            self.refresh_keywords()
    
    def update_legend_config(self, visible, font_name, font_size):
        """更新图例配置"""
        if hasattr(self, 'network_graph_view'):
            self.network_graph_view.update_legend_config(visible, font_name, font_size)
    
    def update_connect_btn_config(self, size, color):
        """更新连接按钮配置"""
        if hasattr(self, 'network_graph_view'):
            self.network_graph_view.update_connect_btn_config(size, color)
    
    def update_node_visual_config(self, min_size, max_size, min_brightness, max_brightness):
        """更新节点视觉配置"""
        if hasattr(self, 'network_graph_view'):
            self.network_graph_view.update_node_visual_config(min_size, max_size, min_brightness, max_brightness)
    
    def update_glow_config(self, enabled):
        """更新辉光效果开关"""
        if hasattr(self, 'network_graph_view'):
            self.network_graph_view.update_glow_enabled(enabled)
    
    def update_size_sort_config(self, enabled):
        """更新面积排序显示开关"""
        if hasattr(self, 'network_graph_view'):
            self.network_graph_view.update_size_sort_enabled(enabled)
    
    def set_overlay_position(self, pos):
        """设置覆盖层位置"""
        if hasattr(self, 'network_graph_view'):
            self.network_graph_view.set_overlay_position(pos)

    # ====== 视图切换辅助方法（组织卡&族谱图） ======

    def _edit_faction_structure(self, faction_name):
        """打开组织架构编辑器"""
        try:
            from novelhelper.ui.faction_editor import FactionEditorDialog
            dialog = FactionEditorDialog(faction_name, self)
            
            def on_saved(fname, structure):
                logger.info(f"架构已保存: {fname}")
                # 保存后自动刷新当前视图
                if self._current_view_mode == ViewMode.FACTION_CARD:
                    if self._current_faction_name == fname:
                        self._show_faction_card(fname)
                    else:
                        self._show_faction_list()
            
            dialog.saved.connect(on_saved)
            dialog.exec_()
        except Exception as e:
            logger.error(f"打开架构编辑器失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _export_faction_structure(self, faction_name):
        """显示组织架构详情视图"""
        try:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout
            from novelhelper.ui.faction_detail_view import FactionDetailView
            
            # 创建字体配置
            font_config = {
                'family': self.kwlist_font_family,
                'nav': self._get_body_size(),
                'title': self._get_h1_size(),
                'section': self._get_h2_size(),
                'btn': self._get_body_size()
            }
            
            # 创建对话框容器
            dialog = QDialog(self)
            dialog.setWindowTitle(f"组织架构 - {faction_name}")
            dialog.setMinimumSize(900, 600)
            
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(0, 0, 0, 0)
            
            # 创建详情视图
            detail_view = FactionDetailView(faction_name, font_config)
            
            # 连接信号
            detail_view.go_back.connect(dialog.accept)
            detail_view.edit_faction.connect(lambda name: dialog.accept())
            detail_view.edit_faction.connect(self._edit_faction_structure)
            
            layout.addWidget(detail_view)
            
            # 显示对话框
            dialog.exec_()
        except Exception as e:
            logger.error(f"显示架构视图失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "提示", f"显示架构视图失败: {str(e)}")
    
    def _switch_to_view(self, mode):
        """切换到指定视图模式

        Args:
            mode: ViewMode枚举值
        """
        self._current_view_mode = mode

        if hasattr(self, 'stacked_widget'):
            mode_index = {
                ViewMode.LIST: 0,
                ViewMode.CHARACTER_CARD: 0,
                ViewMode.NETWORK_GRAPH: 1,
                ViewMode.FREQUENCY_DASHBOARD: 0,
                ViewMode.FACTION_CARD: 2,
                ViewMode.FAMILY_TREE: 3
            }
            index = mode_index.get(mode, 0)
            self.stacked_widget.setCurrentIndex(index)

        if hasattr(self, 'keyword_view_combo'):
            self.keyword_view_combo.blockSignals(True)
            view_data_map = {
                ViewMode.LIST: "list",
                ViewMode.CHARACTER_CARD: "card",
                ViewMode.NETWORK_GRAPH: "neural",
                ViewMode.FREQUENCY_DASHBOARD: "frequency",
                ViewMode.FACTION_CARD: "faction_card",
                ViewMode.FAMILY_TREE: "family_tree"
            }
            target_data = view_data_map.get(mode, "list")
            for i in range(self.keyword_view_combo.count()):
                if self.keyword_view_combo.itemData(i) == target_data:
                    self.keyword_view_combo.setCurrentIndex(i)
                    break
            self.keyword_view_combo.blockSignals(False)

    def _show_faction_list(self):
        """显示所有组织的卡片列表"""
        try:
            keywords = keyword_manager.load_keywords()
            factions = [kw for kw in keywords if kw.get('type') == 'faction']
        except Exception as e:
            logger.error(f"加载组织列表失败: {e}")
            factions = []

        h1_size = self._get_h1_size()
        h2_size = self._get_h2_size()
        body_size = self._get_body_size()
        ff = self.kwlist_font_family

        bg_color = self._t('bg_color', '#F8F9FA')
        fg_color = self._t('fg_color', '#212529')
        accent_color = self._t('accent_color', '#0078D4')
        warning_color = self._t('warning_color', '#FFC107')
        text_secondary = self._t('text_secondary', '#6C757D')
        border_color = self._t('border_color', '#DEE2E6')
        card_bg = self._t('card_bg', '#FFFFFF')

        if not factions:
            html = f"""
            <div style="text-align:center; padding:60px; color:#888; background:{bg_color};">
                <p style="font-size:{h1_size}px; color:{fg_color}; margin-bottom:20px;">暂无注册组织</p>
                <p style="font-size:{body_size}px; color:{text_secondary};">请先在关键词中添加类型为[faction]的关键词</p>
            </div>
            """
        else:
            cards = []
            for faction in factions:
                name = faction.get('name', '?')
                desc = faction.get('description', '')
                desc_short = (desc[:80] + '...') if desc and len(desc) > 80 else (desc or '')
                cards.append(f"""
                <div style="display:inline-block;width:360px;margin:12px;padding:20px;border:1px solid {border_color};border-radius:10px;background:{card_bg};vertical-align:top;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                        <h3 style="color:{accent_color};font-size:{h1_size}px;margin:0;font-weight:bold;">{name}</h3>
                        <a href='faction:{name}' style="color:#FFFFFF;text-decoration:none;padding:7px 18px;background:{accent_color};border:none;border-radius:6px;display:inline-block;font-size:{body_size}px;font-weight:bold;cursor:pointer;white-space:nowrap;text-align:center;">查看详情</a>
                    </div>
                    <p style="color:{text_secondary};font-size:{body_size}px;margin:0;line-height:1.6;">{desc_short}</p>
                </div>""")

            html = f"""
            <div style="background:{bg_color};padding:20px;font-family:{ff};font-size:{body_size}px;">
                <h1 style='color:{accent_color};font-size:{h1_size}px;font-weight:bold;margin:0 0 24px 0;'>组织列表</h1>
                <div style="text-align:left;">
                    {''.join(cards)}
                </div>
            </div>
            """

        if hasattr(self, 'faction_card_browser'):
            self._set_faction_browser_html(html)

        self._set_faction_action_buttons_visible(False)
        self._switch_to_view(ViewMode.FACTION_CARD)
        logger.info(f"已显示组织列表: {len(factions)}个")

    def _show_faction_card(self, faction_name):
        """显示组织卡视图

        Args:
            faction_name: 组织名称
        """
        self._current_faction_name = faction_name

        try:
            from ..models.keyword_manager import KeywordManager
            structure = KeywordManager.load_faction_structure(faction_name)
            members = KeywordManager.get_faction_members(faction_name)
        except Exception as e:
            logger.error(f"加载组织数据失败 [{faction_name}]: {e}")
            structure = {'template': '未知'}
            members = []

        html_content = self._render_faction_card_html(faction_name, structure, members)

        self._set_faction_browser_html(html_content)

        self._set_faction_action_buttons_visible(True)
        self._switch_to_view(ViewMode.FACTION_CARD)
        logger.info(f"已切换到组织卡视图: {faction_name}")

    def _render_faction_card_html(self, faction_name, structure, members):
        """
        渲染组织卡HTML内容 - 多叉树结构
        序列(level)为层级用虚线划分，职位(position)为区间，
        职能/姓名/性别标注节点，下辖机构为下一序列的区间
        """
        from collections import defaultdict

        h1_size = self._get_h1_size()
        h2_size = self._get_h2_size()
        body_size = self._get_body_size()
        ff = self.kwlist_font_family

        bg_color = self._t('bg_color', '#F8F9FA')
        fg_color = self._t('fg_color', '#212529')
        accent_color = self._t('accent_color', '#0078D4')
        border_color = self._t('border_color', '#DEE2E6')
        text_secondary = self._t('text_secondary', '#6C757D')
        success_color = self._t('success_color', '#28A745')
        warning_color = self._t('warning_color', '#FFC107')
        card_bg = self._t('card_bg', '#FFFFFF')

        if not structure or not isinstance(structure, dict) or not structure.get('roles'):
            return f"""
            <div style="text-align:center; padding:40px; color:#888; background:{bg_color};">
                <p style="font-size:{h1_size}px; color:{fg_color};">该组织尚未设置职能架构</p>
                <p><a href='edit_faction:{faction_name}' style="color:{accent_color}; font-size:{body_size}px; text-decoration:none;">[初始化架构]</a></p>
            </div>
            """

        keywords = keyword_manager.load_keywords()
        gender_map = {}
        for kw in keywords:
            if kw.get('type') == 'character':
                gender_map[kw['name']] = kw.get('gender', 'unknown')

        # 按层级、职位分组
        roles_by_level = defaultdict(list)
        for role_id, role_data in structure.get('roles', {}).items():
            level = role_data.get('level', 0)
            roles_by_level[level].append({'id': role_id, **role_data})
        sorted_levels = sorted(roles_by_level.keys())

        templates = keyword_manager.load_faction_templates()
        template_id = structure.get('template', 'custom')
        template = templates.get(template_id, {})
        template_name = template.get('name', '自定义架构')

        faction_data = next(
            (kw for kw in keywords if kw.get('name') == faction_name and kw.get('type') == 'faction'),
            None
        )
        description = faction_data.get('description', '') if faction_data else ''
        type_label = {'sect': '宗门', 'family': '家族', 'guild': '公会', 'kingdom': '势力'}.get(template_id, '势力')

        html_parts = []
        for level_idx, level in enumerate(sorted_levels):
            level_roles = sorted(roles_by_level[level], key=lambda r: r.get('title', ''))

            # 序列虚线分隔
            html_parts.append(f"""
            <div style="border-top:1px dashed {accent_color}40;margin:12px 0 8px 0;padding-top:8px;">
                <span style="color:{text_secondary};font-size:{body_size}px;">序列 LV{level + 1}</span>
            </div>""")

            # 按职位分组（同职位聚合）
            positions = defaultdict(list)
            for role in level_roles:
                positions[role.get('title', '未命名')].append(role)

            for pos_title, pos_roles in positions.items():
                member_count = len([r for r in pos_roles if r.get('member')])
                total_count = len(pos_roles)
                filled = f"{member_count}/{total_count}"

                html_parts.append(f"""
                <div style="margin-left:16px;margin-bottom:6px;border-left:2px solid {border_color};padding-left:12px;">
                    <div style="color:{accent_color};font-weight:bold;font-size:{body_size}px;margin-bottom:4px;">
                        {pos_title} <span style="color:{text_secondary};font-weight:normal;font-size:{body_size}px;">[{filled}]</span>
                    </div>""")

                for role in pos_roles:
                    member_name = role.get('member', '')
                    gender = gender_map.get(member_name, 'unknown') if member_name else ''
                    gender_text = {'male': '[男]', 'female': '[女]', 'unknown': ''}.get(gender, '')
                    func_label = role.get('title', '')

                    if member_name:
                        html_parts.append(f"""
                        <div style="margin-left:20px;padding:3px 0;line-height:1.6;">
                            <span style="color:{fg_color};font-size:{body_size}px;">{func_label}</span>
                            <span style="color:{fg_color};font-size:{body_size}px;"> - </span>
                            <a href='character:{member_name}' style="color:{accent_color};text-decoration:none;font-size:{body_size}px;">{member_name}</a>
                            <span style="color:{text_secondary};font-size:{body_size}px;margin-left:4px;">{gender_text}</span>
                        </div>""")
                    else:
                        required = role.get('required', False)
                        error_color = self._t('error_color', '#DC3545')
                        vacancy = f"<span style='color:{error_color};'>[必填-空缺]</span>" if required else "<span style='color:#666666;'>[空缺]</span>"
                        html_parts.append(f"""
                        <div style="margin-left:20px;padding:3px 0;line-height:1.6;">
                            <span style="color:{fg_color};font-size:{body_size}px;">{func_label}</span>
                            <span style="margin-left:8px;">{vacancy}</span>
                        </div>""")

                html_parts.append("</div>")

        roles_html = '\n'.join(html_parts)

        stats_parts = []
        total_positions = sum(len(v) for v in roles_by_level.values())
        total_members = sum(1 for v in roles_by_level.values() for r in v if r.get('member'))
        stats_parts.append(f"总编制<strong>{total_positions}</strong>")
        stats_html = ' | '.join(stats_parts)

        desc_html = ''
        if description:
            desc_html = f"""
            <div style="margin:16px 0;padding:12px 16px;border-left:3px solid {accent_color};background:{accent_color}15;border-radius:0 6px 6px 0;">
                <p style='color:{fg_color};font-size:{body_size}px;line-height:1.7;margin:0;'>{description.replace(chr(10), '<br>')}</p>
            </div>"""

        return f"""
        <div style="background:{bg_color};color:{fg_color};padding:20px;font-family:{ff};font-size:{body_size}px;">
            <div style="margin-bottom:16px;">
                <a href='back:factions' style="color:{text_secondary};text-decoration:none;font-size:{body_size}px;cursor:pointer;">< 返回组织列表</a>
            </div>
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;flex-wrap:wrap;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <h1 style='color:{accent_color};font-size:{h1_size}px;font-weight:bold;margin:0;'>{faction_name}</h1>
                    <span style="background:{accent_color}18;color:{accent_color};padding:4px 12px;border-radius:6px;font-size:{body_size}px;border:1px solid {accent_color}40;"><{type_label}></span>
                </div>
            </div>
            <div style="height:3px;background:linear-gradient(90deg,{accent_color},{border_color},{bg_color});margin-bottom:20px;border-radius:2px;"></div>

            {desc_html}

            <div style="border:1px solid {border_color};border-radius:10px;padding:24px;margin:20px 0;background:{card_bg};min-height:160px;">
                <h2 style='color:{accent_color};font-size:{h2_size}px;margin:0 0 16px 0;padding-bottom:10px;border-bottom:1px solid {border_color};font-weight:bold;'>
                    职能架构（{template_name}）
                </h2>
                {roles_html if roles_html else '<p style="color:#666;text-align:center;padding:24px;font-size:{body_size}px;">暂无职位定义</p>'}
            </div>

            <div style="margin:20px 0;padding:14px 20px;background:{accent_color}15;border-radius:8px;font-size:{body_size}px;color:{text_secondary};">
                统计：{stats_html}
            </div>
        </div>
        """

    # ====== 族谱图视图 ======

    def _render_family_tree_view(self):
        """渲染族谱图视图"""
        self.search_bar.setVisible(False)
        self._filter_panel.setVisible(False)
        self._layout_save_btn.setVisible(False)
        self._layout_reset_btn.setVisible(False)
        self._isolated_btn.setVisible(False)
        self._export_png_btn.setVisible(False)
        self._freq_tab_bar.setVisible(False)

        self._populate_root_combo()

    def _populate_root_combo(self):
        """填充根节点下拉框：列出所有有人物关系的关键词"""
        self.family_root_combo.blockSignals(True)
        current_text = self.family_root_combo.currentText()
        self.family_root_combo.clear()

        try:
            keywords = keyword_manager.load_keywords()
            characters = [kw for kw in keywords if kw.get('type') == 'character']

            if not characters:
                self.family_root_combo.addItem("-- 暂无人物关键词 --", None)
            else:
                self.family_root_combo.addItem("-- 选择根节点人物 --", None)
                for char in sorted(characters, key=lambda x: x.get('name', '')):
                    name = char.get('name', '')
                    rels = char.get('relationships', [])
                    has_family = any(r.get('type') in ('parent', 'child', 'spouse', 'father', 'mother', 'son', 'daughter') for r in rels)
                    display_name = name
                    if has_family:
                        display_name = name
                    self.family_root_combo.addItem(display_name, name)

            if current_text:
                idx = self.family_root_combo.findText(current_text)
                if idx >= 0:
                    self.family_root_combo.setCurrentIndex(idx)

        except Exception as e:
            logger.error(f"填充根节点列表失败: {e}")
            self.family_root_combo.addItem("-- 加载失败 --", None)

        self.family_root_combo.blockSignals(False)

    def _on_family_root_changed(self, text):
        """根节点选择改变时重新渲染族谱"""
        root_name = self.family_root_combo.currentData()
        if root_name:
            self._load_and_display_family_tree(root_name)
        else:
            self._show_family_tree_placeholder()

    def _refresh_family_tree(self):
        """刷新族谱（重新加载数据）"""
        self._populate_root_combo()
        root_name = self.family_root_combo.currentData()
        if root_name:
            self._load_and_display_family_tree(root_name)

    def _load_and_display_family_tree(self, root_name):
        """加载并显示指定人物的家族树

        Args:
            root_name: 根节点人物名称
        """
        try:
            from ..models.keyword_manager import KeywordManager
            tree_data = KeywordManager.build_family_tree(root_name)

            if not tree_data:
                self._show_family_tree_placeholder(f"未找到人物 '{root_name}' 的家族关系数据")
                return

            if hasattr(self, '_family_tree_widget') and self._family_tree_widget:
                layout = self._family_tree_container.layout()
                if layout:
                    layout.removeWidget(self._family_tree_widget)
                    self._family_tree_widget.deleteLater()

            from ..ui.family_tree_view import FamilyTreeView
            self._family_tree_widget = FamilyTreeView(tree_data=tree_data)
            self._family_tree_widget.node_clicked.connect(self._on_family_node_clicked)

            layout = self._family_tree_container.layout()
            if layout:
                layout.replaceWidget(self._family_tree_placeholder, self._family_tree_widget)
                self._family_tree_placeholder.hide()
                self._family_tree_widget.show()

            logger.info(f"已加载族谱: 根节点={root_name}")

        except Exception as e:
            logger.error(f"加载族谱失败 [{root_name}]: {e}")
            import traceback
            traceback.print_exc()
            self._show_family_tree_placeholder(f"加载族谱失败: {str(e)}")

    def _show_family_tree_placeholder(self, message=None):
        """显示占位符提示"""
        if hasattr(self, '_family_tree_widget') and self._family_tree_widget:
            self._family_tree_widget.hide()
        if hasattr(self, '_family_tree_placeholder'):
            if message:
                self._family_tree_placeholder.setText(message)
            self._family_tree_placeholder.show()

    def _on_family_node_clicked(self, node_name):
        """点击族谱节点时的处理"""
        logger.info(f"族谱节点被点击: {node_name}")
        self.keyword_selected.emit(node_name)

    def _export_family_tree_png(self):
        """导出族谱图为PNG"""
        if not hasattr(self, '_family_tree_widget') or not self._family_tree_widget:
            QMessageBox.warning(self, "提示", "请先选择根节点并生成族谱图")
            return

        try:
            from PyQt5.QtWidgets import QFileDialog
            filepath, _ = QFileDialog.getSaveFileName(
                self, "导出族谱图", f"family_tree.png",
                "PNG 图片 (*.png);;所有文件 (*)"
            )
            if filepath:
                self._family_tree_widget.export_to_png(filepath)
                QMessageBox.information(self, "成功", f"族谱图已导出到:\n{filepath}")
        except Exception as e:
            logger.error(f"导出族谱图失败: {e}")
            QMessageBox.critical(self, language_manager.tr("error"), f"{language_manager.tr('export_failed')}:\n{str(e)}")

    def show_family_tree_for_character(self, character_name):
        """外部调用：显示指定人物的族谱（从其他视图跳转过来）

        Args:
            character_name: 人物名称
        """
        self._current_view_mode = ViewMode.FAMILY_TREE
        if hasattr(self, 'keyword_view_combo'):
            for i in range(self.keyword_view_combo.count()):
                if self.keyword_view_combo.itemData(i) == "family_tree":
                    self.keyword_view_combo.setCurrentIndex(i)
                    break

        QTimer.singleShot(100, lambda: self._select_and_show_family_tree(character_name))

    def _select_and_show_family_tree(self, character_name):
        """选择根节点并显示族谱"""
        idx = self.family_root_combo.findData(character_name)
        if idx >= 0:
            self.family_root_combo.setCurrentIndex(idx)
        else:
            self.family_root_combo.setCurrentIndex(0)
            if character_name:
                self._load_and_display_family_tree(character_name)