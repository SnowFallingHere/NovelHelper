"""
参数配置标签页
提供完整的UI配置、颜色方案、网络图、监控、词频等设置功能
"""

import os
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
    QFormLayout, QComboBox, QScrollArea, QMessageBox, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import pyqtSignal, Qt

from .base_tab import BaseTab
from ..core.config_manager import ConfigManager
from ..core.language_manager import language_manager
from ..core.file_manager import get_novel_dir, FileManager, file_manager

logger = logging.getLogger(__name__)


class ConfigTab(BaseTab):
    """参数配置标签页"""
    
    # 信号定义
    config_saved = pyqtSignal()           # 配置保存时发出
    config_applied = pyqtSignal()         # 配置应用时发出
    overlay_pos_changed = pyqtSignal(str) # 覆盖层位置改变时发出
    legend_config_changed = pyqtSignal(bool, str, int)  # 图例配置改变时发出
    glow_config_changed = pyqtSignal(bool)              # 辉光效果开关改变时发出
    size_sort_config_changed = pyqtSignal(bool)         # 面积排序开关改变时发出
    brightness_sort_config_changed = pyqtSignal(bool)   # 亮度排序开关改变时发出
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_name = "参数配置"
        
        # 加载所有配置值到实例属性
        self._load_all_config_values()
        
        logger.info(f"[{self.tab_name}] 创建实例")
    
    def _load_all_config_values(self):
        """加载所有配置值"""
        # UI 配置
        self.base_font_size = int(ConfigManager.get('UI', 'base_font_size', fallback='14'))
        self.base_title_size = int(ConfigManager.get('UI', 'base_title_size', fallback='16'))
        self.log_font_size = int(ConfigManager.get('UI', 'log_font_size', fallback='12'))
        self.graph_font_size = int(ConfigManager.get('UI', 'graph_font_size', fallback='12'))
        self.line_height = float(ConfigManager.get('UI', 'line_height', fallback='1.5'))
        self.initial_width = int(ConfigManager.get('UI', 'initial_width', fallback='1400'))
        self.initial_height = int(ConfigManager.get('UI', 'initial_height', fallback='900'))
        self.kwlist_font_family = ConfigManager.get('UI', 'kwlist_font_family', fallback='Microsoft YaHei UI')
        self.current_theme = ConfigManager.get('UI', 'theme', fallback='fluent')
        self.enable_animations = ConfigManager.get_int('UI', 'enable_animations', fallback=1) == 1
        self.enable_acrylic = ConfigManager.get_int('UI', 'enable_acrylic', fallback=1) == 1
        
        # 关键词字体/颜色配置
        self.kw_h1_size = int(ConfigManager.get('UI', 'kw_h1_size', fallback='20'))
        self.kw_h1_color = ConfigManager.get('UI', 'kw_h1_color', fallback='#0078D4')
        self.kw_h2_size = int(ConfigManager.get('UI', 'kw_h2_size', fallback='18'))
        self.kw_h2_color = ConfigManager.get('UI', 'kw_h2_color', fallback='#107C10')
        self.kw_body_size = int(ConfigManager.get('UI', 'kw_body_size', fallback='14'))
        self.kw_body_color = ConfigManager.get('UI', 'kw_body_color', fallback='#606060')
        self.kw_link_size = int(ConfigManager.get('UI', 'kw_link_size', fallback='14'))
        self.kw_link_color = ConfigManager.get('UI', 'kw_link_color', fallback='#0078D4')
        
        # 字号自适应缩放配置
        self.enable_font_scaling = ConfigManager.get_int('UI', 'enable_font_scaling', fallback=1) == 1
        self.scaling_reference_width = ConfigManager.get_int('UI', 'scaling_reference_width', fallback=1570)
        self.scaling_min = ConfigManager.get_float('UI', 'scaling_min', fallback=0.8)
        self.scaling_max = ConfigManager.get_float('UI', 'scaling_max', fallback=1.5)
        
        # 链接样式
        self.link_italic = ConfigManager.get('UI', 'link_italic', fallback='1') == '1'
        self.link_bold = ConfigManager.get('UI', 'link_bold', fallback='0') == '1'
        
        # 全局颜色
        self.bg_color = ConfigManager.get('UI', 'bg_color', fallback='#F8F9FA')
        self.fg_color = ConfigManager.get('UI', 'fg_color', fallback='#212529')
        self.border_color = ConfigManager.get('UI', 'border_color', fallback='#DEE2E6')
        self.error_color = ConfigManager.get('UI', 'error_color', fallback='#D13438')
        self.warn_color = ConfigManager.get('UI', 'warn_color', fallback='#FF8C00')
        self.btn_bg_color = ConfigManager.get('UI', 'btn_bg_color', fallback='#0078D4')
        self.btn_hover_color = ConfigManager.get('UI', 'btn_hover_color', fallback='#106EBE')
        self.input_bg_color = ConfigManager.get('UI', 'input_bg_color', fallback='#FFFFFF')
        
        # 网络图配置
        self.graph_bg = ConfigManager.get('Theme', 'graph_bg_color', fallback='#F8F9FA')
        self.graph_bg_follow_theme = ConfigManager.get('Theme', 'graph_bg_follow_theme', fallback='1') == '1'
        self.grid_color = ConfigManager.get('Theme', 'graph_grid_color', fallback='#E9ECEF')
        self.edge_width = int(ConfigManager.get('Theme', 'edge_width', fallback='3'))
        self.layout_ideal = int(ConfigManager.get('Graph', 'layout_ideal_length', fallback='200'))
        self.node_limit = int(ConfigManager.get('Graph', 'node_limit', fallback='200'))
        self.node_min_size = int(ConfigManager.get('Graph', 'node_min_size', fallback='60'))
        self.node_max_size = int(ConfigManager.get('Graph', 'node_max_size', fallback='160'))
        self.node_min_brightness = int(ConfigManager.get('Graph', 'node_min_brightness', fallback='15'))
        self.node_max_brightness = int(ConfigManager.get('Graph', 'node_max_brightness', fallback='65'))
        
        # 节点视觉效果差异化配置
        self.enable_glow = ConfigManager.get_int('Graph', 'enable_glow', fallback=1) == 1
        self.enable_size_sort = ConfigManager.get_int('Graph', 'enable_size_sort', fallback=1) == 1
        self.enable_brightness_sort = ConfigManager.get_int('Graph', 'enable_brightness_sort', fallback=1) == 1
        
        # 监控配置
        self.check_interval = int(ConfigManager.get('Monitor', 'check_interval', fallback='15'))
        self.max_ahead = int(ConfigManager.get('Monitor', 'max_ahead_chapters', fallback='2'))
        self.min_word = int(ConfigManager.get('Monitor', 'min_word_count', fallback='20'))
        self.novel_dir = ConfigManager.get('Monitor', 'novel_dir', fallback='')
        self.heartbeat_timeout = int(ConfigManager.get('Monitor', 'heartbeat_timeout', fallback='120'))
        
        # 词频配置
        self.freq_min_len = int(ConfigManager.get('Frequency', 'min_word_length', fallback='2'))
        self.freq_min_occ = int(ConfigManager.get('Frequency', 'min_occurrences', fallback='3'))
        self.freq_inactive = int(ConfigManager.get('Frequency', 'inactive_chapters', fallback='3'))
        self.freq_auto = ConfigManager.get('Frequency', 'auto_scan', fallback='1') == '1'
        self.freq_stopwords = ConfigManager.get('Frequency', 'filter_stopwords', fallback='1') == '1'
        self.freq_keywords_only = ConfigManager.get('Frequency', 'keywords_only', fallback='0') == '1'
        self.freq_stale_ratio = int(float(ConfigManager.get('Frequency', 'stale_ratio', fallback='3.0')))
        self.freq_stale_gap = int(ConfigManager.get('Frequency', 'stale_gap', fallback='3'))
        
        # 格式配置（空值时使用语言默认格式）
        current_lang = language_manager.get_current_language()
        _fmt_defaults = FileManager.get_default_formats(current_lang)
        self.export_format = ConfigManager.get('Format', 'export_format', fallback='') or _fmt_defaults['filename']
        self.export_volume_format = ConfigManager.get('Format', 'export_volume_format', fallback='') or _fmt_defaults['volume']
        self.export_chapter_format = ConfigManager.get('Format', 'export_chapter_format', fallback='') or _fmt_defaults['chapter']
        self.volume_folder_format = ConfigManager.get('Format', 'volume_folder_format', fallback='{cn.low.Volume}{title}')
        self.preview_color = ConfigManager.get('Format', 'preview_color', fallback='#66ccff')
        self.preview_font_size = int(ConfigManager.get('Format', 'preview_font_size', fallback='23'))
        self.format_help_font_size = int(ConfigManager.get('Format', 'format_help_font_size', fallback='20'))
    
    def _build_ui(self):
        """构建完整的UI界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 10)
        
        # ====== 标题 ======
        self._config_title_label = QLabel(language_manager.tr("parameter_config"))
        from ..core.theme_manager import theme_manager
        title_color = theme_manager.get('accent_color', '#0078D4')
        self._config_title_label.setStyleSheet(f"font-size: {self.base_title_size}px; font-weight: bold; color: {title_color};")
        main_layout.addWidget(self._config_title_label)
        
        # ====== 滚动区域 ======
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # ====== 小说目录（页面第一行）======
        self._dir_group = QGroupBox(language_manager.tr("novel_dir_label"))
        dir_group_layout = QFormLayout(self._dir_group)
        
        self.config_novel_dir_btn = QPushButton(language_manager.tr("select_directory"))
        self.config_novel_dir = QLineEdit()
        self.config_novel_dir.setText(self.novel_dir)
        self.config_novel_dir.setReadOnly(True)
        self.config_novel_dir_btn.clicked.connect(self._select_config_dir)
        
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.config_novel_dir)
        dir_layout.addWidget(self.config_novel_dir_btn)
        dir_group_layout.addRow(language_manager.tr("novel_dir_label"), dir_layout)
        
        scroll_layout.addWidget(self._dir_group)
        
        # === UI 尺寸配置 ===
        self._ui_group = QGroupBox(language_manager.tr("ui_size_config"))
        self._ui_form = QFormLayout(self._ui_group)
        
        self.config_base_font = QSpinBox()
        self.config_base_font.setRange(8, 48)
        self.config_base_font.setValue(self.base_font_size)
        self._ui_form.addRow(language_manager.tr("base_font_size"), self.config_base_font)
        
        self.config_title_font = QSpinBox()
        self.config_title_font.setRange(12, 72)
        self.config_title_font.setValue(self.base_title_size)
        self._ui_form.addRow(language_manager.tr("title_font_size"), self.config_title_font)
        
        self.config_log_font = QSpinBox()
        self.config_log_font.setRange(8, 32)
        self.config_log_font.setValue(self.log_font_size)
        self._ui_form.addRow(language_manager.tr("log_font_size"), self.config_log_font)
        
        self.config_graph_font = QSpinBox()
        self.config_graph_font.setRange(8, 32)
        self.config_graph_font.setValue(self.graph_font_size)
        self._ui_form.addRow(language_manager.tr("graph_font_size_label"), self.config_graph_font)
        
        self.config_line_height = QDoubleSpinBox()
        self.config_line_height.setRange(0.8, 3.0)
        self.config_line_height.setSingleStep(0.05)
        self.config_line_height.setValue(self.line_height)
        self._ui_form.addRow(language_manager.tr("line_height_label"), self.config_line_height)
        
        self.config_initial_width = QSpinBox()
        self.config_initial_width.setRange(400, 2000)
        self.config_initial_width.setValue(self.initial_width)
        self._ui_form.addRow(language_manager.tr("initial_width"), self.config_initial_width)
        
        self.config_initial_height = QSpinBox()
        self.config_initial_height.setRange(300, 2000)
        self.config_initial_height.setValue(self.initial_height)
        self._ui_form.addRow(language_manager.tr("initial_height"), self.config_initial_height)
        
        self.config_kwlist_family = QLineEdit()
        self.config_kwlist_family.setText(self.kwlist_font_family)
        self._ui_form.addRow(language_manager.tr("font_family_label"), self.config_kwlist_family)
        
        # 主题选择
        self.config_theme = QComboBox()
        from ..core.theme_manager import ThemeManager
        for theme_info in ThemeManager.list_themes():
            self.config_theme.addItem(theme_info['name'], theme_info['id'])
        idx = self.config_theme.findData(self.current_theme)
        if idx >= 0:
            self.config_theme.setCurrentIndex(idx)
        self.config_theme.setToolTip(language_manager.tr("theme_tooltip"))
        self._ui_form.addRow(language_manager.tr("theme_label"), self.config_theme)
        
        # 视觉效果开关
        self.config_enable_animations = QCheckBox(language_manager.tr("enable_animations_label"))
        self.config_enable_animations.setChecked(self.enable_animations)
        self.config_enable_animations.setToolTip(
            language_manager.tr("animations_tooltip")
        )
        self._ui_form.addRow("", self.config_enable_animations)
        
        self.config_enable_acrylic = QCheckBox(language_manager.tr("enable_acrylic"))
        self.config_enable_acrylic.setChecked(self.enable_acrylic)
        self.config_enable_acrylic.setToolTip(
            language_manager.tr("acrylic_tooltip")
        )
        self._ui_form.addRow("", self.config_enable_acrylic)
        
        # 字号自适应缩放配置
        self._scaling_label = QLabel(language_manager.tr("font_scaling_label"))
        self._scaling_label.setStyleSheet(f"color: {theme_manager.get('accent_color', '#0078D4')}; font-weight: bold; margin-top: 8px;")
        self._ui_form.addRow(self._scaling_label)
        
        self.config_enable_font_scaling = QCheckBox(language_manager.tr("enable_font_scaling_label"))
        self.config_enable_font_scaling.setChecked(self.enable_font_scaling)
        self.config_enable_font_scaling.setToolTip(
            language_manager.tr("font_scaling_tooltip")
        )
        self._ui_form.addRow("", self.config_enable_font_scaling)
        
        self.config_scaling_reference_width = QSpinBox()
        self.config_scaling_reference_width.setRange(800, 2500)
        self.config_scaling_reference_width.setValue(self.scaling_reference_width)
        self.config_scaling_reference_width.setSuffix(" px")
        self._ui_form.addRow(language_manager.tr("reference_width"), self.config_scaling_reference_width)
        
        scaling_range_layout = QHBoxLayout()
        
        self.config_scaling_min = QDoubleSpinBox()
        self.config_scaling_min.setRange(0.5, 1.0)
        self.config_scaling_min.setSingleStep(0.05)
        self.config_scaling_min.setValue(self.scaling_min)
        scaling_range_layout.addWidget(QLabel(language_manager.tr("minimum")))
        scaling_range_layout.addWidget(self.config_scaling_min)
        
        self.config_scaling_max = QDoubleSpinBox()
        self.config_scaling_max.setRange(1.0, 3.0)
        self.config_scaling_max.setSingleStep(0.1)
        self.config_scaling_max.setValue(self.scaling_max)
        scaling_range_layout.addWidget(QLabel(language_manager.tr("maximum")))
        scaling_range_layout.addWidget(self.config_scaling_max)
        scaling_range_layout.addStretch()
        
        range_widget = QWidget()
        range_widget.setLayout(scaling_range_layout)
        self._ui_form.addRow(language_manager.tr("scaling_range"), range_widget)
        
        scroll_layout.addWidget(self._ui_group)
        
        # === 标签配置 ===
        self._tab_group = QGroupBox(language_manager.tr("tab_config"))
        self._tab_form = QFormLayout(self._tab_group)
        
        # Tab 配置
        self.config_link_italic = QCheckBox(language_manager.tr("link_italic"))
        self.config_link_italic.setChecked(self.link_italic)
        self._tab_form.addRow("", self.config_link_italic)
        
        self.config_link_bold = QCheckBox(language_manager.tr("link_bold"))
        self.config_link_bold.setChecked(self.link_bold)
        self._tab_form.addRow("", self.config_link_bold)
        
        scroll_layout.addWidget(self._tab_group)
        
        # === 关键词字体/颜色配置 ===
        self._kw_group = QGroupBox(language_manager.tr("keyword_config"))
        self._kw_form = QFormLayout(self._kw_group)
        
        self.config_kw_h1_size = QSpinBox()
        self.config_kw_h1_size.setRange(10, 48)
        self.config_kw_h1_size.setValue(self.kw_h1_size)
        self._kw_form.addRow(language_manager.tr("h1_font_size"), self.config_kw_h1_size)

        self.config_kw_h1_color = QLineEdit()
        self.config_kw_h1_color.setText(self.kw_h1_color)
        self._kw_form.addRow(language_manager.tr("h1_color"), self.config_kw_h1_color)

        self.config_kw_h2_size = QSpinBox()
        self.config_kw_h2_size.setRange(8, 40)
        self.config_kw_h2_size.setValue(self.kw_h2_size)
        self._kw_form.addRow(language_manager.tr("h2_font_size"), self.config_kw_h2_size)

        self.config_kw_h2_color = QLineEdit()
        self.config_kw_h2_color.setText(self.kw_h2_color)
        self._kw_form.addRow(language_manager.tr("h2_color"), self.config_kw_h2_color)

        self.config_kw_body_size = QSpinBox()
        self.config_kw_body_size.setRange(8, 36)
        self.config_kw_body_size.setValue(self.kw_body_size)
        self._kw_form.addRow(language_manager.tr("body_font_size"), self.config_kw_body_size)

        self.config_kw_body_color = QLineEdit()
        self.config_kw_body_color.setText(self.kw_body_color)
        self._kw_form.addRow(language_manager.tr("body_color"), self.config_kw_body_color)

        self.config_kw_link_size = QSpinBox()
        self.config_kw_link_size.setRange(8, 36)
        self.config_kw_link_size.setValue(self.kw_link_size)
        self._kw_form.addRow(language_manager.tr("link_font_size"), self.config_kw_link_size)

        self.config_kw_link_color = QLineEdit()
        self.config_kw_link_color.setText(self.kw_link_color)
        self._kw_form.addRow(language_manager.tr("link_color"), self.config_kw_link_color)
        
        scroll_layout.addWidget(self._kw_group)
        
        # === 全局颜色配置 ===
        self._color_group = QGroupBox(language_manager.tr("color_scheme_group"))
        self._color_form = QFormLayout(self._color_group)
        
        self.config_bg_color = QLineEdit()
        self.config_bg_color.setText(self.bg_color)
        self._color_form.addRow(language_manager.tr("bg_color_label"), self.config_bg_color)
        
        self.config_fg_color = QLineEdit()
        self.config_fg_color.setText(self.fg_color)
        self._color_form.addRow(language_manager.tr("fg_color_label"), self.config_fg_color)
        
        self.config_border_color = QLineEdit()
        self.config_border_color.setText(self.border_color)
        self._color_form.addRow(language_manager.tr("border_color_label"), self.config_border_color)
        
        self.config_error_color = QLineEdit()
        self.config_error_color.setText(self.error_color)
        self._color_form.addRow(language_manager.tr("error_color_label"), self.config_error_color)
        
        self.config_warn_color = QLineEdit()
        self.config_warn_color.setText(self.warn_color)
        self._color_form.addRow(language_manager.tr("warn_color_label"), self.config_warn_color)
        
        self.config_btn_bg_color = QLineEdit()
        self.config_btn_bg_color.setText(self.btn_bg_color)
        self._color_form.addRow(language_manager.tr("btn_bg_color_label"), self.config_btn_bg_color)
        
        self.config_btn_hover_color = QLineEdit()
        self.config_btn_hover_color.setText(self.btn_hover_color)
        self._color_form.addRow(language_manager.tr("btn_hover_color_label"), self.config_btn_hover_color)
        
        self.config_input_bg_color = QLineEdit()
        self.config_input_bg_color.setText(self.input_bg_color)
        self._color_form.addRow(language_manager.tr("input_bg_color"), self.config_input_bg_color)
        
        scroll_layout.addWidget(self._color_group)
        
        # === 网络图配置 ===
        self._graph_group = QGroupBox(language_manager.tr("graph_config"))
        self._graph_form = QFormLayout(self._graph_group)

        self._bg_row = QWidget()
        bg_layout = QHBoxLayout(self._bg_row)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        self.config_graph_bg = QLineEdit()
        self.config_graph_bg.setText(self.graph_bg)
        bg_layout.addWidget(self.config_graph_bg)
        self.config_graph_bg_follow = QCheckBox(language_manager.tr("follow_theme"))
        self.config_graph_bg_follow.setChecked(self.graph_bg_follow_theme)
        self.config_graph_bg_follow.toggled.connect(self.config_graph_bg.setDisabled)
        self.config_graph_bg.setDisabled(self.graph_bg_follow_theme)
        bg_layout.addWidget(self.config_graph_bg_follow)
        self._graph_form.addRow(language_manager.tr("graph_bg_color"), self._bg_row)
        
        self.config_graph_grid_color = QLineEdit()
        self.config_graph_grid_color.setText(self.grid_color)
        self._graph_form.addRow(language_manager.tr("grid_color_label"), self.config_graph_grid_color)
        
        self.config_edge_width = QSpinBox()
        self.config_edge_width.setRange(1, 10)
        self.config_edge_width.setValue(self.edge_width)
        self._graph_form.addRow(language_manager.tr("edge_width_label"), self.config_edge_width)
        
        self.config_layout_ideal = QSpinBox()
        self.config_layout_ideal.setRange(50, 500)
        self.config_layout_ideal.setValue(self.layout_ideal)
        self._graph_form.addRow(language_manager.tr("layout_ideal_distance"), self.config_layout_ideal)
        
        self.config_node_limit = QSpinBox()
        self.config_node_limit.setRange(50, 500)
        self.config_node_limit.setValue(self.node_limit)
        self._graph_form.addRow(language_manager.tr("max_nodes"), self.config_node_limit)
        
        self.config_auto_layout = QCheckBox(language_manager.tr("auto_save_layout"))
        self.config_auto_layout.setChecked(
            ConfigManager.get_int('Graph', 'auto_save_layout', fallback=1) == 1
        )
        self._graph_form.addRow("", self.config_auto_layout)
        
        # === 节点视觉效果差异化配置 ===
        self._visual_label = QLabel(language_manager.tr("node_visual_effects"))
        self._visual_label.setStyleSheet(f"color: {theme_manager.get('accent_color', '#0078D4')}; font-weight: bold; margin-top: 8px;")
        self._graph_form.addRow(self._visual_label)
        
        # 辉光效果开关
        self.config_enable_glow = QCheckBox(language_manager.tr("enable_glow"))
        self.config_enable_glow.setChecked(
            ConfigManager.get_int('Graph', 'enable_glow', fallback=1) == 1
        )
        self.config_enable_glow.setToolTip(
            language_manager.tr("glow_tooltip")
        )
        self.config_enable_glow.stateChanged.connect(self._on_glow_config_changed)
        self._graph_form.addRow("", self.config_enable_glow)
        
        # 面积排序显示开关
        self.config_enable_size_sort = QCheckBox(language_manager.tr("sort_by_connection_size"))
        self.config_enable_size_sort.setChecked(
            ConfigManager.get_int('Graph', 'enable_size_sort', fallback=1) == 1
        )
        self.config_enable_size_sort.setToolTip(
            language_manager.tr("size_sort_tooltip")
        )
        self.config_enable_size_sort.stateChanged.connect(self._on_size_sort_config_changed)
        self._graph_form.addRow("", self.config_enable_size_sort)
        
        # 亮度排序显示开关
        self.config_enable_brightness_sort = QCheckBox(language_manager.tr("sort_by_connection_brightness"))
        self.config_enable_brightness_sort.setChecked(
            ConfigManager.get_int('Graph', 'enable_brightness_sort', fallback=1) == 1
        )
        self.config_enable_brightness_sort.setToolTip(
            language_manager.tr("brightness_sort_tooltip")
        )
        self.config_enable_brightness_sort.stateChanged.connect(self._on_brightness_sort_config_changed)
        self._graph_form.addRow("", self.config_enable_brightness_sort)
        
        # 图例位置
        self.config_overlay_pos = QComboBox()
        for pos_key, pos_label in [
            ('bottom-right', language_manager.tr("pos_bottom_right")),
            ('bottom-left', language_manager.tr("pos_bottom_left")),
            ('top-right', language_manager.tr("pos_top_right")),
            ('top-left', language_manager.tr("pos_top_left"))
        ]:
            self.config_overlay_pos.addItem(pos_label, pos_key)
        
        current_pos = ConfigManager.get('UI', 'overlay_position', fallback='bottom-right')
        for i in range(self.config_overlay_pos.count()):
            if self.config_overlay_pos.itemData(i) == current_pos:
                self.config_overlay_pos.setCurrentIndex(i)
                break
        
        self.config_overlay_pos.currentIndexChanged.connect(self._on_overlay_pos_changed)
        self._graph_form.addRow(language_manager.tr("legend_position"), self.config_overlay_pos)
        
        # 图例显示配置
        self.config_legend_visible = QCheckBox(language_manager.tr("show"))
        self.config_legend_visible.setChecked(
            ConfigManager.get_int('UI', 'legend_visible', fallback=1) == 1
        )
        self.config_legend_visible.stateChanged.connect(self._on_legend_config_changed)
        self._graph_form.addRow(language_manager.tr("legend_visible"), self.config_legend_visible)
        
        # 图例样式配置
        legend_font_layout = QHBoxLayout()
        
        self.config_legend_font = QComboBox()
        for font_name in ['Microsoft YaHei', 'SimHei', 'KaiTi', 'FangSong', 'Consolas', 'Arial']:
            self.config_legend_font.addItem(font_name)
        
        current_font = ConfigManager.get('UI', 'legend_font', fallback='Microsoft YaHei')
        for i in range(self.config_legend_font.count()):
            if self.config_legend_font.itemText(i) == current_font:
                self.config_legend_font.setCurrentIndex(i)
                break
        
        self.config_legend_font.currentIndexChanged.connect(self._on_legend_config_changed)
        legend_font_layout.addWidget(QLabel(language_manager.tr("font_label")))
        legend_font_layout.addWidget(self.config_legend_font)
        
        self.config_legend_size = QSpinBox()
        self.config_legend_size.setRange(10, 28)
        self.config_legend_size.setValue(
            ConfigManager.get_int('UI', 'legend_font_size', fallback=16)
        )
        self.config_legend_size.valueChanged.connect(self._on_legend_config_changed)
        legend_font_layout.addWidget(QLabel(language_manager.tr("font_size_label")))
        legend_font_layout.addWidget(self.config_legend_size)
        legend_font_layout.addStretch()
        
        font_widget = QWidget()
        font_widget.setLayout(legend_font_layout)
        self._graph_form.addRow(language_manager.tr("legend_style"), font_widget)
        
        # 节点大小范围
        node_size_layout = QHBoxLayout()
        
        self.config_node_min_size = QSpinBox()
        self.config_node_min_size.setRange(40, 120)
        self.config_node_min_size.setValue(self.node_min_size)
        self.config_node_min_size.setSuffix(" px")
        self.config_node_min_size.valueChanged.connect(self._on_node_visual_config_changed)
        node_size_layout.addWidget(QLabel(language_manager.tr("min_size_label")))
        node_size_layout.addWidget(self.config_node_min_size)
        
        self.config_node_max_size = QSpinBox()
        self.config_node_max_size.setRange(100, 250)
        self.config_node_max_size.setValue(self.node_max_size)
        self.config_node_max_size.setSuffix(" px")
        self.config_node_max_size.valueChanged.connect(self._on_node_visual_config_changed)
        node_size_layout.addWidget(QLabel(language_manager.tr("max_size_label")))
        node_size_layout.addWidget(self.config_node_max_size)
        node_size_layout.addStretch()
        
        size_widget = QWidget()
        size_widget.setLayout(node_size_layout)
        self._graph_form.addRow(language_manager.tr("node_size_range"), size_widget)
        
        # 节点亮度范围
        brightness_layout = QHBoxLayout()
        
        self.config_node_min_brightness = QSpinBox()
        self.config_node_min_brightness.setRange(5, 40)
        self.config_node_min_brightness.setValue(self.node_min_brightness)
        self.config_node_min_brightness.setSuffix(" %")
        self.config_node_min_brightness.valueChanged.connect(self._on_node_visual_config_changed)
        brightness_layout.addWidget(QLabel(language_manager.tr("darkest_label")))
        brightness_layout.addWidget(self.config_node_min_brightness)
        
        self.config_node_max_brightness = QSpinBox()
        self.config_node_max_brightness.setRange(45, 85)
        self.config_node_max_brightness.setValue(self.node_max_brightness)
        self.config_node_max_brightness.setSuffix(" %")
        self.config_node_max_brightness.valueChanged.connect(self._on_node_visual_config_changed)
        brightness_layout.addWidget(QLabel(language_manager.tr("brightest_label")))
        brightness_layout.addWidget(self.config_node_max_brightness)
        brightness_layout.addStretch()
        
        bright_widget = QWidget()
        bright_widget.setLayout(brightness_layout)
        self._graph_form.addRow(language_manager.tr("node_brightness_range"), bright_widget)
        
        # 连线按钮配置
        btn_cfg_layout = QHBoxLayout()
        
        self.config_connect_btn_size = QSpinBox()
        self.config_connect_btn_size.setRange(24, 60)
        self.config_connect_btn_size.setValue(
            ConfigManager.get_int('UI', 'connect_btn_size', fallback=36)
        )
        self.config_connect_btn_size.valueChanged.connect(self._on_connect_btn_config_changed)
        btn_cfg_layout.addWidget(QLabel(language_manager.tr("size_label")))
        btn_cfg_layout.addWidget(self.config_connect_btn_size)
        
        self.config_connect_btn_color = QLineEdit()
        self.config_connect_btn_color.setText(
            ConfigManager.get('UI', 'connect_btn_color', fallback='#00ff88')
        )
        self.config_connect_btn_color.setFixedWidth(100)
        self.config_connect_btn_color.textChanged.connect(self._on_connect_btn_config_changed)
        btn_cfg_layout.addWidget(QLabel(language_manager.tr("color_label")))
        btn_cfg_layout.addWidget(self.config_connect_btn_color)
        btn_cfg_layout.addStretch()
        
        btn_widget = QWidget()
        btn_widget.setLayout(btn_cfg_layout)
        self._graph_form.addRow(language_manager.tr("connect_button"), btn_widget)
        
        scroll_layout.addWidget(self._graph_group)
        
        # === 自定义规则配置（辉光与面积程度） ===
        self._rule_group = QGroupBox(language_manager.tr("glow_size_config"))
        rule_layout = QVBoxLayout(self._rule_group)
        
        # 规则列表区域
        self.rule_list_widget = QListWidget()
        self.rule_list_widget.setMaximumHeight(200)
        self._defined_rules_label = QLabel(language_manager.tr("defined_rules"))
        rule_layout.addWidget(self._defined_rules_label)
        rule_layout.addWidget(self.rule_list_widget)
        
        # 规则操作按钮
        rule_btn_layout = QHBoxLayout()
        
        self.add_rule_btn = QPushButton(language_manager.tr("add_rule"))
        self.add_rule_btn.clicked.connect(self._show_rule_editor)
        rule_btn_layout.addWidget(self.add_rule_btn)
        
        self.delete_rule_btn = QPushButton(language_manager.tr("delete_rule"))
        self.delete_rule_btn.clicked.connect(self._delete_selected_rule)
        rule_btn_layout.addWidget(self.delete_rule_btn)
        
        rule_btn_layout.addStretch()
        rule_layout.addLayout(rule_btn_layout)
        
        # 规则编辑器面板（默认隐藏）
        self.rule_editor_widget = QWidget()
        self.rule_editor_widget.setVisible(False)
        self._rule_editor_layout = QFormLayout(self.rule_editor_widget)
        
        # 规则类型选择
        self.rule_type_combo = QComboBox()
        self.rule_type_combo.addItems(["范围 [min,max]", "阈值 >=threshold"])
        self.rule_type_combo.currentIndexChanged.connect(self._on_rule_type_changed)
        self._rule_editor_layout.addRow(language_manager.tr("rule_type"), self.rule_type_combo)
        
        # 关联数区间/阈值输入
        range_input_layout = QHBoxLayout()
        
        self.min_conn_input = QSpinBox()
        self.min_conn_input.setRange(0, 9999)
        self.min_conn_input.setValue(0)
        self.min_conn_input.setSuffix(language_manager.tr("connections_unit"))
        range_input_layout.addWidget(QLabel(language_manager.tr("minimum")))
        range_input_layout.addWidget(self.min_conn_input)
        
        self.max_conn_input = QSpinBox()
        self.max_conn_input.setRange(0, 9999)
        self.max_conn_input.setValue(10)
        self.max_conn_input.setSuffix(language_manager.tr("connections_unit"))
        range_input_layout.addWidget(QLabel(language_manager.tr("maximum")))
        range_input_layout.addWidget(self.max_conn_input)
        
        range_input_widget = QWidget()
        range_input_widget.setLayout(range_input_layout)
        self.range_input_container = range_input_widget
        self._rule_editor_layout.addRow(language_manager.tr("connection_range"), self.range_input_container)
        
        # 阈值输入（默认隐藏）
        threshold_input_layout = QHBoxLayout()
        
        self.threshold_input = QSpinBox()
        self.threshold_input.setRange(0, 9999)
        self.threshold_input.setValue(5)
        self.threshold_input.setSuffix(language_manager.tr("connections_unit"))
        threshold_input_layout.addWidget(QLabel(language_manager.tr("threshold_label")))
        threshold_input_layout.addWidget(self.threshold_input)
        threshold_input_layout.addStretch()
        
        threshold_input_widget = QWidget()
        threshold_input_widget.setLayout(threshold_input_layout)
        self.threshold_input_container = threshold_input_widget
        self.threshold_input_container.setVisible(False)
        self._rule_editor_layout.addRow(language_manager.tr("connection_threshold"), self.threshold_input_container)
        
        # 亮度区间输入
        brightness_input_layout = QHBoxLayout()
        
        self.brightness_min_input = QDoubleSpinBox()
        self.brightness_min_input.setRange(0.0, 100.0)
        self.brightness_min_input.setValue(10.0)
        self.brightness_min_input.setSuffix(" %")
        self.brightness_min_input.setSingleStep(5.0)
        brightness_input_layout.addWidget(QLabel(language_manager.tr("darkest_label")))
        brightness_input_layout.addWidget(self.brightness_min_input)
        
        self.brightness_max_input = QDoubleSpinBox()
        self.brightness_max_input.setRange(0.0, 100.0)
        self.brightness_max_input.setValue(30.0)
        self.brightness_max_input.setSuffix(" %")
        self.brightness_max_input.setSingleStep(5.0)
        brightness_input_layout.addWidget(QLabel(language_manager.tr("brightest_label")))
        brightness_input_layout.addWidget(self.brightness_max_input)
        
        brightness_input_widget = QWidget()
        brightness_input_widget.setLayout(brightness_input_layout)
        self._rule_editor_layout.addRow(language_manager.tr("brightness_range"), brightness_input_widget)
        
        # 面积区间输入
        size_input_layout = QHBoxLayout()
        
        self.size_min_input = QDoubleSpinBox()
        self.size_min_input.setRange(0.0, 100.0)
        self.size_min_input.setValue(10.0)
        self.size_min_input.setSuffix(" %")
        self.size_min_input.setSingleStep(5.0)
        size_input_layout.addWidget(QLabel(language_manager.tr("minimum_label")))
        size_input_layout.addWidget(self.size_min_input)
        
        self.size_max_input = QDoubleSpinBox()
        self.size_max_input.setRange(0.0, 100.0)
        self.size_max_input.setValue(30.0)
        self.size_max_input.setSuffix(" %")
        self.size_max_input.setSingleStep(5.0)
        size_input_layout.addWidget(QLabel(language_manager.tr("maximum_label")))
        size_input_layout.addWidget(self.size_max_input)
        
        size_input_widget = QWidget()
        size_input_widget.setLayout(size_input_layout)
        self._rule_editor_layout.addRow(language_manager.tr("size_range"), size_input_widget)
        
        # 编辑器按钮
        editor_btn_layout = QHBoxLayout()
        
        self.save_rule_btn = QPushButton(language_manager.tr("save_rule"))
        self.save_rule_btn.clicked.connect(self._save_current_rule)
        editor_btn_layout.addWidget(self.save_rule_btn)
        
        self.cancel_rule_btn = QPushButton(language_manager.tr("cancel_rule"))
        self.cancel_rule_btn.clicked.connect(self._hide_rule_editor)
        
        editor_btn_layout.addStretch()
        self._rule_editor_layout.addRow("", editor_btn_layout)
        
        rule_layout.addWidget(self.rule_editor_widget)
        
        # 帮助文本
        self._rules_help_label = QLabel(language_manager.tr("rules_help"))
        self._rules_help_label.setStyleSheet(
            "color: #888888; font-size: 12px; margin-top: 8px;"
        )
        self._rules_help_label.setWordWrap(True)
        rule_layout.addWidget(self._rules_help_label)
        
        scroll_layout.addWidget(self._rule_group)
        
        # === Monitor 配置 ===
        self._monitor_group = QGroupBox(language_manager.tr("monitor_config"))
        self._monitor_form = QFormLayout(self._monitor_group)
        
        self.config_check_interval = QSpinBox()
        self.config_check_interval.setRange(1, 300)
        self.config_check_interval.setValue(self.check_interval)
        self._monitor_form.addRow(language_manager.tr("monitor_interval"), self.config_check_interval)
        
        self.config_max_ahead = QSpinBox()
        self.config_max_ahead.setRange(0, 10)
        self.config_max_ahead.setValue(self.max_ahead)
        self._monitor_form.addRow(language_manager.tr("pregenerate_chapters"), self.config_max_ahead)
        
        self.config_min_word = QSpinBox()
        self.config_min_word.setRange(1, 1000)
        self.config_min_word.setValue(self.min_word)
        self._monitor_form.addRow(language_manager.tr("trigger_word_count"), self.config_min_word)
        
        self.config_heartbeat = QSpinBox()
        self.config_heartbeat.setRange(30, 600)
        self.config_heartbeat.setValue(self.heartbeat_timeout)
        self._monitor_form.addRow(language_manager.tr("heartbeat_timeout_label"), self.config_heartbeat)
        
        scroll_layout.addWidget(self._monitor_group)
        
        # === 词频追踪配置 ===
        self._freq_group = QGroupBox(language_manager.tr("freq_track_group"))
        self._freq_form = QFormLayout(self._freq_group)
        
        self.config_freq_min_len = QSpinBox()
        self.config_freq_min_len.setRange(1, 10)
        self.config_freq_min_len.setValue(self.freq_min_len)
        self._freq_form.addRow(language_manager.tr("min_word_length_label"), self.config_freq_min_len)
        
        self.config_freq_min_occ = QSpinBox()
        self.config_freq_min_occ.setRange(1, 20)
        self.config_freq_min_occ.setValue(self.freq_min_occ)
        self._freq_form.addRow(language_manager.tr("min_occurrences_label"), self.config_freq_min_occ)
        
        self.config_freq_inactive = QSpinBox()
        self.config_freq_inactive.setRange(1, 50)
        self.config_freq_inactive.setValue(self.freq_inactive)
        self._freq_form.addRow(language_manager.tr("inactive_chapters_label"), self.config_freq_inactive)
        
        self.config_freq_auto = QCheckBox(language_manager.tr("auto_scan_label"))
        self.config_freq_auto.setChecked(self.freq_auto)
        self._freq_form.addRow("", self.config_freq_auto)
        
        self.config_freq_stopwords = QCheckBox(language_manager.tr("filter_stopwords_label"))
        self.config_freq_stopwords.setChecked(self.freq_stopwords)
        self._freq_form.addRow("", self.config_freq_stopwords)
        
        self.config_freq_keywords_only = QCheckBox(language_manager.tr("keywords_only_label"))
        self.config_freq_keywords_only.setChecked(self.freq_keywords_only)
        self._freq_form.addRow("", self.config_freq_keywords_only)
        
        self.config_freq_stale_ratio = QSpinBox()
        self.config_freq_stale_ratio.setRange(2, 10)
        self.config_freq_stale_ratio.setValue(self.freq_stale_ratio)
        self._freq_form.addRow(language_manager.tr("stale_ratio_label"), self.config_freq_stale_ratio)
        
        self.config_freq_stale_gap = QSpinBox()
        self.config_freq_stale_gap.setRange(1, 20)
        self.config_freq_stale_gap.setValue(self.freq_stale_gap)
        self._freq_form.addRow(language_manager.tr("stale_gap_label"), self.config_freq_stale_gap)
        
        scroll_layout.addWidget(self._freq_group)
        
        # === 格式配置 ===
        self._format_group = QGroupBox(language_manager.tr("format_config"))
        self._format_form = QFormLayout(self._format_group)
        
        self.config_export_format = QLineEdit()
        self.config_export_format.setText(self.export_format)
        self.config_export_format.textChanged.connect(self.update_format_preview)
        self._format_form.addRow(language_manager.tr("export_filename_format"), self.config_export_format)
        
        self.config_export_format_help = QLabel(language_manager.tr("format_help_filename"))
        self.config_export_format_help.setStyleSheet(
            f"color: #888888; font-size: {self.format_help_font_size}px;"
        )
        self.config_export_format_help.setWordWrap(True)
        self._format_form.addRow("", self.config_export_format_help)
        
        self.config_export_format_preview = QLabel("")
        self.config_export_format_preview.setStyleSheet(
            f"color: {self.preview_color}; font-size: {self.preview_font_size}px; font-weight: bold;"
        )
        self._format_form.addRow("", self.config_export_format_preview)
        
        self.config_export_volume_format = QLineEdit()
        self.config_export_volume_format.setText(self.export_volume_format)
        self.config_export_volume_format.textChanged.connect(self.update_format_preview)
        self._format_form.addRow(language_manager.tr("export_volume_format"), self.config_export_volume_format)
        
        self.config_export_volume_help = QLabel(language_manager.tr("format_help_volume"))
        self.config_export_volume_help.setStyleSheet(
            f"color: #888888; font-size: {self.format_help_font_size}px;"
        )
        self.config_export_volume_help.setWordWrap(True)
        self._format_form.addRow("", self.config_export_volume_help)
        
        self.config_export_volume_preview = QLabel("")
        self.config_export_volume_preview.setStyleSheet(
            f"color: {self.preview_color}; font-size: {self.preview_font_size}px; font-weight: bold;"
        )
        self._format_form.addRow("", self.config_export_volume_preview)
        
        self.config_export_chapter_format = QLineEdit()
        self.config_export_chapter_format.setText(self.export_chapter_format)
        self.config_export_chapter_format.textChanged.connect(self.update_format_preview)
        self._format_form.addRow(language_manager.tr("export_chapter_format"), self.config_export_chapter_format)
        
        self.config_export_chapter_help = QLabel(language_manager.tr("format_help_chapter"))
        self.config_export_chapter_help.setStyleSheet(
            f"color: #888888; font-size: {self.format_help_font_size}px;"
        )
        self.config_export_chapter_help.setWordWrap(True)
        self._format_form.addRow("", self.config_export_chapter_help)
        
        self.config_export_chapter_preview = QLabel("")
        self.config_export_chapter_preview.setStyleSheet(
            f"color: {self.preview_color}; font-size: {self.preview_font_size}px; font-weight: bold;"
        )
        self._format_form.addRow("", self.config_export_chapter_preview)

        self.config_volume_folder_format = QLineEdit()
        self.config_volume_folder_format.setText(self.volume_folder_format)
        self.config_volume_folder_format.textChanged.connect(self.update_format_preview)
        self._format_form.addRow(language_manager.tr("volume_folder_format"), self.config_volume_folder_format)

        self.config_volume_folder_help = QLabel(
            "{num}=数字  {cn.up.Volume}=第壹佰伍拾叁卷  {cn.low.Volume}=第一百五十三卷\n"
            "{cn.num.Volume}=第153卷  {en.Volume}=Volume153  {ip.Volume}=一百五十三卷\n"
            "{display:on}=显示格式描述  {display:off}=隐藏格式描述  {title}=标题名"
        )
        self.config_volume_folder_help.setStyleSheet(
            f"color: #888888; font-size: {self.format_help_font_size}px;"
        )
        self.config_volume_folder_help.setWordWrap(True)
        self._format_form.addRow("", self.config_volume_folder_help)

        self.config_volume_folder_preview = QLabel("")
        self.config_volume_folder_preview.setStyleSheet(
            f"color: {self.preview_color}; font-size: {self.preview_font_size}px; font-weight: bold;"
        )
        self._format_form.addRow("", self.config_volume_folder_preview)

        self.config_preview_color = QLineEdit()
        self.config_preview_color.setText(self.preview_color)
        self.config_preview_color.textChanged.connect(self._update_format_preview_style)
        self._format_form.addRow(language_manager.tr("preview_color"), self.config_preview_color)
        
        self.config_preview_font_size = QSpinBox()
        self.config_preview_font_size.setRange(12, 48)
        self.config_preview_font_size.setValue(self.preview_font_size)
        self.config_preview_font_size.valueChanged.connect(self._update_format_preview_style)
        self._format_form.addRow(language_manager.tr("preview_font_size"), self.config_preview_font_size)
        
        self.config_format_help_font = QSpinBox()
        self.config_format_help_font.setRange(14, 36)
        self.config_format_help_font.setValue(self.format_help_font_size)
        self.config_format_help_font.valueChanged.connect(self._update_format_help_style)
        self._format_form.addRow(language_manager.tr("format_help_font_label"), self.config_format_help_font)
        
        scroll_layout.addWidget(self._format_group)

        # === 写作统计配置 ===
        self._stats_group = QGroupBox(language_manager.tr("writing_goal_config"))
        self._stats_form = QFormLayout(self._stats_group)
        self.config_volume_target = QSpinBox()
        self.config_volume_target.setRange(1000, 10000000)
        self.config_volume_target.setSingleStep(10000)
        self.config_volume_target.setValue(
            int(ConfigManager.get('Stats', 'volume_target_words', fallback='100000'))
        )
        self.config_volume_target.setSuffix(language_manager.tr("word_unit"))
        self._stats_form.addRow(language_manager.tr("volume_target_words"), self.config_volume_target)

        self.config_daily_target = QSpinBox()
        self.config_daily_target.setRange(100, 100000)
        self.config_daily_target.setSingleStep(500)
        self.config_daily_target.setValue(
            int(ConfigManager.get('Stats', 'daily_target_words', fallback='2000'))
        )
        self.config_daily_target.setSuffix(language_manager.tr("word_unit"))
        self._stats_form.addRow(language_manager.tr("daily_target_words"), self.config_daily_target)

        scroll_layout.addWidget(self._stats_group)

        # === 语言设置 ===
        self._lang_group = QGroupBox(language_manager.tr("language_config"))
        self._lang_form = QFormLayout(self._lang_group)

        self.config_language = QComboBox()
        for lang_code in language_manager.get_available_languages():
            lang_name = {"zh_CN": "简体中文", "en_US": "English", "ja_JP": "日本語"}.get(lang_code, lang_code)
            self.config_language.addItem(lang_name, lang_code)
        current_lang = language_manager.get_current_language()
        for i in range(self.config_language.count()):
            if self.config_language.itemData(i) == current_lang:
                self.config_language.setCurrentIndex(i)
                break
        self._lang_form.addRow(language_manager.tr("select_language"), self.config_language)

        self._lang_tip = QLabel(language_manager.tr("tip_change_language"))
        self._lang_tip.setStyleSheet("color: #888888; font-size: 12px;")
        self._lang_tip.setWordWrap(True)
        self._lang_form.addRow("", self._lang_tip)

        scroll_layout.addWidget(self._lang_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        # ====== 操作按钮 ======
        btn_layout = QHBoxLayout()
        
        self._config_apply_btn = QPushButton(language_manager.tr("save_and_apply"))
        self._config_apply_btn.clicked.connect(self.save_and_apply_config)
        btn_layout.addWidget(self._config_apply_btn)
        
        reset_btn = QPushButton(language_manager.tr("reset_default_btn"))
        self._reset_btn = reset_btn
        reset_btn.clicked.connect(self._reset_config_default)
        btn_layout.addWidget(reset_btn)
        
        main_layout.addLayout(btn_layout)
        
        # 初始化预览
        self.update_format_preview()
        self._update_format_preview_style()
        self._update_format_help_style()
        
        # 加载已保存的自定义规则
        self.load_custom_rules_from_config()
        
        logger.debug(f"[{self.tab_name}] UI构建完成")
    
    def _load_data(self):
        """加载数据"""
        pass
    
    # ====== 配置写入方法 ======
    
    def _write_config_to_file(self):
        """将当前UI配置写入文件"""
        # UI 配置
        ConfigManager.set('UI', 'base_font_size', str(self.config_base_font.value()))
        ConfigManager.set('UI', 'base_title_size', str(self.config_title_font.value()))
        ConfigManager.set('UI', 'log_font_size', str(self.config_log_font.value()))
        ConfigManager.set('UI', 'line_height', str(self.config_line_height.value()))
        ConfigManager.set('UI', 'initial_width', str(self.config_initial_width.value()))
        ConfigManager.set('UI', 'initial_height', str(self.config_initial_height.value()))
        ConfigManager.set('UI', 'graph_font_size', str(self.config_graph_font.value()))
        ConfigManager.set('UI', 'kwlist_font_family', self.config_kwlist_family.text())
        ConfigManager.set('UI', 'theme', self.config_theme.currentData())
        ConfigManager.set('UI', 'kw_h1_size', str(self.config_kw_h1_size.value()))
        ConfigManager.set('UI', 'kw_h1_color', self.config_kw_h1_color.text())
        ConfigManager.set('UI', 'kw_h2_size', str(self.config_kw_h2_size.value()))
        ConfigManager.set('UI', 'kw_h2_color', self.config_kw_h2_color.text())
        ConfigManager.set('UI', 'kw_body_size', str(self.config_kw_body_size.value()))
        ConfigManager.set('UI', 'kw_body_color', self.config_kw_body_color.text())
        ConfigManager.set('UI', 'kw_link_size', str(self.config_kw_link_size.value()))
        ConfigManager.set('UI', 'kw_link_color', self.config_kw_link_color.text())
        ConfigManager.set('UI', 'link_italic', '1' if self.config_link_italic.isChecked() else '0')
        ConfigManager.set('UI', 'enable_font_scaling', '1' if self.config_enable_font_scaling.isChecked() else '0')
        ConfigManager.set('UI', 'enable_animations', '1' if self.config_enable_animations.isChecked() else '0')
        ConfigManager.set('UI', 'enable_acrylic', '1' if self.config_enable_acrylic.isChecked() else '0')
        ConfigManager.set('UI', 'scaling_reference_width', str(self.config_scaling_reference_width.value()))
        ConfigManager.set('UI', 'scaling_min', str(self.config_scaling_min.value()))
        ConfigManager.set('UI', 'scaling_max', str(self.config_scaling_max.value()))
        ConfigManager.set('UI', 'link_bold', '1' if self.config_link_bold.isChecked() else '0')
        ConfigManager.set('UI', 'bg_color', self.config_bg_color.text())
        ConfigManager.set('UI', 'fg_color', self.config_fg_color.text())
        ConfigManager.set('UI', 'border_color', self.config_border_color.text())
        ConfigManager.set('UI', 'error_color', self.config_error_color.text())
        ConfigManager.set('UI', 'warn_color', self.config_warn_color.text())
        ConfigManager.set('UI', 'btn_bg_color', self.config_btn_bg_color.text())
        ConfigManager.set('UI', 'btn_hover_color', self.config_btn_hover_color.text())
        ConfigManager.set('UI', 'input_bg_color', self.config_input_bg_color.text())
        
        # Monitor 配置
        ConfigManager.set('Monitor', 'check_interval', str(self.config_check_interval.value()))
        ConfigManager.set('Monitor', 'max_ahead_chapters', str(self.config_max_ahead.value()))
        ConfigManager.set('Monitor', 'min_word_count', str(self.config_min_word.value()))
        ConfigManager.set('Monitor', 'novel_dir', self.config_novel_dir.text())
        ConfigManager.set('Monitor', 'heartbeat_timeout', str(self.config_heartbeat.value()))
        
        # Graph 配置
        ConfigManager.set('Graph', 'layout_ideal_length', str(self.config_layout_ideal.value()))
        ConfigManager.set('Graph', 'node_limit', str(self.config_node_limit.value()))
        ConfigManager.set('Graph', 'auto_save_layout', '1' if self.config_auto_layout.isChecked() else '0')
        ConfigManager.set('Theme', 'edge_width', str(self.config_edge_width.value()))
        ConfigManager.set('Theme', 'graph_bg_color', self.config_graph_bg.text())
        ConfigManager.set('Theme', 'graph_bg_follow_theme', '1' if self.config_graph_bg_follow.isChecked() else '0')
        ConfigManager.set('Theme', 'graph_grid_color', self.config_graph_grid_color.text())
        ConfigManager.set('Graph', 'node_min_size', str(self.config_node_min_size.value()))
        ConfigManager.set('Graph', 'node_max_size', str(self.config_node_max_size.value()))
        ConfigManager.set('Graph', 'node_min_brightness', str(self.config_node_min_brightness.value()))
        ConfigManager.set('Graph', 'node_max_brightness', str(self.config_node_max_brightness.value()))
        ConfigManager.set('Graph', 'enable_glow', '1' if self.config_enable_glow.isChecked() else '0')
        ConfigManager.set('Graph', 'enable_size_sort', '1' if self.config_enable_size_sort.isChecked() else '0')
        ConfigManager.set('Graph', 'enable_brightness_sort', '1' if self.config_enable_brightness_sort.isChecked() else '0')
        
        # Frequency 配置
        ConfigManager.set('Frequency', 'min_word_length', str(self.config_freq_min_len.value()))
        ConfigManager.set('Frequency', 'min_occurrences', str(self.config_freq_min_occ.value()))
        ConfigManager.set('Frequency', 'inactive_chapters', str(self.config_freq_inactive.value()))
        ConfigManager.set('Frequency', 'auto_scan', '1' if self.config_freq_auto.isChecked() else '0')
        ConfigManager.set('Frequency', 'filter_stopwords', '1' if self.config_freq_stopwords.isChecked() else '0')
        ConfigManager.set('Frequency', 'keywords_only', '1' if self.config_freq_keywords_only.isChecked() else '0')
        ConfigManager.set('Frequency', 'stale_ratio', str(self.config_freq_stale_ratio.value()))
        ConfigManager.set('Frequency', 'stale_gap', str(self.config_freq_stale_gap.value()))
        
        # Format 配置
        ConfigManager.set('Format', 'export_format', self.config_export_format.text())
        ConfigManager.set('Format', 'export_volume_format', self.config_export_volume_format.text())
        ConfigManager.set('Format', 'export_chapter_format', self.config_export_chapter_format.text())
        ConfigManager.set('Format', 'volume_folder_format', self.config_volume_folder_format.text())
        ConfigManager.set('Format', 'preview_color', self.config_preview_color.text())
        ConfigManager.set('Format', 'preview_font_size', str(self.config_preview_font_size.value()))
        ConfigManager.set('Format', 'format_help_font_size', str(self.config_format_help_font.value()))
        
        # Stats 配置
        ConfigManager.set('Stats', 'volume_target_words', str(self.config_volume_target.value()))
        ConfigManager.set('Stats', 'daily_target_words', str(self.config_daily_target.value()))
        
        # 语言配置
        selected_lang = self.config_language.currentData()
        language_manager.set_current_language(selected_lang)
        
        # 保存自定义规则
        import json
        rules = self.get_current_custom_rules()
        ConfigManager.set('Graph', 'custom_rules', json.dumps(rules))
    
    # ====== 配置操作方法 ======
    
    def _select_config_dir(self):
        """选择小说目录"""
        from PyQt5.QtWidgets import QFileDialog
        
        dir_path = QFileDialog.getExistingDirectory(
            self, 
            language_manager.tr("select_directory"),
            get_novel_dir() or ""
        )
        if dir_path:
            self.config_novel_dir.setText(dir_path)
    
    def save_config(self):
        """保存配置"""
        try:
            self._write_config_to_file()
            file_manager._load_custom_formats()
            
            self.config_saved.emit()
            QMessageBox.information(
                self, 
                language_manager.tr("success"), 
                language_manager.tr("config_saved_applied")
            )
            logger.info("Configuration saved")
        except Exception as e:
            QMessageBox.critical(
                self, 
                language_manager.tr("error"),
                f"{language_manager.tr('save_config_failed')}: {str(e)}"
            )
            logger.error(f"保存配置失败: {e}", exc_info=True)
    
    def save_and_apply_config(self):
        """保存并应用配置"""
        try:
            old_lang = language_manager.get_current_language()
            self._write_config_to_file()
            file_manager._load_custom_formats()
            
            self.config_applied.emit()
            
            self.update_format_preview()
            self._update_format_preview_style()
            self._update_format_help_style()
            
            QMessageBox.information(
                self, 
                language_manager.tr("success"), 
                language_manager.tr("config_saved_applied")
            )
            logger.info("Configuration saved and applied")
        except Exception as e:
            QMessageBox.critical(
                self, 
                language_manager.tr("error"),
                f"{language_manager.tr('save_apply_failed')}: {str(e)}"
            )
            logger.error(f"Save and apply failed: {e}", exc_info=True)
    
    def retranslate_ui(self):
        lm = language_manager.tr
        
        self._config_title_label.setText(lm("parameter_config"))
        
        self._dir_group.setTitle(lm("novel_dir_label"))
        self._ui_group.setTitle(lm("ui_size_config"))
        self._tab_group.setTitle(lm("tab_config"))
        self._kw_group.setTitle(lm("keyword_config"))
        self._color_group.setTitle(lm("color_scheme_group"))
        self._graph_group.setTitle(lm("graph_config"))
        self._rule_group.setTitle(lm("glow_size_config"))
        self._monitor_group.setTitle(lm("monitor_config"))
        self._freq_group.setTitle(lm("freq_track_group"))
        self._format_group.setTitle(lm("format_config"))
        self._stats_group.setTitle(lm("writing_goal_config"))
        self._lang_group.setTitle(lm("language_config"))
        
        self._scaling_label.setText(lm("font_scaling_label"))
        self._visual_label.setText(lm("node_visual_effects"))
        self._defined_rules_label.setText(lm("defined_rules"))
        self._rules_help_label.setText(lm("rules_help"))
        self._lang_tip.setText(lm("tip_change_language"))
        
        self.config_novel_dir_btn.setText(lm("select_directory"))
        self._config_apply_btn.setText(lm("save_and_apply"))
        self._reset_btn.setText(lm("reset_default_btn"))
        self.add_rule_btn.setText(lm("add_rule"))
        self.delete_rule_btn.setText(lm("delete_rule"))
        self.save_rule_btn.setText(lm("save_rule"))
        self.cancel_rule_btn.setText(lm("cancel_rule"))
        
        self.config_enable_animations.setText(lm("enable_animations_label"))
        self.config_enable_acrylic.setText(lm("enable_acrylic"))
        self.config_enable_font_scaling.setText(lm("enable_font_scaling_label"))
        self.config_link_italic.setText(lm("link_italic"))
        self.config_link_bold.setText(lm("link_bold"))
        self.config_graph_bg_follow.setText(lm("follow_theme"))
        self.config_auto_layout.setText(lm("auto_save_layout"))
        self.config_enable_glow.setText(lm("enable_glow"))
        self.config_enable_size_sort.setText(lm("sort_by_connection_size"))
        self.config_enable_brightness_sort.setText(lm("sort_by_connection_brightness"))
        self.config_legend_visible.setText(lm("show"))
        self.config_freq_auto.setText(lm("auto_scan_label"))
        self.config_freq_stopwords.setText(lm("filter_stopwords_label"))
        self.config_freq_keywords_only.setText(lm("keywords_only_label"))
        
        self.config_enable_animations.setToolTip(lm("animations_tooltip"))
        self.config_enable_acrylic.setToolTip(lm("acrylic_tooltip"))
        self.config_enable_font_scaling.setToolTip(lm("font_scaling_tooltip"))
        self.config_enable_glow.setToolTip(lm("glow_tooltip"))
        self.config_enable_size_sort.setToolTip(lm("size_sort_tooltip"))
        self.config_enable_brightness_sort.setToolTip(lm("brightness_sort_tooltip"))
        self.config_theme.setToolTip(lm("theme_tooltip"))
        
        self.config_base_font.setSuffix(lm("font_unit"))
        self.config_title_font.setSuffix(lm("font_unit"))
        self.config_log_font.setSuffix(lm("font_unit"))
        self.config_graph_font.setSuffix(lm("font_unit"))
        self.config_line_height.setSuffix(lm("line_height_unit"))
        self.config_initial_width.setSuffix(lm("pixel_unit"))
        self.config_initial_height.setSuffix(lm("pixel_unit"))
        self.config_scaling_reference_width.setSuffix(lm("pixel_unit"))
        self.config_volume_target.setSuffix(lm("word_unit"))
        self.config_daily_target.setSuffix(lm("word_unit"))
        self.config_check_interval.setSuffix(lm("second_unit"))
        self.config_max_ahead.setSuffix(lm("chapter_unit"))
        self.config_min_word.setSuffix(lm("word_unit"))
        self.config_heartbeat.setSuffix(lm("second_unit"))
        self.min_conn_input.setSuffix(lm("connections_unit"))
        self.max_conn_input.setSuffix(lm("connections_unit"))
        self.threshold_input.setSuffix(lm("connections_unit"))
        
        for form in [self._ui_form, self._kw_form, self._color_form, self._graph_form,
                     self._monitor_form, self._freq_form, self._format_form,
                     self._stats_form, self._lang_form, self._tab_form]:
            if form is None:
                continue
            label_map = self._get_form_label_map(form)
            for tr_key, field_widget in label_map.items():
                label = form.labelForField(field_widget)
                if label:
                    label.setText(lm(tr_key))
        
        current_data = self.config_language.currentData()
        self.config_language.clear()
        for lang_code in language_manager.get_available_languages():
            lang_name = {"zh_CN": "简体中文", "en_US": "English", "ja_JP": "日本語"}.get(lang_code, lang_code)
            self.config_language.addItem(lang_name, lang_code)
        for i in range(self.config_language.count()):
            if self.config_language.itemData(i) == current_data:
                self.config_language.setCurrentIndex(i)
                break
    
    def _get_form_label_map(self, form):
        mapping = {}
        widget_key_map = {
            # _ui_form
            self.config_base_font: "base_font_size",
            self.config_title_font: "title_font_size",
            self.config_log_font: "log_font_size",
            self.config_graph_font: "graph_font_size_label",
            self.config_line_height: "line_height_label",
            self.config_kwlist_family: "font_family_label",
            self.config_initial_width: "initial_width",
            self.config_initial_height: "initial_height",
            self.config_theme: "theme_label",
            self.config_scaling_reference_width: "reference_width",
            # _kw_form
            self.config_kw_h1_size: "h1_font_size",
            self.config_kw_h2_size: "h2_font_size",
            self.config_kw_h1_color: "h1_color",
            self.config_kw_h2_color: "h2_color",
            self.config_kw_body_size: "body_font_size",
            self.config_kw_body_color: "body_color",
            self.config_kw_link_size: "link_font_size",
            self.config_kw_link_color: "link_color",
            # _color_form
            self.config_bg_color: "bg_color_label",
            self.config_fg_color: "fg_color_label",
            self.config_border_color: "border_color_label",
            self.config_error_color: "error_color_label",
            self.config_warn_color: "warn_color_label",
            self.config_btn_bg_color: "btn_bg_color_label",
            self.config_btn_hover_color: "btn_hover_color_label",
            self.config_input_bg_color: "input_bg_color",
            # _monitor_form
            self.config_check_interval: "monitor_interval",
            self.config_max_ahead: "pregenerate_chapters",
            self.config_min_word: "trigger_word_count",
            self.config_heartbeat: "heartbeat_timeout_label",
            # _freq_form
            self.config_freq_min_len: "min_word_length_label",
            self.config_freq_min_occ: "min_occurrences_label",
            self.config_freq_inactive: "inactive_chapters_label",
            self.config_freq_stale_ratio: "stale_ratio_label",
            self.config_freq_stale_gap: "stale_gap_label",
            # _graph_form
            self._bg_row: "graph_bg_color",
            self.config_graph_grid_color: "grid_color_label",
            self.config_edge_width: "edge_width_label",
            self.config_layout_ideal: "layout_ideal_distance",
            self.config_node_limit: "max_nodes",
            self.config_overlay_pos: "legend_position",
            self.config_legend_visible: "legend_visible",
            # _format_form
            self.config_export_format: "export_filename_format",
            self.config_export_volume_format: "export_volume_format",
            self.config_export_chapter_format: "export_chapter_format",
            self.config_volume_folder_format: "volume_folder_format",
            self.config_preview_color: "preview_color",
            self.config_preview_font_size: "preview_font_size",
            self.config_format_help_font: "format_help_font_label",
            # _stats_form
            self.config_volume_target: "volume_target_words",
            self.config_daily_target: "daily_target_words",
            # _lang_form
            self.config_language: "select_language",
        }
        for i in range(form.count()):
            field_item = form.itemAt(i, QFormLayout.FieldRole)
            if field_item:
                widget = field_item.widget()
                if widget and widget in widget_key_map:
                    mapping[widget_key_map[widget]] = widget
        return mapping
    
    def reload_config(self):
        """重新加载配置"""
        self._load_all_config_values()
        
        # 更新所有控件的值
        self.config_base_font.setValue(self.base_font_size)
        self.config_title_font.setValue(self.base_title_size)
        self.config_log_font.setValue(self.log_font_size)
        self.config_graph_font.setValue(self.graph_font_size)
        self.config_line_height.setValue(self.line_height)
        self.config_initial_width.setValue(self.initial_width)
        self.config_initial_height.setValue(self.initial_height)
        self.config_kwlist_family.setText(self.kwlist_font_family)
        self.config_kw_h1_size.setValue(self.kw_h1_size)
        self.config_kw_h1_color.setText(self.kw_h1_color)
        self.config_kw_h2_size.setValue(self.kw_h2_size)
        self.config_kw_h2_color.setText(self.kw_h2_color)
        self.config_kw_body_size.setValue(self.kw_body_size)
        self.config_kw_body_color.setText(self.kw_body_color)
        self.config_kw_link_size.setValue(self.kw_link_size)
        self.config_kw_link_color.setText(self.kw_link_color)
        self.config_enable_font_scaling.setChecked(self.enable_font_scaling)
        self.config_scaling_reference_width.setValue(self.scaling_reference_width)
        self.config_scaling_min.setValue(self.scaling_min)
        self.config_scaling_max.setValue(self.scaling_max)
        self.config_link_italic.setChecked(self.link_italic)
        self.config_link_bold.setChecked(self.link_bold)
        self.config_bg_color.setText(self.bg_color)
        self.config_fg_color.setText(self.fg_color)
        self.config_border_color.setText(self.border_color)
        self.config_error_color.setText(self.error_color)
        self.config_warn_color.setText(self.warn_color)
        self.config_btn_bg_color.setText(self.btn_bg_color)
        self.config_btn_hover_color.setText(self.btn_hover_color)
        self.config_input_bg_color.setText(self.input_bg_color)
        self.config_graph_bg.setText(self.graph_bg)
        self.config_graph_grid_color.setText(self.grid_color)
        self.config_edge_width.setValue(self.edge_width)
        self.config_layout_ideal.setValue(self.layout_ideal)
        self.config_node_limit.setValue(self.node_limit)
        self.config_enable_glow.setChecked(self.enable_glow)
        self.config_enable_size_sort.setChecked(self.enable_size_sort)
        self.config_enable_brightness_sort.setChecked(self.enable_brightness_sort)
        self.config_export_format.setText(self.export_format)
        self.config_export_volume_format.setText(self.export_volume_format)
        self.config_export_chapter_format.setText(self.export_chapter_format)
        self.config_volume_folder_format.setText(self.volume_folder_format)        
        self.config_preview_color.setText(self.preview_color)
        self.config_preview_font_size.setValue(self.preview_font_size)
        
        # 语言配置
        current_lang = language_manager.get_current_language()
        for i in range(self.config_language.count()):
            if self.config_language.itemData(i) == current_lang:
                self.config_language.setCurrentIndex(i)
                break
        
        file_manager._load_custom_formats()
        self.update_format_preview()
        self._update_format_preview_style()
        self._update_format_help_style()
    
    def _reset_config_default(self):
        """恢复默认配置"""
        reply = QMessageBox.question(
            self, language_manager.tr("confirm"),
            language_manager.tr("reset_config_confirm"),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        # 设置默认值 (Fluent 主题)
        self.config_bg_color.setText('#F8F9FA')
        self.config_fg_color.setText('#212529')
        self.config_border_color.setText('#DEE2E6')
        self.config_error_color.setText('#D13438')
        self.config_warn_color.setText('#FF8C00')
        self.config_btn_bg_color.setText('#0078D4')
        self.config_btn_hover_color.setText('#106EBE')
        self.config_input_bg_color.setText('#FFFFFF')
        self.config_base_font.setValue(14)
        self.config_title_font.setValue(16)
        self.config_log_font.setValue(12)
        self.config_line_height.setValue(1.5)
        self.config_graph_font.setValue(12)
        self.config_kw_h1_size.setValue(20)
        self.config_kw_h1_color.setText('#0078D4')
        self.config_kw_h2_size.setValue(18)
        self.config_kw_h2_color.setText('#107C10')
        self.config_kw_body_size.setValue(14)
        self.config_kw_body_color.setText('#606060')
        self.config_kw_link_size.setValue(14)
        self.config_kw_link_color.setText('#0078D4')
        self.config_kwlist_family.setText('Microsoft YaHei UI')
        self.config_enable_font_scaling.setChecked(True)
        self.config_scaling_reference_width.setValue(1570)
        self.config_scaling_min.setValue(0.8)
        self.config_scaling_max.setValue(1.5)
        self.config_graph_bg.setText('#F8F9FA')
        self.config_graph_grid_color.setText('#E9ECEF')
        self.config_layout_ideal.setValue(200)
        self.config_node_limit.setValue(200)
        self.config_edge_width.setValue(3)
        self.config_freq_min_len.setValue(2)
        self.config_freq_min_occ.setValue(3)
        self.config_freq_inactive.setValue(3)
        self.config_auto_layout.setChecked(True)
        self.config_freq_auto.setChecked(True)
        self.config_enable_glow.setChecked(True)
        self.config_enable_size_sort.setChecked(True)
        self.config_enable_brightness_sort.setChecked(True)
        
        self._write_config_to_file()
        self.reload_config()
        
        # 发出信号通知主窗口
        self.config_applied.emit()
        
        QMessageBox.information(self, language_manager.tr("ok"), language_manager.tr("reset_config_done"))
    
    # ====== 格式预览相关方法 ======
    
    def update_format_preview(self):
        """更新格式预览"""
        filename_fmt = self.config_export_format.text().strip()
        if filename_fmt:
            try:
                preview = file_manager._format_chapter(filename_fmt, 3, "name")
                self.config_export_format_preview.setText(
                    language_manager.tr("preview_text") + preview
                )
            except Exception:
                self.config_export_format_preview.setText(
                    language_manager.tr("format_error_text")
                )
        else:
            default_fmt = "{num}{cn.low.Chapter}_{title}"
            try:
                preview = file_manager._format_chapter(default_fmt, 3, "name")
                self.config_export_format_preview.setText(
                    language_manager.tr("default_text") + preview
                )
            except Exception:
                self.config_export_format_preview.setText("")
        
        vol_fmt = self.config_export_volume_format.text().strip()
        if vol_fmt:
            try:
                preview = file_manager._format_export(vol_fmt, 1, "潜龙在渊", 37523)
                self.config_export_volume_preview.setText(
                    language_manager.tr("preview_text") + preview
                )
            except Exception:
                self.config_export_volume_preview.setText(
                    language_manager.tr("format_error_text")
                )
        else:
            self.config_export_volume_preview.setText("")
        
        chapter_fmt = self.config_export_chapter_format.text().strip()
        if chapter_fmt:
            try:
                preview = file_manager._format_export(chapter_fmt, 3, "回家")
                self.config_export_chapter_preview.setText(
                    language_manager.tr("preview_text") + preview
                )
            except Exception:
                self.config_export_chapter_preview.setText(
                    language_manager.tr("format_error_text")
                )
        else:
            self.config_export_chapter_preview.setText("")
        
        vol_folder_fmt = self.config_volume_folder_format.text().strip()
        if vol_folder_fmt:
            try:
                from datetime import datetime
                preview = vol_folder_fmt
                preview = preview.replace('{num}', '1')
                preview = preview.replace('{cn.up.Volume}', '第壹卷')
                preview = preview.replace('{cn.low.Volume}', '第一卷')
                preview = preview.replace('{cn.num.Volume}', '第1卷')
                preview = preview.replace('{en.Volume}', 'Volume1')
                preview = preview.replace('{ip.Volume}', '一卷')
                preview = preview.replace('{title}', '标题')
                display_off = '{display:off}' in preview
                preview = preview.replace('{display:on}', '')
                preview = preview.replace('{display:off}', '')
                if not display_off:
                    preview = f"1{preview}_title[new_{int(datetime.now().timestamp())}]"
                else:
                    preview = f"1{preview}"
                self.config_volume_folder_preview.setText(
                    language_manager.tr("preview_text") + preview
                )
            except Exception:
                self.config_volume_folder_preview.setText(
                    language_manager.tr("format_error_text")
                )
        else:
            self.config_volume_folder_preview.setText("")
    
    def _update_format_preview_style(self):
        """更新格式预览样式"""
        color = self.config_preview_color.text().strip() or "#FFFFFF"
        font_size = self.config_preview_font_size.value()
        style = f"color: {color}; font-size: {font_size}px; font-weight: bold;"
        self.config_export_format_preview.setStyleSheet(style)
        self.config_export_volume_preview.setStyleSheet(style)
        self.config_export_chapter_preview.setStyleSheet(style)
        self.config_volume_folder_preview.setStyleSheet(style)
    
    def _update_format_help_style(self):
        """更新帮助文本样式"""
        fs = self.config_format_help_font.value()
        style = f"color: #888888; font-size: {fs}px;"
        self.config_export_format_help.setStyleSheet(style)
        self.config_export_volume_help.setStyleSheet(style)
        self.config_export_chapter_help.setStyleSheet(style)
        self.config_volume_folder_help.setStyleSheet(style)
    
    # ====== 网络图配置回调方法 ======
    
    def _on_overlay_pos_changed(self):
        """覆盖层位置改变回调"""
        pos = self.config_overlay_pos.currentData()
        ConfigManager.set('UI', 'overlay_position', pos)
        self.overlay_pos_changed.emit(pos)
    
    def _on_legend_config_changed(self):
        """图例配置改变回调"""
        visible = self.config_legend_visible.isChecked()
        font_name = self.config_legend_font.currentText()
        font_size = self.config_legend_size.value()
        
        ConfigManager.set('UI', 'legend_visible', '1' if visible else '0')
        ConfigManager.set('UI', 'legend_font', font_name)
        ConfigManager.set('UI', 'legend_font_size', str(font_size))
        
        self.legend_config_changed.emit(visible, font_name, font_size)
    
    def _on_node_visual_config_changed(self):
        """节点视觉配置改变回调"""
        min_size = self.config_node_min_size.value()
        max_size = self.config_node_max_size.value()
        min_brightness = self.config_node_min_brightness.value()
        max_brightness = self.config_node_max_brightness.value()
        
        ConfigManager.set('Graph', 'node_min_size', str(min_size))
        ConfigManager.set('Graph', 'node_max_size', str(max_size))
        ConfigManager.set('Graph', 'node_min_brightness', str(min_brightness))
        ConfigManager.set('Graph', 'node_max_brightness', str(max_brightness))
        
        # 节点视觉效果差异化配置
        ConfigManager.set('Graph', 'enable_glow', '1' if self.config_enable_glow.isChecked() else '0')
        ConfigManager.set('Graph', 'enable_size_sort', '1' if self.config_enable_size_sort.isChecked() else '0')
    
    def _on_connect_btn_config_changed(self):
        """连接按钮配置改变回调"""
        size = self.config_connect_btn_size.value()
        color = self.config_connect_btn_color.text().strip()
        
        ConfigManager.set('UI', 'connect_btn_size', str(size))
        ConfigManager.set('UI', 'connect_btn_color', color)
    
    def _on_glow_config_changed(self, state):
        """辉光效果配置改变回调"""
        enabled = state == Qt.Checked
        ConfigManager.set('Graph', 'enable_glow', '1' if enabled else '0')
        
        # 发出信号通知 keyword_tab 更新辉光设置
        self.glow_config_changed.emit(enabled)
    
    def _on_size_sort_config_changed(self, state):
        """面积排序配置改变回调"""
        enabled = state == Qt.Checked
        ConfigManager.set('Graph', 'enable_size_sort', '1' if enabled else '0')
        
        # 发出信号通知 network_graph 更新节点大小计算方式
        self.size_sort_config_changed.emit(enabled)
    
    def _on_brightness_sort_config_changed(self, state):
        """亮度排序配置改变回调"""
        enabled = state == Qt.Checked
        ConfigManager.set('Graph', 'enable_brightness_sort', '1' if enabled else '0')
        
        # 发出信号通知 network_graph 更新节点亮度计算方式
        self.brightness_sort_config_changed.emit(enabled)
    
    # ====== 自定义规则管理方法 ======
    
    def _show_rule_editor(self):
        """显示规则编辑器面板"""
        self.rule_editor_widget.setVisible(True)
        self.add_rule_btn.setEnabled(False)
        self._reset_rule_editor_inputs()
        
        # 滚动到编辑器位置
        scroll = self.findChild(QScrollArea)
        if scroll:
            scroll.ensureWidgetVisible(self.rule_editor_widget)
    
    def _hide_rule_editor(self):
        """隐藏规则编辑器面板"""
        self.rule_editor_widget.setVisible(False)
        self.add_rule_btn.setEnabled(True)
        self._reset_rule_editor_inputs()
    
    def _reset_rule_editor_inputs(self):
        """重置编辑器输入框的值"""
        self.rule_type_combo.setCurrentIndex(0)
        self.min_conn_input.setValue(0)
        self.max_conn_input.setValue(10)
        self.threshold_input.setValue(5)
        self.brightness_min_input.setValue(10.0)
        self.brightness_max_input.setValue(30.0)
        self.size_min_input.setValue(10.0)
        self.size_max_input.setValue(30.0)
        self._on_rule_type_changed(0)
    
    def _on_rule_type_changed(self, index):
        """规则类型改变回调"""
        if index == 0:  # 范围模式
            self.range_input_container.setVisible(True)
            self.threshold_input_container.setVisible(False)
        else:  # 阈值模式
            self.range_input_container.setVisible(False)
            self.threshold_input_container.setVisible(True)
    
    def _save_current_rule(self):
        """保存当前编辑的规则"""
        try:
            rule = {}
            
            # 获取规则类型
            rule_type_index = self.rule_type_combo.currentIndex()
            if rule_type_index == 0:  # 范围模式
                rule['type'] = 'range'
                min_conn = self.min_conn_input.value()
                max_conn = self.max_conn_input.value()
                
                # 验证区间有效性
                if min_conn > max_conn:
                    QMessageBox.warning(
                        self, language_manager.tr("input_error"),
                        language_manager.tr("range_min_max_error")
                    )
                    return
                
                rule['min_conn'] = min_conn
                rule['max_conn'] = max_conn
                
                # 检查是否与现有规则冲突
                for i in range(self.rule_list_widget.count()):
                    existing_rule = self.rule_list_widget.item(i).data(Qt.UserRole)
                    if existing_rule and existing_rule.get('type') == 'range':
                        existing_min = existing_rule.get('min_conn', 0)
                        existing_max = existing_rule.get('max_conn', 99999)
                        
                        # 检查区间重叠（不允许）
                        if not (max_conn < existing_min or min_conn > existing_max):
                            QMessageBox.warning(
                                self, language_manager.tr("rule_conflict"),
                                f"{language_manager.tr('range_rule_conflict_error')} [{min_conn}, {max_conn}] "
                                f"[{existing_min}, {existing_max}]"
                            )
                            return
                
            else:  # 阈值模式
                rule['type'] = 'threshold'
                threshold = self.threshold_input.value()
                rule['threshold'] = threshold
                
                # 检查是否与现有阈值规则冲突
                for i in range(self.rule_list_widget.count()):
                    existing_rule = self.rule_list_widget.item(i).data(Qt.UserRole)
                    if existing_rule and existing_rule.get('type') == 'threshold':
                        existing_threshold = existing_rule.get('threshold', 0)
                        if threshold == existing_threshold:
                            QMessageBox.warning(
                                self, language_manager.tr("rule_conflict"),
                                f"{language_manager.tr('threshold_exists_error')} {threshold}"
                            )
                            return
            
            # 获取亮度和面积因子
            brightness_min = self.brightness_min_input.value() / 100.0
            brightness_max = self.brightness_max_input.value() / 100.0
            size_min = self.size_min_input.value() / 100.0
            size_max = self.size_max_input.value() / 100.0
            
            # 验证范围有效性
            if brightness_min > brightness_max or size_min > size_max:
                QMessageBox.warning(
                    self, language_manager.tr("input_error"),
                    language_manager.tr("brightness_range_error")
                )
                return
            
            rule['brightness_factor'] = (brightness_min + brightness_max) / 2
            rule['size_factor'] = (size_min + size_max) / 2
            
            # 添加到列表
            display_text = self._format_rule_display_text(rule)
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, rule)
            self.rule_list_widget.addItem(item)
            
            # 隐藏编辑器
            self._hide_rule_editor()
            
            # 立即应用规则到网络图
            self._apply_rules_to_network_graph()
            
            logger.info(f"已添加自定义规则: {display_text}")
            
        except Exception as e:
            QMessageBox.critical(
                self, language_manager.tr("error"),
                f"{language_manager.tr('save_rule_failed')}: {str(e)}"
            )
            logger.error(f"保存自定义规则失败: {e}", exc_info=True)
    
    def _delete_selected_rule(self):
        """删除选中的规则"""
        current_item = self.rule_list_widget.currentItem()
        if current_item:
            reply = QMessageBox.question(
                self, language_manager.tr("confirm_delete"),
                language_manager.tr("confirm_delete_rule"),
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                row = self.rule_list_widget.row(current_item)
                self.rule_list_widget.takeItem(row)
                
                # 应用更新后的规则
                self._apply_rules_to_network_graph()
                
                logger.info("已删除自定义规则")
        else:
            QMessageBox.information(
                self, language_manager.tr("hint"),
                language_manager.tr("select_rule_first")
            )
    
    def _format_rule_display_text(self, rule):
        """格式化规则的显示文本"""
        if rule.get('type') == 'range':
            min_c = rule.get('min_conn', 0)
            max_c = rule.get('max_conn', 9999)
            bf = rule.get('brightness_factor', 1.0) * 100
            sf = rule.get('size_factor', 1.0) * 100
            
            if max_c >= 9999:
                range_text = f"[{min_c}, ∞)"
            else:
                range_text = f"[{min_c}, {max_c}]"
            
            return (f"范围{range_text} → "
                   f"亮度{bf:.0f}% & 面积{sf:.0f}%")
        
        elif rule.get('type') == 'threshold':
            threshold = rule.get('threshold', 0)
            bf = rule.get('brightness_factor', 1.0) * 100
            sf = rule.get('size_factor', 1.0) * 100
            
            return (f"阈值≥{threshold} → "
                   f"亮度{bf:.0f}% & 面积{sf:.0f}%")
        
        return "未知规则类型"
    
    def _apply_rules_to_network_graph(self):
        """将当前规则应用到网络图组件"""
        try:
            rules = []
            for i in range(self.rule_list_widget.count()):
                item = self.rule_list_widget.item(i)
                rule = item.data(Qt.UserRole)
                if rule:
                    rules.append(rule)
            
            # 保存规则到配置文件
            import json
            ConfigManager.set('Graph', 'custom_rules', json.dumps(rules))
            
            # 更新网络图组件的规则
            from ..ui.network_graph import SciFiNodeItem
            SciFiNodeItem.load_custom_rules(rules)
            
            # 发出信号通知重新渲染
            self.config_applied.emit()
            
            logger.info(f"已应用 {len(rules)} 条自定义规则")
            
        except Exception as e:
            logger.error(f"应用自定义规则失败: {e}", exc_info=True)
    
    def load_custom_rules_from_config(self):
        """从配置文件加载自定义规则"""
        try:
            import json
            rules_str = ConfigManager.get('Graph', 'custom_rules', fallback='[]')
            rules = json.loads(rules_str)
            
            if rules:
                self.rule_list_widget.clear()
                for rule in rules:
                    display_text = self._format_rule_display_text(rule)
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.UserRole, rule)
                    self.rule_list_widget.addItem(item)
                
                # 同时加载到 SciFiNodeItem
                from ..ui.network_graph import SciFiNodeItem
                SciFiNodeItem.load_custom_rules(rules)
                
                logger.info(f"从配置加载了 {len(rules)} 条自定义规则")
                
        except Exception as e:
            logger.error(f"加载自定义规则失败: {e}", exc_info=True)
    
    def get_current_custom_rules(self):
        """获取当前所有自定义规则"""
        rules = []
        for i in range(self.rule_list_widget.count()):
            item = self.rule_list_widget.item(i)
            rule = item.data(Qt.UserRole)
            if rule:
                rules.append(rule)
        return rules
