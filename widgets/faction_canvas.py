
"""组织架构编辑器 - 可视化画布核心
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from PyQt5.QtWidgets import (
    QFileDialog,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QToolBar,
    QVBoxLayout,
    QWidget
)
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QImage, QFont

from .faction_nodes import EditableNode, GroupBoxNode, TextAnnotation
from .faction_connections import FactionConnection
from .faction_tools import (
    EditorTool, AlignmentManager, ArrowTool, CommandStack,
    MoveNodeCommand, ChangeTextCommand, AddNodeCommand, RemoveNodeCommand
)
from ..core.language_manager import language_manager
from ..core.theme_manager import theme_manager


def _tr(key):
    return language_manager.tr(key)


class LevelGuideLine(QGraphicsLineItem):
    """动态层级虚线：根据 level_config._available 自动生成
    """

    def __init__(self, level_value, y_pos, label_format='LV{value}', parent=None):
        super().__init__(parent)
        self.level = level_value
        self.setLine(-9999, y_pos, 9999, y_pos)
        pen = QPen(QColor('#AAAAAA'), 1, Qt.DashLine)
        pen.setDashPattern([6, 4])
        self.setPen(pen)
        self.setZValue(-2)

        # 左侧 LV 标签
        self._label = QGraphicsTextItem(label_format.format(value=level_value), self)
        self._label.setDefaultTextColor(QColor('#888888'))
        self._label.setPos(-550, y_pos - 10)
        font = QFont('Microsoft YaHei', 10)
        self._label.setFont(font)


def _create_level_guides(scene, level_config, base_y=0, spacing=80):
    """根据 level_config 动态生成所有层级虚线
    """
    guides = []
    label_format = level_config.get('label_format', 'LV{value}')
    for i, lv in enumerate(level_config.get('_available', [])):
        y = base_y + i * spacing
        guide = LevelGuideLine(lv, y, label_format)
        scene.addItem(guide)
        guides.append(guide)
    return guides


class FactionCanvas(QGraphicsView):
    """可视化编辑画布
    """

    structure_changed = pyqtSignal(dict)
    edit_mode_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        # 配置主题背景
        t = theme_manager.get_current_theme()
        self.setStyleSheet(f"""
            QGraphicsView {{
                background-color: {t.get('graph_bg', '#F8F9FA')};
            }}
        """)

        # 工具状态
        self._current_tool = EditorTool.SELECT
        self._edit_mode = False

        # 子系统
        self._nodes = {}
        self._node_data = {}
        self._connections = []
        self._annotations = []
        self._group_boxes = []
        self._level_guides = []
        self._command_stack = CommandStack()
        self._alignment_manager = AlignmentManager(self._scene)
        self._arrow_tool = ArrowTool(self._scene)

        # 数据
        self._faction_tree_data = None
        self._level_config = None

        # 拖动状态
        self._dragging_node = None
        self._drag_start_pos = None
        self._mouse_press_pos = None

    def set_edit_mode(self, enabled):
        """切换编辑/预览模式
        """
        self._edit_mode = enabled
        for node in self._nodes.values():
            node.setFlag(QGraphicsItem.ItemIsMovable, enabled)
            node.setFlag(QGraphicsItem.ItemIsSelectable, enabled)
        for box in self._group_boxes:
            box.setFlag(QGraphicsItem.ItemIsMovable, enabled)
            box.setFlag(QGraphicsItem.ItemIsSelectable, enabled)
        for ann in self._annotations:
            ann.setFlag(QGraphicsItem.ItemIsMovable, enabled)
            ann.setFlag(QGraphicsItem.ItemIsSelectable, enabled)
        self.edit_mode_changed.emit(enabled)

    def load_faction_tree_file(self, file_path):
        """从 factiontree_node.json 文件加载
        """
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.load_faction_tree_data(data)
            return True
        return False

    def load_faction_tree_data(self, data):
        """从数据结构加载
        """
        self._clear_all()
        self._faction_tree_data = data
        self._level_config = data.get('level_config', {})
        node_styles = data.get('node_styles', {})
        line_styles = data.get('line_styles', {})
        layout = data.get('layout', {})

        # 创建层级辅助线
        vertical_spacing = layout.get('vertical_spacing', 80)
        self._level_guides = _create_level_guides(
            self._scene, self._level_config, base_y=0, spacing=vertical_spacing
        )

        # 创建卷分组框
        for volume in data.get('volumes', []):
            self._create_volume_group_box(volume)

        # 创建所有节点
        for node_data in data.get('nodes', []):
            self._create_node(node_data, node_styles)

        # 创建父子关系连线
        for node_id, node in self._nodes.items():
            node_data = self._node_data.get(node_id, {})
            children = node_data.get('children', [])
            for child_id in children:
                child_node = self._nodes.get(child_id)
                if child_node:
                    self._create_connection(node, child_node, 'hierarchy', '',
                                           line_styles.get('solid', {}))

        # 创建节点级特殊关联
        for node_id, node in self._nodes.items():
            node_data = self._node_data.get(node_id, {})
            relations = node_data.get('relations', [])
            for rel in relations:
                target_id = rel.get('target')
                target_node = self._nodes.get(target_id)
                if target_node:
                    style_key = rel.get('style', 'dashed')
                    self._create_connection(node, target_node, 'special',
                                           rel.get('label', ''),
                                           line_styles.get(style_key, line_styles.get('dashed', {})))

        # 创建跨层级连线
        for link in data.get('cross_links', []):
            source_id = link.get('source')
            target_id = link.get('target')
            source_node = self._nodes.get(source_id)
            target_node = self._nodes.get(target_id)
            if source_node and target_node:
                style_key = link.get('style', 'solid')
                self._create_connection(source_node, target_node, 'special',
                                       link.get('label', ''),
                                       line_styles.get(style_key, line_styles.get('solid', {})))

        # 自动布局节点
        self._auto_layout_nodes()

    def _create_node(self, node_data, node_styles):
        """创建单个节点
        """
        node_id = node_data.get('id')
        node_type = node_data.get('node_type', 'member')
        node = EditableNode(node_id, node_type, node_data,
                           self._level_config, node_styles)
        self._nodes[node_id] = node
        self._node_data[node_id] = node_data

        # 连接信号
        node.position_changed.connect(lambda *args: self._on_node_position_changed(node_id))
        node.content_changed.connect(self._on_node_content_changed)
        node.delete_requested.connect(self._on_node_delete_requested)

        self._scene.addItem(node)

    def _create_connection(self, parent_node, child_node, connection_type, label, style_config):
        """创建连线
        """
        conn = FactionConnection(parent_node, child_node, connection_type,
                                  label, style_config=style_config)
        self._connections.append(conn)
        self._scene.addItem(conn)

        # 连接位置改变信号
        parent_node.position_changed.connect(conn._update_path)
        child_node.position_changed.connect(conn._update_path)

        if label:
            conn.set_label(label)

    def _create_volume_group_box(self, volume):
        """创建卷分组框
        """
        from PyQt5.QtCore import QRectF
        rect = QRectF(-400, 0, 800, 200)  # 临时大小，稍后调整
        box = GroupBoxNode(
            f"volume_{volume.get('name')}",
            volume.get('name'),
            'module',
            rect,
            volume.get('color', '#5B8DEF')
        )
        self._group_boxes.append(box)
        self._scene.addItem(box)

    def _auto_layout_nodes(self):
        """自动布局节点
        """
        layout = self._faction_tree_data.get('layout', {})
        horizontal_spacing = layout.get('horizontal_spacing', 160)
        vertical_spacing = layout.get('vertical_spacing', 80)
        level_label_offset = layout.get('level_label_offset', 60)

        # 按层级分组
        level_nodes = {}
        for node_id, node in self._nodes.items():
            node_data = self._node_data.get(node_id, {})
            level = node_data.get('level')
            if level is not None:
                if level not in level_nodes:
                    level_nodes[level] = []
                level_nodes[level].append((node_id, node))
            elif node.node_type == 'root':
                node.setPos(0, -vertical_spacing)

        # 按层级排列
        y_offset = 0
        available_levels = self._level_config.get('_available', [])
        for level in available_levels:
            nodes = level_nodes.get(level, [])
            if not nodes:
                continue

            # 计算X位置，居中对齐
            total_width = len(nodes) * horizontal_spacing
            start_x = -total_width / 2 + horizontal_spacing / 2

            for i, (node_id, node) in enumerate(nodes):
                x = start_x + i * horizontal_spacing
                y = y_offset
                node.setPos(x, y)

            y_offset += vertical_spacing

    def _clear_all(self):
        """清空所有内容
        """
        # 移除所有项目
        self._scene.clear()
        self._nodes.clear()
        self._node_data.clear()
        self._connections.clear()
        self._annotations.clear()
        self._group_boxes.clear()
        self._level_guides.clear()
        self._command_stack = CommandStack()

    def _on_node_position_changed(self, node_id):
        """节点位置改变
        """
        node = self._nodes.get(node_id)
        if node:
            for conn in self._connections:
                if conn.parent_node == node or conn.child_node == node:
                    conn._update_path()

    def _on_node_content_changed(self, node_id, new_text):
        """节点内容改变
        """
        if node_id in self._node_data:
            self._node_data[node_id]['name'] = new_text

    def _on_node_delete_requested(self, node_id):
        """删除节点请求
        """
        node = self._nodes.get(node_id)
        if node:
            cmd = RemoveNodeCommand(self._scene, node)
            self._command_stack.execute(cmd)
            del self._nodes[node_id]
            del self._node_data[node_id]

            # 移除相关连线
            self._connections = [c for c in self._connections
                               if c.parent_node != node and c.child_node != node]

    def mousePressEvent(self, event):
        """鼠标按下事件
        """
        self._mouse_press_pos = event.pos()

        if self._current_tool == EditorTool.SELECT:
            item = self.itemAt(event.pos())
            if item:
                self._dragging_node = item
                self._drag_start_pos = item.pos()
            super().mousePressEvent(event)
        elif self._current_tool == EditorTool.ARROW:
            self._arrow_tool.mouse_press(event)
        elif self._current_tool == EditorTool.TEXT:
            ann = TextAnnotation(_tr('new_annotation'))
            ann.setPos(self.mapToScene(event.pos()))
            self._annotations.append(ann)
            self._scene.addItem(ann)
            cmd = AddNodeCommand(self._scene, ann)
            self._command_stack.execute(cmd)
            self._current_tool = EditorTool.SELECT

    def mouseMoveEvent(self, event):
        """鼠标移动事件
        """
        if self._current_tool == EditorTool.ARROW:
            self._arrow_tool.mouse_move(event)
        else:
            super().mouseMoveEvent(event)

        if self._dragging_node and self._current_tool == EditorTool.SELECT:
            snap_x, snap_y = self._alignment_manager.calculate_snaps(
                self._dragging_node, self._nodes.values())
            self._alignment_manager.show_guides(snap_x, snap_y, self._dragging_node)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件
        """
        if self._current_tool == EditorTool.ARROW:
            self._arrow_tool.mouse_release(event, self._on_arrow_connection_created)
        elif self._dragging_node and self._drag_start_pos is not None:
            if self._drag_start_pos != self._dragging_node.pos():
                cmd = MoveNodeCommand(self._dragging_node,
                                     self._drag_start_pos,
                                     self._dragging_node.pos())
                self._command_stack.execute(cmd)
            self._alignment_manager.clear_guides()
            self._dragging_node = None
            self._drag_start_pos = None
            super().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

    def _on_arrow_connection_created(self, start_node, end_node):
        """箭头工具创建连线
        """
        from PyQt5.QtWidgets import QInputDialog
        label, ok = QInputDialog.getText(None, _tr('connection_label'),
                                        _tr('connection_label_prompt'))
        if ok:
            style_config = {
                'color': '#666666',
                'width': 1.5,
                'dash': None,
                'arrow': True
            }
            self._create_connection(start_node, end_node, 'special', label, style_config)

    def undo(self):
        """撤销
        """
        self._command_stack.undo()

    def redo(self):
        """重做
        """
        self._command_stack.redo()

    def set_tool(self, tool: EditorTool):
        """设置当前工具
        """
        self._current_tool = tool

    def export_to_image(self, file_path):
        """导出为图片
        """
        # 计算场景实际大小
        rect = self._scene.sceneRect()

        # 渲染到 QImage
        image = QImage(rect.size().toSize() * 2, QImage.Format_ARGB32)  # 2x 高清
        image.fill(Qt.white)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        self._scene.render(painter, QRectF(), rect)
        painter.end()

        image.save(file_path)

