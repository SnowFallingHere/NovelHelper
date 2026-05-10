
"""组织架构编辑器 - 工具系统与命令栈

包含：
- EditorTool: 工具枚举
- AlignmentManager: 对齐辅助线管理
- ArrowTool: 箭头工具状态机
- CommandStack: 撤销/重做命令栈
"""

from enum import Enum
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
from PyQt5.QtWidgets import QGraphicsLineItem, QWidget
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QColor, QPen

from ..core.language_manager import language_manager


def _tr(key):
    return language_manager.tr(key)


class EditorTool(Enum):
    SELECT = 'select'
    GROUP_BOX = 'group_box'
    ARROW = 'arrow'
    TEXT = 'text'
    DELETE = 'delete'


class AlignmentGuide(QGraphicsLineItem):
    """吸附辅助线
    """
    SNAP_THRESHOLD = 8

    def __init__(self, orientation='horizontal'):
        super().__init__()
        self.orientation = orientation
        self.setPen(QPen(QColor('#2196F3'), 1, Qt.DashLine))
        self.setZValue(999)


class AlignmentManager:
    """管理节点拖拽时的对齐辅助线
    """

    def __init__(self, scene):
        self.scene = scene
        self.guides = []
        self.snap_positions = {}

    def calculate_snaps(self, moving_node, all_nodes):
        """计算移动节点与其他节点的对齐位置
        """
        snap_x = []
        snap_y = []

        m_rect = moving_node.sceneBoundingRect()
        for node in all_nodes:
            if node is moving_node:
                continue
            n_rect = node.sceneBoundingRect()

            # 左对齐
            if abs(m_rect.left() - n_rect.left()) < AlignmentGuide.SNAP_THRESHOLD:
                snap_x.append(n_rect.left())
            # 右对齐
            if abs(m_rect.right() - n_rect.right()) < AlignmentGuide.SNAP_THRESHOLD:
                snap_x.append(n_rect.right() - m_rect.width())
            # 水平居中
            if abs(m_rect.center().x() - n_rect.center().x()) < AlignmentGuide.SNAP_THRESHOLD:
                snap_x.append(n_rect.center().x() - m_rect.width()/2)
            # 顶对齐
            if abs(m_rect.top() - n_rect.top()) < AlignmentGuide.SNAP_THRESHOLD:
                snap_y.append(n_rect.top())
            # 底对齐
            if abs(m_rect.bottom() - n_rect.bottom()) < AlignmentGuide.SNAP_THRESHOLD:
                snap_y.append(n_rect.bottom() - m_rect.height())
            # 垂直居中
            if abs(m_rect.center().y() - n_rect.center().y()) < AlignmentGuide.SNAP_THRESHOLD:
                snap_y.append(n_rect.center().y() - m_rect.height()/2)

        return snap_x, snap_y

    def show_guides(self, snap_x, snap_y, moving_node):
        """显示蓝色辅助线
        """
        self.clear_guides()
        m_rect = moving_node.sceneBoundingRect()

        for x in snap_x:
            guide = AlignmentGuide('vertical')
            guide.setLine(x, -9999, x, 9999)
            self.scene.addItem(guide)
            self.guides.append(guide)

        for y in snap_y:
            guide = AlignmentGuide('horizontal')
            guide.setLine(-9999, y, 9999, y)
            self.scene.addItem(guide)
            self.guides.append(guide)

    def clear_guides(self):
        """清除辅助线
        """
        for guide in self.guides:
            self.scene.removeItem(guide)
        self.guides = []


class ArrowTool:
    """箭头绘制工具的状态机
    """

    def __init__(self, scene):
        self.scene = scene
        self._start_node = None
        self._temp_line = None
        self._drawing = False

    def mouse_press(self, event):
        """检测是否点击到节点上，开始绘制箭头
        """
        from .faction_nodes import EditableNode
        item = self.scene.itemAt(event.scenePos(), self.scene.views()[0].transform())
        if isinstance(item, EditableNode):
            self._start_node = item
            self._drawing = True
            from PyQt5.QtWidgets import QGraphicsLineItem
            self._temp_line = QGraphicsLineItem()
            self._temp_line.setPen(QPen(QColor('#333'), 2, Qt.DashLine))
            self.scene.addItem(self._temp_line)

    def mouse_move(self, event):
        if self._drawing and self._temp_line:
            start = self._start_node.sceneBoundingRect().center()
            end = event.scenePos()
            self._temp_line.setLine(start.x(), start.y(), end.x(), end.y())

    def mouse_release(self, event, on_connection_created):
        if not self._drawing:
            return

        end_node = None
        from .faction_nodes import EditableNode
        item = self.scene.itemAt(event.scenePos(), self.scene.views()[0].transform())
        if isinstance(item, EditableNode) and item != self._start_node:
            end_node = item

        if end_node:
            on_connection_created(self._start_node, end_node)

        self._cleanup_temp()

    def _cleanup_temp(self):
        if self._temp_line:
            self.scene.removeItem(self._temp_line)
            self._temp_line = None
        self._start_node = None
        self._drawing = False


class EditCommand(ABC):
    """命令基类
    """

    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def undo(self):
        pass


class MoveNodeCommand(EditCommand):
    """移动节点命令
    """

    def __init__(self, node, old_pos, new_pos):
        self.node = node
        self.old_pos = old_pos
        self.new_pos = new_pos

    def execute(self):
        self.node.setPos(self.new_pos)

    def undo(self):
        self.node.setPos(self.old_pos)


class ChangeTextCommand(EditCommand):
    """修改节点文本命令
    """

    def __init__(self, node, old_text, new_text):
        self.node = node
        self.old_text = old_text
        self.new_text = new_text

    def execute(self):
        self.node._text = self.new_text
        self.node.update()

    def undo(self):
        self.node._text = self.old_text
        self.node.update()


class AddNodeCommand(EditCommand):
    """添加节点命令
    """

    def __init__(self, scene, node, parent_id=None):
        self.scene = scene
        self.node = node
        self.parent_id = parent_id

    def execute(self):
        self.scene.addItem(self.node)

    def undo(self):
        self.scene.removeItem(self.node)


class RemoveNodeCommand(EditCommand):
    """删除节点命令
    """

    def __init__(self, scene, node):
        self.scene = scene
        self.node = node
        self._old_pos = node.pos()

    def execute(self):
        self.scene.removeItem(self.node)

    def undo(self):
        self.scene.addItem(self.node)
        self.node.setPos(self._old_pos)


class CommandStack:
    """命令栈 - 撤销/重做
    """

    def __init__(self, max_size=50):
        self._undo_stack = []
        self._redo_stack = []
        self._max_size = max_size

    def execute(self, command):
        command.execute()
        self._undo_stack.append(command)
        self._redo_stack.clear()
        if len(self._undo_stack) > self._max_size:
            self._undo_stack.pop(0)

    def undo(self):
        if not self._undo_stack:
            return False
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        return True

    def redo(self):
        if not self._redo_stack:
            return False
        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)
        return True

    def can_undo(self):
        return len(self._undo_stack) > 0

    def can_redo(self):
        return len(self._redo_stack) > 0

