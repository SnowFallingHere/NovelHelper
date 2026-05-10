"""
亚克力无边框窗口基类
- 无边框窗口（隐藏系统标题栏）
- Windows 原生亚克力/Mica 背景
- 自定义标题栏 + 窗口缩放
- 修复移动窗口白色残影：加回 WS_THICKFRAME + 正确处理 WM_NCCALCSIZE
"""
import ctypes
import logging
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt, QRect, QPoint, QEvent, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor

from ..core.theme_manager import theme_manager
from ..core.windows_dwm import enable_acrylic, set_rounded_corners, set_dark_mode, extend_frame
from .title_bar import TitleBar

logger = logging.getLogger(__name__)


class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                ('right', ctypes.c_long), ('bottom', ctypes.c_long)]


class NCCALCSIZE_PARAMS(ctypes.Structure):
    _fields_ = [('rgrc', RECT * 3), ('lppos', ctypes.c_void_p)]


class MSG(ctypes.Structure):
    _fields_ = [('hwnd', ctypes.c_void_p),
                ('message', ctypes.c_uint),
                ('wParam', ctypes.c_ulonglong),
                ('lParam', ctypes.c_longlong)]


class AcrylicMainWindow(QMainWindow):
    """亚克力无边框主窗口基类"""

    BORDER_WIDTH = 4
    dragging = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self._resizing = False
        self._resize_dir = None
        self._resize_start_pos = QPoint()
        self._resize_start_rect = QRect()
        self._acrylic_enabled = False
        self._acrylic_method = 'none'
        self._is_dragging = False
        self._init_window()

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, '_ws_thickframe_added', False):
            self._ws_thickframe_added = True
            self._add_ws_thickframe()

    def _add_ws_thickframe(self):
        """FramelessWindowHint 移除了 WS_THICKFRAME。加回它使 DWM 正确合成亚克力窗口。
        配合 nativeEvent 中 WM_NCCALCSIZE 将客户区设为全窗口，看起来仍是无边框的。"""
        try:
            hwnd = int(self.winId())
            if not hwnd:
                return
            GWL_STYLE = -16
            WS_THICKFRAME = 0x00040000
            SWP_FRAMECHANGED = 0x0020
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            user32.SetWindowLongW(hwnd, GWL_STYLE, style | WS_THICKFRAME)
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)
        except Exception as e:
            logger.warning(f"DWM 样式修复失败: {e}")

    def nativeEvent(self, eventType, message):
        """处理 WM_NCCALCSIZE — 将客户区设为整个窗口区域。
        ws_thickframe 已手动加回，Windows 会发送 NCCALCSIZE 请求。
        rgrc[2] = 窗口整体矩形 → 把客户区 rgrc[0] 设为它 = 无边框。"""
        if eventType == b'windows_generic_MSG':
            msg = ctypes.cast(ctypes.c_void_p(int(message)), ctypes.POINTER(MSG))
            if msg.contents.message == 0x0083:
                if msg.contents.wParam:
                    params = ctypes.cast(ctypes.c_void_p(msg.contents.lParam),
                                         ctypes.POINTER(NCCALCSIZE_PARAMS))
                    try:
                        params.contents.rgrc[0] = params.contents.rgrc[2]
                    except Exception:
                        pass
                return True, 0
        return False, 0

    # ───────── 窗口初始化 ──────────
    def _init_window(self):
        self.setWindowFlags(
            Qt.Window |
            Qt.FramelessWindowHint |
            Qt.WindowSystemMenuHint |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        central = QWidget()
        central.setObjectName('acrylicCentral')
        self._main_layout = QVBoxLayout(central)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        self._title_bar = TitleBar(self)
        self._title_bar.minimized.connect(self.showMinimized)
        self._title_bar.maximized.connect(self._on_maximize)
        self._title_bar.restored.connect(self._on_restore)
        self._title_bar.closed.connect(self.close)
        self._title_bar.drag_started.connect(self._on_drag_started)
        self._title_bar.drag_ended.connect(self._on_drag_ended)

        self._main_layout.addWidget(self._title_bar)

        self._content_widget = QWidget()
        self._content_widget.setObjectName('acrylicContent')
        self._main_layout.addWidget(self._content_widget, 1)

        self.setCentralWidget(central)

    # ────────── 属性 ──────────
    @property
    def content_widget(self):
        return self._content_widget

    @property
    def title_bar(self):
        return self._title_bar

    def _on_drag_started(self):
        self._is_dragging = True

    def _on_drag_ended(self):
        self._is_dragging = False
        self.setCursor(Qt.ArrowCursor)

    # ────────── 亚克力 ──────────
    def enable_acrylic(self, use_mica=False):
        success, method = enable_acrylic(self,
            dark_mode='dark' in theme_manager.get('name', 'matrix'),
            use_mica=use_mica)
        self._acrylic_enabled = success
        self._acrylic_method = method
        if success:
            theme_manager.set('_acrylic_method', method)
        self._update_background()
        return success

    def _update_background(self):
        t = theme_manager
        bg_color = t.get('bg_color', '#F8F9FA')
        self.centralWidget().setStyleSheet(f"""
            QWidget#acrylicCentral {{ background-color: {bg_color}; }}
        """)
        r, g, b = int(bg_color[1:3], 16), int(bg_color[3:5], 16), int(bg_color[5:7], 16)
        if self._acrylic_enabled:
            alpha = 180 if t.get('name') == 'fluent' else 160
            self._content_widget.setStyleSheet(f"""
                QWidget#acrylicContent {{ background-color: rgba({r},{g},{b},{alpha}); }}
            """)
        else:
            self._content_widget.setStyleSheet(f"""
                QWidget#acrylicContent {{ background-color: rgba({r},{g},{b},255); }}
            """)

    def update_acrylic_theme(self):
        t = theme_manager
        is_dark = t.get('name') == 'matrix'
        set_dark_mode(self, is_dark)
        self._title_bar._apply_theme()
        self._update_background()

    def _on_maximize(self):
        self.showMaximized()

    def _on_restore(self):
        self.showNormal()

    def changeEvent(self, event):
        if event.type() == event.WindowStateChange:
            is_max = self.windowState() == Qt.WindowMaximized
            if hasattr(self, '_title_bar'):
                self._title_bar._is_maximized = is_max
                self._title_bar._update_max_icon()
        super().changeEvent(event)

    # ───────── 边缘缩放 ──────────
    def _get_resize_dir(self, pos):
        w, h = self.width(), self.height()
        b = self.BORDER_WIDTH
        dirs = set()
        if pos.x() < b: dirs.add('w')
        elif pos.x() > w - b: dirs.add('e')
        if pos.y() < b: dirs.add('n')
        elif pos.y() > h - b: dirs.add('s')
        return ''.join(sorted(dirs)) if dirs else None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            d = self._get_resize_dir(event.pos())
            if d:
                self._resizing = True
                self._resize_dir = d
                self._resize_start_pos = event.globalPos()
                self._resize_start_rect = self.geometry()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing and self._resize_dir:
            dx = event.globalPos().x() - self._resize_start_pos.x()
            dy = event.globalPos().y() - self._resize_start_pos.y()
            r = QRect(self._resize_start_rect)
            d = self._resize_dir
            if 'w' in d: r.setLeft(r.left() + dx)
            if 'e' in d: r.setRight(r.right() + dx)
            if 'n' in d: r.setTop(r.top() + dy)
            if 's' in d: r.setBottom(r.bottom() + dy)
            if r.width() >= self.minimumWidth() and r.height() >= self.minimumHeight():
                self.setGeometry(r)
            return

        if not self._resizing and not self._is_dragging:
            d = self._get_resize_dir(event.pos())
            if d:
                cursors = {'n': Qt.SizeVerCursor, 's': Qt.SizeVerCursor,
                           'w': Qt.SizeHorCursor, 'e': Qt.SizeHorCursor,
                           'nw': Qt.SizeFDiagCursor, 'se': Qt.SizeFDiagCursor,
                           'ne': Qt.SizeBDiagCursor, 'sw': Qt.SizeBDiagCursor}
                self.setCursor(cursors.get(d, Qt.ArrowCursor))
            else:
                self.setCursor(Qt.ArrowCursor)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._resizing = False
        self._resize_dir = None
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        if not self._acrylic_enabled:
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(theme_manager.get('bg_color', '#F8F9FA')))
            painter.end()
        else:
            QMainWindow.paintEvent(self, event)
