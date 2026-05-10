"""
Fluent 风格自定义标题栏
支持：
- 窗口拖拽
- 最小化/最大化/关闭按钮（Win11 风格）
- 双击最大化/还原
- 右键系统菜单
- 主题感知的颜色
"""
import logging
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton,
    QApplication, QMenu, QAction
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPainterPath

from ..core.theme_manager import theme_manager

logger = logging.getLogger(__name__)


class TitleBarButton(QPushButton):
    """标题栏按钮（最小化/最大化/关闭）"""
    
    def __init__(self, btn_type='close', parent=None):
        super().__init__(parent)
        self._btn_type = btn_type
        self.setFixedSize(46, 32)
        self.setCursor(Qt.ArrowCursor)
        self._hovered = False
        
    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        t = theme_manager
        bg_val = t.get('bg_color', '#F8F9FA')
        fg_val = t.get('fg_color', '#212529')
        r, g, b = int(bg_val[1:3],16), int(bg_val[3:5],16), int(bg_val[5:7],16)
        is_dark = (r + g + b) < 384
        
        if self._hovered:
            if self._btn_type == 'close':
                painter.fillRect(0, 0, w, h, QColor('#E81123'))
            else:
                hover_bg = QColor(255, 255, 255, 25) if is_dark else QColor(0, 0, 0, 15)
                painter.fillRect(0, 0, w, h, hover_bg)
        
        # 图标颜色
        icon_color = QColor('#FFFFFF') if self._btn_type == 'close' and self._hovered else \
                     QColor(fg_val)
        
        painter.setPen(QPen(icon_color, 1.5))
        
        cx, cy = w // 2, h // 2
        
        if self._btn_type == 'close':
            # X 图标
            painter.drawLine(cx - 5, cy - 5, cx + 5, cy + 5)
            painter.drawLine(cx + 5, cy - 5, cx - 5, cy + 5)
        
        elif self._btn_type == 'maximize':
            # 方框图标
            painter.drawRect(cx - 5, cy - 5, 10, 10)
        
        elif self._btn_type == 'minimize':
            # 横线图标
            painter.drawLine(cx - 5, cy, cx + 5, cy)
        
        elif self._btn_type == 'restore':
            # 重叠方框
            painter.drawRect(cx - 4, cy - 6, 8, 8)
            painter.drawRect(cx - 6, cy - 4, 8, 8)
        
        painter.end()


class TitleBar(QWidget):
    """自定义标题栏"""
    
    minimized = pyqtSignal()
    maximized = pyqtSignal()
    restored = pyqtSignal()
    closed = pyqtSignal()
    drag_started = pyqtSignal()
    drag_ended = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self._is_maximized = False
        self._drag_pos = QPoint()
        self._dragging = False
        
        self._init_ui()
        self._apply_theme()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(0)
        
        # 标题/图标
        self._icon_label = QLabel("📖")
        self._icon_label.setFixedWidth(24)
        icon_font = QFont('Segoe UI Emoji', 12)
        self._icon_label.setFont(icon_font)
        layout.addWidget(self._icon_label)
        
        self._title_label = QLabel("NovelHelper")
        title_font = QFont('Segoe UI', 10)
        self._title_label.setFont(title_font)
        layout.addWidget(self._title_label)
        
        layout.addStretch()
        
        # 标题栏按钮
        self._min_btn = TitleBarButton('minimize', self)
        self._max_btn = TitleBarButton('maximize', self)
        self._close_btn = TitleBarButton('close', self)
        
        self._min_btn.clicked.connect(self.minimized.emit)
        self._max_btn.clicked.connect(self._toggle_maximize)
        self._close_btn.clicked.connect(self.closed.emit)
        
        layout.addWidget(self._min_btn)
        layout.addWidget(self._max_btn)
        layout.addWidget(self._close_btn)
    
    def _apply_theme(self):
        t = theme_manager
        bg = t.get('bg_color', '#F8F9FA')
        fg = t.get('fg_color', '#212529')
        self.setStyleSheet(f"""
            TitleBar {{
                background-color: {bg};
                border: none;
            }}
        """)
        self._title_label.setStyleSheet(f"color: {fg}; background: transparent;")
    
    def _toggle_maximize(self):
        if self._is_maximized:
            self.restored.emit()
        else:
            self.maximized.emit()
        self._is_maximized = not self._is_maximized
        self._update_max_icon()
    
    def _update_max_icon(self):
        from PyQt5.QtWidgets import QPushButton
        # 通过替换按钮实现图标切换
        idx = self.layout().indexOf(self._max_btn)
        self.layout().takeAt(self.layout().count() - 2)
        self._max_btn.deleteLater()
        
        btn_type = 'restore' if self._is_maximized else 'maximize'
        self._max_btn = TitleBarButton(btn_type, self)
        self._max_btn.clicked.connect(self._toggle_maximize)
        self.layout().insertWidget(self.layout().count() - 1, self._max_btn)
    
    def set_title(self, text):
        self._title_label.setText(text)
    
    def set_icon(self, icon_text):
        self._icon_label.setText(icon_text)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.parent().frameGeometry().topLeft()
            self._dragging = True
            self._click_pos = event.globalPos()
            self.drag_started.emit()
        elif event.button() == Qt.RightButton:
            self._show_system_menu(event.globalPos())
    
    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.LeftButton:
            parent = self.parent()
            if self._is_maximized:
                ratio = event.pos().x() / self.width()
                self._toggle_maximize()
                self._drag_pos = QPoint(int(parent.width() * ratio), event.pos().y())
            parent.move(event.globalPos() - self._drag_pos)
    
    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            self.drag_ended.emit()
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_maximize()
    
    def _show_system_menu(self, pos):
        menu = QMenu(self)
        restore_action = QAction("还原", self)
        restore_action.triggered.connect(lambda: self.restored.emit() if self._is_maximized else None)
        menu.addAction(restore_action)
        
        move_action = QAction("移动", self)
        menu.addAction(move_action)
        
        size_action = QAction("大小", self)
        menu.addAction(size_action)
        
        menu.addSeparator()
        
        min_action = QAction("最小化", self)
        min_action.triggered.connect(self.minimized.emit)
        menu.addAction(min_action)
        
        max_action = QAction("最大化" if not self._is_maximized else "还原", self)
        max_action.triggered.connect(self._toggle_maximize)
        menu.addAction(max_action)
        
        menu.addSeparator()
        
        close_action = QAction("关闭", self)
        close_action.triggered.connect(self.closed.emit)
        menu.addAction(close_action)
        
        menu.exec_(pos)
