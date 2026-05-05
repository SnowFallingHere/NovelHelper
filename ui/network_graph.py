import os
import random
import math
import logging
from PyQt5.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsRectItem, 
                              QGraphicsTextItem, QGraphicsPathItem, QGraphicsItem,
                              QGraphicsEllipseItem, QGraphicsItemGroup, QMenu,
                              QGraphicsDropShadowEffect, QAction, QInputDialog,
                              QLineEdit, QToolBar, QVBoxLayout, QWidget, QHBoxLayout,
                              QFrame, QLabel, QListWidget, QWidgetAction, QPushButton, QCheckBox,
                              QScrollArea)
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF, QPropertyAnimation, QEasingCurve, QVariantAnimation
from PyQt5.QtGui import (QFont, QColor, QPen, QBrush, QPainter, QPainterPath, 
                          QLinearGradient, QFontMetrics, QRadialGradient, QPolygonF,
                          QImage, QCursor)
from models.keyword_manager import keyword_manager

logger = logging.getLogger(__name__)

NODE_LABELS = {
    'character': '人物', 'skill': '技能', 'location': '地点',
    'item': '物品', 'foreshadowing': '伏笔',
    'relationship': '关系', 'custom': 'TAG',
    'adventure': '事件', 'faction': '组织', 'time_point': '时间点'
}

RELATION_CATEGORIES = {
    'related_to': {'label': '关联', 'style': 'solid', 'color': '#88aacc', 'width': 1.5, 'arrow': 'none'},
    'friendship': {'label': '友谊', 'style': 'solid', 'color': '#00ff88', 'width': 2, 'arrow': 'none'},
    'romance': {'label': '恋情', 'style': 'solid', 'color': '#ff69b4', 'width': 2, 'arrow': 'none'},
    'hostility': {'label': '敌对', 'style': 'solid', 'color': '#ff4444', 'width': 2.5, 'arrow': 'triangle'},
    'family': {'label': '血缘', 'style': 'solid', 'color': '#ffa500', 'width': 2, 'arrow': 'none'},
    'mentorship': {'label': '师徒', 'style': 'solid', 'color': '#ffd700', 'width': 2, 'arrow': 'triangle'},
    'owns': {'label': '拥有', 'style': 'solid', 'color': '#ffcc00', 'width': 2, 'arrow': 'diamond'},
    'uses': {'label': '使用', 'style': 'solid', 'color': '#ffcc00', 'width': 1.5, 'arrow': 'diamond'},
    'masters': {'label': '掌握', 'style': 'dash', 'color': '#ff4466', 'width': 2, 'arrow': 'circle'},
    'teaches': {'label': '传授', 'style': 'dash', 'color': '#ff4466', 'width': 2, 'arrow': 'circle'},
    'located_at': {'label': '位于', 'style': 'dash_dot', 'color': '#00ccff', 'width': 2, 'arrow': 'square'},
    'travels_to': {'label': '前往', 'style': 'dash_dot', 'color': '#00ccff', 'width': 2, 'arrow': 'square'},
    'participates_in': {'label': '参与', 'style': 'solid', 'color': '#ff8c42', 'width': 3, 'arrow': 'triangle'},
    'triggers': {'label': '触发', 'style': 'solid', 'color': '#ff8c42', 'width': 2.5, 'arrow': 'triangle'},
    'carries': {'label': '背负', 'style': 'dash', 'color': '#ff6b6b', 'width': 2, 'arrow': 'triangle'},
    'hints_at': {'label': '暗示', 'style': 'dot', 'color': '#aaaaaa', 'width': 1.5, 'arrow': 'question'},
    'connects_to': {'label': '连接', 'style': 'dash_dot', 'color': '#4488ff', 'width': 2, 'arrow': 'triangle'},
    'contains': {'label': '包含', 'style': 'dash_dot', 'color': '#4488ff', 'width': 2, 'arrow': 'triangle'},
    'derives_from': {'label': '派生', 'style': 'dash', 'color': '#cc66ff', 'width': 2, 'arrow': 'circle'},
    'counters': {'label': '克制', 'style': 'dash', 'color': '#cc66ff', 'width': 2, 'arrow': 'triangle'},
    'combines_with': {'label': '组合', 'style': 'solid', 'color': '#cc66ff', 'width': 2, 'arrow': 'plus'},
}

class SciFiNodeItem(QGraphicsItem):
    """科幻风格节点 - 自定义绘制，按类型显示不同形状"""
    
    GRAPH_FONT_SIZE = 14
    
    def __init__(self, name, node_type, color, x, y, parent=None):
        super().__init__(parent)
        self.node_name = name
        self.node_type = node_type
        self.base_color = QColor(color)
        self._edges = []
        self._is_pinned = False
        self._on_double_click = None
        self._on_right_click = None
        self._hovered = False
        
        self._drag_start = None
        self._drag_original_pos = None
        self._is_dragging = False
        self._drag_line = None
        
        self._name_font = QFont('Microsoft YaHei', SciFiNodeItem.GRAPH_FONT_SIZE, QFont.Bold)
        fm = QFontMetrics(self._name_font)
        self._text_w = fm.horizontalAdvance(name)
        
        max_w = 160
        if self._text_w > max_w:
            smaller_size = SciFiNodeItem.GRAPH_FONT_SIZE
            while smaller_size > max(8, SciFiNodeItem.GRAPH_FONT_SIZE - 6):
                smaller_size -= 1
                test_font = QFont('Microsoft YaHei', smaller_size, QFont.Bold)
                test_fm = QFontMetrics(test_font)
                if test_fm.horizontalAdvance(name) <= max_w:
                    self._name_font = QFont('Microsoft YaHei', smaller_size, QFont.Bold)
                    self._text_w = test_fm.horizontalAdvance(name)
                    break
        
        self._highlight_color = None
        
        self._node_size = max(80, self._text_w + 40)
        if self.node_type == 'character':
            self._node_size = max(90, self._text_w + 50)
        
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(10)
        self.setAcceptHoverEvents(True)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(self.base_color.red(), self.base_color.green(), self.base_color.blue(), 120))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)
    
    def boundingRect(self):
        s = self._node_size + 20
        return QRectF(-s/2, -s/2, s, s)
    
    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        c = self._highlight_color if self._highlight_color else self.base_color
        s = self._node_size
        half = s / 2
        
        if self._hovered:
            outer_pen = QPen(QColor(c.red(), c.green(), c.blue(), 220), 3)
        else:
            outer_pen = QPen(QColor(c.red(), c.green(), c.blue(), 160), 2)
        
        if self.node_type == 'character':
            self._draw_circle(painter, c, half, outer_pen)
        elif self.node_type == 'skill':
            self._draw_hexagon(painter, c, half, outer_pen)
        elif self.node_type == 'item':
            self._draw_diamond(painter, c, half, outer_pen)
        elif self.node_type == 'foreshadowing':
            self._draw_dashed_rect(painter, c, half, outer_pen)
        elif self.node_type == 'adventure':
            self._draw_adventure(painter, c, half, outer_pen)
        elif self.node_type == 'faction':
            self._draw_faction(painter, c, half, outer_pen)
        elif self.node_type == 'time_point':
            self._draw_time_point(painter, c, half, outer_pen)
        else:
            self._draw_rounded_rect(painter, c, half, outer_pen)
        
        self._draw_label(painter, c, half)
        self._draw_name(painter, half)
        
        if self._is_pinned:
            pin_pen = QPen(QColor(255, 255, 100, 200), 2)
            painter.setPen(pin_pen)
            painter.drawLine(QPointF(-half + 4, -half + 4), QPointF(-half + 14, -half + 14))
            painter.drawLine(QPointF(-half + 4, -half + 14), QPointF(-half + 14, -half + 4))
    
    def _draw_circle(self, painter, c, r, pen):
        painter.setPen(pen)
        grad = QRadialGradient(QPointF(0, 0), r)
        grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 80))
        grad.setColorAt(0.7, QColor(c.red(), c.green(), c.blue(), 40))
        grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 20))
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(QPointF(0, 0), r, r)
        
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
        painter.drawEllipse(QPointF(0, 0), r * 0.75, r * 0.75)
    
    def _draw_hexagon(self, painter, c, r, pen):
        painter.setPen(pen)
        poly = QPolygonF()
        for i in range(6):
            angle = math.pi * 2 * i / 6 - math.pi / 2
            poly.append(QPointF(r * math.cos(angle), r * math.sin(angle)))
        grad = QLinearGradient(QPointF(-r, -r), QPointF(r, r))
        grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 60))
        grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 20))
        painter.setBrush(QBrush(grad))
        painter.drawPolygon(poly)
    
    def _draw_diamond(self, painter, c, r, pen):
        painter.setPen(pen)
        poly = QPolygonF()
        poly.append(QPointF(0, -r))
        poly.append(QPointF(r * 0.65, 0))
        poly.append(QPointF(0, r))
        poly.append(QPointF(-r * 0.65, 0))
        grad = QLinearGradient(QPointF(0, -r), QPointF(0, r))
        grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 60))
        grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 20))
        painter.setBrush(QBrush(grad))
        painter.drawPolygon(poly)
    
    def _draw_dashed_rect(self, painter, c, r, pen):
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        cor = 6
        painter.setBrush(QBrush(QColor(c.red(), c.green(), c.blue(), 20)))
        painter.drawRoundedRect(QRectF(-r * 0.8, -r * 0.6, r * 1.6, r * 1.2), cor, cor)
    
    def _draw_adventure(self, painter, c, r, pen):
        painter.setPen(pen)
        tri_top = QPolygonF()
        tri_top.append(QPointF(0, -r))
        tri_top.append(QPointF(r, 0))
        tri_top.append(QPointF(0, r))
        tri_bottom = QPolygonF()
        tri_bottom.append(QPointF(0, -r))
        tri_bottom.append(QPointF(-r, 0))
        tri_bottom.append(QPointF(0, r))
        grad_top = QLinearGradient(QPointF(0, -r), QPointF(0, r))
        grad_top.setColorAt(0, QColor(255, 140, 66, 80))
        grad_top.setColorAt(1, QColor(255, 140, 66, 30))
        grad_bottom = QLinearGradient(QPointF(0, r), QPointF(0, -r))
        grad_bottom.setColorAt(0, QColor(255, 140, 66, 80))
        grad_bottom.setColorAt(1, QColor(255, 140, 66, 30))
        painter.setBrush(QBrush(grad_top))
        painter.drawPolygon(tri_top)
        painter.setBrush(QBrush(grad_bottom))
        painter.drawPolygon(tri_bottom)
    
    def _draw_faction(self, painter, c, r, pen):
        painter.setPen(pen)
        poly = QPolygonF()
        poly.append(QPointF(0, -r))
        poly.append(QPointF(-r * 0.65, -r * 0.5))
        poly.append(QPointF(-r * 0.65, r * 0.2))
        poly.append(QPointF(0, r))
        poly.append(QPointF(r * 0.65, r * 0.2))
        poly.append(QPointF(r * 0.65, -r * 0.5))
        grad = QLinearGradient(QPointF(0, -r), QPointF(0, r))
        grad.setColorAt(0, QColor(153, 51, 255, 70))
        grad.setColorAt(0.6, QColor(153, 51, 255, 30))
        grad.setColorAt(1, QColor(153, 51, 255, 10))
        painter.setBrush(QBrush(grad))
        painter.drawPolygon(poly)
    
    def _draw_time_point(self, painter, c, r, pen):
        painter.setPen(pen)
        tri_top = QPolygonF()
        tri_top.append(QPointF(-r * 0.65, -r))
        tri_top.append(QPointF(r * 0.65, -r))
        tri_top.append(QPointF(0, 0))
        tri_bottom = QPolygonF()
        tri_bottom.append(QPointF(-r * 0.65, r))
        tri_bottom.append(QPointF(r * 0.65, r))
        tri_bottom.append(QPointF(0, 0))
        grad_top = QLinearGradient(QPointF(0, -r), QPointF(0, 0))
        grad_top.setColorAt(0, QColor(255, 215, 0, 80))
        grad_top.setColorAt(1, QColor(255, 215, 0, 20))
        grad_bottom = QLinearGradient(QPointF(0, r), QPointF(0, 0))
        grad_bottom.setColorAt(0, QColor(255, 215, 0, 80))
        grad_bottom.setColorAt(1, QColor(255, 215, 0, 20))
        painter.setBrush(QBrush(grad_top))
        painter.drawPolygon(tri_top)
        painter.setBrush(QBrush(grad_bottom))
        painter.drawPolygon(tri_bottom)
    
    def _draw_rounded_rect(self, painter, c, r, pen):
        painter.setPen(pen)
        cor = 8
        painter.setBrush(QBrush(QColor(c.red(), c.green(), c.blue(), 20)))
        painter.drawRoundedRect(QRectF(-r * 0.85, -r * 0.6, r * 1.7, r * 1.2), cor, cor)
    
    def _draw_label(self, painter, c, r):
        label = NODE_LABELS.get(self.node_type, 'TAG')
        painter.setFont(QFont('Consolas', 8))
        painter.setPen(QColor(c.red(), c.green(), c.blue(), 180))
        if self.node_type == 'character':
            painter.drawText(QPointF(-r + 2, -r - 8), label)
        elif self.node_type == 'skill':
            painter.drawText(QPointF(-r + 2, -r - 8), label)
        elif self.node_type == 'item':
            painter.drawText(QPointF(-r + 2, -r - 8), label)
        elif self.node_type == 'adventure':
            painter.drawText(QPointF(-r + 2, -r - 8), label)
        elif self.node_type == 'faction':
            painter.drawText(QPointF(-r + 2, -r - 8), label)
        elif self.node_type == 'time_point':
            painter.drawText(QPointF(-r + 2, -r - 8), label)
        else:
            painter.drawText(QPointF(-r * 0.85, -r * 0.6 - 8), label)
    
    def _draw_name(self, painter, r):
        painter.setFont(self._name_font)
        painter.setPen(QColor(255, 255, 255, 250))
        fm = QFontMetrics(self._name_font)
        text_w = fm.horizontalAdvance(self.node_name)
        painter.drawText(QPointF(-text_w / 2, 5), self.node_name)
    
    def set_highlight_color(self, color):
        self._highlight_color = color
        self.update()

    def add_edge_ref(self, edge_data):
        self._edges.append(edge_data)
    
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for edge_data in self._edges:
                if hasattr(edge_data, 'update_positions'):
                    edge_data.update_positions()
        return super().itemChange(change, value)
    
    def hoverEnterEvent(self, event):
        self._hovered = True
        self.setZValue(20)
        shadow = self.graphicsEffect()
        if shadow:
            shadow.setColor(QColor(self.base_color.red(), self.base_color.green(), self.base_color.blue(), 200))
            shadow.setBlurRadius(35)
        views = self.scene().views() if self.scene() else []
        for v in views:
            if isinstance(v, NetworkGraphView):
                SciFiEdge.highlight_node_edges(self.node_name, v.node_items, v.edge_items)
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.setZValue(10)
        shadow = self.graphicsEffect()
        if shadow:
            shadow.setColor(QColor(self.base_color.red(), self.base_color.green(), self.base_color.blue(), 120))
            shadow.setBlurRadius(25)
        views = self.scene().views() if self.scene() else []
        for v in views:
            if isinstance(v, NetworkGraphView):
                SciFiEdge.clear_highlight(v.edge_items)
        self.update()
        super().hoverLeaveEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        if self._on_double_click:
            self._on_double_click(self.node_name)
        super().mouseDoubleClickEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            if self._on_right_click:
                self._on_right_click(self.node_name, event.screenPos(), self.mapToScene(event.pos()))
            event.accept()
            return
        elif event.button() == Qt.LeftButton:
            self._drag_start = event.scenePos()
            self._drag_original_pos = self.pos()
            self._is_dragging = False
            self._drag_line = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_start is not None:
            super().mouseMoveEvent(event)
            dist = (event.scenePos() - self._drag_start).manhattanLength()
            if dist > 20:
                if not self._is_dragging:
                    self._is_dragging = True
                    self._drag_line = QGraphicsPathItem()
                    pen = QPen(QColor(255, 255, 255, 150), 2, Qt.DashLine)
                    self._drag_line.setPen(pen)
                    self._drag_line.setZValue(100)
                    if self.scene():
                        self.scene().addItem(self._drag_line)
                if self._drag_line:
                    path = QPainterPath()
                    path.moveTo(self.pos())
                    path.lineTo(event.scenePos())
                    self._drag_line.setPath(path)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._is_dragging:
            if self._drag_line and self.scene():
                self.scene().removeItem(self._drag_line)
                self._drag_line = None

            items = self.scene().items(event.scenePos()) if self.scene() else []
            target_node = None
            for item in items:
                if isinstance(item, SciFiNodeItem) and item is not self:
                    target_node = item
                    break

            if target_node:
                self.setPos(self._drag_original_pos)
                self._show_relation_menu(target_node)

            self._is_dragging = False
            self._drag_start = None
            self._drag_original_pos = None
            event.accept()
            return

        self._is_dragging = False
        self._drag_start = None
        self._drag_original_pos = None
        if self._drag_line and self.scene():
            self.scene().removeItem(self._drag_line)
            self._drag_line = None
        super().mouseReleaseEvent(event)

    def _show_relation_menu(self, target_node):
        sorted_types = sorted(RELATION_CATEGORIES.items(), key=lambda x: x[1]['label'])
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1a2e;
                color: white;
                border: 1px solid #333;
            }
            QMenu::item:selected {
                background-color: #00ff88;
                color: #1a1a2e;
            }
        """)
        for rel_key, rel_info in sorted_types:
            action = menu.addAction(rel_info['label'])
            action.setData(rel_key)

        chosen = menu.exec_(QCursor.pos())
        if chosen:
            rel_type = chosen.data()
            keyword_manager.add_relationship(self.node_name, target_node.node_name, rel_type, '')
            views = self.scene().views()
            if views:
                view = views[0]
                if isinstance(view, NetworkGraphView):
                    keywords = keyword_manager.load_keywords()
                    view.build_graph(keywords)


class SciFiEdge:
    """科幻风格连线 - 按关系类型区分线型"""
    
    STYLE_MAP = {
        'solid': Qt.SolidLine,
        'dash': Qt.DashLine,
        'dot': Qt.DotLine,
        'dash_dot': Qt.DashDotDotLine,
    }
    
    _current_highlight_node = None
    
    def __init__(self, scene, from_node, to_node, rel_type='related_to'):
        self.scene = scene
        self.from_node = from_node
        self.to_node = to_node
        self.rel_type = rel_type
        self._hovered = False
        self._force_highlight = False
        
        cat = RELATION_CATEGORIES.get(rel_type, RELATION_CATEGORIES['related_to'])
        style_name = cat['style']
        color_hex = cat['color']
        width = cat['width']
        self.arrow_type = cat['arrow']
        
        q_style = self.STYLE_MAP.get(style_name, Qt.SolidLine)
        q_color = QColor(color_hex)
        self._q_color = q_color
        self._q_style = q_style
        self._width = width
        
        self.glow_path = QGraphicsPathItem()
        gp = QPen(QColor(q_color.red(), q_color.green(), q_color.blue(), 25), width * 3.5)
        gp.setCosmetic(True)
        gp.setStyle(q_style)
        self.glow_path.setPen(gp)
        self.glow_path.setZValue(1)
        self.scene.addItem(self.glow_path)
        
        self.edge_path = QGraphicsPathItem()
        ep = QPen(QColor(q_color.red(), q_color.green(), q_color.blue(), 140), width)
        ep.setCosmetic(True)
        ep.setStyle(q_style)
        self.edge_path.setPen(ep)
        self.edge_path.setZValue(2)
        self.scene.addItem(self.edge_path)
        
        self._arrow_item = None
        self._create_arrow_item(q_color)
        
        self.dot = self.scene.addEllipse(-3, -3, 6, 6,
                                          QPen(Qt.NoPen),
                                          QBrush(QColor(q_color.red(), q_color.green(), q_color.blue(), 180)))
        self.dot.setZValue(3)
        
        self._update_path()
        self._apply_dim()
    
    def _create_arrow_item(self, color):
        if self.arrow_type == 'none':
            return
        
        mid_color = QColor(color.red(), color.green(), color.blue(), 220)
        
        if self.arrow_type == 'triangle':
            poly = QPolygonF()
            poly.append(QPointF(8, 0))
            poly.append(QPointF(-5, -5))
            poly.append(QPointF(-5, 5))
            self._arrow_item = self.scene.addPolygon(poly, QPen(Qt.NoPen), QBrush(mid_color))
        
        elif self.arrow_type == 'diamond':
            poly = QPolygonF()
            poly.append(QPointF(8, 0))
            poly.append(QPointF(0, -5))
            poly.append(QPointF(-8, 0))
            poly.append(QPointF(0, 5))
            self._arrow_item = self.scene.addPolygon(poly, QPen(Qt.NoPen), QBrush(mid_color))
        
        elif self.arrow_type == 'circle':
            self._arrow_item = self.scene.addEllipse(-5, -5, 10, 10,
                                                      QPen(Qt.NoPen), QBrush(mid_color))
        
        elif self.arrow_type == 'square':
            self._arrow_item = self.scene.addRect(-5, -5, 10, 10,
                                                   QPen(Qt.NoPen), QBrush(mid_color))
        
        elif self.arrow_type == 'question':
            txt = QGraphicsTextItem('?')
            txt.setDefaultTextColor(mid_color)
            txt.setFont(QFont('Consolas', 12, QFont.Bold))
            txt.setPos(-txt.boundingRect().width() / 2, -txt.boundingRect().height() / 2)
            self.scene.addItem(txt)
            self._arrow_item = txt
        
        elif self.arrow_type == 'plus':
            txt = QGraphicsTextItem('+')
            txt.setDefaultTextColor(mid_color)
            txt.setFont(QFont('Consolas', 14, QFont.Bold))
            txt.setPos(-txt.boundingRect().width() / 2, -txt.boundingRect().height() / 2)
            self.scene.addItem(txt)
            self._arrow_item = txt
        
        if self._arrow_item:
            self._arrow_item.setZValue(3)
    
    def set_hovered(self, hovered):
        self._hovered = hovered
        self._apply_style()
    
    def _apply_dim(self):
        q_color = self._q_color
        width = self._width
        q_style = self._q_style
        ep = QPen(QColor(q_color.red(), q_color.green(), q_color.blue(), 35), width)
        ep.setCosmetic(True)
        ep.setStyle(q_style)
        self.edge_path.setPen(ep)
        gp = QPen(QColor(q_color.red(), q_color.green(), q_color.blue(), 8), width * 2)
        gp.setCosmetic(True)
        gp.setStyle(q_style)
        self.glow_path.setPen(gp)
    
    def _apply_highlight(self):
        q_color = self._q_color
        width = self._width
        q_style = self._q_style
        ep = QPen(QColor(q_color.red(), q_color.green(), q_color.blue(), 255), width + 1.5)
        ep.setCosmetic(True)
        ep.setStyle(q_style)
        self.edge_path.setPen(ep)
        gp = QPen(QColor(q_color.red(), q_color.green(), q_color.blue(), 60), width * 4)
        gp.setCosmetic(True)
        gp.setStyle(q_style)
        self.glow_path.setPen(gp)
    
    def _apply_style(self):
        if self._force_highlight or self._hovered:
            self._apply_highlight()
        else:
            self._apply_dim()
    
    def set_force_highlight(self, on):
        self._force_highlight = on
        self._apply_style()
    
    @classmethod
    def highlight_node_edges(cls, node_name, node_items, edge_items):
        if cls._current_highlight_node == node_name:
            return
        cls._current_highlight_node = node_name
        for edge in edge_items:
            connected = (edge.from_node.node_name == node_name or edge.to_node.node_name == node_name)
            edge.set_force_highlight(connected)
    
    @classmethod
    def clear_highlight(cls, edge_items):
        cls._current_highlight_node = None
        for edge in edge_items:
            edge.set_force_highlight(False)
    
    def _compute_path(self):
        if self.from_node is None or self.to_node is None:
            return QPainterPath(), QPointF(0, 0), 0
        
        from_pos = self.from_node.pos()
        to_pos = self.to_node.pos()
        
        dx = to_pos.x() - from_pos.x()
        dy = to_pos.y() - from_pos.y()
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 1:
            return QPainterPath(), QPointF(0, 0), 0
        
        path = QPainterPath()
        path.moveTo(from_pos)
        
        mid_x = (from_pos.x() + to_pos.x()) / 2
        mid_y = (from_pos.y() + to_pos.y()) / 2
        ctrl_off = min(abs(dx), abs(dy)) * 0.2 + 20
        
        if abs(dx) > abs(dy):
            sgn = 1 if from_pos.y() < to_pos.y() else -1
            c1 = QPointF(mid_x, from_pos.y() + ctrl_off * sgn)
            c2 = QPointF(mid_x, to_pos.y() - ctrl_off * sgn)
        else:
            sgn = 1 if from_pos.x() < to_pos.x() else -1
            c1 = QPointF(from_pos.x() + ctrl_off * sgn, mid_y)
            c2 = QPointF(to_pos.x() - ctrl_off * sgn, mid_y)
        
        path.cubicTo(c1, c2, to_pos)
        
        curve_mid = path.pointAtPercent(0.5)
        eps = 0.001
        p_next = path.pointAtPercent(min(0.5 + eps, 1.0))
        angle = math.degrees(math.atan2(p_next.y() - curve_mid.y(), p_next.x() - curve_mid.x()))
        
        return path, curve_mid, angle
    
    def _update_path(self):
        path, mid, angle = self._compute_path()
        self.glow_path.setPath(path)
        self.edge_path.setPath(path)
        self.dot.setPos(mid)
        if self._arrow_item:
            self._arrow_item.setPos(mid)
            if self.arrow_type not in ('question', 'plus'):
                self._arrow_item.setRotation(angle)
    
    def set_visible(self, visible):
        self.glow_path.setVisible(visible)
        self.edge_path.setVisible(visible)
        self.dot.setVisible(visible)
        if self._arrow_item:
            self._arrow_item.setVisible(visible)

    def update_positions(self):
        self._update_path()


class NodeNavigator(QWidget):
    """节点导向面板 - 嵌入在 NetworkGraphView 左上角"""
    
    def __init__(self, graph_view):
        super().__init__(graph_view.viewport())
        self._graph_view = graph_view
        self._popup = None
        self._font_scale = 1.0
        
        self.setFixedHeight(44)
        self.setStyleSheet("""
            NodeNavigator {
                background-color: rgba(10, 10, 30, 200);
                border: 1px solid #1a4a5a;
                border-radius: 4px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 6, 0)
        layout.setSpacing(6)
        
        self._label = QLabel("节点导向")
        self._label.setStyleSheet("color: #00ff88; font-size: 20px; font-weight: bold;")
        layout.addWidget(self._label)
        
        layout.addStretch()
        
        self._dropdown_btn = QPushButton("▼")
        self._dropdown_btn.setFixedSize(36, 32)
        self._dropdown_btn.setStyleSheet("""
            QPushButton {
                background-color: #001a00;
                color: #00ff88;
                border: 1px solid #00ff88;
                border-radius: 3px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #003300;
            }
        """)
        self._dropdown_btn.clicked.connect(self._toggle_popup)
        layout.addWidget(self._dropdown_btn)
    
    def set_font_scale(self, scale):
        self._font_scale = scale
        self._label.setStyleSheet(f"color: #00ff88; font-size: {max(12, int(20 * scale))}px; font-weight: bold;")
        # 如果弹出菜单已打开，刷新它
        if self._popup and self._popup.isVisible():
            self._popup.close()
            self._show_popup()
    
    def _toggle_popup(self):
        if self._popup and self._popup.isVisible():
            self._popup.close()
            self._popup = None
            return
        self._show_popup()
    
    def _show_popup(self):
        self._popup = QMenu(self)
        self._popup.setStyleSheet("""
            QMenu {
                background-color: #0a0a1e;
                border: 1px solid #1a4a5a;
                padding: 8px;
            }
        """)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(4)
        
        title_bar = QHBoxLayout()
        self._start_select_all = QPushButton("全选")
        self._start_select_all.setFixedSize(int(80 * self._font_scale), int(32 * self._font_scale))
        self._start_select_all.setStyleSheet(f"QPushButton{{background:#001a00;color:#00ff88;border:1px solid #00ff88;font-size:{max(14, int(18 * self._font_scale))}px;}}QPushButton:hover{{background:#003300;}}")
        self._start_select_all.clicked.connect(lambda: self._toggle_check_all(self._start_checkboxes, True))
        title_bar.addWidget(self._start_select_all)
        
        title_bar.addStretch()
        
        arrow_label = QLabel("➜")
        arrow_label.setStyleSheet(f"color: #00ff88; font-size: {max(20, int(28 * self._font_scale))}px;")
        title_bar.addWidget(arrow_label)
        
        title_bar.addStretch()
        
        self._end_select_all = QPushButton("全选")
        self._end_select_all.setFixedSize(int(80 * self._font_scale), int(32 * self._font_scale))
        self._end_select_all.setStyleSheet(f"QPushButton{{background:#110000;color:#ff4466;border:1px solid #ff4466;font-size:{max(14, int(18 * self._font_scale))}px;}}QPushButton:hover{{background:#330000;}}")
        self._end_select_all.clicked.connect(lambda: self._toggle_check_all(self._end_checkboxes, True))
        title_bar.addWidget(self._end_select_all)
        
        layout.addLayout(title_bar)
        
        lists_layout = QHBoxLayout()
        
        self._start_checkboxes = {}
        self._end_checkboxes = {}
        
        # 创建可滚动的起始节点区域
        start_scroll_area = QScrollArea()
        start_scroll_area.setWidgetResizable(True)
        start_scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #1a1a3e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #00ff88;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        self._start_list_widget = QWidget()
        self._start_scroll = QVBoxLayout(self._start_list_widget)
        self._start_scroll.setContentsMargins(0, 0, 0, 0)
        self._start_scroll.setSpacing(max(2, int(2 * self._font_scale)))
        self._start_scroll.addStretch()
        start_scroll_area.setWidget(self._start_list_widget)
        
        # 创建可滚动的结束节点区域
        end_scroll_area = QScrollArea()
        end_scroll_area.setWidgetResizable(True)
        end_scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #1a1a3e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #ff4466;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        self._end_list_widget = QWidget()
        self._end_scroll = QVBoxLayout(self._end_list_widget)
        self._end_scroll.setContentsMargins(0, 0, 0, 0)
        self._end_scroll.setSpacing(max(2, int(2 * self._font_scale)))
        self._end_scroll.addStretch()
        end_scroll_area.setWidget(self._end_list_widget)
        
        lists_layout.addWidget(start_scroll_area)
        lists_layout.addWidget(end_scroll_area)
        
        layout.addLayout(lists_layout)
        
        btn_layout = QHBoxLayout()
        focus_btn = QPushButton("定位节点")
        focus_btn.setStyleSheet(f"QPushButton{{background:#001100;color:#00ff88;border:1px solid #00ff88;padding:{max(6, int(8 * self._font_scale))}px {max(15, int(18 * self._font_scale))}px;border-radius:3px;font-size:{max(15, int(20 * self._font_scale))}px;}}QPushButton:hover{{background:#003300;}}")
        focus_btn.clicked.connect(self._on_focus)
        btn_layout.addWidget(focus_btn)
        
        path_btn = QPushButton("显示路径")
        path_btn.setStyleSheet(f"QPushButton{{background:#001100;color:#ffd700;border:1px solid #ffd700;padding:{max(6, int(8 * self._font_scale))}px {max(15, int(18 * self._font_scale))}px;border-radius:3px;font-size:{max(15, int(20 * self._font_scale))}px;}}QPushButton:hover{{background:#332200;}}")
        path_btn.clicked.connect(self._on_find_path)
        btn_layout.addWidget(path_btn)
        
        clear_btn = QPushButton("清除")
        clear_btn.setStyleSheet(f"QPushButton{{background:#110000;color:#ff4444;border:1px solid #ff4444;padding:{max(6, int(8 * self._font_scale))}px {max(15, int(18 * self._font_scale))}px;border-radius:3px;font-size:{max(15, int(20 * self._font_scale))}px;}}QPushButton:hover{{background:#330000;}}")
        clear_btn.clicked.connect(self._on_clear)
        btn_layout.addWidget(clear_btn)
        
        layout.addLayout(btn_layout)
        
        widget_action = QWidgetAction(self._popup)
        widget_action.setDefaultWidget(container)
        self._popup.addAction(widget_action)
        
        self._popup.setFixedSize(int(450 * self._font_scale), int(450 * self._font_scale))
        
        self._populate_checkboxes()
        
        btn_pos = self._dropdown_btn.mapToGlobal(self._dropdown_btn.rect().bottomLeft())
        self._popup.popup(btn_pos)
        
        self._popup.aboutToHide.connect(lambda: setattr(self, '_popup', None))
    
    def _populate_checkboxes(self):
        self._start_checkboxes.clear()
        self._end_checkboxes.clear()
        self._clear_layout(self._start_scroll)
        self._clear_layout(self._end_scroll)
        
        names = sorted(self._graph_view.node_items.keys())
        for name in names:
            cb_start = QCheckBox(name)
            cb_start.setStyleSheet(f"color:#88aacc;font-size:{max(18, int(22 * self._font_scale))}px;")
            self._start_checkboxes[name] = cb_start
            self._start_scroll.addWidget(cb_start)
            
            cb_end = QCheckBox(name)
            cb_end.setStyleSheet(f"color:#88aacc;font-size:{max(18, int(22 * self._font_scale))}px;")
            self._end_checkboxes[name] = cb_end
            self._end_scroll.addWidget(cb_end)
        
        self._start_scroll.addStretch()
        self._end_scroll.addStretch()
    
    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _toggle_check_all(self, checkboxes_dict, checked):
        for cb in checkboxes_dict.values():
            cb.setChecked(checked)
    
    def _get_checked(self, checkboxes_dict):
        return [name for name, cb in checkboxes_dict.items() if cb.isChecked()]
    
    def _on_focus(self):
        starts = self._get_checked(self._start_checkboxes)
        ends = self._get_checked(self._end_checkboxes)
        targets = starts + ends
        if len(targets) == 1:
            self._graph_view.focus_on_node(targets[0])
        if self._popup:
            self._popup.close()
    
    def _on_find_path(self):
        starts = self._get_checked(self._start_checkboxes)
        ends = self._get_checked(self._end_checkboxes)
        if starts and ends:
            all_paths = []
            for s in starts:
                for e in ends:
                    if s != e:
                        path = self._graph_view.find_shortest_path(s, e)
                        if path:
                            all_paths.append(path)
            if all_paths:
                best = max(all_paths, key=len)
                self._graph_view.highlight_path(best)
        if self._popup:
            self._popup.close()
    
    def _on_clear(self):
        self._graph_view.clear_path_highlight()
        if self._popup:
            self._popup.close()
    
    def refresh_nodes(self):
        self._populate_checkboxes()


class NetworkGraphView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self._is_panning = False
        self._pan_start = None
        
        self.zoom = 1.0
        self.node_items = {}
        self.edge_items = []
        self._legend_group = None
        self._relation_legend_group = None
        self._pinned_nodes = set()
        self._focus_node = None
        self._on_node_double_click = None
        self._on_node_right_click = None
        self._path_highlight_active = False
        self._highlighted_path_nodes = set()

        self._filter_state = {
            'character': True, 'skill': True, 'location': True,
            'item': True, 'foreshadowing': True, 'relationship': True,
            'custom': True, 'adventure': True, 'faction': True, 'time_point': True,
        }
        self._filter_edge_state = {}
        for key in RELATION_CATEGORIES:
            self._filter_edge_state[key] = True
        
        self._navigator = NodeNavigator(self)
        self._position_navigator()
    
    def _position_navigator(self):
        if hasattr(self, '_navigator'):
            self._navigator.move(10, 10)
    
    def update_navigator_font(self, scale):
        if hasattr(self, '_navigator'):
            self._navigator.set_font_scale(scale)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._pin_legend_to_corner()
        self._position_navigator()
    
    MAX_NODES = 200
    LAYOUT_IDEAL_LENGTH = 200.0
    LAYOUT_REPULSION = 50000.0
    LAYOUT_ATTRACTION = 0.01
    LAYOUT_CENTER_GRAVITY = 0.005
    LAYOUT_DAMPING = 0.9
    LAYOUT_ITERATIONS = 150
    GRAPH_FONT_SIZE = 14

    def set_graph_font_size(self, size):
        self.GRAPH_FONT_SIZE = size
        SciFiNodeItem.GRAPH_FONT_SIZE = size

    def set_double_click_callback(self, callback):
        self._on_node_double_click = callback
    
    def set_right_click_callback(self, callback):
        self._on_node_right_click = callback

    def toggle_node_filter(self, node_type, visible):
        if node_type in self._filter_state:
            self._filter_state[node_type] = visible

    def toggle_edge_filter(self, rel_type, visible):
        if rel_type in self._filter_edge_state:
            self._filter_edge_state[rel_type] = visible

    def set_filter_state(self, node_types_visible: dict):
        for node_type, visible in node_types_visible.items():
            if node_type in self._filter_state:
                self._filter_state[node_type] = visible
        self.apply_filter()

    def set_edge_filter_state(self, edge_types_visible: dict):
        for rel_type, visible in edge_types_visible.items():
            if rel_type in self._filter_edge_state:
                self._filter_edge_state[rel_type] = visible
        self.apply_filter()

    def apply_filter(self):
        for name, data in self.node_items.items():
            node_type = data['keyword'].get('type', 'custom')
            visible = self._filter_state.get(node_type, True)
            data['item'].setVisible(visible)

        for edge in self.edge_items:
            rel_type = edge.rel_type
            visible = self._filter_edge_state.get(rel_type, True)
            if visible:
                from_node = edge.from_node
                to_node = edge.to_node
                if from_node and to_node:
                    visible = from_node.isVisible() and to_node.isVisible()
            edge.set_visible(visible)

    def save_layout(self, filepath):
        data = {}
        for name, info in self.node_items.items():
            pos = info['item'].pos()
            data[name] = {'x': pos.x(), 'y': pos.y()}
        try:
            import json
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存布局失败: {e}")
            return False
    
    def load_layout(self, filepath):
        try:
            import json
            if not os.path.exists(filepath):
                return False
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            count = 0
            for name, info in self.node_items.items():
                if name in data:
                    info['item'].setPos(data[name]['x'], data[name]['y'])
                    count += 1
            logger.info(f"已恢复 {count} 个节点位置")
            return True
        except Exception as e:
            logger.error(f"加载布局失败: {e}")
            return False
    
    def export_to_png(self, filepath):
        try:
            rect = self.scene.itemsBoundingRect()
            margin = 50
            rect = rect.adjusted(-margin, -margin, margin, margin)
            img = QImage(rect.size().toSize(), QImage.Format_ARGB32_Premultiplied)
            img.fill(Qt.transparent)
            painter = QPainter(img)
            painter.setRenderHint(QPainter.Antialiasing)
            self.scene.render(painter, source=rect)
            painter.end()
            img.save(filepath)
            return True
        except Exception as e:
            logger.error(f"导出PNG失败: {e}")
            return False
    
    def _pin_legend_to_corner(self):
        vp_rect = self.viewport().rect()
        margin = 15
        inv = 1.0 / max(self.zoom, 0.1)
        if self._legend_group:
            target = vp_rect.topRight() + QPointF(-margin - 150, margin)
            target_scene = self.mapToScene(int(target.x()), int(target.y()))
            self._legend_group.setPos(target_scene.x(), target_scene.y())
            self._legend_group.setScale(inv)
        if hasattr(self, '_relation_legend_group') and self._relation_legend_group:
            target_r = vp_rect.topRight() + QPointF(-margin - 240, margin + 160)
            target_scene_r = self.mapToScene(int(target_r.x()), int(target_r.y()))
            self._relation_legend_group.setPos(target_scene_r.x(), target_scene_r.y())
            self._relation_legend_group.setScale(inv)
    
    def get_isolated_nodes(self):
        connected = set()
        for from_name, info in self.node_items.items():
            edges = info['item']._edges
            if edges:
                connected.add(from_name)
                for edge in edges:
                    if hasattr(edge, 'from_node') and hasattr(edge, 'to_node'):
                        for n, d in self.node_items.items():
                            if d['item'] is edge.to_node:
                                connected.add(n)
                            if d['item'] is edge.from_node:
                                connected.add(n)
        isolated = [n for n in self.node_items if n not in connected]
        return isolated
    
    def drawBackground(self, painter, rect):
        painter.save()
        painter.fillRect(rect, QColor(6, 6, 18))
        
        grid_size = 50
        pen = QPen(QColor(18, 35, 52, 35), 1)
        painter.setPen(pen)
        
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)
        
        lines = []
        x = left
        while x < rect.right():
            lines.append(QPointF(x, rect.top()))
            lines.append(QPointF(x, rect.bottom()))
            x += grid_size
        y = top
        while y < rect.bottom():
            lines.append(QPointF(rect.left(), y))
            lines.append(QPointF(rect.right(), y))
            y += grid_size
        painter.drawLines(lines)
        
        cp = QPen(QColor(0, 255, 136, 22), 1, Qt.DashLine)
        painter.setPen(cp)
        painter.drawLine(QPointF(rect.left(), 0), QPointF(rect.right(), 0))
        painter.drawLine(QPointF(0, rect.top()), QPointF(0, rect.bottom()))
        painter.restore()
    
    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self._pin_legend_to_corner()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._focus_node is not None:
            item = self.itemAt(event.pos())
            if item is None:
                self.exit_focus_mode()
        if event.button() == Qt.LeftButton and self.itemAt(event.pos()) is None:
            SciFiEdge.clear_highlight(self.edge_items)
        if event.button() == Qt.MidButton or (event.button() == Qt.LeftButton and self.itemAt(event.pos()) is None):
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.RightButton and self.itemAt(event.pos()) is None:
            return
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self._is_panning:
            delta = self._pan_start - event.pos()
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        node_item = None
        if isinstance(item, SciFiNodeItem):
            node_item = item
        elif item is not None:
            parent = item
            while parent:
                if isinstance(parent, SciFiNodeItem):
                    node_item = parent
                    break
                parent = parent.parentItem()
        if node_item is not None:
            if node_item._on_double_click:
                node_item._on_double_click(node_item.node_name)
            else:
                self.enter_focus_mode(node_item.node_name)
        elif self._focus_node is not None:
            self.exit_focus_mode()
    
    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 0.87
        self.zoom *= factor
        self.scale(factor, factor)
        QTimer.singleShot(10, self._pin_legend_to_corner)
    
    def clear_graph(self):
        self.scene.clear()
        self.node_items = {}
        self.edge_items = []
        self._legend_group = None
        self._relation_legend_group = None
        self._pinned_nodes = set()
        self._focus_node = None
        self._path_highlight_active = False
        self._highlighted_path_nodes = set()
    
    def build_graph(self, keywords):
        self.clear_graph()
        if not keywords:
            return
        
        if len(keywords) > self.MAX_NODES:
            logger.warning(f"关键词数量 {len(keywords)} 超过限制 {self.MAX_NODES}，仅显示前 {self.MAX_NODES} 个")
            keywords = keywords[:self.MAX_NODES]
        
        type_colors = {
            'character': '#00ff88',
            'skill': '#ff4466',
            'location': '#00ccff',
            'item': '#ffcc00',
            'foreshadowing': '#ff8c42',
            'relationship': '#cc66ff',
            'custom': '#88aacc',
            'adventure': '#ff8c42',
            'faction': '#9933ff',
            'time_point': '#ffd700'
        }
        
        type_order = ['character', 'skill', 'item', 'location',
                      'foreshadowing', 'relationship', 'custom',
                      'adventure', 'faction', 'time_point']
        
        groups = {}
        for kw in keywords:
            t = kw.get('type', 'custom')
            if t not in groups:
                groups[t] = []
            groups[t].append(kw)
        
        import random
        node_positions = {}
        node_sizes = {}
        
        test_font = QFont('Microsoft YaHei', self.GRAPH_FONT_SIZE, QFont.Bold)
        fm = QFontMetrics(test_font)
        
        for kw in keywords:
            name = kw.get('name', '?')
            tw = fm.horizontalAdvance(name) + 50
            w = max(150, tw)
            h = 60
            node_sizes[name] = (w, h)
            node_positions[name] = (random.uniform(-300, 300), random.uniform(-300, 300))
        
        edges_list = []
        for kw in keywords:
            name = kw.get('name')
            if not name:
                continue
            for rel in kw.get('relationships', []):
                target = rel.get('target')
                if target in node_positions:
                    rel_type = rel.get('type', 'related_to')
                    edges_list.append((name, target, rel_type))
        
        char_names = set()
        for kw in keywords:
            if kw.get('type') == 'character':
                char_names.add(kw.get('name'))
        
        for kw in keywords:
            if kw.get('type') == 'character':
                continue
            name = kw.get('name')
            if not name or name not in node_positions:
                continue
            has_edge = any((e[0] == name or e[1] == name) for e in edges_list)
            if not has_edge:
                for char_name in char_names:
                    for k in keywords:
                        if k.get('name') == char_name and k.get('type') == 'character':
                            for rel in k.get('relationships', []):
                                if rel.get('target') == name:
                                    rel_type = rel.get('type', 'related_to')
                                    edges_list.append((char_name, name, rel_type))
                                    break
                            else:
                                continue
                            break
                    else:
                        continue
                    break
        
        ideal_length = self.LAYOUT_IDEAL_LENGTH
        repulsion_strength = self.LAYOUT_REPULSION
        attraction_strength = self.LAYOUT_ATTRACTION
        center_gravity = self.LAYOUT_CENTER_GRAVITY
        damping = self.LAYOUT_DAMPING
        iterations = self.LAYOUT_ITERATIONS
        
        velocities = {name: [0.0, 0.0] for name in node_positions}
        
        for iteration in range(iterations):
            forces = {name: [0.0, 0.0] for name in node_positions}
            
            for n1 in node_positions:
                for n2 in node_positions:
                    if n1 >= n2:
                        continue
                    x1, y1 = node_positions[n1]
                    x2, y2 = node_positions[n2]
                    dx = x1 - x2
                    dy = y1 - y2
                    dist_sq = dx * dx + dy * dy
                    dist = max(dist_sq ** 0.5, 1.0)
                    
                    min_dist = (node_sizes[n1][0] + node_sizes[n2][0]) * 1.2
                    if dist < min_dist:
                        overlap_force = (min_dist - dist) * 2.0
                        fx = overlap_force * dx / dist
                        fy = overlap_force * dy / dist
                        forces[n1][0] += fx
                        forces[n1][1] += fy
                        forces[n2][0] -= fx
                        forces[n2][1] -= fy
                    
                    repulsion = repulsion_strength / dist_sq
                    fx = repulsion * dx / dist
                    fy = repulsion * dy / dist
                    forces[n1][0] += fx
                    forces[n1][1] += fy
                    forces[n2][0] -= fx
                    forces[n2][1] -= fy
            
            for from_name, to_name, _ in edges_list:
                x1, y1 = node_positions[from_name]
                x2, y2 = node_positions[to_name]
                dx = x2 - x1
                dy = y2 - y1
                dist = max((dx * dx + dy * dy) ** 0.5, 1.0)
                
                attraction = attraction_strength * (dist - ideal_length)
                fx = attraction * dx / dist
                fy = attraction * dy / dist
                forces[from_name][0] += fx
                forces[from_name][1] += fy
                forces[to_name][0] -= fx
                forces[to_name][1] -= fy
            
            for name in node_positions:
                x, y = node_positions[name]
                forces[name][0] -= center_gravity * x
                forces[name][1] -= center_gravity * y
            
            max_force = 50.0
            for name in node_positions:
                fx, fy = forces[name]
                force_mag = (fx * fx + fy * fy) ** 0.5
                if force_mag > max_force:
                    fx = fx / force_mag * max_force
                    fy = fy / force_mag * max_force
                
                velocities[name][0] = (velocities[name][0] + fx) * damping
                velocities[name][1] = (velocities[name][1] + fy) * damping
                
                node_positions[name] = (
                    node_positions[name][0] + velocities[name][0],
                    node_positions[name][1] + velocities[name][1]
                )
        
        for kw in keywords:
            name = kw.get('name', '?')
            t = kw.get('type', 'custom')
            color = type_colors.get(t, '#88aacc')
            x, y = node_positions.get(name, (0, 0))
            node = SciFiNodeItem(name, t, color, x, y)
            node._on_double_click = self._on_node_double_click
            node._on_right_click = self._on_node_right_click
            self.scene.addItem(node)
            self.node_items[name] = {'item': node, 'keyword': kw}
        
        for from_name, to_name, rel_type in edges_list:
            if from_name in self.node_items and to_name in self.node_items:
                self._determine_and_add_edge(from_name, to_name, rel_type)
        
        self._add_legend(type_colors, groups)
        self._add_relation_legend()
        QTimer.singleShot(100, self._pin_legend_to_corner)
        self.apply_filter()
    
    def _determine_and_add_edge(self, from_name, to_name, rel_type='related_to'):
        from_item = self.node_items[from_name]['item']
        to_item = self.node_items[to_name]['item']
        edge = SciFiEdge(self.scene, from_item, to_item, rel_type)
        self.edge_items.append(edge)
        from_item.add_edge_ref(edge)
        to_item.add_edge_ref(edge)
    
    def _add_legend(self, type_colors, groups):
        active_types = [t for t in type_colors if t in groups]
        if not active_types:
            return
        
        self._legend_group = QGraphicsItemGroup()
        self._legend_group.setZValue(50)
        
        lw = 150
        lh = len(active_types) * 26 + 36
        
        bg = QGraphicsRectItem(-8, -8, lw, lh, self._legend_group)
        bg.setBrush(QBrush(QColor(6, 6, 18, 200)))
        bg.setPen(QPen(QColor(25, 50, 70, 140), 1))
        
        title = QGraphicsTextItem("NODE TYPES", self._legend_group)
        title.setDefaultTextColor(QColor(0, 255, 136, 180))
        title.setFont(QFont('Consolas', 9, QFont.Bold))
        title.setPos(0, 0)
        
        for i, t in enumerate(active_types):
            c = QColor(type_colors[t])
            y = 24 + i * 26
            
            dot = QGraphicsEllipseItem(0, y + 3, 12, 12, self._legend_group)
            dot.setPen(QPen(Qt.NoPen))
            dot.setBrush(QBrush(c))
            
            lbl = QGraphicsTextItem(NODE_LABELS.get(t, t), self._legend_group)
            lbl.setDefaultTextColor(QColor(180, 200, 218, 200))
            lbl.setFont(QFont('Microsoft YaHei', 9))
            lbl.setPos(20, y)
        
        self.scene.addItem(self._legend_group)
        self._pin_legend_to_corner()
    
    def _add_relation_legend(self):
        sample_styles = [
            ('── 实线', 'solid', '密切关系(友谊/恋情/敌对)'),
            ('- - 虚线', 'dash', '间接关系(掌握/传授/背负)'),
            ('· · 点线', 'dot', '暗示/推测关系(hints_at)'),
            ('-· -· 点划线', 'dash_dot', '空间关系(位于/连接/包含)'),
        ]
        nl = len(sample_styles)
        lw = 240
        lh = nl * 24 + 32
        self._relation_legend_group = QGraphicsItemGroup()
        self._relation_legend_group.setZValue(50)
        
        bg = QGraphicsRectItem(0, 0, lw, lh, self._relation_legend_group)
        bg.setBrush(QBrush(QColor(6, 6, 18, 200)))
        bg.setPen(QPen(QColor(25, 50, 70, 140), 1))
        
        title = QGraphicsTextItem("RELATION TYPES", self._relation_legend_group)
        title.setDefaultTextColor(QColor(0, 255, 136, 180))
        title.setFont(QFont('Consolas', 8, QFont.Bold))
        title.setPos(6, 2)
        
        for i, (label, style_key, desc) in enumerate(sample_styles):
            y = 24 + i * 24
            qs = {'solid': Qt.SolidLine, 'dash': Qt.DashLine, 'dot': Qt.DotLine, 'dash_dot': Qt.DashDotDotLine}[style_key]
            line_y = y + 8
            line_item = QGraphicsPathItem(self._relation_legend_group)
            p = QPainterPath()
            p.moveTo(8, line_y)
            p.lineTo(58, line_y)
            line_item.setPath(p)
            pen = QPen(QColor(0, 255, 136, 200), 1.5)
            pen.setCosmetic(True)
            pen.setStyle(qs)
            line_item.setPen(pen)
            line_item.setZValue(51)
            
            lbl = QGraphicsTextItem(desc, self._relation_legend_group)
            lbl.setDefaultTextColor(QColor(140, 180, 160, 180))
            lbl.setFont(QFont('Microsoft YaHei', 7))
            lbl.setPos(64, y - 1)
        
        self.scene.addItem(self._relation_legend_group)
    
    def focus_on_node(self, node_name):
        if node_name not in self.node_items:
            return False
        item = self.node_items[node_name]['item']
        pos = item.pos()
        
        anim = QVariantAnimation()
        anim.setDuration(400)
        anim.setStartValue(self.mapToScene(self.viewport().rect().center()))
        anim.setEndValue(pos)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.valueChanged.connect(lambda p: self.centerOn(p))
        anim.start()
        
        item.setZValue(30)
        shadow = item.graphicsEffect()
        if shadow:
            shadow.setColor(QColor(255, 255, 255, 200))
            shadow.setBlurRadius(50)
        QTimer.singleShot(1500, lambda: self._reset_node_glow(item))
        
        return True
    
    def _reset_node_glow(self, item):
        if item and item.scene():
            item.setZValue(10)
            shadow = item.graphicsEffect()
            if shadow:
                shadow.setColor(QColor(item.base_color.red(), item.base_color.green(), item.base_color.blue(), 120))
                shadow.setBlurRadius(25)
    
    def enter_focus_mode(self, node_name):
        if node_name not in self.node_items:
            return
        self._focus_node = node_name

        distances = {}
        queue = [(node_name, 0)]
        visited = {node_name}
        distances[node_name] = 0

        while queue:
            current, dist = queue.pop(0)
            if dist >= 2:
                continue
            current_item = self.node_items[current]['item']
            for edge in current_item._edges:
                if not hasattr(edge, 'from_node') or not hasattr(edge, 'to_node'):
                    continue
                neighbor_item = edge.to_node if edge.from_node is current_item else edge.from_node
                neighbor_name = None
                for n, data in self.node_items.items():
                    if data['item'] is neighbor_item:
                        neighbor_name = n
                        break
                if neighbor_name and neighbor_name not in visited:
                    visited.add(neighbor_name)
                    distances[neighbor_name] = dist + 1
                    queue.append((neighbor_name, dist + 1))

        focus_item = self.node_items[node_name]['item']
        focus_item.setOpacity(1.0)
        focus_item.setZValue(30)

        for name, data in self.node_items.items():
            item = data['item']
            if name == node_name:
                continue
            dist = distances.get(name, -1)
            if dist == 1:
                item.setOpacity(1.0)
                item.setZValue(10)
            elif dist == 2:
                item.setOpacity(0.4)
                item.setZValue(10)
            else:
                item.setOpacity(0.08)
                item.setZValue(5)

        for edge in self.edge_items:
            from_name = to_name = None
            for n, data in self.node_items.items():
                if data['item'] is edge.from_node:
                    from_name = n
                if data['item'] is edge.to_node:
                    to_name = n
            if not from_name or not to_name:
                continue
            from_dist = distances.get(from_name, -1)
            to_dist = distances.get(to_name, -1)
            if from_dist == -1 or to_dist == -1 or (from_dist > 2 and to_dist > 2):
                opacity = 0.08
            elif from_dist == 2 or to_dist == 2:
                opacity = 0.4
            else:
                opacity = 1.0
            edge.glow_path.setOpacity(opacity)
            edge.edge_path.setOpacity(opacity)
            edge.dot.setOpacity(opacity)
            if edge._arrow_item:
                edge._arrow_item.setOpacity(opacity)

        self.centerOn(focus_item)
        self.scene.update()

    def exit_focus_mode(self):
        self._focus_node = None
        for data in self.node_items.values():
            item = data['item']
            item.setOpacity(1.0)
            item.setZValue(10)
        for edge in self.edge_items:
            edge.glow_path.setOpacity(1.0)
            edge.edge_path.setOpacity(1.0)
            edge.dot.setOpacity(1.0)
            if edge._arrow_item:
                edge._arrow_item.setOpacity(1.0)
        self._update_highlight()
        self.scene.update()

    def toggle_pin_node(self, node_name):
        if node_name not in self.node_items:
            return
        item = self.node_items[node_name]['item']
        if node_name in self._pinned_nodes:
            self._pinned_nodes.discard(node_name)
            item._is_pinned = False
            self._update_highlight()
        else:
            self._pinned_nodes.add(node_name)
            item._is_pinned = True
            self._update_highlight()
    
    def _update_highlight(self):
        if self._pinned_nodes:
            highlighted_edges = set()
            for name in self._pinned_nodes:
                for edge in self.node_items[name]['item']._edges:
                    if hasattr(edge, 'from_node') and hasattr(edge, 'to_node'):
                        from_name = None
                        to_name = None
                        for n, data in self.node_items.items():
                            if data['item'] is edge.from_node:
                                from_name = n
                            if data['item'] is edge.to_node:
                                to_name = n
                        if from_name and to_name:
                            highlighted_edges.add(edge)
            
            for edge in self.edge_items:
                is_highlighted = edge in highlighted_edges
                edge.set_hovered(is_highlighted)
            
            for name, data in self.node_items.items():
                item = data['item']
                if name in self._pinned_nodes:
                    item.setOpacity(1.0)
                else:
                    has_edge = any(
                        edge in highlighted_edges
                        for edge in item._edges
                        if hasattr(edge, 'from_node')
                    )
                    item.setOpacity(1.0 if has_edge else 0.25)
        else:
            for edge in self.edge_items:
                edge.set_hovered(False)
            for data in self.node_items.values():
                data['item'].setOpacity(1.0)
        self.scene.update()

    def find_shortest_path(self, node_a, node_b):
        if node_a not in self.node_items or node_b not in self.node_items:
            return []
        if node_a == node_b:
            return [node_a]

        adj = {name: [] for name in self.node_items}
        for name, data in self.node_items.items():
            item = data['item']
            for edge in item._edges:
                if not hasattr(edge, 'from_node') or not hasattr(edge, 'to_node'):
                    continue
                neighbor_item = edge.to_node if edge.from_node is item else edge.from_node
                neighbor_name = None
                for n, d in self.node_items.items():
                    if d['item'] is neighbor_item:
                        neighbor_name = n
                        break
                if neighbor_name:
                    adj[name].append(neighbor_name)

        visited = {node_a}
        queue = [[node_a]]
        while queue:
            path = queue.pop(0)
            current = path[-1]
            if current == node_b:
                return path
            for neighbor in adj[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = list(path)
                    new_path.append(neighbor)
                    queue.append(new_path)
        return []

    def highlight_path(self, path):
        self._path_highlight_active = True
        self._highlighted_path_nodes = set(path)

        path_edges = []
        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            a_item = self.node_items[a]['item']
            for edge in a_item._edges:
                if not hasattr(edge, 'from_node') or not hasattr(edge, 'to_node'):
                    continue
                from_n = to_n = None
                for n, d in self.node_items.items():
                    if d['item'] is edge.from_node:
                        from_n = n
                    if d['item'] is edge.to_node:
                        to_n = n
                if (from_n == a and to_n == b) or (from_n == b and to_n == a):
                    path_edges.append(edge)
                    break

        gold_color = QColor(255, 215, 0)
        for name, data in self.node_items.items():
            item = data['item']
            if name in self._highlighted_path_nodes:
                item.setOpacity(1.0)
                item.setZValue(30)
                item.set_highlight_color(gold_color)
            else:
                item.setOpacity(0.08)
                item.setZValue(5)
                item.set_highlight_color(None)

        for edge in self.edge_items:
            if edge in path_edges:
                cat = RELATION_CATEGORIES.get(edge.rel_type, RELATION_CATEGORIES['related_to'])
                style_name = cat['style']
                q_style = SciFiEdge.STYLE_MAP.get(style_name, Qt.SolidLine)
                ep = QPen(gold_color, cat['width'] + 2)
                ep.setCosmetic(True)
                ep.setStyle(q_style)
                edge.edge_path.setPen(ep)
                gp = QPen(QColor(255, 215, 0, 60), (cat['width'] + 2) * 3)
                gp.setCosmetic(True)
                gp.setStyle(q_style)
                edge.glow_path.setPen(gp)
                edge.edge_path.setOpacity(1.0)
                edge.glow_path.setOpacity(1.0)
                edge.dot.setOpacity(1.0)
                if edge._arrow_item:
                    edge._arrow_item.setOpacity(1.0)
            else:
                edge.glow_path.setOpacity(0.08)
                edge.edge_path.setOpacity(0.08)
                edge.dot.setOpacity(0.08)
                if edge._arrow_item:
                    edge._arrow_item.setOpacity(0.08)

        self.scene.update()

    def clear_path_highlight(self):
        if not self._path_highlight_active:
            return
        self._path_highlight_active = False
        self._highlighted_path_nodes = set()

        for data in self.node_items.values():
            item = data['item']
            item.setOpacity(1.0)
            item.setZValue(10)
            item.set_highlight_color(None)

        for edge in self.edge_items:
            cat = RELATION_CATEGORIES.get(edge.rel_type, RELATION_CATEGORIES['related_to'])
            style_name = cat['style']
            color_hex = cat['color']
            width = cat['width']
            q_style = SciFiEdge.STYLE_MAP.get(style_name, Qt.SolidLine)
            q_color = QColor(color_hex)

            ep = QPen(QColor(q_color.red(), q_color.green(), q_color.blue(), 140), width)
            ep.setCosmetic(True)
            ep.setStyle(q_style)
            edge.edge_path.setPen(ep)

            gp = QPen(QColor(q_color.red(), q_color.green(), q_color.blue(), 25), width * 3.5)
            gp.setCosmetic(True)
            gp.setStyle(q_style)
            edge.glow_path.setPen(gp)

            edge.edge_path.setOpacity(1.0)
            edge.glow_path.setOpacity(1.0)
            edge.dot.setOpacity(1.0)
            if edge._arrow_item:
                edge._arrow_item.setOpacity(1.0)

        self.scene.update()
