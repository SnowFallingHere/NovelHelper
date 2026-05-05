from PyQt5.QtWidgets import (QPushButton, QLineEdit, QLabel, QGroupBox, 
                             QRadioButton, QSpinBox, QComboBox, QHBoxLayout)
from PyQt5.QtCore import Qt


def create_button(text, color="#00ff88", on_click=None, min_height=35, min_width=None):
    btn = QPushButton(text)
    btn.setMinimumHeight(min_height)
    if min_width:
        btn.setMinimumWidth(min_width)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: rgba(0,0,0,0);
            border: 2px solid {color};
            border-radius: 8px;
            color: {color};
            padding: 8px 20px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {color}30;
        }}
        QPushButton:pressed {{
            background-color: {color};
            color: #000;
        }}
    """)
    if on_click:
        btn.clicked.connect(on_click)
    return btn


def create_input(placeholder="", min_height=35, read_only=False):
    inp = QLineEdit()
    inp.setMinimumHeight(min_height)
    inp.setReadOnly(read_only)
    if placeholder:
        inp.setPlaceholderText(placeholder)
    inp.setStyleSheet("""
        QLineEdit {
            background-color: #050508;
            color: #ffffff;
            border: 2px solid #1a3a4a;
            border-radius: 8px;
            padding: 8px;
        }
        QLineEdit:focus {
            border-color: #00ff88;
        }
    """)
    return inp


def create_label(text, color="#ffffff", font_size=15, bold=False):
    lbl = QLabel(text)
    weight = "bold" if bold else "normal"
    lbl.setStyleSheet(f"""
        QLabel {{
            color: {color};
            font-size: {font_size}px;
            font-weight: {weight};
        }}
    """)
    return lbl


def create_group_box(title, color="#00ff88"):
    gb = QGroupBox(title)
    gb.setStyleSheet(f"""
        QGroupBox {{
            border: 2px solid #1a3a4a;
            border-radius: 10px;
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


def create_radio(text, color="#00ff88", checked=False):
    rb = QRadioButton(text)
    rb.setChecked(checked)
    rb.setStyleSheet(f"""
        QRadioButton {{
            color: #ffffff;
            font-size: 15px;
            spacing: 8px;
        }}
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {color};
            border-radius: 9px;
        }}
        QRadioButton::indicator:checked {{
            background-color: {color};
        }}
    """)
    return rb


def create_spinbox(min_val=0, max_val=9999, default=0, color="#00ff88"):
    sb = QSpinBox()
    sb.setRange(min_val, max_val)
    sb.setValue(default)
    sb.setStyleSheet(f"""
        QSpinBox {{
            background-color: #050508;
            color: #ffffff;
            border: 2px solid #1a3a4a;
            border-radius: 8px;
            padding: 5px;
            min-height: 30px;
        }}
        QSpinBox:focus {{
            border-color: {color};
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            background-color: {color}30;
            border: none;
            width: 20px;
        }}
    """)
    return sb


def create_combo(items=None, color="#00ff88"):
    cb = QComboBox()
    if items:
        cb.addItems(items)
    cb.setStyleSheet(f"""
        QComboBox {{
            background-color: #050508;
            color: #ffffff;
            border: 2px solid #1a3a4a;
            border-radius: 8px;
            padding: 5px;
            min-height: 30px;
        }}
        QComboBox:focus {{
            border-color: {color};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 25px;
        }}
        QComboBox QAbstractItemView {{
            background-color: #0a0a0f;
            color: #ffffff;
            border: 2px solid {color};
            selection-background-color: {color}30;
        }}
    """)
    return cb


def create_form_row(label_text, widget, label_color="#00ff88"):
    layout = QHBoxLayout()
    lbl = create_label(label_text, color=label_color, bold=True)
    lbl.setMinimumWidth(100)
    layout.addWidget(lbl)
    layout.addWidget(widget)
    layout.setStretch(1, 1)
    return layout
