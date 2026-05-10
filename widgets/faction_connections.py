
"""组织架构编辑器 - 动态连线系统
"""

from typing import Optional, Tuple
from PyQt5.QtWidgets import QGraphicsPathItem, QGraphicsTextItem
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QColor, QPen, QBrush, QPainterPath, QPolygonF

from ..core.language_manager import language_manager


def _tr(key):
    return language_manager.tr(key)


class FactionConnection(QGraphicsPathItem):
    """动态连线：跟踪父节点→子节点的贝塞尔曲线
    """

    def __init__(self, parent_node, child_node, connection_type='hierarchy', label='', line_style='bezier', style_config=None):
        super().__init__()
        self.parent_node = parent_node
        self.child_node = child_node
        self.connection_type = connection_type
        self._label_text = label
        self.line_style = line_style
        self.style_config = style_config or {}

        self._label_item = None

        # 设置 z-value 在节点下面
        self.setZValue(-1)

        # 初始更新路径
        self._update_path()

    def set_label(self, text):
        """在线中间显示文字标注
        """
        self._label_text = text
        if not self._label_item:
            from PyQt5.QtWidgets import QGraphicsTextItem
            self._label_item = QGraphicsTextItem(self)
            self._label_item.setDefaultTextColor(QColor('#555555'))
            from PyQt5.QtGui import QFont
            font = QFont('Microsoft YaHei', 9)
            self._label_item.setFont(font)

        self._label_item.setPlainText(text)
        self._update_label_position()

    def _update_label_position(self):
        if self._label_item:
            path = self.path()
            length = path.length()
            mid_point = path.pointAtPercent(0.5)
            self._label_item.setPos(mid_point.x() - 30, mid_point.y() - 10)

    def _update_path(self):
        """根据父子节点当前位置重新计算贝塞尔路径
        """
        if not self.parent_node or not self.child_node:
            return

        p_center = self.parent_node.sceneBoundingRect().center()
        c_center = self.child_node.sceneBoundingRect().center()

        # 根据连线类型选择路径算法
        if self.line_style == 'straight':
            path = self._straight_path(p_center, c_center)
        elif self.line_style == 'polyline':
            path = self._polyline_path(p_center, c_center)
        else:
            path = self._bezier_path(p_center, c_center)

        self.setPath(path)

        # 设置画笔
        color = QColor(self.style_config.get('color', '#666666'))
        width = self.style_config.get('width', 1.5)
        dash = self.style_config.get('dash')
        pen = QPen(color, width)
        if dash:
            pen.setDashPattern(dash)
        self.setPen(pen)

        if self._label_item:
            self._update_label_position()

    def _straight_path(self, p1, p2):
        path = QPainterPath(p1)
        path.lineTo(p2)
        return path

    def _polyline_path(self, p1, p2):
        path = QPainterPath(p1)
        mid_x = (p1.x() + p2.x()) / 2
        path.lineTo(mid_x, p1.y())
        path.lineTo(mid_x, p2.y())
        path.lineTo(p2)
        return path

    def _bezier_path(self, p1, p2):
        path = QPainterPath()
        path.moveTo(p1)
        mid_y = (p1.y() + p2.y()) / 2
        path.cubicTo(
            p1.x(), mid_y,
            p2.x(), mid_y,
            p2.x(), p2.y()
        )
        return path

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)

        # 绘制箭头
        if self.style_config.get('arrow', True):
            self._draw_arrow(painter)

    def _draw_arrow(self, painter):
        path = self.path()
        if path.isEmpty():
            return

        # 获取路径终点
        end_point = path.pointAtPercent(1.0)
        if path.length() < 10:
            return

        # 计算箭头角度
        angle = path.angleAtPercent(1.0)

        arrow_size = 8
        painter.save()
        painter.translate(end_point)
        painter.rotate(-angle)
        painter.setBrush(QBrush(self.pen().color()))
        painter.setPen(Qt.NoPen)

        # 绘制三角形箭头
        arrow = QPolygonF([
            QPointF(0, 0),
            QPointF(-arrow_size, -arrow_size / 2),
            QPointF(-arrow_size, arrow_size / 2)
        ])
        painter.drawPolygon(arrow)
        painter.restore()

