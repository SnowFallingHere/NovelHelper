from PyQt5.QtWidgets import (QPushButton, QLineEdit, QLabel, QGroupBox,
                             QRadioButton, QSpinBox, QComboBox, QHBoxLayout)
from PyQt5.QtCore import Qt
from ..core.theme_manager import theme_manager


def _is_fluent():
    return theme_manager.current_theme_name == 'fluent'


def create_button(text, color=None, on_click=None, min_height=40, min_width=None, kind='primary'):
    t = theme_manager
    btn = QPushButton(text)
    btn.setMinimumHeight(min_height)
    if min_width:
        btn.setMinimumWidth(min_width)

    if _is_fluent():
        accent = t.get('accent_color', '#0078D4')
        hover = t.get('btn_hover_color', '#106EBE')
        radius = t.get('button_radius', '6px')
        font_family = t.get('font_family', "'Segoe UI', 'Microsoft YaHei UI', sans-serif")

        if kind == 'primary':
            bg = accent
            fg = '#FFFFFF'
        elif kind == 'danger':
            bg = t.get('error_color', '#D13438')
            fg = '#FFFFFF'
            hover = '#A82A2A'
        elif kind == 'warning':
            bg = t.get('warn_color', '#FF8C00')
            fg = '#FFFFFF'
            hover = '#CC7000'
        else:
            bg = '#FFFFFF'
            fg = t.get('fg_color', '#212529')
            border = t.get('border_color', '#DEE2E6')
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    color: {fg};
                    border: 1px solid {border};
                    border-radius: {radius};
                    padding: 6px 16px;
                    font-weight: 500;
                    font-family: {font_family};
                    font-size: 14px;
                }}
                QPushButton:hover {{ background-color: #F5F5F5; border-color: #C8C8C8; }}
                QPushButton:pressed {{ background-color: #E8E8E8; }}
            """)
            if on_click:
                btn.clicked.connect(on_click)
            return btn

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: none;
                border-radius: {radius};
                padding: 6px 20px;
                font-weight: 500;
                font-family: {font_family};
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:pressed {{ background-color: {bg}; }}
            QPushButton:disabled {{ background-color: #C8C8C8; color: #999999; }}
        """)
    else:
        if color is None:
            color = t.get('accent_color', '#00FF41')
        radius = t.get('button_radius', '2px')
        font_family = t.get('font_family', "Consolas, Microsoft YaHei, monospace")
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(0,0,0,0);
                border: 2px solid {color};
                border-radius: {radius};
                color: {color};
                padding: 8px 20px;
                font-weight: bold;
                font-family: {font_family};
            }}
            QPushButton:hover {{ background-color: {color}30; }}
            QPushButton:pressed {{ background-color: {color}; color: {t.get('bg_color', '#000')}; }}
        """)

    if on_click:
        btn.clicked.connect(on_click)
    return btn


def create_input(placeholder="", min_height=42, read_only=False):
    t = theme_manager
    inp = QLineEdit()
    inp.setMinimumHeight(min_height)
    inp.setReadOnly(read_only)
    if placeholder:
        inp.setPlaceholderText(placeholder)

    if _is_fluent():
        inp.setStyleSheet(f"""
            QLineEdit {{
                background-color: {t.get('input_bg_color', '#FFFFFF')};
                color: {t.get('fg_color', '#212529')};
                border: 1px solid {t.get('border_color', '#DEE2E6')};
                border-radius: {t.get('input_radius', '6px')};
                padding: 8px 10px;
                font-family: {t.get('font_family', "'Segoe UI', 'Microsoft YaHei UI', sans-serif")};
                font-size: 14px;
                selection-background-color: {t.get('accent_color', '#0078D4')};
                selection-color: #FFFFFF;
            }}
            QLineEdit:focus {{ border: 2px solid {t.get('accent_color', '#0078D4')}; padding: 7px 9px; }}
            QLineEdit:hover {{ border-color: #C8C8C8; }}
        """)
    else:
        inp.setStyleSheet(f"""
            QLineEdit {{
                background-color: {t.get('input_bg_color', '#FFFFFF')};
                color: {t.get('fg_color', '#212529')};
                border: 2px solid {t.get('border_color', '#DEE2E6')};
                border-radius: {t.get('input_radius', '6px')};
                padding: 8px;
                font-family: {t.get('font_family', "'Segoe UI', 'Microsoft YaHei', sans-serif")};
            }}
            QLineEdit:focus {{ border-color: {t.get('accent_color', '#00FF41')}; }}
        """)
    return inp


def create_label(text, color=None, font_size=None, bold=False):
    t = theme_manager
    if color is None:
        color = t.get('fg_color', '#212529')
    if font_size is None:
        font_size = int(t.get('base_font_size', '14'))
    lbl = QLabel(text)
    weight = "bold" if bold else "normal"
    font_family = t.get('font_family', "'Segoe UI', 'Microsoft YaHei UI', sans-serif") if _is_fluent() else t.get('font_family', "Consolas, Microsoft YaHei, monospace")
    lbl.setStyleSheet(f"""
        QLabel {{
            color: {color};
            font-size: {font_size}px;
            font-weight: {weight};
            font-family: {font_family};
        }}
    """)
    return lbl


def create_group_box(title, color=None):
    t = theme_manager
    if color is None:
        color = t.get('accent_color', '#0078D4')

    if _is_fluent():
        gb = QGroupBox(title)
        gb.setStyleSheet(f"""
            QGroupBox {{
                background-color: #FFFFFF;
                border: 1px solid {t.get('border_color', '#DEE2E6')};
                border-radius: {t.get('card_radius', '12px')};
                padding: 32px 20px 20px 20px;
                color: {t.get('fg_color', '#212529')};
                font-weight: 600;
                font-family: {t.get('font_family', "'Segoe UI', 'Microsoft YaHei UI', sans-serif")};
                font-size: 14px;
            }}
            QGroupBox::title {{
                subcontrol-origin: padding;
                left: 20px;
                top: 10px;
                padding: 0 8px;
                color: {t.get('fg_color', '#212529')};
            }}
        """)
        return gb
    else:
        gb = QGroupBox(title)
        gb.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {t.get('border_color', '#00AA30')};
                border-radius: {t.get('widget_radius', '2px')};
                margin-top: 18px;
                margin-bottom: 10px;
                padding-top: 20px;
                color: {color};
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }}
        """)
        return gb


def create_radio(text, color=None, checked=False):
    t = theme_manager
    if color is None:
        color = t.get('accent_color', '#0078D4')
    base_size = int(t.get('base_font_size', '14'))
    font_family = t.get('font_family', "'Segoe UI', 'Microsoft YaHei UI', sans-serif") if _is_fluent() else t.get('font_family', "Consolas, Microsoft YaHei, monospace")
    rb = QRadioButton(text)
    rb.setChecked(checked)
    rb.setStyleSheet(f"""
        QRadioButton {{
            color: {t.get('fg_color', '#212529')};
            font-size: {base_size}px;
            spacing: 8px;
            font-family: {font_family};
        }}
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {color};
            border-radius: 9px;
        }}
        QRadioButton::indicator:checked {{ background-color: {color}; }}
    """)
    return rb


def create_spinbox(min_val=0, max_val=9999, default=0, color=None):
    t = theme_manager
    if color is None:
        color = t.get('accent_color', '#0078D4')
    sb = QSpinBox()
    sb.setRange(min_val, max_val)
    sb.setValue(default)

    if _is_fluent():
        sb.setStyleSheet(f"""
            QSpinBox {{
                background-color: {t.get('input_bg_color', '#FFFFFF')};
                color: {t.get('fg_color', '#212529')};
                border: 1px solid {t.get('border_color', '#DEE2E6')};
                border-radius: {t.get('input_radius', '6px')};
                padding: 5px;
                min-height: 30px;
                font-family: {t.get('font_family', "'Segoe UI', 'Microsoft YaHei UI', sans-serif")};
                font-size: 14px;
            }}
            QSpinBox:focus {{ border: 2px solid {color}; padding: 4px; }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: transparent;
                border: none;
                width: 20px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {color}15;
            }}
        """)
    else:
        sb.setStyleSheet(f"""
            QSpinBox {{
                background-color: {t.get('input_bg_color', '#000804')};
                color: {t.get('fg_color', '#00FF41')};
                border: 2px solid {t.get('border_color', '#00AA30')};
                border-radius: {t.get('input_radius', '2px')};
                padding: 5px;
                min-height: 30px;
                font-family: {t.get('font_family', "Consolas, Microsoft YaHei, monospace")};
            }}
            QSpinBox:focus {{ border-color: {color}; }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {color}30;
                border: none;
                width: 20px;
            }}
        """)
    return sb


def create_combo(items=None, color=None):
    t = theme_manager
    if color is None:
        color = t.get('accent_color', '#0078D4')
    cb = QComboBox()
    if items:
        cb.addItems(items)

    if _is_fluent():
        cb.setStyleSheet(f"""
            QComboBox {{
                background-color: {t.get('input_bg_color', '#FFFFFF')};
                color: {t.get('fg_color', '#212529')};
                border: 1px solid {t.get('border_color', '#DEE2E6')};
                border-radius: {t.get('input_radius', '6px')};
                padding: 8px 14px;
                min-height: 30px;
                font-family: {t.get('font_family', "'Segoe UI', 'Microsoft YaHei UI', sans-serif")};
                font-size: 14px;
            }}
            QComboBox:hover {{ border-color: #C8C8C8; }}
            QComboBox:focus {{ border: 2px solid {color}; padding: 7px 13px; }}
            QComboBox::drop-down {{ border: none; width: 30px; }}
            QComboBox QAbstractItemView {{
                background-color: #FFFFFF;
                color: {t.get('fg_color', '#212529')};
                border: 1px solid {t.get('border_color', '#DEE2E6')};
                border-radius: 6px;
                selection-background-color: {color}20;
                selection-color: {t.get('fg_color', '#212529')};
                padding: 4px;
                font-family: {t.get('font_family', "'Segoe UI', 'Microsoft YaHei UI', sans-serif")};
                font-size: 14px;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                border-radius: 4px;
                color: {t.get('fg_color', '#212529')};
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {color}15;
                color: {t.get('fg_color', '#212529')};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {color}25;
                color: {t.get('fg_color', '#212529')};
            }}
        """)
    else:
        cb.setStyleSheet(f"""
            QComboBox {{
                background-color: {t.get('input_bg_color', '#000804')};
                color: {t.get('fg_color', '#00FF41')};
                border: 2px solid {t.get('border_color', '#00AA30')};
                border-radius: {t.get('input_radius', '2px')};
                padding: 5px;
                min-height: 30px;
                font-family: {t.get('font_family', "Consolas, Microsoft YaHei, monospace")};
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background-color: {t.get('input_bg_color', '#000804')};
                color: {t.get('fg_color', '#00FF41')};
                border: 2px solid {color};
                selection-background-color: {color}30;
            }}
        """)
    return cb


def create_form_row(label_text, widget, label_color=None):
    t = theme_manager
    if label_color is None:
        label_color = t.get('accent_color', '#0078D4')
    layout = QHBoxLayout()
    lbl = create_label(label_text, color=label_color, bold=True)
    lbl.setMinimumWidth(100)
    layout.addWidget(lbl)
    layout.addWidget(widget)
    layout.setStretch(1, 1)
    return layout
