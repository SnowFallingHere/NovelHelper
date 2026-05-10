
"""组织架构编辑器 - 可编辑节点类

包含：
- EditableNode: 可编辑节点基类
- GroupBoxNode: 分组框节点
- TextAnnotation: 文本标注
"""

import json
import os
from typing import Dict, List, Optional, Any
from PyQt5.QtWidgets import (
    QGraphicsObject, QGraphicsItem, QGraphicsTextItem,
    QMenu, QInputDialog, QStyle
)
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QRect
from PyQt5.QtGui import (
    QColor, QFont, QPen, QBrush, QPainter,
    QPainterPath, QCursor
)

from ..core.language_manager import language_manager


def _tr(key):
    return language_manager.tr(key)


def _generate_level_styles(level_config):
    """根据 level_config 动态生成每层样式
    """
    palette = [
        ('#6B5B95', '#4A3F6B'), ('#7B9CC2', '#5A7A9E'),
        ('#89B894', '#6A9A75'), ('#B8A9D4', '#9688B3'),
        ('#D4A76A', '#B88A50'), ('#D48B8B', '#B87070'),
        ('#A0A0A0', '#808080'), ('#5B8DEF', '#4A6FBF'),
        ('#9B59B6', '#7D3C98'), ('#E67E22', '#BA5C12'),
        ('#2ECC71', '#239B56'),
    ]
    styles = {}
    for i, lv in enumerate(level_config.get('_available', [])):
        bg, border = palette[i % len(palette)]
        styles[lv] = {'bg': bg, 'text': '#FFFFFF', 'border': border}
    return styles


class EditableNode(QGraphicsObject):
    """所有可编辑节点的统一基类
    """
    position_changed = pyqtSignal(str)
    content_changed = pyqtSignal(str, str)
    selected = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, node_id, node_type, node_data, level_config, node_styles, parent=None):
        super().__init__(parent)
        self.node_id = node_id
        self.node_type = node_type
        self.node_data = node_data
        self.level_config = level_config
        self.node_styles = node_styles
        self._is_editing = False
        self._show_alignment = False

        # 设置标志
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        # 获取样式
        style = self.node_styles.get(node_type, self.node_styles.get('member', {}))
        self._w = style.get('width', 100)
        self._h = style.get('height', 30)
        self._bg = QColor(style.get('bg', '#FFFFFF'))
        self._text_color = QColor(style.get('text', '#555555'))
        self._border = QColor(style.get('border', '#D0D4D9'))
        self._radius = style.get('radius', 6)
        self._font_size = style.get('font_size', 10)

        # 生成层级样式（如果有 level）
        self._level_style = {}
        level = node_data.get('level')
        if level is not None:
            lv_styles = _generate_level_styles(level_config)
            if level in lv_styles:
                ls = lv_styles[level]
                self._level_bg = QColor(ls['bg'])
                self._level_border = QColor(ls['border'])

        self._text = node_data.get('name', '')

    def boundingRect(self):
        return QRectF(-self._w / 2, -self._h / 2, self._w, self._h)

    def paint(self, painter, option, widget=None):
        is_hovered = option.state & QStyle.State_MouseOver
        is_selected = option.state & QStyle.State_Selected

        # 背景和边框颜色
        if hasattr(self, '_level_bg'):
            bg = self._level_bg.lighter(108) if is_hovered else self._level_bg
            border = self._level_border
        else:
            bg = self._bg.lighter(105) if is_hovered else self._bg
            border = self._border

        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border, 2 if is_selected else 1))

        path = QPainterPath()
        path.addRoundedRect(-self._w / 2, -self._h / 2, self._w, self._h, self._radius, self._radius)
        painter.drawPath(path)

        # 绘制文字
        painter.setPen(self._text_color)
        font = QFont('Microsoft YaHei', self._font_size,
                      QFont.Bold if self.node_type in ('root', 'level') else QFont.Normal)
        painter.setFont(font)
        elided = (self._text[:14] + '..') if len(self._text) > 14 else self._text
        painter.drawText(QRectF(-self._w / 2 + 6, -self._h / 2, self._w - 12, self._h),
                         Qt.AlignCenter, elided)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            self.position_changed.emit(self.node_id)
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        if self.node_type == 'root':
            return
        self._enter_edit_mode()

    def _enter_edit_mode(self):
        """进入编辑模式
        """
        text, ok = QInputDialog.getText(
            None,
            _tr('edit_node_title'),
            _tr('edit_node_prompt'),
            text=self._text
        )
        if ok and text:
            old_text = self._text
            self._text = text
            self.content_changed.emit(self.node_id, text)
            self.update()

    def contextMenuEvent(self, event):
        menu = QMenu()
        edit_action = menu.addAction(_tr('edit_text'))
        edit_action.triggered.connect(self._enter_edit_mode)

        change_color_action = menu.addAction(_tr('change_color'))
        change_color_action.triggered.connect(self._change_color)

        menu.addSeparator()
        delete_action = menu.addAction(_tr('delete_node'))
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.node_id))

        menu.exec_(event.screenPos())

    def _change_color(self):
        # TODO: 实现颜色选择
        pass


class GroupBoxNode(QGraphicsObject):
    """可拖拽的分组框（大模块框/模块分组框）
    """
    bounds_changed = pyqtSignal(str)

    def __init__(self, box_id, name, box_type='group', rect=QRectF(0, 0, 200, 100), color='#5B8DEF', parent=None):
        super().__init__(parent)
        self.box_id = box_id
        self._name = name
        self.box_type = box_type
        self._rect = rect
        self.box_color = QColor(color)
        self.border_style = 'solid'
        self._resize_handle = False

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)

    def boundingRect(self):
        return self._rect.adjusted(-10, -10, 10, 10)

    def paint(self, painter, option, widget=None):
        is_hovered = option.state & QStyle.State_MouseOver
        is_selected = option.state & QStyle.State_Selected

        # 半透明背景
        bg_color = self.box_color
        bg_color.setAlpha(30)
        painter.setBrush(QBrush(bg_color))

        # 边框
        pen_width = 2.5 if self.box_type == 'module' else 2
        if self.border_style == 'dashed':
            pen = QPen(self.box_color, pen_width, Qt.DashLine)
        elif self.border_style == 'dotted':
            pen = QPen(self.box_color, pen_width, Qt.DotLine)
        else:
            pen = QPen(self.box_color, pen_width, Qt.SolidLine)

        if is_selected:
            pen.setWidth(pen_width + 1)

        painter.setPen(pen)
        painter.drawRoundedRect(self._rect, 10, 10)

        # 标题
        painter.setPen(self.box_color)
        font = QFont('Microsoft YaHei', 11, QFont.Bold)
        painter.setFont(font)
        painter.drawText(self._rect.adjusted(10, 4, 0, 0),
                     Qt.AlignLeft | Qt.AlignTop, self._name)

    def get_contained_nodes(self, all_nodes):
        """返回完全在分组框内的节点列表
        """
        contained = []
        for node in all_nodes:
            if node.sceneBoundingRect().intersects(self.sceneBoundingRect()):
                contained.append(node)
        return contained


class TextAnnotation(QGraphicsTextItem):
    """可拖拽的文本标注
    """

    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setTextInteractionFlags(Qt.TextEditorInteraction)

        # 默认样式
        self.setDefaultTextColor(QColor('#555555'))
        font = QFont('Microsoft YaHei', 10)
        self.setFont(font)

    def contextMenuEvent(self, event):
        menu = QMenu()

        edit_action = menu.addAction(_tr('edit_text'))
        edit_action.triggered.connect(self._start_editing)

        font_menu = menu.addMenu(_tr('font'))
        font_menu.addAction(_tr('increase_font')).triggered.connect(lambda: self._change_font_size(1))
        font_menu.addAction(_tr('decrease_font')).triggered.connect(lambda: self._change_font_size(-1))

        color_menu = menu.addMenu(_tr('color'))
        for name, color in [
            (_tr('color_black'), '#000000'),
            (_tr('color_gray'), '#666666'),
            (_tr('color_red'), '#C0392B'),
            (_tr('color_blue'), '#2980B9')
        ]:
            color_menu.addAction(name, lambda c=color: self.setDefaultTextColor(QColor(c)))

        menu.addSeparator()
        delete_action = menu.addAction(_tr('delete_annotation'))
        delete_action.triggered.connect(lambda: self.scene().removeItem(self))

        menu.exec_(event.screenPos())

    def _start_editing(self):
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus()

    def _change_font_size(self, delta):
        font = self.font()
        font.setPointSize(max(6, min(24, font.pointSize() + delta)))
        self.setFont(font)

