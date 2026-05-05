BG_COLOR = "#020804"
FG_COLOR = "#00FF41"
ACCENT_COLOR = "#00FF41"
ACCENT_DIM = "#00FF4130"
BORDER_COLOR = "#00AA30"
ERROR_COLOR = "#FF3333"
WARN_COLOR = "#FFAA00"
CARD_BG = "rgba(0,10,4,0.97)"
CARD_BORDER = "#00AA30"

NODE_COLORS = {
    'character': '#00ff88',
    'skill': '#ff4466',
    'location': '#00ccff',
    'item': '#ffcc00',
    'foreshadowing': '#ff8c42',
    'adventure': '#ff66cc',
    'faction': '#88ccff',
    'time_point': '#ffd700',
    'relationship': '#cc66ff',
    'custom': '#88aacc',
}

GRAPH_BG = "#060612"
GRAPH_GRID = "#0a1a10"
GRAPH_ACCENT = "#00ff41"

MATRIX_GRADIENT = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00ff41, stop:0.5 #008822, stop:1 #004411)"
MATRIX_DIM = "#005522"

RELATION_COLORS = {
    'related_to': '#88aacc',
    'friendship': '#00ff88',
    'romance': '#ff69b4',
    'hostility': '#ff4444',
    'master_student': '#ffd700',
    'family': '#66ccff',
    'colleague': '#66ff66',
    'belongs_to': '#cc66ff',
    'located_in': '#00ccff',
    'owns': '#ffcc00',
    'uses': '#ff66cc',
    'leads': '#ff8c42',
    'opposes': '#ff0000',
    'depends_on': '#9999ff',
    'causes': '#ff9933',
    'prevents': '#33ccff',
    'resolves': '#66ff99',
    'hints_at': '#cc99ff',
    'conflicts_with': '#ff3366',
    'replaces': '#ff9966',
    'merges_with': '#66cc99',
}


def button_style(color=ACCENT_COLOR, bg_hover=None):
    bg_hover = bg_hover or "#003300"
    return f"""
    QPushButton {{
        background-color: rgba(0,0,0,0);
        border: 2px solid {color};
        border-radius: 2px;
        color: {color};
        padding: 8px 20px;
        font-weight: bold;
        font-family: 'Consolas', monospace;
    }}
    QPushButton:hover {{
        background-color: {bg_hover};
        border-color: #00ff41;
    }}
    QPushButton:pressed {{
        background-color: {color};
        color: #000;
    }}
    """


def input_style(border_color=BORDER_COLOR):
    return f"""
    QLineEdit, QTextEdit, QTextBrowser {{
        background-color: #000804;
        color: {FG_COLOR};
        border: 2px solid {border_color};
        border-radius: 2px;
        padding: 8px;
        font-family: 'Consolas', 'Microsoft YaHei', monospace;
    }}
    QLineEdit:focus, QTextEdit:focus {{
        border-color: {ACCENT_COLOR};
    }}
    """


def group_box_style(border_color=BORDER_COLOR):
    return f"""
    QGroupBox {{
        border: 2px solid {border_color};
        border-radius: 2px;
        margin-top: 18px;
        margin-bottom: 10px;
        padding-top: 20px;
        color: {ACCENT_COLOR};
        font-weight: bold;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 15px;
        padding: 0 8px;
        color: {ACCENT_COLOR};
    }}
    """


def tab_style():
    return f"""
    QTabWidget::pane {{
        border: 2px solid {BORDER_COLOR};
        border-radius: 2px;
        background-color: {BG_COLOR};
    }}
    QTabBar::tab {{
        background-color: rgba(0,0,0,0);
        border: 2px solid {BORDER_COLOR};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        padding: 10px 25px;
        color: {FG_COLOR};
        font-weight: bold;
        min-height: 35px;
        font-family: 'Consolas', monospace;
    }}
    QTabBar::tab:selected {{
        background-color: {BG_COLOR};
        border-color: {ACCENT_COLOR};
        color: {ACCENT_COLOR};
    }}
    QTabBar::tab:hover {{
        border-color: {ACCENT_DIM};
    }}
    """
