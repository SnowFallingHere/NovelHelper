from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QFrame, QSizePolicy,
                             QTextBrowser, QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal
import logging
from models.keyword_manager import KeywordManager
from core.theme_manager import theme_manager

logger = logging.getLogger(__name__)

_t = lambda k, d='': theme_manager.get(k, d)


class FactionDetailView(QWidget):
    """
    组织详情视图 — 主题感知
    """

    go_back = pyqtSignal()
    edit_faction = pyqtSignal(str)
    character_clicked = pyqtSignal(str)

    def __init__(self, faction_name, font_config=None, parent=None):
        super().__init__(parent)
        self.faction_name = faction_name
        self.font_config = font_config or {}
        self.structure = None
        self.members = []
        self._init_ui()
        self._load_data()

    def _get_font_size(self, key, default=22):
        return self.font_config.get(key, default)

    def _get_font_family(self):
        return _t('font_family', "'Segoe UI', 'Microsoft YaHei', sans-serif")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)

        family = self._get_font_family()
        nav_size = self._get_font_size('nav', 22)
        title_size = self._get_font_size('title', 30)

        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 6)

        back_btn = QPushButton("<< 返回列表")
        back_btn.setStyleSheet(self._nav_button_style(nav_size, family))
        back_btn.clicked.connect(self.go_back.emit)
        nav_layout.addWidget(back_btn)

        nav_layout.addStretch()

        title_label = QLabel(f"[ {self.faction_name} ]")
        title_label.setStyleSheet(
            f"color: {_t('accent_color', '#0078D4')}; font-size: {title_size}px; font-weight: bold; "
            f"font-family: {family}, 'Microsoft YaHei';"
        )
        nav_layout.addWidget(title_label)

        nav_layout.addStretch()
        layout.addWidget(nav_widget)

        splitter = QSplitter(Qt.Vertical)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {_t('border_color', '#DEE2E6')};
                height: 1px;
            }}
        """)

        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        info_splitter = QSplitter(Qt.Horizontal)

        structure_frame = QFrame()
        structure_frame.setStyleSheet(self._frame_style())
        structure_layout = QVBoxLayout(structure_frame)
        structure_layout.setContentsMargins(20, 15, 20, 15)

        section_size = self._get_font_size('section', 24)

        structure_title = QLabel(">> 组织架构")
        structure_title.setStyleSheet(self._section_title_style(section_size, family))
        structure_layout.addWidget(structure_title)

        self.structure_browser = QTextBrowser()
        self.structure_browser.setOpenLinks(False)
        self.structure_browser.anchorClicked.connect(self._on_structure_link_clicked)
        self.structure_browser.setStyleSheet(self._browser_style(family))
        structure_layout.addWidget(self.structure_browser, 1)

        info_splitter.addWidget(structure_frame)

        right_frame = QFrame()
        right_frame.setStyleSheet(self._frame_style())
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(20, 15, 20, 15)

        members_title = QLabel(">> 成员列表")
        members_title.setStyleSheet(self._section_title_style(section_size, family))
        right_layout.addWidget(members_title)

        self.members_browser = QTextBrowser()
        self.members_browser.setOpenLinks(False)
        self.members_browser.anchorClicked.connect(self._on_member_link_clicked)
        self.members_browser.setStyleSheet(self._browser_style(family))
        right_layout.addWidget(self.members_browser, 1)

        btn_size = self._get_font_size('btn', 22)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)

        edit_btn = QPushButton("[ 编辑架构 ]")
        edit_btn.setStyleSheet(self._action_button_style(btn_size, family))
        edit_btn.clicked.connect(lambda: self.edit_faction.emit(self.faction_name))
        action_layout.addWidget(edit_btn)

        right_layout.addLayout(action_layout)

        info_splitter.addWidget(right_frame)
        info_splitter.setStretchFactor(0, 3)
        info_splitter.setStretchFactor(1, 2)

        top_layout.addWidget(info_splitter, 1)
        splitter.addWidget(top_widget)

        layout.addWidget(splitter, 1)

    def _load_data(self):
        try:
            self.structure = KeywordManager.load_faction_structure(self.faction_name)
            self.members = KeywordManager.get_faction_members(self.faction_name)
            self._render_structure()
            self._render_members()
        except Exception as e:
            logger.error(f"加载组织数据失败 [{self.faction_name}]: {e}")
            self._show_error(str(e))

    def _html_style(self):
        accent = _t('accent_color', '#0078D4')
        fg = _t('fg_color', '#212529')
        dim = _t('accent_dim', '#0078D420')
        font = self._get_font_family()
        return f"<style>body{{color:{fg};font-family:{font};font-size:20px;}}a{{color:{accent};text-decoration:none;font-weight:bold;}}</style>"

    def _render_structure(self):
        if not self.structure or not self.structure.get('roles'):
            html = f"""<style>body{{color:{_t('fg_color','#212529')};font-family:{self._get_font_family()};font-size:20px;}}</style>
                <div style='padding:12px;text-align:center;'>
                    <p>[!!] 暂未配置架构</p>
                    <p style='font-size:11px;margin-top:6px;'>>>> 点击右侧 [ 编辑架构 ] 按钮进行配置</p>
                </div>"""
            self.structure_browser.setHtml(html)
            return

        template_id = self.structure.get('template', 'custom')
        try:
            templates = KeywordManager.load_faction_templates()
            template = templates.get(template_id, {})
            template_name = template.get('name', '自定义架构')
            template_icon = template.get('icon', '')
        except:
            template_name = '自定义架构'
            template_icon = ''

        roles = self.structure.get('roles', {})
        roles_by_level = {}
        for role_id, role_data in roles.items():
            level = role_data.get('level', 0)
            roles_by_level.setdefault(level, []).append((role_id, role_data))

        accent = _t('accent_color', '#0078D4')
        fg = _t('fg_color', '#212529')
        dim = _t('accent_dim', '#0078D420')
        warn = _t('warn_color', '#FF8C00')
        font = self._get_font_family()

        icon_str = f"{template_icon} " if template_icon else ""
        html_parts = [f"""<style>body{{color:{fg};font-family:{font};font-size:20px;}}a{{color:{accent};text-decoration:none;font-weight:bold;}}</style>
            <div style='padding:12px;font-size:20px;'>
                <p style='color:{accent};font-size:20px;margin:0 0 12px 0;'>{icon_str}:: {template_name}</p>"""]

        for level in sorted(roles_by_level.keys()):
            level_roles = roles_by_level[level]
            html_parts.append("<div style='margin-bottom:10px;'>")
            html_parts.append(
                f"<p style='color:{warn};font-size:22px;font-weight:bold;margin:8px 0;'>"
                f"== 层级 {level + 1} ==</p>"
            )
            for role_id, role_data in level_roles:
                title = role_data.get('title', role_id)
                member = role_data.get('member')
                html_parts.append("<div style='margin-left:16px;margin-bottom:6px;'>")
                if member:
                    html_parts.append(
                        f"<span style='color:{accent};font-size:20px;'>| {title}</span>: "
                        f"<a href='character:{member}' style='color:{accent};'>{member}</a>"
                    )
                else:
                    html_parts.append(
                        f"<span style='color:{fg};font-size:20px;'>| {title}</span>: "
                        f"<span style='color:{fg};font-size:20px;'>(空缺)</span>"
                    )
                html_parts.append("</div>")
            html_parts.append("</div>")

        html_parts.append("</div>")
        self.structure_browser.setHtml('\n'.join(html_parts))

    def _render_members(self):
        accent = _t('accent_color', '#0078D4')
        fg = _t('fg_color', '#212529')
        warn = _t('warn_color', '#FF8C00')
        font = self._get_font_family()
        css = f"<style>body{{color:{fg};font-family:{font};font-size:20px;}}a{{color:{accent};text-decoration:none;font-weight:bold;}}</style>"

        if not self.members:
            html = f"""{css}
                <div style='padding:12px;text-align:center;'>
                    <p>[!] 暂无成员</p>
                </div>"""
            self.members_browser.setHtml(html)
            return

        html_parts = [f"{css}<div style='padding:12px;font-size:20px;'>"]
        for idx, member in enumerate(self.members, 1):
            member_name = member.get('name', member) if isinstance(member, dict) else member
            desc = ''
            if isinstance(member, dict):
                desc = member.get('description', '')
                if desc and len(desc) > 40:
                    desc = desc[:37] + "..."
            html_parts.append(
                f"<div style='padding:10px 12px;margin-bottom:8px;"
                f"border-left:2px solid {_t('border_color','#DEE2E6')};'>"
                f"<span style='color:{warn};font-weight:bold;font-size:22px;'>{idx}. </span>"
                f"<a href='character:{member_name}'>{member_name}</a>"
            )
            if desc:
                html_parts.append(f"<br><span style='color:{fg};font-size:18px;margin-left:16px;'>>>> {desc}</span>")
            html_parts.append("</div>")
        html_parts.append("</div>")
        self.members_browser.setHtml('\n'.join(html_parts))

    def _on_structure_link_clicked(self, url):
        url_str = url.toString()
        if url_str.startswith('character:'):
            name = url_str.replace('character:', '')
            self.character_clicked.emit(name)

    def _on_member_link_clicked(self, url):
        url_str = url.toString()
        if url_str.startswith('character:'):
            name = url_str.replace('character:', '')
            self.character_clicked.emit(name)

    def refresh(self):
        self._load_data()

    def _show_error(self, error_msg):
        error_html = f"<div style='color:{_t('error_color','#D13438')};padding:15px;'>>>> 错误: {error_msg}</div>"
        self.structure_browser.setHtml(error_html)
        self.members_browser.setHtml(error_html)

    def _frame_style(self):
        return f"""
        QFrame {{
            background-color: {_t('card_bg', '#FFFFFF')};
            border: 1px solid {_t('border_color', '#DEE2E6')};
            border-radius: {_t('card_radius', '12px')};
        }}
        """

    def _section_title_style(self, font_size, font_family):
        return (
            f"color: {_t('accent_color', '#0078D4')}; font-size: {font_size}px; font-weight: bold; "
            f"font-family: {font_family}, 'Microsoft YaHei'; margin: 0 0 8px 0; "
            f"padding-bottom: 5px; border-bottom: 1px solid {_t('border_color', '#DEE2E6')};"
        )

    def _browser_style(self, font_family):
        return f"""
        QTextBrowser {{
            background-color: {_t('input_bg_color', '#FFFFFF')};
            color: {_t('fg_color', '#212529')};
            border: 1px solid {_t('border_color', '#DEE2E6')};
            border-radius: {_t('input_radius', '6px')};
            padding: 12px;
            font-family: {font_family}, 'Microsoft YaHei';
            font-size: 20px;
        }}
        """

    def _nav_button_style(self, font_size, font_family):
        accent = _t('accent_color', '#0078D4')
        btn_bg = _t('btn_bg_color', '#0078D4')
        return f"""
        QPushButton {{
            background-color: transparent;
            color: {accent};
            border: 1px solid {_t('border_color', '#DEE2E6')};
            border-radius: {_t('button_radius', '6px')};
            padding: 10px 20px;
            font-size: {font_size}px;
            font-family: {font_family}, 'Microsoft YaHei';
        }}
        QPushButton:hover {{
            background-color: {btn_bg};
            color: #FFFFFF;
        }}
        """

    def _action_button_style(self, font_size, font_family, primary=False):
        btn_bg = _t('btn_bg_color', '#0078D4')
        return f"""
        QPushButton {{
            background-color: {btn_bg};
            color: #FFFFFF;
            border: none;
            border-radius: {_t('button_radius', '6px')};
            padding: 12px 24px;
            font-size: {font_size}px;
            font-weight: bold;
            font-family: {font_family}, 'Microsoft YaHei';
        }}
        QPushButton:hover {{
            background-color: {_t('btn_hover_color', '#106EBE')};
        }}
        """
