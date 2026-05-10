"""
主题样式工具 — 完全通用化
所有样式函数从当前主题 JSON 读取参数，不区分特定风格
用户创建新主题只需在 themes/ 放入对应的 JSON 文件即可
"""
from ..core.theme_manager import theme_manager


def _t(key, fallback=''):
    return theme_manager.get(key, fallback)


def _is_dark():
    bg = _t('bg_color', '#F8F9FA')
    r, g, b = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
    return (r + g + b) < 384


# ── 全局变量（向后兼容） ──
BG_COLOR = _t('bg_color', '#F8F9FA')
FG_COLOR = _t('fg_color', '#212529')
ACCENT_COLOR = _t('accent_color', '#0078D4')
ACCENT_DIM = _t('accent_dim', '#0078D420')
BORDER_COLOR = _t('border_color', '#DEE2E6')
ERROR_COLOR = _t('error_color', '#D13438')
WARN_COLOR = _t('warn_color', '#FF8C00')
CARD_BG = _t('card_bg', '#FFFFFF')
CARD_BORDER = _t('card_border', '#E5E5E5')
NODE_COLORS = _t('node_colors', {})
GRAPH_BG = _t('graph_bg', '#F8F9FA')
GRAPH_GRID = _t('graph_grid', '#E9ECEF')
GRAPH_ACCENT = _t('graph_accent', '#0078D4')
MATRIX_GRADIENT = _t('matrix_gradient', 'none')
MATRIX_DIM = _t('matrix_dim', 'transparent')
RELATION_COLORS = _t('relation_colors', {})


# ── 通用样式函数（从当前主题 JSON 取值） ──

def button_style():
    t = theme_manager.get_current_theme()
    return f"""
    QPushButton {{
        background-color: {t.get('btn_bg_color', '#0078D4')};
        color: {'#FFFFFF' if not _is_dark() else t.get('fg_color','#00FF41')};
        border: {f"2px solid {t.get('border_color','#00AA30')}" if _is_dark() else 'none'};
        border-radius: {t.get('button_radius','6px')};
        padding: 10px 24px;
        font-weight: {'bold' if _is_dark() else '500'};
        font-family: {t.get('font_family', "'Segoe UI',sans-serif")};
        font-size: 14px;
    }}
    QPushButton:hover {{ background-color: {t.get('btn_hover_color','#106EBE')}; }}
    QPushButton:pressed {{ background-color: {t.get('btn_bg_color','#0078D4')}; }}
    """


def input_style():
    t = theme_manager.get_current_theme()
    return f"""
    QLineEdit, QTextEdit, QTextBrowser {{
        background-color: {t.get('input_bg_color','#FFFFFF')};
        color: {t.get('fg_color','#212529')};
        border: {'2px' if _is_dark() else '1px'} solid {t.get('border_color','#DEE2E6')};
        border-radius: {t.get('input_radius','6px')};
        padding: {'8px' if _is_dark() else '10px 12px'};
        font-family: {t.get('font_family', "'Segoe UI',sans-serif")};
        font-size: 14px;
    }}
    QLineEdit:focus, QTextEdit:focus {{
        border-color: {t.get('accent_color','#0078D4')};
    }}
    """


def group_box_style():
    t = theme_manager.get_current_theme()
    dark = _is_dark()
    return f"""
    QGroupBox {{
        {f"background-color: {t.get('card_bg','#FFFFFF')};" if not dark else ''}
        border: {'2px' if dark else '1px'} solid {t.get('border_color','#DEE2E6')};
        border-radius: {t.get('card_radius','12px')};
        padding: 28px 16px 16px 16px;
         {'padding-top: 20px;' if dark else ''}
        color: {t.get('accent_color' if dark else 'fg_color','#212529')};
        font-weight: {'bold' if dark else '600'};
        font-family: {t.get('font_family', "'Segoe UI',sans-serif")};
        font-size: 14px;
    }}
    QGroupBox::title {{
        subcontrol-origin: padding;
        left: {'15px' if dark else '16px'};
        top: {'4px' if dark else '8px'};
        padding: 0 8px;
        color: {t.get('accent_color' if dark else 'fg_color','#212529')};
    }}
    """


def scrollbar_style():
    t = theme_manager.get_current_theme()
    dark = _is_dark()
    if dark:
        return f"""
        QScrollBar:vertical {{
            border: none; background-color: {t.get('bg_color','#020804')};
            width: 12px; margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {t.get('accent_color','#00FF41')};
            min-height: 20px; border-radius: 6px; margin: 2px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """
    return """
    QScrollBar:vertical { border: none; background-color: transparent; width: 10px; }
    QScrollBar::handle:vertical { background-color: #C8C8C8; min-height: 30px; border-radius: 5px; }
    QScrollBar::handle:vertical:hover { background-color: #A8A8A8; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    """


def checkbox_style():
    t = theme_manager.get_current_theme()
    return f"""
    QCheckBox {{
        color: {t.get('fg_color','#212529')};
        font-family: {t.get('font_family', "'Segoe UI',sans-serif")};
        font-size: 14px; spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 20px; height: 20px;
        border: 2px solid {t.get('accent_color','#0078D4')};
        border-radius: {'2px' if _is_dark() else '4px'};
    }}
    QCheckBox::indicator:checked {{ background-color: {t.get('accent_color','#0078D4')}; }}
    """


def combo_box_style():
    t = theme_manager.get_current_theme()
    fg = t.get('fg_color', '#212529')
    return f"""
    QComboBox {{
        background-color: {t.get('input_bg_color','#FFFFFF')};
        color: {fg};
        border: {'2px' if _is_dark() else '1px'} solid {t.get('border_color','#DEE2E6')};
        border-radius: {t.get('input_radius','6px')};
        padding: {'6px 12px' if _is_dark() else '8px 14px'};
        font-family: {t.get('font_family', "'Segoe UI',sans-serif")};
        font-size: 14px;
    }}
    QComboBox:hover {{ border-color: {t.get('accent_color','#0078D4')}; }}
    QComboBox QAbstractItemView {{
        background-color: {t.get('input_bg_color','#FFFFFF')};
        color: {fg};
        border: 1px solid {t.get('border_color','#DEE2E6')};
        selection-background-color: {t.get('accent_color','#0078D4')}25;
        selection-color: {fg};
        outline: none;
    }}
    QComboBox QAbstractItemView::item {{
        padding: 8px 12px;
        color: {fg};
    }}
    QComboBox QAbstractItemView::item:hover {{
        background-color: {t.get('accent_color','#0078D4')}15;
        color: {fg};
    }}
    QComboBox QAbstractItemView::item:selected {{
        background-color: {t.get('accent_color','#0078D4')}25;
        color: {fg};
    }}
    """


def tab_style():
    t = theme_manager.get_current_theme()
    dark = _is_dark()
    return f"""
    QTabWidget::pane {{
        {f"border: 2px solid {t.get('border_color','#00AA30')};" if dark else 'border: none;'}
        background-color: transparent;
    }}
    QTabBar::tab {{
        color: {t.get('fg_color','#212529')};
        font-weight: {'bold' if dark else '500'};
        border-bottom: 2px solid transparent;
        padding: 8px 16px;
        margin-right: 4px;
        {f"border: 2px solid {t.get('border_color','#00AA30')}; border-bottom: none;" if dark else ''}
    }}
    QTabBar::tab:selected {{
        color: {t.get('accent_color','#0078D4')};
        border-bottom: 2px solid {t.get('accent_color','#0078D4')};
    }}
    QTabBar::tab:last {{
        margin-right: 0;
    }}
    """


def apply_global_stylesheet(app=None):
    """应用全局样式表到应用程序"""
    from PyQt5.QtWidgets import QApplication

    if app is None:
        app = QApplication.instance()
    if not app:
        return

    t = theme_manager.get_current_theme()
    dark = _is_dark()

    stylesheet = f"""
    /* ===== 全局基础样式 ===== */
    * {{
        font-family: {t.get('font_family', "'Segoe UI', 'Microsoft YaHei UI', sans-serif")};
        outline: none;
    }}

    QMainWindow {{
        background-color: {t.get('bg_color', '#F8F9FA')};
    }}

    /* ===== 按钮样式 ===== */
    {button_style()}

    /* ===== 输入框样式 ===== */
    {input_style()}

    /* ===== 分组框样式 ===== */
    {group_box_style()}

    /* ===== 滚动条样式 ===== */
    {scrollbar_style()}

    /* ===== 复选框样式 ===== */
    {checkbox_style()}

    /* ===== 下拉框样式 ===== */
    {combo_box_style()}

    /* ===== 标签页样式 ===== */
    {tab_style()}

    /* ===== 进度条样式 ===== */
    QProgressBar {{
        background-color: {t.get('input_bg_color', '#FFFFFF')};
        border: {'2px' if dark else '1px'} solid {t.get('border_color', '#DEE2E6')};
        border-radius: {t.get('widget_radius', '6px')};
        text-align: center;
        color: {t.get('fg_color', '#212529')};
        font-weight: bold;
    }}
    QProgressBar::chunk {{
        background-color: {t.get('accent_color', '#0078D4')};
        border-radius: {t.get('widget_radius', '6px')};
    }}

    /* ===== 标签样式 ===== */
    QLabel {{
        color: {t.get('fg_color', '#212529')};
        font-family: {t.get('font_family', "'Segoe UI', sans-serif")};
    }}

    /* ===== 分隔线样式 ===== */
    QSplitter::handle {{
        background-color: {t.get('border_color', '#DEE2E6')};
        height: 2px;
    }}

    /* ===== 工具提示样式 ===== */
    QToolTip {{
        background-color: {t.get('card_bg', '#FFFFFF')};
        color: {t.get('fg_color', '#212529')};
        border: 1px solid {t.get('border_color', '#DEE2E6')};
        padding: 6px;
        border-radius: {t.get('widget_radius', '6px')};
    }}

    /* ===== 菜单样式 ===== */
    QMenu {{
        background-color: {t.get('card_bg', '#FFFFFF')};
        color: {t.get('fg_color', '#212529')};
        border: 1px solid {t.get('border_color', '#DEE2E6')};
        border-radius: {t.get('widget_radius', '6px')};
        padding: 4px;
    }}
    QMenu::item:selected {{
        background-color: {t.get('accent_color', '#0078D4')}30;
        color: {t.get('accent_color', '#0078D4')};
    }}

    /* ===== 底部操作栏样式 ===== */
    #bottomBar {{
        background-color: {t.get('card_bg', '#FFFFFF')};
        border-top: 1px solid {t.get('border_color', '#DEE2E6')};
    }}
    #saveExitBtn {{
        padding: 4px 16px;
        font-size: 13px;
        min-width: 100px;
    }}
    """

    app.setStyleSheet(stylesheet)
    logger_info = __import__('logging').getLogger(__name__)
    logger_info.info(f"已应用全局样式表 - 当前主题: {theme_manager.current_theme_name}")
