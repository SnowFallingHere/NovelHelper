"""
大纲时间线视图组件
提供可视化的章节/事件时间线展示和编辑功能

功能：
- 按卷/章节展示时间线
- 关键节点标记（伏笔、高潮、转折）
- 时间线缩放和平移
- 节点详情查看
- 导航跳转

使用示例：
    timeline = TimelineView(parent=self)
    timeline.set_data(volumes_data)
    layout.addWidget(timeline)
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from collections import OrderedDict

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QPushButton, QMenu,
    QGraphicsScene, QGraphicsView, QGraphicsItem, QGraphicsObject,
    QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsTextItem,
    QToolTip, QApplication, QStyle
)
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QTimer
from PyQt5.QtGui import (QColor, QFont, QPen, QBrush, QPainter,
                          QPainterPath, QLinearGradient, QRadialGradient)

logger = logging.getLogger(__name__)


def _clean_title(title: str) -> str:
    """去除标题中的 [new_xxx] 后缀"""
    return re.sub(r'\[new_\d+\]', '', title).strip()


def _format_volume_name(vol_name: str) -> str:
    """将卷名格式化为「第X卷 卷名」，去除前导数字和 [new_xxx] 后缀"""
    cleaned = re.sub(r'\[new_\d+\]', '', vol_name).strip()
    match = re.match(r'^(\d+)(.*)', cleaned)
    if match:
        vol_num = match.group(1)
        name = match.group(2).strip()
        if name:
            return f"第{vol_num}卷 {name}"
        return f"第{vol_num}卷"
    return cleaned


class VolumeLabelNode(QGraphicsObject):
    """可点击的卷标题节点（支持折叠/展开）"""

    clicked = pyqtSignal(str)  # volume_name, toggled

    def __init__(self, vol_name, parent=None):
        super().__init__(parent)
        self.vol_name = vol_name
        self.display_name = _format_volume_name(vol_name)
        self._collapsed = False
        self._width = 220
        self._height = 36
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)

    @property
    def collapsed(self):
        return self._collapsed

    def toggle(self):
        self._collapsed = not self._collapsed
        self.update()
        return self._collapsed

    def boundingRect(self):
        return QRectF(-self._width / 2, -self._height / 2,
                       self._width, self._height)

    def paint(self, painter, option, widget=None):
        from ..core.theme_manager import theme_manager as _tv
        _tt = _tv.get_current_theme()

        accent = QColor(_tt.get('accent_color', '#0078D4'))
        is_hovered = option.state & QStyle.State_MouseOver

        bg = accent.lighter(115) if is_hovered else accent
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(accent.darker(120), 1))

        path = QPainterPath()
        path.addRoundedRect(-self._width / 2, -self._height / 2,
                            self._width, self._height, 8, 8)
        painter.drawPath(path)

        # 折叠/展开图标
        painter.setPen(Qt.white)
        font = QFont('Segoe UI Symbol', 12, QFont.Bold)
        painter.setFont(font)
        icon = "▶" if self._collapsed else "▼"
        painter.drawText(QRectF(-self._width / 2 + 10, -self._height / 2,
                                24, self._height), Qt.AlignCenter, icon)

        # 卷名文本
        font = QFont('Microsoft YaHei', 11, QFont.Bold)
        painter.setFont(font)
        text_rect = QRectF(-self._width / 2 + 36, -self._height / 2,
                           self._width - 48, self._height)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.display_name)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle()
            self.clicked.emit(self.vol_name)

    def hoverEnterEvent(self, event):
        self.update()

    def hoverLeaveEvent(self, event):
        self.update()


class TimelineNode(QGraphicsItem):
    """时间线节点"""
    
    def __init__(self, node_data: Dict, parent=None):
        super().__init__(parent)

        self.node_data = node_data
        self._width = 200
        self._height = 68

        # 设置可选中
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

        # 颜色配置（使用主题变量）
        from ..core.theme_manager import theme_manager
        t = theme_manager.get_current_theme()

        type_colors = {
            'chapter': t.get('timeline_node_bg', '#4A5568'),
            'climax': t.get('timeline_climax', '#E53E3E'),
            'foreshadowing': t.get('timeline_foreshadow', '#D69E2E'),
            'turning_point': t.get('timeline_turning', '#D53F8C'),
            'character_intro': t.get('timeline_character', '#3182CE'),
            'normal': t.get('timeline_normal', '#718096')
        }

        node_type = node_data.get('type', 'normal')
        self.color = QColor(type_colors.get(node_type, '#718096'))

        # 文本（清洗 [new_xxx] 后缀）
        self.title = _clean_title(node_data.get('title', ''))
        self.subtitle = node_data.get('subtitle', '')
    
    def boundingRect(self):
        return QRectF(-self._width / 2, -self._height / 2, 
                       self._width, self._height)
    
    def paint(self, painter, option, widget=None):
        # 背景
        is_hovered = option.state & QStyle.State_MouseOver
        bg_color = QColor(self.color) if not is_hovered else QColor(self.color).lighter(130)
        
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(self.color.darker(120), 2))
        
        # 圆角矩形背景
        path = QPainterPath()
        path.addRoundedRect(
            -self._width / 2, -self._height / 2,
            self._width, self._height, 8, 8
        )
        painter.drawPath(path)
        
        # 标题文本
        painter.setPen(Qt.white)
        font = QFont('Microsoft YaHei', 10, QFont.Bold)
        painter.setFont(font)
        
        title_rect = QRectF(-self._width / 2 + 8, -self._height / 2 + 6,
                            self._width - 16, 24)
        elided_title = self.title[:22] + '…' if len(self.title) > 22 else self.title
        painter.drawText(title_rect, Qt.AlignCenter | Qt.TextWordWrap, elided_title)
        
        # 副标题
        if self.subtitle:
            painter.setPen(QColor('#cccccc'))
            font = QFont('Microsoft YaHei', 8)
            painter.setFont(font)
            
            sub_rect = QRectF(-self._width / 2 + 8, self._height / 2 - 22,
                              self._width - 16, 18)
            elided_sub = self.subtitle[:18] + '…' if len(self.subtitle) > 18 else self.subtitle
            painter.drawText(sub_rect, Qt.AlignCenter, elided_sub)
    
    def hoverEnterEvent(self, event):
        """鼠标悬停显示提示"""
        tooltip_text = f"【{self.title}】\n{self.subtitle}\n\n类型: {self.node_data.get('type', '未知')}"
        QToolTip.showText(event.screenPos(), tooltip_text)
        self.update()
    
    def hoverLeaveEvent(self, event):
        QToolTip.hideText()
        self.update()


class TimelineView(QWidget):
    """
    大纲时间线视图
    
    展示内容：
    - 垂直/水平时间线
    - 章节节点（按顺序排列）
    - 特殊标记点（伏笔、高潮等）
    - 卷分隔符
    - 缩放控制
    """
    
    # 信号定义
    node_clicked = pyqtSignal(dict)      # 点击节点时发出
    node_double_clicked = pyqtSignal(str) # 双击时发出
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._data = []
        self._orientation = Qt.Vertical
        self._zoom_factor = 1.0
        self._node_spacing = 80
        self._collapsed_volumes = set()
        self._volume_nodes = {}   # vol_name -> VolumeLabelNode
        self._chapter_items = []  # (vol_name, node_item, conn_line) per chapter
        
        logger.info("[TimelineView] 初始化")
        self._build_ui()
    
    def _build_ui(self):
        """构建UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)

        from ..core.theme_manager import theme_manager
        t = theme_manager.get_current_theme()

        # ====== 紧凑工具栏 ======
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 4)
        toolbar.setSpacing(4)

        btn_compact_style = f"""
            QPushButton {{
                background-color: {t.get('card_bg', '#FFFFFF')};
                color: {t.get('fg_color', '#212529')};
                border: 1px solid {t.get('border_color', '#DEE2E6')};
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {t.get('accent_color', '#0078D4')}20;
                border-color: {t.get('accent_color', '#0078D4')};
            }}
        """

        # 方向切换
        self.orientation_btn = QPushButton("切换方向")
        self.orientation_btn.setStyleSheet(btn_compact_style)
        self.orientation_btn.setFixedHeight(26)
        self.orientation_btn.clicked.connect(self._toggle_orientation)
        toolbar.addWidget(self.orientation_btn)

        # 缩放控制
        zoom_label = QLabel("缩放:")
        zoom_label.setStyleSheet(f"color: {t.get('fg_color', '#212529')}; font-size: 11px; margin-left: 4px;")
        toolbar.addWidget(zoom_label)

        zoom_btn_small = f"""
            QPushButton {{
                background-color: {t.get('card_bg', '#FFFFFF')};
                color: {t.get('fg_color', '#212529')};
                border: 1px solid {t.get('border_color', '#DEE2E6')};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 13px;
                min-width: 26px;
                max-width: 26px;
                min-height: 26px;
                max-height: 26px;
            }}
            QPushButton:hover {{
                background-color: {t.get('accent_color', '#0078D4')}20;
                border-color: {t.get('accent_color', '#0078D4')};
            }}
        """
        
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setStyleSheet(zoom_btn_small)
        self.zoom_in_btn.clicked.connect(lambda: self._set_zoom(self._zoom_factor * 1.2))
        toolbar.addWidget(self.zoom_in_btn)
        
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.setStyleSheet(zoom_btn_small)
        self.zoom_out_btn.clicked.connect(lambda: self._set_zoom(self._zoom_factor / 1.2))
        toolbar.addWidget(self.zoom_out_btn)

        self.zoom_reset_btn = QPushButton("重置")
        self.zoom_reset_btn.setStyleSheet(btn_compact_style)
        self.zoom_reset_btn.setFixedHeight(26)
        self.zoom_reset_btn.clicked.connect(lambda: self._set_zoom(1.0))
        toolbar.addWidget(self.zoom_reset_btn)

        toolbar.addStretch()
        main_layout.addLayout(toolbar)
        
        # ====== 图形视图 ======
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setStyleSheet(f"""
            QGraphicsView {{
                background-color: {t.get('graph_bg', '#F8F9FA')};
                border: 1px solid {t.get('border_color', '#DEE2E6')};
                border-radius: 8px;
            }}
        """)
        self.view.setMinimumHeight(520)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        main_layout.addWidget(self.view, 1)
        
        logger.debug("[TimelineView] UI构建完成")
    
    def set_data(self, data: List[Dict]):
        """
        设置时间线数据
        
        Args:
            data: 数据列表，每个元素包含：
                - volume: 卷名
                - chapter: 章节名
                - type: 类型 ('chapter', 'climax', 'foreshadowing' 等)
                - title: 标题
                - subtitle: 副标题
                - order: 排序号
        """
        self._data = sorted(data, key=lambda x: x.get('order', 0))
        self._render_timeline()
    
    def _render_timeline(self):
        """渲染时间线（支持卷折叠/展开）"""
        self.scene.clear()
        self._volume_nodes.clear()
        self._chapter_items.clear()

        if not self._data:
            empty_text = QGraphicsTextItem("暂无数据，请先加载小说目录")
            empty_text.setDefaultTextColor(QColor('#556655'))
            empty_text.setFont(QFont('Microsoft YaHei', 14))
            self.scene.addItem(empty_text)
            return

        from ..core.theme_manager import theme_manager as _tm_axis
        _t_axis = _tm_axis.get_current_theme()

        if self._orientation == Qt.Vertical:
            spacing = self._node_spacing
            offset = 140
        else:
            spacing = max(self._node_spacing, 200 + 40)
            offset = 80

        axis_color = QColor(_t_axis.get('border_color', '#A0AEC0'))

        current_volume = None
        vol_chapters = []  # 当前卷下的章节索引列表
        vol_first_y = 0
        y_positions = []

        # 第一遍：计算每个数据项的 y 位置
        for i, item in enumerate(self._data):
            if self._orientation == Qt.Vertical:
                y = i * spacing
            else:
                y = i * spacing
            y_positions.append(y)

        total_length = len(self._data) * spacing
        if self._orientation == Qt.Vertical:
            axis_line = self.scene.addLine(
                0, -60, 0, total_length + 60,
                QPen(axis_color, 2)
            )
        else:
            axis_line = self.scene.addLine(
                -60, 0, total_length + 60, 0,
                QPen(axis_color, 2)
            )

        # 第二遍：创建节点和卷标签
        for i, item in enumerate(self._data):
            y = y_positions[i]
            vol_name = item.get('volume', '')

            # 检测新卷
            if vol_name != current_volume:
                # 处理上一个卷（创建卷标签节点）
                if current_volume is not None and vol_chapters:
                    self._create_volume_label(
                        current_volume, vol_first_y,
                        y_positions[vol_chapters[0]], y_positions[vol_chapters[-1]],
                        offset
                    )
                current_volume = vol_name
                vol_chapters = []
                vol_first_y = y

            vol_chapters.append(i)

            # 创建章节节点
            node = TimelineNode(item)

            if self._orientation == Qt.Vertical:
                x_pos = offset
                node.setPos(x_pos, y)
            else:
                x_pos = y
                node.setPos(x_pos, offset)

            is_collapsed = current_volume in self._collapsed_volumes
            node.setVisible(not is_collapsed)
            self.scene.addItem(node)

            # 连接线到主轴
            conn_color = QColor(_t_axis.get('border_color', '#A0AEC0'))
            conn_color.setAlpha(100)

            if self._orientation == Qt.Vertical:
                conn_line = self.scene.addLine(0, y, offset, y, QPen(conn_color, 1, Qt.DashLine))
            else:
                conn_line = self.scene.addLine(x_pos, 0, x_pos, offset, QPen(conn_color, 1, Qt.DashLine))

            conn_line.setVisible(not is_collapsed)
            self._chapter_items.append((current_volume, node, conn_line))

        # 最后一个卷的标签
        if current_volume is not None and vol_chapters:
            last_y = y_positions[-1] + spacing
            self._create_volume_label(
                current_volume, vol_first_y,
                y_positions[vol_chapters[0]], y_positions[vol_chapters[-1]],
                offset
            )

        self.view.resetTransform()
        self.view.scale(self._zoom_factor, self._zoom_factor)

    def _create_volume_label(self, vol_name, first_y, ch_start_y, ch_end_y, offset):
        """创建蓝色卡片式卷标题节点"""
        mid_y = (ch_start_y + ch_end_y) / 2

        vol_node = VolumeLabelNode(vol_name)
        vol_node._collapsed = vol_name in self._collapsed_volumes

        if self._orientation == Qt.Vertical:
            vol_node.setPos(-110, mid_y)
        else:
            vol_node.setPos(mid_y, -60)

        vol_node.clicked.connect(self._on_volume_toggle)
        self.scene.addItem(vol_node)
        self._volume_nodes[vol_name] = vol_node

    def _on_volume_toggle(self, vol_name):
        """点击卷标签时切换折叠/展开"""
        vol_node = self._volume_nodes.get(vol_name)
        if not vol_node:
            return

        is_collapsed = vol_node.toggle()
        if is_collapsed:
            self._collapsed_volumes.add(vol_name)
        else:
            self._collapsed_volumes.discard(vol_name)

        # 同步显示/隐藏该卷下的所有章节和连线
        for cvol, node_item, conn_line in self._chapter_items:
            if cvol == vol_name:
                visible = not is_collapsed
                node_item.setVisible(visible)
                conn_line.setVisible(visible)
    
    def _toggle_orientation(self):
        """切换时间线方向"""
        if self._orientation == Qt.Vertical:
            self._orientation = Qt.Horizontal
        else:
            self._orientation = Qt.Vertical
        
        self._render_timeline()
    
    def _set_zoom(self, factor: float):
        """设置缩放因子"""
        self._zoom_factor = max(0.3, min(3.0, factor))
        self.view.resetTransform()
        self.view.scale(self._zoom_factor, self._zoom_factor)
    
    def load_from_chapter_cache(self, cache):
        """从章节缓存加载数据"""
        from core.chapter_index_cache import ChapterIndexCache
        
        if isinstance(cache, ChapterIndexCache):
            volumes = cache.get_volumes()
            data = []
            order = 0
            
            for vol in volumes:
                vol_name = vol['name']
                chapters = cache.get_chapters(vol_name)
                
                for ch in chapters:
                    data.append({
                        'volume': vol_name,
                        'chapter': ch['name'],
                        'type': 'chapter',
                        'title': ch['name'],
                        'subtitle': f"{ch['word_count']}字",
                        'order': order,
                        'path': ch['path']
                    })
                    order += 1
            
            self.set_data(data)
            logger.info(f"[TimelineView] 已加载 {len(data)} 个章节到时间线")


class MiniTimelineWidget(QFrame):
    """
    迷你时间线小部件（用于侧边栏或面板）
    
    特点：
    - 紧凑型设计
    - 只显示关键节点
    - 可点击导航
    """
    
    node_selected = pyqtSignal(str)
    
    def __init__(self, max_items: int = 10, parent=None):
        super().__init__(parent)
        
        self.max_items = max_items
        self._items: List[Dict] = []
        
        from ..core.theme_manager import theme_manager
        t = theme_manager.get_current_theme()

        self.setMinimumHeight(340)
        self.setStyleSheet(f"""
            MiniTimelineWidget {{
                background-color: {t.get('card_bg', '#FFFFFF')};
                border: 1px solid {t.get('border_color', '#DEE2E6')};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # 内容区域
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(2)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setAlignment(Qt.AlignTop)
        
        scroll = QScrollArea()
        scroll.setWidget(self.content_widget)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(300)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 6px; }
        """)
        
        layout.addWidget(scroll)
    
    def add_item(self, item: Dict):
        """添加时间线条目"""
        self._items.insert(0, item)
        
        # 限制数量
        while len(self._items) > self.max_items:
            self._items.pop()
        
        self._refresh_ui()
    
    def set_items(self, items: List[Dict]):
        """设置所有条目"""
        self._items = items[:self.max_items]
        self._refresh_ui()
    
    def _refresh_ui(self):
        """刷新UI显示"""
        # 清除现有内容
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 添加新条目
        from ..core.theme_manager import theme_manager as _tm_mini
        _t_mini = _tm_mini.get_current_theme()

        fg_color = _t_mini.get('fg_color', '#212529')
        accent = _t_mini.get('accent_color', '#0078D4')
        
        current_volume = None
        
        for item in self._items[:self.max_items]:
            vol_name = item.get('volume', '')
            
            # 检测卷变化，插入卷标题（蓝色样式）
            if vol_name and vol_name != current_volume:
                current_volume = vol_name
                vol_frame = QFrame()
                vol_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
                vol_layout = QHBoxLayout(vol_frame)
                vol_layout.setContentsMargins(0, 10, 0, 4)
                
                vol_label = QLabel(_format_volume_name(vol_name))
                vol_label.setStyleSheet(f"""
                    color: {accent}; font-size: 12px; font-weight: bold;
                    border: none; background: transparent;
                """)
                vol_layout.addWidget(vol_label)
                vol_layout.addStretch()
                
                self.content_layout.addWidget(vol_frame)
            
            # 章节条目（在卷下方缩进24px）
            frame = QFrame()
            frame.setMinimumHeight(34)
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {fg_color}06;
                    border-left: 2px solid {fg_color}30;
                    border-radius: 4px;
                    padding: 4px 8px;
                }}
                QFrame:hover {{
                    background-color: {fg_color}10;
                }}
            """)
            
            h_layout = QHBoxLayout(frame)
            h_layout.setContentsMargins(28, 6, 10, 6)
            h_layout.setSpacing(8)
            
            # 清理后的章节名
            title = _clean_title(item.get('title', item.get('chapter', '?')))
            subtitle = item.get('subtitle', '')
            
            label = QLabel(title)
            label.setStyleSheet(f"color: {fg_color}; font-size: 11px; border: none;")
            label.setMaximumWidth(140)
            h_layout.addWidget(label)
            
            if subtitle:
                sub_label = QLabel(subtitle)
                sub_label.setStyleSheet(f"color: {fg_color}80; font-size: 10px; border: none;")
                h_layout.addWidget(sub_label)
            
            h_layout.addStretch()
            
            # 连接点击事件
            frame.mousePressEvent = lambda e, d=item: self.node_selected.emit(d.get('path', ''))
            
            self.content_layout.addWidget(frame)
