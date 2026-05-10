
"""组织架构编辑器 - 三栏重构版

布局：
  左栏：待处理区（上半：全部成员列表，下半：待编辑队列）
  中栏：架构主编辑区（成员卡片：序列/职位/职能/下辖机构）
  右栏：架构预览（双模式：树状图 + 可视化画布编辑）

功能：
  - 从角色列表拖入或单击添加到待编辑队列
  - 卡片式编辑每位成员的序列/职位/职能/下辖机构
  - 双模式预览当前架构（文本模式 + 画布模式）
"""

import json
import os
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStyle,
    QTextBrowser,
    QVBoxLayout,
    QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt5.QtGui import QFont, QPainter, QColor, QPen, QBrush, QPainterPath
import logging
from models.keyword_manager import KeywordManager
from ..core.theme_manager import ThemeManager
from ..core.language_manager import language_manager

from ..widgets.faction_canvas import FactionCanvas
from ..widgets.faction_tools import EditorTool

logger = logging.getLogger(__name__)

try:
    from core.config_manager import ConfigManager
    _HAS_CONFIG = True
except ImportError:
    _HAS_CONFIG = False

_POSITION_PRESETS = ["族长", "长老", "执事", "堂主", "护法", "供奉", "弟子", "门主", "盟主", "会长"]
_FUNCTION_PRESETS = []


def _tr(key):
    return language_manager.tr(key)


class FactionTreeNode(QGraphicsItem):
    """架构树节点"""

    def __init__(self, text, node_type='member', parent=None):
        super().__init__(parent)
        self.text = text
        self.node_type = node_type
        self._collapsed = False
        self._child_items = []
        self.setAcceptHoverEvents(True)

        if node_type == 'root':
            self._w, self._h = 160, 44
            self._bg_color = QColor('#6B5B95')
            self._text_color = QColor('#FFFFFF')
            self._radius = 10
            self._font_size = 14
        elif node_type == 'level':
            self._w, self._h = 100, 34
            self._bg_color = QColor('#E8E8F0')
            self._text_color = QColor('#333333')
            self._radius = 8
            self._font_size = 12
        elif node_type == 'position':
            self._w, self._h = 90, 30
            self._bg_color = QColor('#F0F0F5')
            self._text_color = QColor('#444444')
            self._radius = 6
            self._font_size = 11
        else:
            self._w, self._h = 110, 28
            self._bg_color = QColor('#FFFFFF')
            self._text_color = QColor('#555555')
            self._border_color = QColor('#D0D4D9')
            self._radius = 6
            self._font_size = 10

    @property
    def collapsed(self):
        return self._collapsed

    def toggle(self):
        self._collapsed = not self._collapsed
        for child in self._child_items:
            child.setVisible(not self._collapsed)
        self.update()
        return self._collapsed

    def add_child(self, child):
        self._child_items.append(child)

    def boundingRect(self):
        return QRectF(-self._w / 2, -self._h / 2, self._w, self._h)

    def paint(self, painter, option, widget=None):
        is_hovered = option.state & QStyle.State_MouseOver

        if self.node_type == 'root':
            bg = self._bg_color.lighter(108) if is_hovered else self._bg_color
            painter.setBrush(QBrush(bg))
            painter.setPen(QPen(self._bg_color.darker(120), 1))
        elif self.node_type == 'member':
            bg = QColor('#F8FAFC') if not is_hovered else QColor('#EDF2F7')
            painter.setBrush(QBrush(bg))
            painter.setPen(QPen(self._border_color, 1))
        else:
            bg = self._bg_color.lighter(105) if is_hovered else self._bg_color
            painter.setBrush(QBrush(bg))
            painter.setPen(Qt.NoPen)

        path = QPainterPath()
        path.addRoundedRect(-self._w / 2, -self._h / 2, self._w, self._h, self._radius, self._radius)
        painter.drawPath(path)

        painter.setPen(self._text_color)
        font = QFont('Microsoft YaHei', self._font_size,
                      QFont.Bold if self.node_type in ('root', 'level') else QFont.Normal)
        painter.setFont(font)
        elided = (self.text[:14] + '..') if len(self.text) > 14 else self.text
        painter.drawText(QRectF(-self._w / 2 + 6, -self._h / 2, self._w - 12, self._h),
                      Qt.AlignCenter, elided)

        if self._child_items and self.node_type != 'member':
            icon = '+' if self._collapsed else '-'
            painter.setFont(QFont('Segoe UI Symbol', 9, QFont.Bold))
            painter.drawText(QRectF(self._w / 2 - 16, -self._h / 2, 14, self._h), Qt.AlignCenter, icon)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._child_items and self.node_type != 'member':
            self.toggle()

    def hoverEnterEvent(self, event):
        self.update()

    def hoverLeaveEvent(self, event):
        self.update()


class FactionEditorDialog(QDialog):
    """重构版组织架构编辑器"""
    saved = pyqtSignal(str, dict)

    def __init__(self, faction_name, parent=None):
        super().__init__(parent)
        self.faction_name = faction_name
        self.original_structure = None
        self.current_structure = {}
        self._editing_queue = []
        self._member_cards = {}
        self._gender_map = {}
        self._max_sequence = 5
        self._faction_tree_data = None
        self._init_ui()
        self._load_data()
        logger.info(f"架构编辑器已打开: {faction_name}")

    # ============================================================
    # 样式方法
    # ============================================================

    def _fs(self, base):
        return base

    def _tc(self, key, fallback=''):
        tm = ThemeManager()
        return tm.get(key, fallback) if tm else fallback

    def _st_main(self):
        bg = self._tc('bg_color', '#F8F9FA')
        fg = self._tc('fg_color', '#212529')
        return f"QDialog {{ background-color: {bg}; color: {fg}; }}"

    def _st_group(self):
        bg = self._tc('card_bg', '#FFFFFF')
        bd = self._tc('border_color', '#D0D4D9')
        fg = self._tc('fg_color', '#212529')
        return f"""
        QGroupBox {{
            background-color: {bg};
            border: 2px solid {bd};
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 12px;
            color: {fg};
            font-weight: bold;
            font-size: 20px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px;
            color: {fg};
        }}
        """

    def _st_btn(self, primary=False):
        accent = self._tc('accent_color', '#0078D4')
        bg_color = self._tc('bg_color', '#F8F9FA')
        hover = self._tc('hover_bg', '#E8E8E8')
        bd = self._tc('border_color', '#D0D4D9')
        card = self._tc('card_bg', '#FFFFFF')
        fg = self._tc('fg_color', '#212529')
        ts = self._tc('text_secondary', '#6C757D')
        if primary:
            bg = accent
            c = bg_color
            hbg = hover
            b = accent
        else:
            bg = card
            c = fg
            hbg = hover
            b = bd
        return f"""
        QPushButton {{
            background-color: {bg}; border: 1px solid {b};
            border-radius: 4px; color: {c}; font-weight: bold;
            padding: 10px 20px; font-size: 17px; min-height: 36px;
        }}
        QPushButton:hover {{ background-color: {hbg}; border-color: {accent}; }}
        QPushButton:pressed {{ background-color: {accent}; color: {bg_color}; }}
        QPushButton:disabled {{ color: {ts}; border-color: {bd}; }}
        """

    def _st_combo(self):
        ibg = self._tc('input_bg', '#FFFFFF')
        fg = self._tc('fg_color', '#212529')
        bd = self._tc('border_color', '#D0D4D9')
        accent = self._tc('accent_color', '#0078D4')
        hover = self._tc('hover_bg', '#E8E8E8')
        return f"""
        QComboBox {{
            background-color: {ibg}; color: {fg};
            border: 1px solid {bd}; border-radius: 4px;
            padding: 8px 12px; font-size: 17px; min-height: 36px;
        }}
        QComboBox:hover {{ border-color: {accent}; }}
        QComboBox QAbstractItemView {{
            background-color: {ibg}; color: {fg};
            selection-background-color: {hover}; border: 1px solid {bd};
        }}
        """

    def _st_input(self):
        ibg = self._tc('input_bg', '#FFFFFF')
        fg = self._tc('fg_color', '#212529')
        bd = self._tc('border_color', '#D0D4D9')
        accent = self._tc('accent_color', '#0078D4')
        return f"""
        QLineEdit {{
            background-color: {ibg}; color: {fg};
            border: 1px solid {bd}; border-radius: 4px;
            padding: 8px 12px; font-size: 17px; min-height: 36px;
        }}
        QLineEdit:focus {{ border-color: {accent}; }}
        """

    def _st_spin(self):
        ibg = self._tc('input_bg', '#FFFFFF')
        fg = self._tc('fg_color', '#212529')
        bd = self._tc('border_color', '#D0D4D9')
        return f"""
        QSpinBox {{
            background-color: {ibg}; color: {fg};
            border: 1px solid {bd}; border-radius: 4px;
            padding: 8px 10px; font-size: 17px; min-height: 36px;
        }}
        """

    def _st_list(self):
        ibg = self._tc('input_bg', '#FFFFFF')
        fg = self._tc('fg_color', '#212529')
        bd = self._tc('border_color', '#D0D4D9')
        accent = self._tc('accent_color', '#0078D4')
        hover = self._tc('hover_bg', '#E8E8E8')
        return f"""
        QListWidget {{
            background-color: {ibg}; color: {fg};
            border: 1px solid {bd}; border-radius: 4px;
            padding: 6px; font-size: 17px;
        }}
        QListWidget::item:selected {{
            background-color: {hover}; color: {accent};
        }}
        QListWidget::item:hover {{ background-color: {hover}; }}
        """

    def _st_browser(self):
        ibg = self._tc('input_bg', '#FFFFFF')
        fg = self._tc('fg_color', '#212529')
        bd = self._tc('border_color', '#D0D4D9')
        return f"""
        QTextBrowser {{
            background-color: {ibg}; color: {fg};
            border: 1px solid {bd}; border-radius: 4px;
            padding: 14px; font-size: 17px;
        }}
        """

    def _st_frame(self):
        card = self._tc('card_bg', '#FFFFFF')
        bd = self._tc('border_color', '#D0D4D9')
        return f"""
        QFrame {{
            border: 1px solid {bd}; border-radius: 6px;
            background-color: {card}; padding: 10px;
        }}
        """

    def _st_scroll(self):
        accent = self._tc('accent_color', '#0078D4')
        bd = self._tc('border_color', '#D0D4D9')
        card = self._tc('card_bg', '#FFFFFF')
        ibg = self._tc('input_bg', '#FFFFFF')
        return f"""
        QScrollArea {{
            border: 1px solid {bd}; border-radius: 4px;
            background-color: {card};
        }}
        QScrollBar:vertical {{
            background-color: {ibg}; width: 10px; border-radius: 5px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {accent}; border-radius: 5px; min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{ background-color: {accent}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """

    # ============================================================
    # UI 构建
    # ============================================================

    def _init_ui(self):
        self.setWindowTitle(f"{_tr('structure_editor')} - {self.faction_name}")
        self.setMinimumSize(800, 520)
        self.setModal(True)
        self.setStyleSheet(self._st_main())

        if _HAS_CONFIG:
            try:
                w = int(ConfigManager.get('UI', 'faction_editor_width') or 900)
                h = int(ConfigManager.get('UI', 'faction_editor_height') or 620)
                self.resize(w, h)
            except Exception:
                self.resize(900, 620)

        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 10, 12, 10)

        splitter = QSplitter(Qt.Horizontal)
        bd = self._tc('border_color', '#D0D4D9')
        splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {bd}; width: 2px; }}")

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_center_panel())
        splitter.addWidget(self._build_right_panel())

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 4)

        main_layout.addWidget(splitter)

    # ---- 左栏 ----
    def _build_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)

        # 上半：全部成员
        upper = QGroupBox(_tr("all_members"))
        upper.setStyleSheet(self._st_group())
        ul = QVBoxLayout(upper)
        self._all_members_list = QListWidget()
        self._all_members_list.setStyleSheet(self._st_list())
        self._all_members_list.setSelectionMode(QListWidget.ExtendedSelection)
        self._all_members_list.itemDoubleClicked.connect(self._add_to_queue)
        ul.addWidget(self._all_members_list)

        ul2 = QHBoxLayout()
        add_sel_btn = QPushButton(_tr("add_to_queue"))
        add_sel_btn.setStyleSheet(self._st_btn(primary=True))
        add_sel_btn.clicked.connect(lambda: self._add_selected_to_queue())
        ul2.addWidget(add_sel_btn)

        add_all_btn = QPushButton(_tr("add_all_to_queue"))
        add_all_btn.setStyleSheet(self._st_btn())
        add_all_btn.clicked.connect(self._add_all_to_queue)
        ul2.addWidget(add_all_btn)
        ul.addLayout(ul2)
        layout.addWidget(upper, 3)

        # 下半：待编辑队列
        lower = QGroupBox(_tr("edit_queue"))
        lower.setStyleSheet(self._st_group())
        ll = QVBoxLayout(lower)
        self._queue_list = QListWidget()
        self._queue_list.setStyleSheet(self._st_list())
        self._queue_list.setDragDropMode(QListWidget.InternalMove)
        ll.addWidget(self._queue_list)

        ll2 = QHBoxLayout()
        rm_btn = QPushButton(_tr("remove_from_queue"))
        rm_btn.setStyleSheet(self._st_btn())
        rm_btn.clicked.connect(self._remove_from_queue)
        ll2.addWidget(rm_btn)

        clr_btn = QPushButton(_tr("clear_queue"))
        clr_btn.setStyleSheet(self._st_btn())
        clr_btn.clicked.connect(self._clear_queue)
        ll2.addWidget(clr_btn)
        ll.addLayout(ll2)
        layout.addWidget(lower, 2)

        return panel

    # ---- 中栏（主编辑区） ----
    def _build_center_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        accent = self._tc('accent_color', '#0078D4')
        header_label = QLabel(_tr("structure_edit"))
        header_label.setStyleSheet(f"color:{accent};font-weight:bold;font-size:24px;")
        layout.addWidget(header_label)

        self._center_scroll = QScrollArea()
        self._center_scroll.setStyleSheet(self._st_scroll())
        self._center_scroll.setWidgetResizable(True)
        self._center_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._center_container = QWidget()
        self._center_layout = QVBoxLayout(self._center_container)
        self._center_layout.setAlignment(Qt.AlignTop)
        self._center_layout.setSpacing(8)

        self._center_scroll.setWidget(self._center_container)
        layout.addWidget(self._center_scroll, 1)

        # 底部操作栏
        bottom_row = QHBoxLayout()
        self._apply_all_btn = QPushButton(_tr("apply_queue"))
        self._apply_all_btn.setStyleSheet(self._st_btn(primary=True))
        self._apply_all_btn.clicked.connect(self._apply_queue_to_center)
        bottom_row.addWidget(self._apply_all_btn)

        ts = self._tc('text_secondary', '#6C757D')
        max_seq_label = QLabel(_tr("max_sequence"))
        max_seq_label.setStyleSheet(f"color:{ts};font-size:17px;")
        bottom_row.addWidget(max_seq_label)

        self._max_seq_spin = QSpinBox()
        self._max_seq_spin.setStyleSheet(self._st_spin())
        self._max_seq_spin.setRange(1, 99)
        self._max_seq_spin.setValue(3)
        self._max_seq_spin.valueChanged.connect(self._on_max_seq_changed)
        bottom_row.addWidget(self._max_seq_spin)

        bottom_row.addStretch()
        layout.addLayout(bottom_row)

        return panel

    # ---- 右栏（预览） ----
    def _build_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)

        preview_group = QGroupBox(_tr("structure_preview"))
        preview_group.setStyleSheet(self._st_group())
        pl = QVBoxLayout(preview_group)

        # 预览模式切换栏
        mode_row = QHBoxLayout()
        self._preview_mode_combo = QComboBox()
        self._preview_mode_combo.setStyleSheet(self._st_combo())
        self._preview_mode_combo.addItems([_tr("text_mode"), _tr("canvas_mode")])
        self._preview_mode_combo.currentIndexChanged.connect(self._on_preview_mode_changed)
        mode_row.addWidget(QLabel(_tr("preview_mode")))
        mode_row.addWidget(self._preview_mode_combo)
        pl.addLayout(mode_row)

        # 文本模式预览
        self._preview_scene = QGraphicsScene()
        self._preview_view = QGraphicsView(self._preview_scene)
        self._preview_view.setRenderHint(QPainter.Antialiasing)
        bg = self._tc('bg_color', '#F8F9FA')
        bd = self._tc('border_color', '#DEE2E6')
        self._preview_view.setStyleSheet(f"""
            QGraphicsView {{
                background-color: {bg};
                border: 1px solid {bd};
                border-radius: 6px;
            }}
        """)
        self._preview_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._preview_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        pl.addWidget(self._preview_view, 1)

        # 画布模式预览
        self._canvas = FactionCanvas()
        self._canvas.hide()
        pl.addWidget(self._canvas, 1)

        # 画布工具栏
        canvas_toolbar = QHBoxLayout()
        self._edit_mode_btn = QPushButton(_tr("edit_mode"))
        self._edit_mode_btn.setCheckable(True)
        self._edit_mode_btn.setStyleSheet(self._st_btn())
        self._edit_mode_btn.clicked.connect(self._on_edit_mode_toggled)
        canvas_toolbar.addWidget(self._edit_mode_btn)

        self._tool_select_btn = QPushButton(_tr("tool_select"))
        self._tool_select_btn.setCheckable(True)
        self._tool_select_btn.setChecked(True)
        self._tool_select_btn.setStyleSheet(self._st_btn())
        self._tool_select_btn.clicked.connect(lambda: self._set_tool(EditorTool.SELECT))
        canvas_toolbar.addWidget(self._tool_select_btn)

        self._tool_arrow_btn = QPushButton(_tr("tool_arrow"))
        self._tool_arrow_btn.setCheckable(True)
        self._tool_arrow_btn.setStyleSheet(self._st_btn())
        self._tool_arrow_btn.clicked.connect(lambda: self._set_tool(EditorTool.ARROW))
        canvas_toolbar.addWidget(self._tool_arrow_btn)

        self._tool_text_btn = QPushButton(_tr("tool_text"))
        self._tool_text_btn.setCheckable(True)
        self._tool_text_btn.setStyleSheet(self._st_btn())
        self._tool_text_btn.clicked.connect(lambda: self._set_tool(EditorTool.TEXT))
        canvas_toolbar.addWidget(self._tool_text_btn)

        canvas_toolbar.addStretch()

        self._undo_btn = QPushButton(_tr("undo"))
        self._undo_btn.setStyleSheet(self._st_btn())
        self._undo_btn.clicked.connect(self._canvas.undo)
        canvas_toolbar.addWidget(self._undo_btn)

        self._redo_btn = QPushButton(_tr("redo"))
        self._redo_btn.setStyleSheet(self._st_btn())
        self._redo_btn.clicked.connect(self._canvas.redo)
        canvas_toolbar.addWidget(self._redo_btn)

        canvas_toolbar.addStretch()

        self._export_btn = QPushButton(_tr("export_image"))
        self._export_btn.setStyleSheet(self._st_btn())
        self._export_btn.clicked.connect(self._export_to_image)
        canvas_toolbar.addWidget(self._export_btn)

        pl.addLayout(canvas_toolbar)

        layout.addWidget(preview_group, 3)

        # 统计
        stats_group = QGroupBox(_tr("statistics"))
        stats_group.setStyleSheet(self._st_group())
        sl = QVBoxLayout(stats_group)
        ts = self._tc('text_secondary', '#6C757D')
        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet(f"color:{ts};font-size:17px;")
        self._stats_label.setWordWrap(True)
        sl.addWidget(self._stats_label)
        layout.addWidget(stats_group)

        # 操作
        action_group = QGroupBox(_tr("actions"))
        action_group.setStyleSheet(self._st_group())
        al = QVBoxLayout(action_group)

        self._save_btn = QPushButton(_tr("save"))
        self._save_btn.setStyleSheet(self._st_btn(primary=True))
        self._save_btn.clicked.connect(self._validate_and_save)
        al.addWidget(self._save_btn)

        self._cancel_btn = QPushButton(_tr("cancel"))
        self._cancel_btn.setStyleSheet(self._st_btn())
        self._cancel_btn.clicked.connect(self.reject)
        al.addWidget(self._cancel_btn)

        self._reset_btn = QPushButton(_tr("reset"))
        self._reset_btn.setStyleSheet(self._st_btn())
        self._reset_btn.clicked.connect(self._reset_to_original)
        al.addWidget(self._reset_btn)

        self._template_btn = QPushButton(_tr("save_as_template"))
        self._template_btn.setStyleSheet(self._st_btn())
        self._template_btn.clicked.connect(self._save_as_template)
        al.addWidget(self._template_btn)

        self._import_btn = QPushButton(_tr("import_from_template"))
        self._import_btn.setStyleSheet(self._st_btn())
        self._import_btn.clicked.connect(self._import_from_template)
        al.addWidget(self._import_btn)

        layout.addWidget(action_group)
        return panel

    # ============================================================
    # 数据加载
    # ============================================================

    def _load_data(self):
        try:
            self.original_structure = KeywordManager.load_faction_structure(self.faction_name) or {}
            self.current_structure = dict(self.original_structure) if self.original_structure else {
                'template': 'custom', 'roles': {}, 'metadata': {}
            }
            if 'roles' not in self.current_structure:
                self.current_structure['roles'] = {}
            if 'template' not in self.current_structure:
                self.current_structure['template'] = 'custom'

            keywords = KeywordManager.load_keywords()
            for kw in keywords:
                if kw.get('type') == 'character':
                    self._gender_map[kw.get('name', '')] = kw.get('gender', 'unknown')

            self._populate_member_list()
            self._populate_from_structure()
            self._load_faction_tree_node()
            self._refresh_preview()
            self._update_stats()
        except Exception as e:
            logger.error(f"加载数据失败 [{self.faction_name}]: {e}")

    def _load_faction_tree_node(self):
        """加载或创建 faction_tree_node.json"""
        try:
            novel_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'novel', self.faction_name)
            if not os.path.exists(novel_dir):
                novel_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'novel', '我欲封神')
            data_file = os.path.join(novel_dir, '.novel_structure', 'factiontree_node.json')
            
            if os.path.exists(data_file):
                with open(data_file, 'r', encoding='utf-8') as f:
                    self._faction_tree_data = json.load(f)
                self._canvas.load_faction_tree_data(self._faction_tree_data)
            else:
                # 创建默认数据文件
                self._faction_tree_data = self._create_default_faction_tree()
                os.makedirs(os.path.dirname(data_file), exist_ok=True)
                with open(data_file, 'w', encoding='utf-8') as f:
                    json.dump(self._faction_tree_data, f, ensure_ascii=False, indent=2)
                self._canvas.load_faction_tree_data(self._faction_tree_data)
        except Exception as e:
            logger.error(f"加载 faction_tree_node.json 失败: {e}")

    def _create_default_faction_tree(self):
        """创建默认的 faction_tree_node 数据"""
        return {
            "_meta": {
                "schema": "factiontree_node",
                "version": "1.0",
                "description": "宗族架构树状图节点定义文件。用户可自定义层级范围和节点关系，支持两种连线类型：parent（实线从属）和 relations（虚线特殊关联+标注）。"
            },
            "level_config": {
                "range": [1, 6],
                "step": 1,
                "_rule": "端点[a,b]必须为整数，step可精确到0.1。例：[1,2] step=0.1 → 1.0,1.1,…,2.0 共11层。",
                "_available": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
                "label_format": "LV{value}",
                "_label_examples": "1.0→LV1, 3.0→LV3, 6.0→LV6"
            },
            "volumes": [
                {"name": "高层", "level_range": [1.0, 2.0], "description": "高层决策层", "color": "#5B8DEF"},
                {"name": "中层", "level_range": [3.0, 4.0], "description": "中层管理层", "color": "#9B59B6"},
                {"name": "底层", "level_range": [5.0, 6.0], "description": "基层执行层", "color": "#E67E22"}
            ],
            "nodes": [
                {
                    "id": "clan_root",
                    "name": self.faction_name,
                    "level": None,
                    "group": None,
                    "volume": None,
                    "node_type": "root",
                    "parent": None,
                    "children": [],
                    "relations": []
                }
            ],
            "cross_links": [],
            "node_styles": {
                "root": {"width": 180, "height": 48, "bg": "#6B5B95", "text": "#FFFFFF", "radius": 10, "font_size": 14},
                "level": {"width": 120, "height": 36, "bg": "#E8E8F0", "text": "#444444", "radius": 8, "font_size": 12},
                "group": {"width": 130, "height": 34, "bg": "#B8D4E8", "text": "#2C3E50", "radius": 8, "font_size": 11},
                "position": {"width": 100, "height": 30, "bg": "#D5E8D4", "text": "#333333", "radius": 6, "font_size": 10},
                "member": {"width": 110, "height": 28, "bg": "#FFFFFF", "text": "#555555", "radius": 6, "font_size": 9}
            },
            "line_styles": {
                "solid": {"color": "#666666", "width": 1.5, "dash": None, "arrow": True},
                "dashed": {"color": "#999999", "width": 1.2, "dash": [6, 4], "arrow": True},
                "dotted": {"color": "#BBBBBB", "width": 1.0, "dash": [2, 3], "arrow": False}
            },
            "layout": {
                "horizontal_spacing": 160,
                "vertical_spacing": 80,
                "level_label_offset": 60,
                "node_margin": 24,
                "group_padding": 20
            }
        }

    def _populate_member_list(self):
        self._all_members_list.clear()
        try:
            keywords = KeywordManager.load_keywords()
            assigned = set()
            if self.current_structure:
                for role in self.current_structure.get('roles', {}).values():
                    m = role.get('member')
                    if m:
                        assigned.add(m)

            for kw in keywords:
                if kw.get('type') == 'character':
                    name = kw.get('name', '')
                    gender = kw.get('gender', 'unknown')
                    gtag = {'male': '[男]', 'female': '[女]'}.get(gender, '')
                    display = f"{name} {gtag}" if gtag else name
                    item = QListWidgetItem(display)
                    item.setData(Qt.UserRole, name)
                    if name in assigned:
                        item.setForeground(Qt.gray)
                        item.setText(f"{display} (已分配)")
                    self._all_members_list.addItem(item)
        except Exception as e:
            logger.error(f"填充成员列表失败: {e}")

    def _populate_from_structure(self):
        """从已保存的结构填充编辑队列和卡片"""
        self._queue_list.clear()
        roles = self.current_structure.get('roles', {})
        if not roles:
            return

        # 先计算最大序列值
        max_seq = 1
        levels = {}
        for rid, rinfo in roles.items():
            lv = rinfo.get('level', 0)
            max_seq = max(max_seq, lv + 1)
            if lv not in levels:
                levels[lv] = []
            levels[lv].append((rid, rinfo))

        # 更新最大序列设置
        self._max_sequence = max(5, max_seq)
        self._max_seq_spin.setValue(self._max_sequence)

        # 填充队列
        for lv in sorted(levels.keys()):
            for rid, rinfo in levels[lv]:
                member = rinfo.get('member')
                if member:
                    item = QListWidgetItem(f"{member} (LV{lv+1})")
                    item.setData(Qt.UserRole, member)
                    item.setData(Qt.UserRole + 1, rinfo)
                    self._queue_list.addItem(item)

        self._apply_queue_to_center()

    # ---- 队列操作 ----

    def _on_max_seq_changed(self, new_max):
        """当最大序列值改变时，更新所有已创建卡片的序列下拉框"""
        self._max_sequence = new_max
        
        # 更新所有现有卡片的序列下拉框
        for card in self._member_cards.values():
            seq_combo = card['seq']
            current_val = seq_combo.currentData()
            
            # 清除并重新填充
            seq_combo.blockSignals(True)
            seq_combo.clear()
            for s in range(1, new_max + 1):
                seq_combo.addItem(f"LV{s}", s)
            
            # 尝试恢复原来选择的值
            if current_val is not None and current_val <= new_max:
                idx = seq_combo.findData(current_val)
                if idx >= 0:
                    seq_combo.setCurrentIndex(idx)
            seq_combo.blockSignals(False)
        
        self._refresh_preview()

    def _add_to_queue(self, item):
        member_name = item.data(Qt.UserRole)
        if not member_name:
            return
        for i in range(self._queue_list.count()):
            if self._queue_list.item(i).data(Qt.UserRole) == member_name:
                return
        new_item = QListWidgetItem(member_name)
        new_item.setData(Qt.UserRole, member_name)
        self._queue_list.addItem(new_item)

    def _add_selected_to_queue(self):
        for item in self._all_members_list.selectedItems():
            self._add_to_queue(item)

    def _add_all_to_queue(self):
        for i in range(self._all_members_list.count()):
            item = self._all_members_list.item(i)
            self._add_to_queue(item)

    def _remove_from_queue(self):
        for item in self._queue_list.selectedItems():
            row = self._queue_list.row(item)
            self._queue_list.takeItem(row)

    def _clear_queue(self):
        self._queue_list.clear()
        self._rebuild_center_cards()

    # ---- 中心编辑区卡片 ----

    def _apply_queue_to_center(self):
        self._rebuild_center_cards()
        self._refresh_preview()
        self._update_stats()

    def _rebuild_center_cards(self):
        while self._center_layout.count():
            child = self._center_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._member_cards.clear()

        for i in range(self._queue_list.count()):
            item = self._queue_list.item(i)
            member_name = item.data(Qt.UserRole)
            if not member_name:
                continue
            card = self._create_member_card(member_name, i)
            self._center_layout.addWidget(card)

        self._center_layout.addStretch()

    def _create_member_card(self, member_name, idx):
        frame = QFrame()
        frame.setStyleSheet(self._st_frame())
        frame.setProperty("member_name", member_name)
        layout = QVBoxLayout(frame)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 10, 12, 10)

        accent = self._tc('accent_color', '#0078D4')
        gender = self._gender_map.get(member_name, 'unknown')
        gtag = {'male': '[男]', 'female': '[女]'}.get(gender, '')
        header = QLabel(f"{member_name}  {gtag}")
        header.setStyleSheet(f"color:{accent};font-weight:bold;font-size:20px;")
        layout.addWidget(header)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel(_tr("sequence")))
        seq_combo = QComboBox()
        seq_combo.setStyleSheet(self._st_combo())
        seq_combo.setEditable(True)
        for s in range(1, self._max_sequence + 1):
            seq_combo.addItem(f"LV{s}", s)
        seq_combo.setCurrentIndex(0)
        row1.addWidget(seq_combo)

        row1.addWidget(QLabel(_tr("position")))
        pos_combo = QComboBox()
        pos_combo.setStyleSheet(self._st_combo())
        pos_combo.setEditable(True)
        pos_combo.addItems(_POSITION_PRESETS)
        row1.addWidget(pos_combo)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel(_tr("function")))
        func_input = QLineEdit()
        func_input.setStyleSheet(self._st_input())
        func_input.setPlaceholderText(_tr("function_placeholder"))
        row2.addWidget(func_input)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel(_tr("subordinate_org")))
        sub_type = QComboBox()
        sub_type.setStyleSheet(self._st_combo())
        sub_type.addItems([_tr("none"), _tr("manager"), _tr("managed")])
        row3.addWidget(sub_type)

        sub_name = QLineEdit()
        sub_name.setStyleSheet(self._st_input())
        sub_name.setPlaceholderText(_tr("org_name"))
        sub_name.setEnabled(False)
        sub_type.currentTextChanged.connect(lambda t: sub_name.setEnabled(t != _tr("none")))
        row3.addWidget(sub_name)
        layout.addLayout(row3)

        # 存储控件引用
        self._member_cards[member_name] = {
            'frame': frame,
            'seq': seq_combo,
            'position': pos_combo,
            'function': func_input,
            'sub_type': sub_type,
            'sub_name': sub_name
        }

        # 将原结构中的已有值填回控件
        self._fill_card_from_structure(member_name)

        # 实时预览
        seq_combo.currentIndexChanged.connect(lambda: self._refresh_preview())
        pos_combo.currentTextChanged.connect(lambda: self._refresh_preview())
        func_input.textChanged.connect(lambda: self._refresh_preview())
        sub_type.currentTextChanged.connect(lambda: self._refresh_preview())
        sub_name.textChanged.connect(lambda: self._refresh_preview())

        return frame

    def _fill_card_from_structure(self, member_name):
        """如果成员在已有结构中，将值填回卡片"""
        roles = self.current_structure.get('roles', {})
        for rid, rinfo in roles.items():
            if rinfo.get('member') == member_name:
                card = self._member_cards.get(member_name)
                if not card:
                    return
                lv = rinfo.get('level', 0)
                target_seq = lv + 1

                # 确保下拉框包含目标序列值
                has_seq = False
                for i in range(card['seq'].count()):
                    if card['seq'].itemData(i) == target_seq:
                        has_seq = True
                        break
                if not has_seq:
                    card['seq'].addItem(f"LV{target_seq}", target_seq)

                seq_idx = card['seq'].findData(target_seq)
                if seq_idx >= 0:
                    card['seq'].setCurrentIndex(seq_idx)

                pos_title = rinfo.get('title', '')
                if pos_title:
                    pi = card['position'].findText(pos_title)
                    if pi >= 0:
                        card['position'].setCurrentIndex(pi)
                    else:
                        card['position'].setEditText(pos_title)

                func = rinfo.get('function', '')
                if func:
                    card['function'].setText(func)

                sub = rinfo.get('subordinate', {})
                if sub:
                    stype = sub.get('type', '')
                    if stype in ('管理者', '被管理者'):
                        card['sub_type'].setCurrentText(stype)
                    sname = sub.get('name', '')
                    if sname:
                        card['sub_name'].setText(sname)
                        card['sub_name'].setEnabled(True)
                return

    # ---- 预览 ----
    def _refresh_preview(self):
        self._update_stats()
        if self._preview_mode_combo.currentIndex() == 0:
            self._render_tree_preview()
        # 画布模式通过数据同步自动更新

    def _on_preview_mode_changed(self, index):
        """预览模式切换"""
        if index == 0:
            self._preview_view.show()
            self._canvas.hide()
            self._edit_mode_btn.hide()
            self._tool_select_btn.hide()
            self._tool_arrow_btn.hide()
            self._tool_text_btn.hide()
            self._undo_btn.hide()
            self._redo_btn.hide()
            self._export_btn.hide()
            self._render_tree_preview()
        else:
            self._preview_view.hide()
            self._canvas.show()
            self._edit_mode_btn.show()
            self._tool_select_btn.show()
            self._tool_arrow_btn.show()
            self._tool_text_btn.show()
            self._undo_btn.show()
            self._redo_btn.show()
            self._export_btn.show()

    def _on_edit_mode_toggled(self, checked):
        """切换编辑模式"""
        self._canvas.set_edit_mode(checked)

    def _set_tool(self, tool):
        """设置当前工具"""
        self._tool_select_btn.setChecked(tool == EditorTool.SELECT)
        self._tool_arrow_btn.setChecked(tool == EditorTool.ARROW)
        self._tool_text_btn.setChecked(tool == EditorTool.TEXT)
        self._canvas.set_tool(tool)

    def _render_tree_preview(self):
        """将架构数据渲染为树状图"""
        self._preview_scene.clear()

        data = self._collect_card_data()
        if not data:
            ts = self._tc('text_secondary', '#6C757D')
            empty = QGraphicsTextItem(_tr("no_data_preview"))
            empty.setDefaultTextColor(QColor(ts))
            empty.setFont(QFont('Microsoft YaHei', 13))
            self._preview_scene.addItem(empty)
            return

        accent = QColor(self._tc('accent_color', '#0078D4'))
        line_color = QColor(self._tc('border_color', '#A0AEC0'))

        levels = {}
        for entry in data:
            lv = entry['sequence']
            if lv not in levels:
                levels[lv] = []
            levels[lv].append(entry)

        sorted_levels = sorted(levels.keys())

        # 根节点（宗族名）
        root = FactionTreeNode(self.faction_name, 'root')
        root.setPos(0, 0)
        self._preview_scene.addItem(root)

        level_y = 80
        h_gap_lv = max(180, len(sorted_levels) * 60)

        for li, lv in enumerate(sorted_levels):
            members = levels[lv]
            pos_groups = {}
            for m in members:
                pos = m['position'] or '未命名'
                if pos not in pos_groups:
                    pos_groups[pos] = []
                pos_groups[pos].append(m)

            n_pos = len(pos_groups)
            if n_pos == 0:
                continue

            lv_x_start = -((n_pos - 1) * h_gap_lv) / 2
            lv_node = FactionTreeNode(f"LV{lv}", 'level')
            lv_node.setPos(0, level_y)
            self._preview_scene.addItem(lv_node)
            root.add_child(lv_node)

            self._draw_curve(root, lv_node, line_color)

            pos_y = level_y + 70
            h_gap_pos = max(140, len(max(pos_groups.values(), key=len)) * 55)

            for pi, (pos_name, pos_members) in enumerate(pos_groups.items()):
                pos_x = lv_x_start + pi * h_gap_lv

                pos_node = FactionTreeNode(pos_name[:8], 'position')
                pos_node.setPos(pos_x, pos_y)
                self._preview_scene.addItem(pos_node)
                lv_node.add_child(pos_node)

                self._draw_curve(lv_node, pos_node, line_color)

                mem_y = pos_y + 58
                for mi, m in enumerate(pos_members):
                    mem_text = f"{m.get('function', '') or ''} {m['name']}"
                    mem_node = FactionTreeNode(mem_text[:16], 'member')
                    mx = pos_x + (mi - len(pos_members) / 2) * h_gap_pos
                    mem_node.setPos(mx, mem_y)
                    self._preview_scene.addItem(mem_node)
                    pos_node.add_child(mem_node)

                    self._draw_curve(pos_node, mem_node, line_color)

            level_y += 160

        self._preview_view.fitInView(self._preview_scene.sceneRect(), Qt.KeepAspectRatio)

    @staticmethod
    def _draw_curve(parent_node, child_node, color):
        """绘制带弧度的连接线"""
        scene = parent_node.scene()
        if not scene:
            return
        p_pos = parent_node.pos()
        c_pos = child_node.pos()
        p_bottom = p_pos.y() + parent_node._h / 2
        c_top = c_pos.y() - child_node._h / 2
        mid_y = (p_bottom + c_top) / 2
        path = QPainterPath()
        path.moveTo(p_pos.x(), p_bottom)
        path.cubicTo(p_pos.x(), mid_y, c_pos.x(), mid_y, c_pos.x(), c_top)
        pen = QPen(color, 1.5)
        pen.setStyle(Qt.DashLine)
        scene.addPath(path, pen)

    def _export_to_image(self):
        """导出画布为图片"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, _tr("export_image"),
            f"{self.faction_name}_架构图.png",
            "PNG (*.png);;JPEG (*.jpg)"
        )
        if file_path:
            self._canvas.export_to_image(file_path)

    def _update_stats(self):
        data = self._collect_card_data()
        n = len(data)
        levels = set()
        positions = set()
        for e in data:
            levels.add(e['sequence'])
            positions.add((e['sequence'], e['position']))
        with_sub = sum(1 for e in data if e.get('subordinate'))
        self._stats_label.setText(
            f"{_tr('members')}: {n} | {_tr('levels')}: {len(levels)} | {_tr('positions')}: {len(positions)} | "
            f"{_tr('with_sub')}: {with_sub}"
        )

    def _collect_card_data(self):
        data = []
        for member_name, card in self._member_cards.items():
            seq = card['seq'].currentData()
            if seq is None:
                try:
                    txt = card['seq'].currentText().strip()
                    seq = int(''.join(c for c in txt if c.isdigit()))
                except Exception:
                    seq = 1
            gender = self._gender_map.get(member_name, 'unknown')
            d = {
                'name': member_name,
                'sequence': int(seq) if seq else 1,
                'position': card['position'].currentText().strip(),
                'function': card['function'].text().strip(),
                'subordinate': None,
                'gender_tag': {'male': '[男]', 'female': '[女]'}.get(gender, '')
            }
            st = card['sub_type'].currentText()
            sn = card['sub_name'].text().strip()
            if st != _tr("none") and sn:
                d['subordinate'] = {'type': st, 'name': sn}
            data.append(d)
        return sorted(data, key=lambda x: (x['sequence'], x['position']))

    # ============================================================
    # 保存与验证
    # ============================================================

    def _validate_and_save(self):
        data = self._collect_card_data()
        if not data:
            reply = QMessageBox.question(
                self, _tr("confirm"), _tr("confirm_save_empty"),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        roles = {}
        for idx, entry in enumerate(data):
            role_id = f"role_{idx}"
            roles[role_id] = {
                'title': entry['position'],
                'member': entry['name'],
                'level': entry['sequence'] - 1,
                'function': entry['function'],
                'subordinate': entry['subordinate'],
                'parent_role': None,
                'max': None,
                'required': False
            }

        self.current_structure = {
            'template': self.current_structure.get('template', 'custom'),
            'roles': roles,
            'metadata': self.current_structure.get('metadata', {})
        }

        success = KeywordManager.save_faction_structure(
            self.faction_name, self.current_structure
        )
        if success:
            logger.info(f"架构保存成功: {self.faction_name}")
            self.saved.emit(self.faction_name, self.current_structure)
            QMessageBox.information(self, _tr("success"), _tr("save_success"))
            self.accept()
        else:
            QMessageBox.critical(self, _tr("error"), _tr("save_failed"))

    def _reset_to_original(self):
        reply = QMessageBox.question(
            self, _tr("confirm_reset"),
            _tr("confirm_reset_msg"),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        self.current_structure = dict(self.original_structure) if self.original_structure else {
            'template': 'custom', 'roles': {}, 'metadata': {}
        }
        if 'roles' not in self.current_structure:
            self.current_structure['roles'] = {}
        self._populate_member_list()
        self._queue_list.clear()
        self._populate_from_structure()
        self._refresh_preview()
        self._update_stats()

    def _save_as_template(self):
        data = self._collect_card_data()
        if not data:
            QMessageBox.warning(self, _tr("prompt"), _tr("no_data_to_save"))
            return
        tid, ok = QLineEdit.getText(self, _tr("template_id"), _tr("template_id_prompt"))
        if not ok or not tid.strip():
            return
        tname, ok = QLineEdit.getText(self, _tr("template_name"), _tr("template_name_prompt"))
        if not ok or not tname.strip():
            return

        levels = []
        seen = set()
        for e in data:
            pos = e['position']
            if pos not in seen:
                seen.add(pos)
                levels.append({
                    'id': f"{tid}_{len(levels)}",
                    'label': pos,
                    'level': e['sequence'] - 1
                })

        templates = KeywordManager.load_faction_templates()
        templates[tid] = {
            'id': tid, 'name': tname, 'name_en': tname,
            'supports_genealogy': False, 'levels': levels
        }
        if KeywordManager.save_faction_templates(templates):
            QMessageBox.information(self, _tr("success"), f"{_tr('template_saved')}: '{tname}'")
        else:
            QMessageBox.critical(self, _tr("error"), _tr("template_save_failed"))

    def _import_from_template(self):
        templates = KeywordManager.load_faction_templates()
        if not templates:
            QMessageBox.information(self, _tr("prompt"), _tr("no_templates_available"))
            return
        names = [f"{t.get('name', tid)} ({tid})" for tid, t in templates.items()]
        choice, ok = QLineEdit.getChooseItem(self, _tr("select_template"), _tr("select_template_prompt"), names)
        if not ok or not choice:
            return
        idx = names.index(choice)
        tid = list(templates.keys())[idx]
        tdata = templates[tid]

        self.current_structure['template'] = tid
        self.current_structure['roles'] = {}
        levels = tdata.get('levels', [])
        for i, lv in enumerate(levels):
            rid = lv.get('id', f"tpl_{i}")
            self.current_structure['roles'][rid] = {
                'title': lv.get('label', ''),
                'member': None,
                'level': lv.get('level', i),
                'function': '',
                'subordinate': None,
                'parent_role': None,
                'max': lv.get('max'),
                'required': lv.get('required', False)
            }
        self._populate_member_list()
        self._queue_list.clear()
        self._rebuild_center_cards()
        self._refresh_preview()
        self._update_stats()

    def _save_window_size(self):
        if not _HAS_CONFIG:
            return
        try:
            size = self.size()
            ConfigManager.set('UI', 'faction_editor_width', str(size.width()))
            ConfigManager.set('UI', 'faction_editor_height', str(size.height()))
        except Exception:
            pass

    def reject(self):
        self._save_window_size()
        super().reject()

    def closeEvent(self, event):
        self._save_window_size()
        super().closeEvent(event)

