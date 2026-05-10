from PyQt5.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsItem,
                             QGraphicsObject, QGraphicsTextItem, QGraphicsLineItem,
                             QMenu, QAction, QApplication)
from PyQt5.QtCore import (Qt, QRectF, QPointF, QLineF, pyqtSignal,
                          QEasingCurve, QPropertyAnimation)
from PyQt5.QtGui import (QPainter, QColor, QPen, QBrush, QFont, QLinearGradient,
                         QPainterPath, QRadialGradient, QImage)
import math
import logging
from core.theme_manager import theme_manager

logger = logging.getLogger(__name__)

_t = lambda k, d='': theme_manager.get(k, d)


class FamilyTreeNode(QGraphicsObject):
    """族谱树节点 - 表示一个人物"""

    clicked = pyqtSignal(str)

    def __init__(self, name, gender='unknown', position='', parent=None):
        super().__init__(parent)
        self.name = name
        self.gender = gender
        self.position = position
        self.spouse_node = None
        self.children_nodes = []
        self.parent_nodes = []
        self._width = 150
        self._height = 60
        self._setup_appearance()
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

    def _setup_appearance(self):
        accent = QColor(_t('accent_color', '#0078D4'))
        fg = QColor(_t('fg_color', '#212529'))
        if self.gender == 'male':
            self._color = QColor(60, 110, 180)
            self._border_color = accent
            self._border_style = Qt.SolidLine
        elif self.gender == 'female':
            self._color = QColor(180, 80, 140)
            self._border_color = QColor(220, 120, 200)
            self._border_style = Qt.DashLine
        else:
            self._color = QColor(128, 128, 128)
            self._border_color = fg
            self._border_style = Qt.DotLine

    def boundingRect(self):
        return QRectF(-self._width/2 - 4, -self._height/2 - 24, self._width + 8, self._height + 28)

    def paint(self, painter, option, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.boundingRect()
        painter.setBrush(QBrush(self._color))
        pen = QPen(self._border_color, 2)
        pen.setStyle(self._border_style)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 6, 6)
        hh = self._height / 2
        hw = self._width / 2
        if self.position:
            painter.setFont(QFont('Microsoft YaHei', 9))
            painter.setPen(QColor(220, 210, 130))
            painter.drawText(QPointF(-hw, -hh - 8), self.position)
        painter.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        painter.setPen(Qt.white)
        painter.drawText(QRectF(-hw + 4, -hh + 8, hw * 2 - 8, hh * 2 - 16),
                       Qt.AlignCenter, self.name)
        painter.restore()

    def hoverEnterEvent(self, event):
        self.setOpacity(0.8)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setOpacity(1.0)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.name)
        super().mousePressEvent(event)


class FamilyTreeEdge(QGraphicsLineItem):
    """族谱树边线 - 表示关系"""

    def __init__(self, start_pos, end_pos, relation_type='child', parent=None):
        super().__init__(parent)
        self.relation_type = relation_type
        self.setLine(QLineF(start_pos, end_pos))
        self._setup_style()

    def _setup_style(self):
        accent = _t('accent_color', '#0078D4')
        if self.relation_type == 'spouse':
            pen = QPen(QColor(148, 0, 211), 3)
            pen.setStyle(Qt.DashDotLine)
        elif self.relation_type == 'adopted':
            pen = QPen(QColor(100, 100, 100), 2)
            pen.setStyle(Qt.DashLine)
        else:
            pen = QPen(QColor(accent), 2)
        self.setPen(pen)


class LayoutDirection:
    TOP_TO_BOTTOM = 'top_to_bottom'
    LEFT_TO_RIGHT = 'left_to_right'


class FamilyTreeView(QGraphicsView):
    """族谱树形视图 — 主题感知"""

    node_clicked = pyqtSignal(str)

    def __init__(self, tree_data=None, direction=LayoutDirection.TOP_TO_BOTTOM, parent=None):
        super().__init__(parent)
        self.tree_data = tree_data or {}
        self.direction = direction
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self._setup_view()
        if self.tree_data:
            self.render_tree()

    def _setup_view(self):
        bg = _t('graph_bg', '#F8F9FA')
        self.setBackgroundBrush(QColor(bg))
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setMinimumSize(400, 300)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.wheel_event_enabled = True
        self.zoom_range = (0.1, 5.0)

    def set_tree_data(self, data):
        self.tree_data = data or {}
        self.render_tree()

    def render_tree(self):
        try:
            self.scene.clear()
            self.node_items = {}
            self.edge_items = []
            if not self.tree_data:
                empty_text = self.scene.addText("暂无族谱数据", QFont('Microsoft YaHei', 16))
                empty_text.setDefaultTextColor(QColor(_t('fg_color', '#212529')))
                return
            positions, layer_info = self._calculate_layout(self.tree_data)
            if not positions:
                logger.warning("无法计算族谱布局")
                return
            self._draw_layer_lines(layer_info, positions)
            self._create_nodes_and_edges(positions)
            self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
            self.scale(0.9, 0.9)
            logger.info(f"族谱渲染完成: {len(positions)}个节点, {len(layer_info)}层")
        except Exception as e:
            logger.error(f"渲染族谱失败: {e}")
            import traceback
            traceback.print_exc()

    def _draw_layer_lines(self, layer_info, positions):
        if not layer_info:
            return
        accent = QColor(_t('accent_color', '#0078D4'))
        all_x = [p[0] for p in positions.values()]
        min_x = min(all_x) - 100
        max_x = max(all_x) + 100
        for y_level, names in sorted(layer_info.items()):
            first_name = names[0]
            if first_name not in positions:
                continue
            y_pos = positions[first_name][1] - 40
            line_item = QGraphicsLineItem(min_x, y_pos, max_x, y_pos)
            qcolor = QColor(accent)
            qcolor.setAlpha(40)
            pen = QPen(qcolor, 1, Qt.DashLine)
            line_item.setPen(pen)
            line_item.setZValue(-10)
            self.scene.addItem(line_item)
            level_title = f"LV{y_level + 1}"
            layer_label = self.scene.addText(level_title, QFont('Microsoft YaHei', 10))
            qcolor2 = QColor(accent)
            qcolor2.setAlpha(80)
            layer_label.setDefaultTextColor(qcolor2)
            layer_label.setPos(min_x - 80, y_pos - 10)
            layer_label.setZValue(-9)

    def _calculate_layout(self, node):
        positions = {}
        layer_info = {}
        if not node:
            return positions, layer_info
        node_spacing_x = 260
        node_spacing_y = 180

        def subtree_width(n):
            if not n:
                return 0
            if len(n.get('children', [])) == 0:
                return 1
            return sum(subtree_width(c) for c in n['children'])

        def assign_positions(n, x_offset, y_level):
            if not n:
                return x_offset
            name = n.get('name', '')
            total_w = subtree_width(n)
            center_x = x_offset + (total_w * node_spacing_x) / 2
            y = y_level * node_spacing_y + 100
            if name:
                positions[name] = (center_x, y)
                layer_info.setdefault(y_level, []).append(name)
            spouse = n.get('spouse')
            if spouse:
                sname = spouse.get('name', '')
                if sname:
                    positions[sname] = (center_x + node_spacing_x * 0.7, y)
                    layer_info.setdefault(y_level, []).append(sname)
            x_ptr = x_offset
            for c in n.get('children', []):
                w = subtree_width(c)
                assign_positions(c, x_ptr, y_level + 1)
                x_ptr += w * node_spacing_x
            for p in n.get('parents', []):
                assign_positions(p, x_offset - node_spacing_x * 0.5, y_level - 1)
            return x_offset

        assign_positions(node, 50, 0)
        return positions, layer_info

    def _create_nodes_and_edges(self, positions):
        if not positions or not self.tree_data:
            return
        created_names = set()

        def create_all_nodes(node_data):
            if node_data is None:
                return
            name = node_data.get('name', '')
            if name and name not in created_names and name in positions:
                gender = node_data.get('gender', 'unknown')
                position = node_data.get('position', '')
                x, y = positions[name]
                node_item = FamilyTreeNode(name, gender, position)
                node_item.setPos(x, y)
                self.scene.addItem(node_item)
                self.node_items[name] = node_item
                created_names.add(name)
                node_item.clicked.connect(lambda n=name: self.node_clicked.emit(n))
            spouse = node_data.get('spouse')
            if spouse:
                sname = spouse.get('name', '')
                if sname and sname not in created_names and sname in positions:
                    sg = spouse.get('gender', 'unknown')
                    sp = spouse.get('position', '')
                    sx, sy = positions[sname]
                    si = FamilyTreeNode(sname, sg, sp)
                    si.setPos(sx, sy)
                    self.scene.addItem(si)
                    self.node_items[sname] = si
                    created_names.add(sname)
                    si.clicked.connect(lambda n=sname: self.node_clicked.emit(n))
            for child in node_data.get('children', []):
                create_all_nodes(child)
            for parent in node_data.get('parents', []):
                create_all_nodes(parent)

        create_all_nodes(self.tree_data)

        created_set = set()

        def create_edges(node_data):
            if node_data is None:
                return
            name = node_data.get('name', '')
            if not name or name in created_set:
                return
            created_set.add(name)
            if name not in positions or name not in self.node_items:
                return
            x1, y1 = positions[name]
            node_half_h = 25
            spouse = node_data.get('spouse')
            if spouse:
                sname = spouse.get('name', '')
                if sname and sname in positions and sname in self.node_items:
                    x2, y2 = positions[sname]
                    mid_x = (x1 + x2) / 2
                    line = FamilyTreeEdge(QPointF(x1 + 60, y1), QPointF(x2 - 60, y2), 'spouse')
                    self.scene.addItem(line)
                    self.edge_items.append(line)
            children = node_data.get('children', [])
            if children:
                valid_kids = [c for c in children if c.get('name', '') in positions and c.get('name', '') in self.node_items]
                if valid_kids:
                    min_x = min(positions[c['name']][0] for c in valid_kids)
                    max_x = max(positions[c['name']][0] for c in valid_kids)
                    parent_bottom_y = y1 + node_half_h
                    junction_y = parent_bottom_y + 40
                    vert1 = FamilyTreeEdge(QPointF(x1, parent_bottom_y), QPointF(x1, junction_y), 'child')
                    self.scene.addItem(vert1)
                    self.edge_items.append(vert1)
                    if len(valid_kids) > 1:
                        horiz = FamilyTreeEdge(QPointF(min_x, junction_y), QPointF(max_x, junction_y), 'child')
                        self.scene.addItem(horiz)
                        self.edge_items.append(horiz)
                    for c in valid_kids:
                        cx, cy = positions[c['name']]
                        child_top_y = cy - node_half_h
                        vert2 = FamilyTreeEdge(QPointF(cx, junction_y), QPointF(cx, child_top_y), 'child')
                        self.scene.addItem(vert2)
                        self.edge_items.append(vert2)
                        create_edges(c)
            for p in node_data.get('parents', []):
                pname = p.get('name', '')
                if pname and pname in positions and pname in self.node_items:
                    px, py = positions[pname]
                    parent_bottom = py + node_half_h
                    child_top = y1 - node_half_h
                    mid_y = (parent_bottom + child_top) / 2
                    vert1 = FamilyTreeEdge(QPointF(px, parent_bottom), QPointF(px, mid_y), 'parent')
                    self.scene.addItem(vert1)
                    self.edge_items.append(vert1)
                    vert2 = FamilyTreeEdge(QPointF(px, mid_y), QPointF(x1, mid_y), 'parent')
                    self.scene.addItem(vert2)
                    self.edge_items.append(vert2)
                    vert3 = FamilyTreeEdge(QPointF(x1, mid_y), QPointF(x1, child_top), 'parent')
                    self.scene.addItem(vert3)
                    self.edge_items.append(vert3)
                    create_edges(p)

        create_edges(self.tree_data)

    def wheelEvent(self, event):
        if not self.wheel_event_enabled:
            super().wheelEvent(event)
            return
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        old_scale = self.transform().m11()
        if event.angleDelta().y() > 0:
            new_scale = old_scale * zoom_in_factor
        else:
            new_scale = old_scale * zoom_out_factor
        min_zoom, max_zoom = self.zoom_range
        if new_scale < min_zoom:
            new_scale = min_zoom
        elif new_scale > max_zoom:
            new_scale = max_zoom
        if new_scale != old_scale:
            scale_factor = new_scale / old_scale
            self.scale(scale_factor, scale_factor)
        event.accept()

    def export_to_png(self, filepath):
        try:
            rect = self.scene.itemsBoundingRect()
            image = QImage(int(rect.width() * 2), int(rect.height() * 2), QImage.Format_ARGB32)
            image.fill(Qt.transparent)
            painter = QPainter(image)
            painter.scale(2, 2)
            painter.translate(-rect.topLeft())
            self.scene.render(painter)
            painter.end()
            success = image.save(filepath)
            if success:
                logger.info(f"族谱已导出到: {filepath}")
            else:
                logger.error(f"导出失败: {filepath}")
            return success
        except Exception as e:
            logger.error(f"导出PNG失败: {e}")
            return False

    def reset_view(self):
        self.resetTransform()
        if self.scene.items():
            self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
            self.scale(0.9, 0.9)
