from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
import logging
from models.keyword_manager import KeywordManager
from core.theme_manager import theme_manager

logger = logging.getLogger(__name__)

_t = lambda k, d='': theme_manager.get(k, d)


class FactionListItem(QFrame):
    """组织列表项组件 — 主题感知"""

    clicked = pyqtSignal(str)

    def __init__(self, faction_data, font_config=None, parent=None):
        super().__init__(parent)
        self.faction_data = faction_data
        self.font_config = font_config or {}
        self._init_ui()

    def _get_font_size(self, key, default=24):
        return self.font_config.get(key, default)

    def _get_font_family(self):
        return _t('font_family', "'Segoe UI', 'Microsoft YaHei', sans-serif")

    def _init_ui(self):
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(self._get_style())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(25, 22, 25, 22)
        layout.setSpacing(20)

        family = self._get_font_family()
        name_size = self._get_font_size('title', 28)
        desc_size = self._get_font_size('desc', 22)
        stats_size = self._get_font_size('stats', 20)
        btn_size = self._get_font_size('btn', 22)

        accent = _t('accent_color', '#0078D4')
        fg = _t('fg_color', '#212529')

        name = self.faction_data.get('name', '未命名')
        desc = self.faction_data.get('description', '')
        if desc and len(desc) > 100:
            desc = desc[:97] + "..."

        left_layout = QVBoxLayout()
        left_layout.setSpacing(6)

        name_label = QLabel(f"[ {name} ]")
        name_label.setStyleSheet(
            f"color: {accent}; font-size: {name_size}px; font-weight: bold; "
            f"font-family: {family}, 'Microsoft YaHei';"
        )
        left_layout.addWidget(name_label)

        desc_label = QLabel(desc if desc else "(无描述)")
        desc_label.setStyleSheet(
            f"color: {fg}; font-size: {desc_size}px; "
            f"font-family: {family}, 'Microsoft YaHei';"
        )
        desc_label.setWordWrap(True)
        left_layout.addWidget(desc_label)

        layout.addLayout(left_layout, 4)

        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        right_info = QVBoxLayout()
        right_info.setSpacing(8)
        right_info.setAlignment(Qt.AlignVCenter)

        faction_name = self.faction_data.get('name', '')
        members = KeywordManager.get_faction_members(faction_name)
        member_count = len(members)

        structure = KeywordManager.load_faction_structure(faction_name)
        has_structure = bool(structure and structure.get('roles'))

        stats_text = f">> 成员: {member_count}人"
        stats_label = QLabel(stats_text)
        stats_label.setStyleSheet(
            f"color: {accent}; font-size: {stats_size}px; "
            f"font-family: {family}, 'Microsoft YaHei';"
        )
        right_info.addWidget(stats_label)

        status_color = _t('success_color', '#107C10') if has_structure else _t('fg_color', '#212529')
        status_text = "[OK] 已配置架构" if has_structure else "[--] 未配置架构"
        status_label = QLabel(status_text)
        status_label.setStyleSheet(
            f"color: {status_color}; font-size: {stats_size - 1}px; "
            f"font-family: {family}, 'Microsoft YaHei';"
        )
        right_info.addWidget(status_label)

        right_layout.addLayout(right_info)

        action_btn = QPushButton(">>> 查看详情")
        action_btn.setStyleSheet(self._button_style(btn_size, family))
        action_btn.setMinimumWidth(130)
        action_btn.clicked.connect(lambda: self.clicked.emit(faction_name))
        right_layout.addWidget(action_btn, 0, Qt.AlignVCenter)

        layout.addWidget(right_widget, 2)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.faction_data.get('name', ''))
        super().mousePressEvent(event)

    def _get_style(self):
        return f"""
        FactionListItem {{
            background-color: {_t('card_bg', '#FFFFFF')};
            border: 1px solid {_t('border_color', '#DEE2E6')};
            border-radius: {_t('card_radius', '12px')};
            margin: 10px 0;
        }}
        FactionListItem:hover {{
            border-color: {_t('accent_color', '#0078D4')};
        }}
        """

    def _button_style(self, font_size, font_family):
        return f"""
        QPushButton {{
            background-color: {_t('btn_bg_color', '#0078D4')};
            color: #FFFFFF;
            border: none;
            border-radius: {_t('button_radius', '6px')};
            padding: 8px 18px;
            font-size: {font_size}px;
            font-weight: bold;
            font-family: {font_family}, 'Microsoft YaHei';
            min-width: 120px;
        }}
        QPushButton:hover {{
            background-color: {_t('btn_hover_color', '#106EBE')};
        }}
        """


class FactionListView(QWidget):
    """组织列表视图 — 主题感知"""

    faction_clicked = pyqtSignal(str)
    action_triggered = pyqtSignal(str)

    def __init__(self, font_config=None, parent=None):
        super().__init__(parent)
        self.font_config = font_config or {}
        self._init_ui()
        self._load_data()

    def _get_font_size(self, key, default=26):
        return self.font_config.get(key, default)

    def _get_font_family(self):
        return _t('font_family', "'Segoe UI', 'Microsoft YaHei', sans-serif")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(18)

        accent = _t('accent_color', '#0078D4')
        fg = _t('fg_color', '#212529')
        border = _t('border_color', '#DEE2E6')

        family = self._get_font_family()
        header_size = self._get_font_size('header', 38)
        sub_size = self._get_font_size('subtitle', 26)

        title_main = QLabel("[ 组织 & 团体管理 ]")
        title_main.setStyleSheet(
            f"color: {accent}; font-size: {header_size}px; font-weight: bold; "
            f"font-family: {family}, 'Microsoft YaHei'; padding-bottom: 6px;"
        )
        layout.addWidget(title_main)

        self.subtitle_label = QLabel(">> 加载中...")
        self.subtitle_label.setStyleSheet(
            f"color: {fg}; font-size: {sub_size}px; "
            f"font-family: {family}, 'Microsoft YaHei'; "
            f"border-bottom: 1px solid {border}; padding-bottom: 10px;"
        )
        layout.addWidget(self.subtitle_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {_t('card_bg', '#FFFFFF')};
                width: 10px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background-color: {_t('accent_color', '#0078D4')};
                min-height: 25px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {_t('btn_hover_color', '#106EBE')};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setSpacing(10)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.list_container.setStyleSheet("background-color: transparent;")

        scroll_area.setWidget(self.list_container)
        layout.addWidget(scroll_area, 1)

        action_frame = QFrame()
        action_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        action_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {_t('card_bg', '#FFFFFF')};
                border: 1px solid {border};
                border-radius: {_t('card_radius', '12px')};
                padding: 12px;
                margin-top: 12px;
            }}
        """)
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(18, 14, 18, 14)
        action_layout.setSpacing(15)

        btn_size = self._get_font_size('btn', 19)

        action_title = QLabel("[ 快速操作 ]")
        action_title.setStyleSheet(
            f"color: {accent}; font-size: {sub_size + 1}px; font-weight: bold; "
            f"font-family: {family}, 'Microsoft YaHei';"
        )
        action_layout.addWidget(action_title)

        migrate_btn = QPushButton("[ 初始化所有组织架构 ]")
        migrate_btn.setStyleSheet(self._action_button_style(btn_size, family))
        migrate_btn.clicked.connect(lambda: self.action_triggered.emit("migrate_factions"))
        action_layout.addWidget(migrate_btn)

        add_btn = QPushButton("[ + 新增组织 ]")
        add_btn.setStyleSheet(self._action_button_style(btn_size, family))
        add_btn.clicked.connect(lambda: self.action_triggered.emit("add_faction"))
        action_layout.addWidget(add_btn)

        action_layout.addStretch()
        layout.addWidget(action_frame)

    def _load_data(self):
        try:
            keywords = KeywordManager.load_keywords()
            factions = [kw for kw in keywords if kw.get('type') == 'faction']
            if not factions:
                self._show_empty_state()
                return
            self.subtitle_label.setText(f">> 共找到 {len(factions)} 个组织 :: 点击查看详情")
            self._render_list_items(factions)
        except Exception as e:
            logger.error(f"加载组织列表失败: {e}")
            self._show_error_state(str(e))

    def _render_list_items(self, factions):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for faction in factions:
            list_item = FactionListItem(faction, self.font_config)
            list_item.clicked.connect(self.faction_clicked)
            self.list_layout.addWidget(list_item)

    def _show_empty_state(self):
        accent = _t('accent_color', '#0078D4')
        fg = _t('fg_color', '#212529')
        empty_label = QLabel(
            f"<div style='text-align:center;padding:35px;'>"
            f"<p style='color:{accent};font-size:22px;'>> [ 组织管理 ]</p>"
            f"<p style='margin-top:18px;color:{fg};font-size:18px;'>>>> 暂无组织数据</p>"
            f"<p style='color:{fg};font-size:15px;'>>>> 请在关键词中添加 type=\"faction\" 的条目</p>"
            f"</div>"
        )
        empty_label.setWordWrap(True)
        self.list_layout.addWidget(empty_label)
        self.subtitle_label.setText(">> 暂无组织数据")

    def _show_error_state(self, error_msg):
        error_label = QLabel(
            f"<div style='color:{_t('error_color','#D13438')};padding:18px;font-size:17px;'>>>> 错误: {error_msg}</div>"
        )
        error_label.setWordWrap(True)
        self.list_layout.addWidget(error_label)

    def refresh(self):
        self._load_data()

    def _action_button_style(self, font_size, font_family):
        return f"""
        QPushButton {{
            background-color: {_t('btn_bg_color', '#0078D4')};
            color: #FFFFFF;
            border: none;
            border-radius: {_t('button_radius', '6px')};
            padding: 10px 22px;
            font-size: {font_size}px;
            font-weight: bold;
            font-family: {font_family}, 'Microsoft YaHei';
        }}
        QPushButton:hover {{
            background-color: {_t('btn_hover_color', '#106EBE')};
        }}
        """
