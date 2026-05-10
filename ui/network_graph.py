import os
import random
import math
import logging
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_script_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from PyQt5.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsRectItem,
                              QGraphicsTextItem, QGraphicsPathItem, QGraphicsPolygonItem, QGraphicsItem,
                              QGraphicsEllipseItem, QGraphicsItemGroup, QMenu,
                              QAction, QInputDialog, QOpenGLWidget,
                              QLineEdit, QToolBar, QVBoxLayout, QWidget, QHBoxLayout,
                              QFrame, QLabel, QListWidget, QListWidgetItem, QWidgetAction, QPushButton, QCheckBox,
                              QScrollArea, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF, QLineF, QPropertyAnimation, QEasingCurve, pyqtSignal, QVariantAnimation
from PyQt5.QtGui import (QFont, QColor, QPen, QBrush, QPainter, QPainterPath,
                          QLinearGradient, QFontMetrics, QRadialGradient, QPolygonF,
                          QImage, QCursor, QPixmap, QSurfaceFormat, QTransform)
from models.keyword_manager import keyword_manager
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

from core.theme_manager import theme_manager
from core.language_manager import language_manager

def _theme(key, fallback=''):
    return theme_manager.get(key, fallback)

def calculate_luminance(color: QColor) -> float:
    """
    计算颜色的明度（灰度值）
    使用公式：0.299*R + 0.587*G + 0.114*B
    返回 0（黑色）到 255（白色）
    """
    r, g, b, _ = color.getRgb()
    return 0.299 * r + 0.587 * g + 0.114 * b

NODE_LABELS = {
    'character': '人物', 'skill': '技能', 'location': '地点',
    'item': '物品', 'foreshadowing': '伏笔',
    'relationship': '关系', 'custom': 'TAG',
    'adventure': '事件', 'faction': '组织', 'time_point': '时间点'
}

RELATION_CATEGORIES = {
    'related_to': {'label': '关联', 'style': 'solid', 'color': '#88aacc', 'width': 1.5, 'arrow': 'none'},
    'friendship': {'label': '友谊', 'style': 'solid', 'color': '#28A745', 'width': 3, 'arrow': 'none'},
    'romance': {'label': '恋情', 'style': 'solid', 'color': '#ff66bb', 'width': 3, 'arrow': 'none'},
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
    BASE_NODE_SIZE = 55
    SIZE_PER_CONNECTION = 7  # 增加每连接的大小步长，让大节点更突出
    
    _global_max_connections = 1
    _config_min_size = 35  # 最小节点更小，突出大小对比
    _config_max_size = 115  # 最大节点稍微增大
    _config_min_brightness = 18
    _config_max_brightness = 55  # 最大节点更亮一些
    
    @classmethod
    def set_global_max_connections(cls, max_conn):
        cls._global_max_connections = max(1, max_conn)
    
    _enable_glow = True  # 类变量：辉光效果开关
    
    @classmethod
    def set_glow_enabled(cls, enabled):
        """设置辉光效果开关（类方法）"""
        cls._enable_glow = enabled
    
    _enable_size_sort = True  # 类变量：面积排序开关
    
    @classmethod
    def set_size_sort_enabled(cls, enabled):
        """设置面积排序显示开关（类方法）"""
        cls._enable_size_sort = enabled
    
    _enable_brightness_sort = True  # 类变量：亮度排序开关
    
    @classmethod
    def set_brightness_sort_enabled(cls, enabled):
        """设置按连接数排序节点亮度开关（类方法）"""
        cls._enable_brightness_sort = enabled
    
    _custom_rules = []
    
    @classmethod
    def set_custom_rules(cls, rules):
        """设置自定义规则列表"""
        cls._custom_rules = rules if rules else []
        cls.invalidate_glow_cache()
    
    @classmethod
    def load_custom_rules(cls, rules):
        """加载自定义规则列表（set_custom_rules的别名）"""
        cls.set_custom_rules(rules)
    
    @classmethod
    def get_custom_rules(cls):
        return cls._custom_rules
    
    @classmethod
    def evaluate_rule_for_node(cls, conn_count):
        """
        根据自定义规则评估节点的亮度和大小
        返回: (brightness_factor, size_px) 或 None(无匹配用默认)
        brightness_factor: 0.0~1.0 (用于计算亮度)
        size_px: 像素值 (直接使用的大小)
        """
        for rule in cls._custom_rules:
            rtype = rule.get('type', 'range')
            matched = False
            if rtype == 'range':
                min_c = rule.get('min_conn', 0)
                max_c = rule.get('max_conn', 99999)
                matched = min_c <= conn_count <= max_c
            elif rtype == 'threshold':
                threshold = rule.get('threshold', 0)
                matched = conn_count >= threshold
            if matched:
                bf = rule.get('brightness_factor', 1.0)
                
                # 优先用绝对像素值，如果没有用默认的factor
                apply_size = rule.get('apply_size', False)
                if apply_size:
                    min_size = rule.get('size_min_px', cls._config_min_size)
                    max_size = rule.get('size_max_px', cls._config_max_size)
                    # 计算在区间内的比例
                    max_conn_rule = rule.get('max_conn', 1)
                    min_conn_rule = rule.get('min_conn', 0)
                    if max_conn_rule > min_conn_rule:
                        ratio = (conn_count - min_conn_rule) / (max_conn_rule - min_conn_rule)
                    else:
                        ratio = 0.5
                    size_px = int(min_size + ratio * (max_size - min_size))
                else:
                    # 如果没有size，默认用原来的factor
                    sf = rule.get('size_factor', 1.0)
                    size_range = cls._config_max_size - cls._config_min_size
                    size_px = int(cls._config_min_size + sf * size_range)
                
                return (bf, size_px)
        return None
    
    @classmethod
    def serialize_rules_to_config(cls):
        import json
        return json.dumps(cls._custom_rules, ensure_ascii=False)
    
    @classmethod
    def deserialize_rules_from_config(cls, json_str):
        import json
        try:
            rules = json.loads(json_str)
            if isinstance(rules, list):
                cls._custom_rules = rules
        except Exception:
            pass
    
    _glow_pixmap_cache = {}
    _glow_exp_lut = None
    
    @classmethod
    def _get_exp_lut(cls):
        if cls._glow_exp_lut is None:
            cls._glow_exp_lut = [math.exp(-3.5 * (i / 11.0) ** 2) for i in range(12)]
        return cls._glow_exp_lut
    
    @classmethod
    def invalidate_glow_cache(cls):
        cls._glow_pixmap_cache.clear()
        cls._glow_exp_lut = None
    
    @classmethod
    def set_visual_config(cls, min_size, max_size, min_brightness, max_brightness):
        cls._config_min_size = min_size
        cls._config_max_size = max_size
        cls._config_min_brightness = min_brightness
        cls._config_max_brightness = max_brightness
        cls._glow_pixmap_cache.clear()
    
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
        self._selected = False  # 选中状态，显示+号按钮
        
        self._drag_start = None
        self._drag_original_pos = None
        self._is_dragging = False
        self._heat_factor = 0
        
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
        
        self._connection_count = 0
        self._node_size = self._calc_node_size()

        self.setPos(x, y)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges)
        self.setFlag(QGraphicsItem.ItemClipsToShape, False)
        self.setZValue(10)
        self.setAcceptHoverEvents(True)
        self._glow_pixmap = None
        self._glow_cache_key = None

    def _calc_node_size(self):
        # 确保节点足够大，能完整显示文字
        text_based = self._text_w + 60
        # 文字宽度有合理上限，防止极端情况
        text_based = min(text_based, 160)
        
        base = max(SciFiNodeItem._config_min_size, text_based)
        
        if self.node_type == 'character':
            base = max(base, 85)  # 人物节点稍大
        
        if SciFiNodeItem._custom_rules:
            rule_result = SciFiNodeItem.evaluate_rule_for_node(self._connection_count)
            if rule_result is not None:
                _, size_px = rule_result
                return max(base, size_px)
        
        # 默认逻辑：基于连接数动态增长
        max_conn = SciFiNodeItem._global_max_connections
        if max_conn > 0:
            normalized = self._connection_count / max_conn
            size_range = SciFiNodeItem._config_max_size - SciFiNodeItem._config_min_size
            dynamic_size = int(SciFiNodeItem._config_min_size + normalized * size_range)
            return max(base, dynamic_size)
        
        return int(base)
    
    def _effective_size(self):
        """统一获取节点大小的入口"""
        return self._node_size

    def update_connection_count(self):
        self._connection_count = len(self._edges)
        new_size = self._calc_node_size()
        if new_size != self._node_size:
            self.prepareGeometryChange()
            self._node_size = new_size
            self._glow_pixmap = None
            self._glow_cache_key = None
            self.update()
    
    def boundingRect(self):
        s = self._effective_size()
        # 合适的边界框，防止辉光被裁切，但不会太大
        padding = max(40, s * 1.2)
        total_size = s + padding * 2
        return QRectF(-total_size / 2, -total_size / 2, total_size, total_size)
    
    def shape(self):
        s = self._effective_size()
        padding = 12

        if self.node_type == 'character':
            path = QPainterPath()
            path.addEllipse(QPointF(0, 5), s/2 + padding, s/2 + padding)
            return path
        elif self.node_type == 'skill':
            path = QPainterPath()
            poly = QPolygonF([
                QPointF(0, -s/2 - padding),
                QPointF(s/2 + padding, -s/4),
                QPointF(s/2 + padding, s/4),
                QPointF(0, s/2 + padding + 5),
                QPointF(-s/2 - padding, s/4),
                QPointF(-s/2 - padding, -s/4)
            ])
            path.addPolygon(poly)
            path.closeSubpath()
            return path
        elif self.node_type == 'item':
            path = QPainterPath()
            poly = QPolygonF([
                QPointF(0, -s/2 - padding),
                QPointF(s/3 + padding, 0),
                QPointF(0, s/2 + padding + 5),
                QPointF(-s/3 - padding, 0)
            ])
            path.addPolygon(poly)
            path.closeSubpath()
            return path
        else:
            path = QPainterPath()
            path.addRoundedRect(QRectF(-s*0.42 - padding, -s*0.3 - padding, s*0.85 + padding*2, s*0.6 + padding*2 + 10), 8, 8)
            return path
    
    def paint(self, painter, option, widget):
        if option and option.exposedRect.isValid() and not option.exposedRect.intersects(self.boundingRect()):
            return
        
        painter.setRenderHint(QPainter.Antialiasing)
        c = self._highlight_color if self._highlight_color else self.base_color
        s = self._effective_size()
        half = s / 2
        
        # 获取背景明度
        bg_luminance = 128
        scene = self.scene()
        if scene and hasattr(scene, 'parent'):
            parent_view = scene.parent()
            if parent_view and hasattr(parent_view, 'get_background_luminance'):
                bg_luminance = parent_view.get_background_luminance()
        
        # 根据背景明度选择轮廓颜色！
        is_dark_background = (bg_luminance < 128)
        if is_dark_background:
            # 暗背景 → 用白色/亮色轮廓
            if self._hovered:
                outer_pen = QPen(QColor(c.red(), c.green(), c.blue(), 220), 3)
            else:
                outer_pen = QPen(QColor(c.red(), c.green(), c.blue(), 160), 2)
        else:
            # 亮背景 → 用黑色轮廓！
            if self._hovered:
                outer_pen = QPen(QColor(0, 0, 0, 220), 3)
            else:
                outer_pen = QPen(QColor(0, 0, 0, 160), 2)
        
        conn_glow_intensity = 0.0
        dim_factor = 1.0
        
        # 优先使用自定义规则，规则更融洽地结合亮度和大小
        if SciFiNodeItem._custom_rules:
            rule_result = SciFiNodeItem.evaluate_rule_for_node(self._connection_count)
            if rule_result is not None:
                dim_factor, _ = rule_result
                # 从 dim_factor 推导出辉光强度（dim>=0.4开始有光，0.4→0, 1.0→1）
                conn_glow_intensity = max(0.0, min(1.0, (dim_factor - 0.4) / 0.6))
            else:
                # 没有规则，回退到默认
                max_conn = SciFiNodeItem._global_max_connections
                if max_conn > 0:
                    ratio = self._connection_count / max_conn
                    if ratio < 0.33:
                        dim_factor = 0.55
                        conn_glow_intensity = 0.0
                    elif ratio < 0.5:
                        dim_factor = 0.8
                        conn_glow_intensity = (ratio - 0.33) / 0.34
                    else:
                        dim_factor = 1.0
                        conn_glow_intensity = (ratio - 0.5) / 0.5
        else:
            # 默认模式
            max_conn = SciFiNodeItem._global_max_connections
            if max_conn > 0:
                ratio = self._connection_count / max_conn
                if ratio < 0.33:
                    dim_factor = 0.55
                    conn_glow_intensity = 0.0
                elif ratio < 0.5:
                    dim_factor = 0.8
                    conn_glow_intensity = (ratio - 0.33) / 0.34
                else:
                    dim_factor = 1.0
                    conn_glow_intensity = (ratio - 0.5) / 0.5
        
        # 根据背景明度决定发光/吸光模式
        bg_luminance = 128  # 默认中间值
        scene = self.scene()
        if scene and hasattr(scene, 'parent'):
            parent_view = scene.parent()
            if parent_view and hasattr(parent_view, 'get_background_luminance'):
                bg_luminance = parent_view.get_background_luminance()
        
        # 阈值设为 128（0-255 中间值）
        is_dark_background = (bg_luminance < 128)
        
        glow_intensity = max(self._heat_factor, conn_glow_intensity)
        if SciFiNodeItem._enable_glow and glow_intensity > 0.05:
            painter.save()
            painter.setPen(Qt.NoPen)
            
            if is_dark_background:
                # ==================== 暗背景：高斯辉光(中心→外衰减) ====================
                glow_r = half * (1.2 + glow_intensity * 0.8)
                g = QRadialGradient(QPointF(0, 0), glow_r)
                g.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(), int(60 + glow_intensity * 195)))
                g.setColorAt(0.25, QColor(c.red(), c.green(), c.blue(), int(40 + glow_intensity * 150)))
                g.setColorAt(0.5, QColor(c.red(), c.green(), c.blue(), int(25 + glow_intensity * 100)))
                g.setColorAt(0.75, QColor(c.red(), c.green(), c.blue(), int(15 + glow_intensity * 60)))
                g.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), int(5 + glow_intensity * 20)))
                painter.setBrush(QBrush(g))
                painter.drawEllipse(QPointF(0, 0), glow_r, glow_r)
            else:
                # ==================== 亮背景：星环效果(仅外部光环) ====================
                ring_outer = half * (1.4 + glow_intensity * 0.6)
                ring_inner = half * 1.05
                outer_path = QPainterPath()
                outer_path.addEllipse(QPointF(0, 0), ring_outer, ring_outer)
                inner_path = QPainterPath()
                inner_path.addEllipse(QPointF(0, 0), ring_inner, ring_inner)
                ring_path = outer_path - inner_path
                ring_alpha = int(50 + glow_intensity * 100)
                painter.setBrush(QBrush(QColor(0, 0, 0, ring_alpha)))
                painter.drawPath(ring_path)
            
            painter.restore()
        
        if self.node_type == 'character':
            self._draw_circle(painter, c, half, outer_pen, dim_factor)
        elif self.node_type == 'skill':
            self._draw_hexagon(painter, c, half, outer_pen, dim_factor)
        elif self.node_type == 'item':
            self._draw_diamond(painter, c, half, outer_pen, dim_factor)
        elif self.node_type == 'foreshadowing':
            self._draw_dashed_rect(painter, c, half, outer_pen, dim_factor)
        elif self.node_type == 'adventure':
            self._draw_adventure(painter, c, half, outer_pen, dim_factor)
        elif self.node_type == 'faction':
            self._draw_faction(painter, c, half, outer_pen, dim_factor)
        elif self.node_type == 'time_point':
            self._draw_time_point(painter, c, half, outer_pen, dim_factor)
        else:
            self._draw_rounded_rect(painter, c, half, outer_pen, dim_factor)
        
        self._draw_label(painter, c, half)
        self._draw_name(painter, half)
        
        if self._selected:
            painter.save()
            painter.setBrush(Qt.NoBrush)
            if is_dark_background:
                painter.setPen(QPen(QColor(255, 255, 255, 180), 4))
                painter.drawEllipse(QPointF(0, 0), half + 4, half + 4)
            painter.setPen(QPen(QColor(0, 0, 0, 220), 3))
            painter.drawEllipse(QPointF(0, 0), half + 2, half + 2)
            painter.restore()
        
        if self._is_pinned:
            pin_pen = QPen(QColor(255, 255, 100, 200), 2)
            painter.setPen(pin_pen)
            painter.drawLine(QPointF(-half + 4, -half + 4), QPointF(-half + 14, -half + 14))
            painter.drawLine(QPointF(-half + 4, -half + 14), QPointF(-half + 14, -half + 4))


    def _draw_circle(self, painter, c, r, pen, dim_factor=1.0):
        painter.setPen(pen)
        grad = QRadialGradient(QPointF(0, 0), r)
        
        if SciFiNodeItem._enable_brightness_sort:
            max_conn = SciFiNodeItem._global_max_connections
            if max_conn > 0:
                normalized = self._connection_count / max_conn
            else:
                normalized = 0
            brightness_range = SciFiNodeItem._config_max_brightness - SciFiNodeItem._config_min_brightness
            brightness_pct = SciFiNodeItem._config_min_brightness + normalized * brightness_range
            brightness = int((brightness_pct / 100.0) * 255 * max(dim_factor, 0.05))
            brightness = min(255, max(0, brightness))
        else:
            brightness = int((SciFiNodeItem._config_max_brightness / 100.0) * 255 * max(dim_factor, 0.05))
        
        center_c = self._blend_color(c, dim_factor)
        
        base_alpha = max(120, int(brightness * 1.5))
        grad.setColorAt(0, QColor(center_c.red(), center_c.green(), center_c.blue(), min(255, base_alpha)))
        grad.setColorAt(0.7, QColor(c.red(), c.green(), c.blue(), int(min(180, brightness))))
        grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), int(min(100, brightness * 0.6))))
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(QPointF(0, 0), r, r)
        
        inner_alpha = min(160, int((100 + self._connection_count * 5) * max(dim_factor, 0.05)))
        painter.setPen(QPen(QColor(255, 255, 255, inner_alpha), 1))
        painter.drawEllipse(QPointF(0, 0), r * 0.75, r * 0.75)
    
    def _blend_color(self, c, dim_factor):
        """根据 dim_factor 混合颜色：
           dim_factor < 0.5 → 混入黑色（变暗）
           dim_factor > 0.5 → 混入白色（变亮）"""
        if dim_factor >= 0.5:
            blend = (dim_factor - 0.5) * 0.8  # 最大40%白色
            return QColor(
                int(c.red() + (255 - c.red()) * blend),
                int(c.green() + (255 - c.green()) * blend),
                int(c.blue() + (255 - c.blue()) * blend),
                c.alpha()
            )
        else:
            blend = (0.5 - dim_factor) * 0.7  # 最大35%黑色
            return QColor(
                int(c.red() * (1.0 - blend)),
                int(c.green() * (1.0 - blend)),
                int(c.blue() * (1.0 - blend)),
                c.alpha()
            )
    
    def _draw_hexagon(self, painter, c, r, pen, dim_factor=1.0):
        painter.setPen(pen)
        poly = QPolygonF()
        for i in range(6):
            angle = math.pi * 2 * i / 6 - math.pi / 2
            poly.append(QPointF(r * math.cos(angle), r * math.sin(angle)))
        
        center_c = self._blend_color(c, dim_factor)
        
        grad = QLinearGradient(QPointF(-r, -r), QPointF(r, r))
        b = int(min(180, 100 + self._connection_count * 8) * max(dim_factor, 0.05))
        grad.setColorAt(0, QColor(center_c.red(), center_c.green(), center_c.blue(), b))
        grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), max(60, int(b * 0.65))))
        painter.setBrush(QBrush(grad))
        painter.drawPolygon(poly)
    
    def _draw_diamond(self, painter, c, r, pen, dim_factor=1.0):
        painter.setPen(pen)
        poly = QPolygonF()
        poly.append(QPointF(0, -r))
        poly.append(QPointF(r * 0.65, 0))
        poly.append(QPointF(0, r))
        poly.append(QPointF(-r * 0.65, 0))
        
        center_c = self._blend_color(c, dim_factor)
        
        grad = QLinearGradient(QPointF(0, -r), QPointF(0, r))
        b = int(min(180, 100 + self._connection_count * 8) * max(dim_factor, 0.05))
        grad.setColorAt(0, QColor(center_c.red(), center_c.green(), center_c.blue(), b))
        grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), max(60, int(b * 0.65))))
        painter.setBrush(QBrush(grad))
        painter.drawPolygon(poly)
    
    def _draw_dashed_rect(self, painter, c, r, pen, dim_factor=1.0):
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        cor = 6
        b = int(min(160, 80 + self._connection_count * 8) * max(dim_factor, 0.05))
        painter.setBrush(QBrush(QColor(c.red(), c.green(), c.blue(), b)))
        painter.drawRoundedRect(QRectF(-r * 0.8, -r * 0.6, r * 1.6, r * 1.2), cor, cor)
    
    def _draw_adventure(self, painter, c, r, pen, dim_factor=1.0):
        painter.setPen(pen)
        tri_top = QPolygonF()
        tri_top.append(QPointF(0, -r))
        tri_top.append(QPointF(r, 0))
        tri_top.append(QPointF(0, r))
        tri_bottom = QPolygonF()
        tri_bottom.append(QPointF(0, -r))
        tri_bottom.append(QPointF(-r, 0))
        tri_bottom.append(QPointF(0, r))
        
        center_c = self._blend_color(c, dim_factor)
        
        b = int(min(200, 120 + self._connection_count * 8) * max(dim_factor, 0.05))
        grad_top = QLinearGradient(QPointF(0, -r), QPointF(0, r))
        grad_top.setColorAt(0, QColor(center_c.red(), center_c.green(), center_c.blue(), b))
        grad_top.setColorAt(1, QColor(c.red(), c.green(), c.blue(), max(70, int(b * 0.65))))
        grad_bottom = QLinearGradient(QPointF(0, r), QPointF(0, -r))
        grad_bottom.setColorAt(0, QColor(center_c.red(), center_c.green(), center_c.blue(), b))
        grad_bottom.setColorAt(1, QColor(c.red(), c.green(), c.blue(), max(70, int(b * 0.65))))
        painter.setBrush(QBrush(grad_top))
        painter.drawPolygon(tri_top)
        painter.setBrush(QBrush(grad_bottom))
        painter.drawPolygon(tri_bottom)
    
    def _draw_faction(self, painter, c, r, pen, dim_factor=1.0):
        painter.setPen(pen)
        poly = QPolygonF()
        poly.append(QPointF(0, -r))
        poly.append(QPointF(-r * 0.65, -r * 0.5))
        poly.append(QPointF(-r * 0.65, r * 0.2))
        poly.append(QPointF(0, r))
        poly.append(QPointF(r * 0.65, r * 0.2))
        poly.append(QPointF(r * 0.65, -r * 0.5))
        
        center_c = self._blend_color(c, dim_factor)
        
        grad = QLinearGradient(QPointF(0, -r), QPointF(0, r))
        b = int(min(190, 110 + self._connection_count * 8) * max(dim_factor, 0.05))
        grad.setColorAt(0, QColor(center_c.red(), center_c.green(), center_c.blue(), b))
        grad.setColorAt(0.6, QColor(c.red(), c.green(), c.blue(), max(70, int(b * 0.65))))
        grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), max(40, int(b * 0.4))))
        painter.setBrush(QBrush(grad))
        painter.drawPolygon(poly)
    
    def _draw_time_point(self, painter, c, r, pen, dim_factor=1.0):
        painter.setPen(pen)
        tri_top = QPolygonF()
        tri_top.append(QPointF(-r * 0.65, -r))
        tri_top.append(QPointF(r * 0.65, -r))
        tri_top.append(QPointF(0, 0))
        tri_bottom = QPolygonF()
        tri_bottom.append(QPointF(-r * 0.65, r))
        tri_bottom.append(QPointF(r * 0.65, r))
        tri_bottom.append(QPointF(0, 0))
        
        center_c = self._blend_color(c, dim_factor)
        
        grad_top = QLinearGradient(QPointF(0, -r), QPointF(0, 0))
        b = int(min(200, 120 + self._connection_count * 8) * max(dim_factor, 0.05))
        grad_top.setColorAt(0, QColor(center_c.red(), center_c.green(), center_c.blue(), b))
        grad_top.setColorAt(1, QColor(c.red(), c.green(), c.blue(), max(60, int(b * 0.65))))
        grad_bottom = QLinearGradient(QPointF(0, r), QPointF(0, 0))
        grad_bottom.setColorAt(0, QColor(center_c.red(), center_c.green(), center_c.blue(), b))
        grad_bottom.setColorAt(1, QColor(c.red(), c.green(), c.blue(), max(60, int(b * 0.65))))
        painter.setBrush(QBrush(grad_top))
        painter.drawPolygon(tri_top)
        painter.setBrush(QBrush(grad_bottom))
        painter.drawPolygon(tri_bottom)
    
    def _draw_rounded_rect(self, painter, c, r, pen, dim_factor=1.0):
        painter.setPen(pen)
        cor = 8
        b = int(min(160, 80 + self._connection_count * 8) * max(dim_factor, 0.05))
        painter.setBrush(QBrush(QColor(c.red(), c.green(), c.blue(), b)))
        painter.drawRoundedRect(QRectF(-r * 0.85, -r * 0.6, r * 1.7, r * 1.2), cor, cor)
    
    def _draw_glow_cached(self, painter, base_color, draw_r, intensity):
        size_key = int(draw_r / 10) * 10
        # 把 intensity 也作为缓存 key，因为不同强度辉光不同
        int_key = int(intensity * 100)
        cache_key = (size_key, base_color.rgb(), int_key)
        pixmap = SciFiNodeItem._glow_pixmap_cache.get(cache_key)
        if pixmap is None:
            # 更大的画布容纳完整光晕
            dim = int(draw_r * 5.0)
            pixmap = QPixmap(dim, dim)
            pixmap.fill(Qt.transparent)
            px_painter = QPainter(pixmap)
            px_painter.setRenderHint(QPainter.Antialiasing)
            
            # 黑洞效果：中心暗，向外渐亮！
            center = QPointF(dim / 2, dim / 2)
            # 强度越大，辉光范围越大
            glow_radius = draw_r * (2.2 + intensity * 1.0)
            gr = QRadialGradient(center, glow_radius)
            
            # 黑洞反向：中心点接近透明，向外变亮！
            # 中心暗（0 → 20）
            center_alpha = int(10 + intensity * 30)
            # 中间区域（30 → 120）
            mid_alpha = int(20 + intensity * 100)
            # 中间偏外（60 → 180）
            outer1_alpha = int(40 + intensity * 140)
            # 最外层亮（80 → 220）
            outer2_alpha = int(60 + intensity * 160)
            
            # 中心点：最暗
            gr.setColorAt(0.0, QColor(base_color.red(), base_color.green(), base_color.blue(), center_alpha))
            # 节点边缘附近
            gr.setColorAt(0.3, QColor(base_color.red(), base_color.green(), base_color.blue(), mid_alpha))
            # 中间偏外
            gr.setColorAt(0.6, QColor(base_color.red(), base_color.green(), base_color.blue(), outer1_alpha))
            # 最外层
            gr.setColorAt(0.9, QColor(base_color.red(), base_color.green(), base_color.blue(), outer2_alpha))
            # 最边缘稍微衰减
            gr.setColorAt(1.0, QColor(base_color.red(), base_color.green(), base_color.blue(), int(outer2_alpha * 0.7)))
            
            px_painter.setPen(QPen(Qt.NoPen))
            px_painter.setBrush(QBrush(gr))
            px_painter.drawEllipse(center, glow_radius, glow_radius)
            
            px_painter.end()
            SciFiNodeItem._glow_pixmap_cache[cache_key] = pixmap
            if len(SciFiNodeItem._glow_pixmap_cache) > 50:
                # 缓存太多时清空
                SciFiNodeItem._glow_pixmap_cache.clear()
        
        cp = painter.compositionMode()
        painter.setCompositionMode(QPainter.CompositionMode_Plus)
        painter.drawPixmap(QPointF(-pixmap.width() / 2, -pixmap.height() / 2), pixmap)
        painter.setCompositionMode(cp)
    
    def _update_cache_mode(self):
        # 始终关闭缓存，防止辉光被裁切！
        self.setCacheMode(QGraphicsItem.NoCache)
    
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
        
        # 获取背景明度
        bg_luminance = 128  # 默认中间值
        scene = self.scene()
        if scene and hasattr(scene, 'parent'):
            parent_view = scene.parent()
            if parent_view and hasattr(parent_view, 'get_background_luminance'):
                bg_luminance = parent_view.get_background_luminance()
        
        # ==================== 字体颜色逻辑 ====================
        # 完全基于背景明度！
        # 背景暗 → 白色字体
        # 背景亮 → 黑色字体
        if bg_luminance < 128:
            painter.setPen(QColor(255, 255, 255, 250))
        else:
            painter.setPen(QColor(0, 0, 0, 255))
        
        fm = QFontMetrics(self._name_font)
        text_w = fm.horizontalAdvance(self.node_name)
        text_height = fm.height()
        baseline_y = -(text_height // 2 - fm.ascent())
        painter.drawText(QPointF(-text_w / 2, baseline_y), self.node_name)
    
    def set_highlight_color(self, color):
        self._highlight_color = color
        self.update()

    def add_edge_ref(self, edge_data):
        self._edges.append(edge_data)

    def remove_edge_ref(self, edge_data):
        if edge_data in self._edges:
            self._edges.remove(edge_data)
    
    def itemChange(self, change, value):
        return super().itemChange(change, value)
    
    def hoverEnterEvent(self, event):
        self._hovered = True
        self.setZValue(20)
        self.setCacheMode(QGraphicsItem.NoCache)
        views = self.scene().views() if self.scene() else []
        for v in views:
            if isinstance(v, NetworkGraphView):
                SciFiEdge.highlight_node_edges(self.node_name, v.node_items, v.edge_items)
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.setZValue(10)
        self._update_cache_mode()
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
                self._on_right_click(self.node_name, event.screenPos().toPoint(), self.mapToScene(event.pos()))
            event.accept()
            return
        elif event.button() == Qt.LeftButton:
            if not self._selected and self.scene():
                views = self.scene().views()
                for view in views:
                    if hasattr(view, '_select_node'):
                        view._select_node(self)
            self._drag_start = event.scenePos()
            self._drag_original_pos = self.pos()
            self._is_dragging = False
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_start is not None:
            delta = event.scenePos() - self._drag_start
            dist = (event.scenePos() - self._drag_start).manhattanLength()
            if dist > 5:
                if not self._is_dragging:
                    self._is_dragging = True
                    self.setCacheMode(QGraphicsItem.NoCache)
                new_pos = self._drag_original_pos + delta
                self.setPos(new_pos)
                view = self.scene().views()[0] if self.scene() and self.scene().views() else None
                if view and isinstance(view, NetworkGraphView):
                    view._dirty_drag_nodes.add(self.node_name)
                    if not view._drag_edge_update_timer.isActive():
                        view._drag_edge_update_timer.start()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._is_dragging:
            self._is_dragging = False
            self._drag_start = None
            self._drag_original_pos = None
            self._update_cache_mode()
            for edge_data in self._edges:
                if hasattr(edge_data, 'update_positions'):
                    edge_data.update_positions()
            views = self.scene().views() if self.scene() else []
            if views and isinstance(views[0], NetworkGraphView):
                views[0].save_node_positions()
            event.accept()
            return

        self._is_dragging = False
        self._drag_start = None
        self._drag_original_pos = None
        super().mouseReleaseEvent(event)


class SciFiEdge:
    """科幻风格连线 - 按关系类型区分线型"""
    
    STYLE_MAP = {
        'solid': Qt.SolidLine,
        'dash': Qt.DashLine,
        'dot': Qt.DotLine,
        'dash_dot': Qt.DashDotDotLine,
    }
    
    _current_highlight_node = None
    _is_dark_background = True  # 由 NetworkGraphView 更新
    
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
        init_color = q_color if SciFiEdge._is_dark_background else QColor(0, 0, 0)
        gp = QPen(QColor(init_color.red(), init_color.green(), init_color.blue(), 15), width * 3.5)
        gp.setCosmetic(True)
        gp.setStyle(q_style)
        self.glow_path.setPen(gp)
        self.glow_path.setZValue(1)
        self.scene.addItem(self.glow_path)
        
        self.edge_path = QGraphicsPathItem()
        ep = QPen(QColor(init_color.red(), init_color.green(), init_color.blue(), 80), width)
        ep.setCosmetic(True)
        ep.setStyle(q_style)
        self.edge_path.setPen(ep)
        self.edge_path.setZValue(2)
        self.scene.addItem(self.edge_path)

        self.hit_area = QGraphicsPathItem()
        hit_pen = QPen(Qt.NoPen)
        hit_brush = QBrush(QColor(255, 255, 255, 0))
        self.hit_area.setPen(hit_pen)
        self.hit_area.setBrush(hit_brush)
        self.hit_area.setZValue(0.5)
        self.scene.addItem(self.hit_area)
        
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
        if hovered:
            anim = QPropertyAnimation(self.glow_path, b"opacity")
            anim.setDuration(200)
            anim.setStartValue(0.5)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()
    
    def _apply_dim(self):
        if SciFiEdge._is_dark_background:
            q_color = self._q_color
        else:
            q_color = QColor(0, 0, 0)  # 亮背景用黑色
        width = self._width
        q_style = self._q_style
        ep = QPen(QColor(q_color.red(), q_color.green(), q_color.blue(), 25), width)
        ep.setCosmetic(True)
        ep.setStyle(q_style)
        self.edge_path.setPen(ep)
        gp = QPen(QColor(q_color.red(), q_color.green(), q_color.blue(), 5), width * 2)
        gp.setCosmetic(True)
        gp.setStyle(q_style)
        self.glow_path.setPen(gp)
    
    def _apply_highlight(self):
        if SciFiEdge._is_dark_background:
            q_color = self._q_color
        else:
            q_color = QColor(0, 0, 0)
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
        
        from_r = self.from_node._effective_size() / 2.0
        to_r = self.to_node._effective_size() / 2.0
        
        ux = dx / dist
        uy = dy / dist
        
        start_pos = QPointF(from_pos.x() + ux * from_r, from_pos.y() + uy * from_r)
        end_pos = QPointF(to_pos.x() - ux * to_r, to_pos.y() - uy * to_r)
        
        path = QPainterPath()
        path.moveTo(start_pos)
        
        mid_x = (start_pos.x() + end_pos.x()) / 2
        mid_y = (start_pos.y() + end_pos.y()) / 2
        ctrl_off = min(abs(dx), abs(dy)) * 0.2 + 20
        
        if abs(dx) > abs(dy):
            sgn = 1 if from_pos.y() < to_pos.y() else -1
            c1 = QPointF(mid_x, from_pos.y() + ctrl_off * sgn)
            c2 = QPointF(mid_x, to_pos.y() - ctrl_off * sgn)
        else:
            sgn = 1 if from_pos.x() < to_pos.x() else -1
            c1 = QPointF(from_pos.x() + ctrl_off * sgn, mid_y)
            c2 = QPointF(to_pos.x() - ctrl_off * sgn, mid_y)
        
        path.cubicTo(c1, c2, end_pos)
        
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

        hit_path = QPainterPath()
        hit_pen = QPen(QColor(0, 0, 0, 1), 18, Qt.SolidLine, Qt.RoundCap)
        hit_path.addPath(path)
        self.hit_area.setPath(hit_path)
        self.hit_area.setPen(hit_pen)
    
    def set_visible(self, visible):
        self.glow_path.setVisible(visible)
        self.edge_path.setVisible(visible)
        self.hit_area.setVisible(visible)
        self.dot.setVisible(visible)
        if self._arrow_item:
            self._arrow_item.setVisible(visible)

    def update_positions(self):
        self._update_path()
    
    def remove_from_scene(self):
        if self.scene:
            if self.glow_path.scene():
                self.scene.removeItem(self.glow_path)
            if self.edge_path.scene():
                self.scene.removeItem(self.edge_path)
            if self.hit_area.scene():
                self.scene.removeItem(self.hit_area)
            if self.dot.scene():
                self.scene.removeItem(self.dot)
            if self._arrow_item and self._arrow_item.scene():
                self.scene.removeItem(self._arrow_item)


class LegendOverlay(QWidget):
    def __init__(self, graph_view):
        super().__init__(graph_view.viewport())
        self._graph_view = graph_view
        self.setMaximumWidth(300)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet(f"""
            LegendOverlay {{
                background-color: {_theme('card_bg', '#FFFFFF')}F0;
                border: 1px solid {_theme('border_color', '#DEE2E6')};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        title = QLabel("图例与关系展示")
        title.setStyleSheet(f"color:{_theme('fg_color', '#212529')};font-size:14px;font-weight:bold;")
        layout.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color:{_theme('border_color', '#DEE2E6')};")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        type_title = QLabel("节点类型")
        type_title.setStyleSheet(f"color:{_theme('accent_color', '#0078D4')};font-size:12px;font-weight:bold;margin-top:4px;")
        layout.addWidget(type_title)

        self._type_content = QLabel()
        self._type_content.setStyleSheet(f"color:{_theme('fg_color', '#212529')};font-size:12px;line-height:1.4;")
        self._type_content.setWordWrap(True)
        layout.addWidget(self._type_content)

        rel_title = QLabel("关系线型")
        rel_title.setStyleSheet(f"color:{_theme('accent_color', '#0078D4')};font-size:12px;font-weight:bold;margin-top:6px;")
        layout.addWidget(rel_title)

        self._rel_content = QLabel()
        self._rel_content.setStyleSheet(f"color:{_theme('fg_color', '#212529')};font-size:11px;line-height:1.4;")
        self._rel_content.setWordWrap(True)
        layout.addWidget(self._rel_content)
        self.adjustSize()
        for child in self.findChildren(QWidget):
            child.setAttribute(Qt.WA_TransparentForMouseEvents, False)

    def refresh(self, type_colors, groups):
        lines = []
        for t in sorted(groups.keys()):
            c = type_colors.get(t, '#888')
            label = NODE_LABELS.get(t, t)
            lines.append(f"<span style='color:{c};font-size:16px;font-weight:bold;'>■ {label}</span>")

        rel_lines = [
            f"<span style='color:{_theme("text_secondary", "#6C757D")};font-size:14px;'>━━ 实线: 友谊 / 恋情 / 敌对</span>",
            f"<span style='color:{_theme("text_secondary", "#6C757D")};font-size:14px;'>┄┄ 虚线: 掌握 / 传授 / 背负</span>",
            f"<span style='color:{_theme("text_secondary", "#6C757D")};font-size:14px;'>… … 点线: 暗示 / 推测</span>",
            f"<span style='color:{_theme("text_secondary", "#6C757D")};font-size:14px;'>┅┅ 点划线: 位于 / 包含</span>",
        ]
        self._type_content.setText("&nbsp;&nbsp;".join(lines))
        self._rel_content.setText("<br>".join(rel_lines))
        self.adjustSize()

    def apply_style(self, font_name, font_size):
        title_fs = font_size + 2
        section_fs = font_size - 1
        content_fs = font_size
        rel_fs = font_size - 1
        self.layout().itemAt(0).widget().setStyleSheet(f"color:{_theme('fg_color', '#212529')};font-size:{title_fs}px;font-weight:bold;font-family:'{font_name}';")
        self.layout().itemAt(2).widget().setStyleSheet(f"color:{_theme('accent_color', '#0078D4')};font-size:{section_fs}px;font-weight:bold;margin-top:6px;font-family:'{font_name}';")
        self._type_content.setStyleSheet(f"color:{_theme('fg_color', '#212529')};font-size:{content_fs}px;line-height:1.5;font-family:'{font_name}';")
        self.layout().itemAt(4).widget().setStyleSheet(f"color:{_theme('accent_color', '#0078D4')};font-size:{section_fs}px;font-weight:bold;margin-top:8px;font-family:'{font_name}';")
        self._rel_content.setStyleSheet(f"color:{_theme('fg_color', '#212529')};font-size:{rel_fs}px;line-height:1.6;font-family:'{font_name}';")
        if hasattr(self, '_last_type_colors'):
            lines = []
            for t in sorted(self._last_groups.keys()):
                c = self._last_type_colors.get(t, '#888')
                label = NODE_LABELS.get(t, t)
                lines.append(f"<span style='color:{c};font-size:{content_fs}px;font-weight:bold;'>■ {label}</span>")
            rel_lines = [
                f"<span style='color:{_theme('text_secondary', '#6C757D')};font-size:{rel_fs}px;'>━━ 实线: 友谊 / 恋情 / 敌对</span>",
                f"<span style='color:{_theme('text_secondary', '#6C757D')};font-size:{rel_fs}px;'>┄┄ 虚线: 掌握 / 传授 / 背负</span>",
                f"<span style='color:{_theme('text_secondary', '#6C757D')};font-size:{rel_fs}px;'>… … 点线: 暗示 / 推测</span>",
                f"<span style='color:{_theme('text_secondary', '#6C757D')};font-size:{rel_fs}px;'>┅┅ 点划线: 位于 / 包含</span>",
            ]
            self._type_content.setText("&nbsp;&nbsp;".join(lines))
            self._rel_content.setText("<br>".join(rel_lines))

    def refresh(self, type_colors, groups):
        self._last_type_colors = type_colors
        self._last_groups = groups
        lines = []
        for t in sorted(groups.keys()):
            c = type_colors.get(t, '#888')
            label = NODE_LABELS.get(t, t)
            lines.append(f"<span style='color:{c};font-size:16px;font-weight:bold;'>■ {label}</span>")

        rel_lines = [
            f"<span style='color:{_theme("text_secondary", "#6C757D")};font-size:14px;'>━━ 实线: 友谊 / 恋情 / 敌对</span>",
            f"<span style='color:{_theme("text_secondary", "#6C757D")};font-size:14px;'>┄┄ 虚线: 掌握 / 传授 / 背负</span>",
            f"<span style='color:{_theme("text_secondary", "#6C757D")};font-size:14px;'>… … 点线: 暗示 / 推测</span>",
            f"<span style='color:{_theme("text_secondary", "#6C757D")};font-size:14px;'>┅┅ 点划线: 位于 / 包含</span>",
        ]
        self._type_content.setText("&nbsp;&nbsp;".join(lines))
        self._rel_content.setText("<br>".join(rel_lines))
        self.adjustSize()


class NodeIndexOverlay(QWidget):
    toggle_changed = pyqtSignal(bool)

    def __init__(self, graph_view, parent=None):
        super().__init__(parent)
        self._graph_view = graph_view
        self._collapsed = True
        self._expanded_width = 280

        self.setFixedWidth(36)
        self.setMinimumHeight(500)
        self.setStyleSheet("NodeIndexOverlay { background: transparent; border: none; }")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header_widget = QWidget()
        header_widget.setStyleSheet(f"background:{_theme('bg_color', '#F8F9FA')};")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(2, 4, 2, 4)
        header_layout.setSpacing(2)

        self._toggle_btn = QPushButton("▶")
        self._toggle_btn.setFixedSize(32, 32)
        self._toggle_btn.setToolTip("展开节点索引面板")
        self._toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_theme('accent_color', '#0078D4')};
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {_theme('btn_hover_color', '#106EBE')};
            }}
        """)
        self._toggle_btn.clicked.connect(self._toggle)
        header_layout.addWidget(self._toggle_btn)

        self._title_label = QLabel("节点索引")
        self._title_label.setStyleSheet(f"color:{_theme('fg_color', '#212529')};font-size:15px;font-weight:bold;padding-left:4px;")
        self._title_label.setVisible(False)
        header_layout.addWidget(self._title_label, 1)

        main_layout.addWidget(header_widget)

        self._list_container = QWidget()
        self._list_container.setVisible(False)
        list_layout = QVBoxLayout(self._list_container)
        list_layout.setContentsMargins(6, 6, 6, 6)
        list_layout.setSpacing(6)

        start_label = QLabel("起点节点 (勾选)")
        start_label.setStyleSheet(f"color:{_theme('fg_color', '#212529')};font-size:14px;font-weight:bold;")
        list_layout.addWidget(start_label)

        self._start_list = QListWidget()
        self._start_list.setMaximumHeight(160)
        list_layout.addWidget(self._start_list)

        self._btn_container = QWidget()
        self._btn_container.setFixedHeight(42)
        self._btn_container.setVisible(False)
        btn_layout = QHBoxLayout(self._btn_container)
        btn_layout.setContentsMargins(2, 0, 2, 0)
        btn_layout.setSpacing(4)

        focus_btn = QPushButton("定位")
        focus_btn.setStyleSheet(f"QPushButton{{background:{_theme('accent_color', '#0078D4')};color:#FFFFFF;border:none;padding:5px 0px;border-radius:4px;font-size:13px;font-weight:bold;}}QPushButton:hover{{background:{_theme('btn_hover_color', '#106EBE')};}}")
        focus_btn.clicked.connect(self._on_focus)
        btn_layout.addWidget(focus_btn, 1)

        path_btn = QPushButton("路径")
        path_btn.setStyleSheet(f"QPushButton{{background:{_theme('accent_color', '#0078D4')};color:#FFFFFF;border:none;padding:5px 0px;border-radius:4px;font-size:13px;font-weight:bold;}}QPushButton:hover{{background:{_theme('btn_hover_color', '#106EBE')};}}")
        path_btn.clicked.connect(self._on_path)
        btn_layout.addWidget(path_btn, 1)

        clear_btn = QPushButton("清除")
        clear_btn.setStyleSheet(f"QPushButton{{background:{_theme('accent_color', '#0078D4')};color:#FFFFFF;border:none;padding:5px 0px;border-radius:4px;font-size:13px;font-weight:bold;}}QPushButton:hover{{background:{_theme('btn_hover_color', '#106EBE')};}}")
        clear_btn.clicked.connect(self._on_clear)
        btn_layout.addWidget(clear_btn, 1)

        list_layout.addWidget(self._btn_container)

        end_label = QLabel("终点节点 (勾选)")
        end_label.setStyleSheet(f"color:{_theme('fg_color', '#212529')};font-size:14px;font-weight:bold;")
        list_layout.addWidget(end_label)

        self._end_list = QListWidget()
        self._end_list.setMaximumHeight(160)
        list_layout.addWidget(self._end_list)

        main_layout.addWidget(self._list_container, 1)
        self._apply_list_style()

    def _apply_list_style(self):
        _accent = _theme('accent_color', '#0078D4')
        _fg = _theme('fg_color', '#212529')
        _bg = _theme('input_bg_color', '#FFFFFF')
        _border = _theme('border_color', '#DEE2E6')
        sheet = f"""
            QListWidget {{
                background: {_bg};
                color: {_fg};
                border: 1px solid {_border};
                font-size:14px;
                border-radius:4px;
                outline:none;
                padding: 2px 0 2px 4px;
            }}
            QListWidget::item {{
                padding:4px 6px;
                min-height:30px;
            }}
            QListWidget::item:selected {{
                background:{_accent}20;
                color:{_accent};
            }}
            QListWidget::item:hover {{
                background:{_accent}15;
                color:{_accent};
            }}
            QListWidget::vertical-scrollbar {{
                width: 10px;
                margin: 2px 4px 2px 2px;
            }}
            QScrollBar::handle:vertical {{
                background: #C0C0C0;
                min-height: 30px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #A0A0A0;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """
        self._start_list.setStyleSheet(sheet)
        self._end_list.setStyleSheet(sheet)

    def _toggle(self):
        self._collapsed = not self._collapsed
        if self._collapsed:
            self.setFixedWidth(36)
            self._toggle_btn.setText("▶")
            self._toggle_btn.setToolTip("展开节点索引面板")
            self._title_label.setVisible(False)
            self._list_container.setVisible(False)
            self._btn_container.setVisible(False)
        else:
            self.setFixedWidth(self._expanded_width)
            self._toggle_btn.setText("◀")
            self._toggle_btn.setToolTip("折叠节点索引面板")
            self._title_label.setVisible(True)
            self._list_container.setVisible(True)
            self._btn_container.setVisible(True)
        self.toggle_changed.emit(not self._collapsed)
        self._graph_view.update_legend_position()

    def refresh(self):
        self._start_list.clear()
        self._end_list.clear()
        names = sorted(self._graph_view.node_items.keys())
        for name in names:
            info = self._graph_view.node_items.get(name)
            kw = info.get('keyword', {}) if info else {}
            ntype = kw.get('type', '?')
            label = NODE_LABELS.get(ntype, ntype)
            text = f"{name} [{label}]"
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self._start_list.addItem(item)
            item2 = QListWidgetItem(text)
            item2.setFlags(item2.flags() | Qt.ItemIsUserCheckable)
            item2.setCheckState(Qt.Unchecked)
            self._end_list.addItem(item2)
    
    def _get_selected(self, lst):
        result = []
        for i in range(lst.count()):
            item = lst.item(i)
            if item.checkState() == Qt.Checked:
                result.append(item.text().split(' [')[0])
        return result
    
    def _on_focus(self):
        targets = self._get_selected(self._start_list) + self._get_selected(self._end_list)
        if len(targets) == 1:
            self._graph_view.focus_on_node(targets[0])
    
    def _on_path(self):
        starts = self._get_selected(self._start_list)
        ends = self._get_selected(self._end_list)
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
    
    def _on_clear(self):
        self._graph_view.clear_path_highlight()



class NetworkGraphView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setOptimizationFlags(QGraphicsView.DontAdjustForAntialiasing)
        self.setCacheMode(QGraphicsView.CacheNone)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self._is_panning = False
        self._pan_start = None
        
        self.zoom = 1.0
        self.node_items = {}
        self.edge_items = []
        self._pinned_nodes = set()
        self._focus_node = None
        self._on_node_double_click = None
        self._on_node_right_click = None
        self._on_edge_right_click = None
        self._connect_from_node = None
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
        
        self._legend_overlay = LegendOverlay(self)
        self._index_overlay = None  # 由外围容器通过 set_index_overlay() 设置
        self._legend_pos = ConfigManager.get('UI', 'overlay_position', fallback='bottom-right')
        self.set_right_click_callback(self._on_node_right_click)
        self.set_edge_right_click_callback(self._on_edge_right_click)

        legend_visible = ConfigManager.get_int('UI', 'legend_visible', fallback=1) == 1
        legend_font = ConfigManager.get('UI', 'legend_font', fallback='Microsoft YaHei')
        legend_size = ConfigManager.get_int('UI', 'legend_font_size', fallback=16)
        self.update_legend_config(legend_visible, legend_font, legend_size)
        
        self._drag_edge_update_timer = QTimer(self)
        self._drag_edge_update_timer.setInterval(16)
        self._drag_edge_update_timer.timeout.connect(self._flush_drag_edge_updates)
        self._dirty_drag_nodes = set()
        
        self._selected_node = None

        self._ctrl_held = False
        self._ctrl_hovered_node = None
        self._connect_source = None
        self._connect_line = None
        self._connect_dragging = False

        self._bg_color = _theme('graph_bg', '#F8F9FA')
        self._grid_color = _theme('graph_grid', '#E9ECEF')
        self._bg_qcolor = QColor(self._bg_color)
        self._bg_luminance = calculate_luminance(self._bg_qcolor)
        SciFiEdge._is_dark_background = (self._bg_luminance < 128)

        self._pin_overlays()
    
    def update_graph_background(self, bg_color=None, grid_color=None):
        if bg_color:
            self._bg_color = bg_color
            self._bg_qcolor = QColor(self._bg_color)
            self._bg_luminance = calculate_luminance(self._bg_qcolor)
            SciFiEdge._is_dark_background = (self._bg_luminance < 128)
        if grid_color:
            self._grid_color = grid_color
        self.scene.update()
        # 更新所有边的颜色
        for edge in self.edge_items:
            edge._apply_style()
    
    def get_background_luminance(self) -> float:
        """获取当前背景颜色的明度值（0-255）"""
        return self._bg_luminance
    
    def get_background_color(self) -> QColor:
        """获取当前背景颜色对象"""
        return self._bg_qcolor
    
    def set_index_overlay(self, overlay):
        self._index_overlay = overlay

    def update_legend_position(self):
        self._pin_overlays()

    def _pin_overlays(self):
        vp = self.viewport().rect()
        pos = self._legend_pos
        margin = 12

        legend_width = min(300, max(200, int(vp.width() * 0.22)))
        self._legend_overlay.setFixedWidth(legend_width)

        if 'bottom' in pos:
            ly = vp.bottom() - self._legend_overlay.height() - margin
        else:
            ly = margin

        if 'right' in pos:
            lx = vp.right() - legend_width - margin
        else:
            lx = margin

        self._legend_overlay.move(int(lx), int(ly))
        self._legend_overlay.raise_()
    
    def set_overlay_position(self, pos):
        self._legend_pos = pos
        ConfigManager.set('UI', 'overlay_position', pos)
        self._pin_overlays()

    def update_legend_config(self, visible, font_name, font_size):
        self._legend_overlay.setVisible(visible)
        self._legend_overlay.apply_style(font_name, font_size)
        self._pin_overlays()

    def update_connect_btn_config(self, size, color):
        pass
    
    def update_node_visual_config(self, min_size, max_size, min_brightness, max_brightness):
        SciFiNodeItem.set_visual_config(min_size, max_size, min_brightness, max_brightness)
        for data in self.node_items.values():
            data['item']._glow_pixmap = None
            data['item']._update_cache_mode()
            data['item'].update()
        self.scene.update()
    
    def update_glow_enabled(self, enabled):
        SciFiNodeItem.set_glow_enabled(enabled)
        SciFiNodeItem.invalidate_glow_cache()
        for data in self.node_items.values():
            data['item'].update()
        self.scene.update()
    
    def update_size_sort_enabled(self, enabled):
        SciFiNodeItem.set_size_sort_enabled(enabled)
        SciFiNodeItem.invalidate_glow_cache()
        if hasattr(self, 'node_items') and self.node_items:
            max_conn = max(
                len(data['item']._edges) 
                for data in self.node_items.values()
            ) or 1
            SciFiNodeItem.set_global_max_connections(max_conn)
        
        for data in self.node_items.values():
            data['item']._update_cache_mode()
            data['item'].update()
        self.scene.update()
    
    def update_brightness_sort_enabled(self, enabled):
        SciFiNodeItem.set_brightness_sort_enabled(enabled)
        SciFiNodeItem.invalidate_glow_cache()
        for data in self.node_items.values():
            data['item']._update_cache_mode()
            data['item'].update()
        self.scene.update()
    
    def highlight_drag_start(self, start_node):
        for name, data in self.node_items.items():
            item = data['item']
            if item is start_node:
                item.setOpacity(1.0)
                item.setZValue(30)
            else:
                item.setOpacity(0.35)
        for edge in self.edge_items:
            edge.glow_path.setOpacity(0.15)
            edge.edge_path.setOpacity(0.15)

    def highlight_drag_nodes(self, start_node, target_node):
        for name, data in self.node_items.items():
            item = data['item']
            if item is start_node or item is target_node:
                item.setOpacity(1.0)
                item.setZValue(30)
            else:
                item.setOpacity(0.35)
        for edge in self.edge_items:
            edge.glow_path.setOpacity(0.15)
            edge.edge_path.setOpacity(0.15)

    def clear_drag_highlight(self):
        for data in self.node_items.values():
            data['item'].setOpacity(1.0)
            data['item'].setZValue(10)
        for edge in self.edge_items:
            edge.glow_path.setOpacity(1.0)
            edge.edge_path.setOpacity(1.0)

    def add_edge_incremental(self, from_name, to_name, rel_type):
        if from_name not in self.node_items or to_name not in self.node_items:
            return
        from_item = self.node_items[from_name]['item']
        to_item = self.node_items[to_name]['item']
        edge = SciFiEdge(self.scene, from_item, to_item, rel_type)
        self.edge_items.append(edge)
        from_item.add_edge_ref(edge)
        to_item.add_edge_ref(edge)
        self._invalidate_cache()
        max_conn = self._calculate_max_connections()
        SciFiNodeItem.set_global_max_connections(max_conn)
        from_item.update_connection_count()
        to_item.update_connection_count()
        for data in self.node_items.values():
            data['item'].update()
        self._cache_node_properties()
        if self._index_overlay:
            self._index_overlay.refresh()
        self.save_node_positions()

    def remove_edge_incremental(self, from_name, to_name, rel_type):
        to_remove = None
        for i, edge in enumerate(self.edge_items):
            if (edge.from_node and edge.to_node and
                hasattr(edge.from_node, 'node_name') and hasattr(edge.to_node, 'node_name') and
                edge.from_node.node_name == from_name and
                edge.to_node.node_name == to_name and
                edge.rel_type == rel_type):
                to_remove = (i, edge)
                break
        if to_remove:
            idx, edge = to_remove
            if edge.from_node:
                edge.from_node.remove_edge_ref(edge)
                edge.from_node.update_connection_count()
            if edge.to_node and edge.to_node is not edge.from_node:
                edge.to_node.remove_edge_ref(edge)
                edge.to_node.update_connection_count()
            edge.remove_from_scene()
            self.edge_items.pop(idx)
            self._invalidate_cache()
            max_conn = self._calculate_max_connections()
            SciFiNodeItem.set_global_max_connections(max_conn)
            for data in self.node_items.values():
                data['item'].update()
            self._cache_node_properties()
            if self._index_overlay:
                self._index_overlay.refresh()

    def save_node_positions(self):
        for name, data in self.node_items.items():
            pos = data['item'].pos()
            ConfigManager.set('Graph', f'node_pos_{name}', f"{pos.x():.1f},{pos.y():.1f}")
        self._cache_node_properties()

    def _cache_node_properties(self):
        max_conn = self._calculate_max_connections()
        ConfigManager.set('Graph', 'max_connections', str(max_conn))
        for name, data in self.node_items.items():
            item = data['item']
            conn_count = len(item._edges)
            size = item._effective_size()
            ConfigManager.set('Graph', f'node_cache_{name}_conn', str(conn_count))
            ConfigManager.set('Graph', f'node_cache_{name}_size', str(size))
        ConfigManager.set('Graph', 'on_stored', '1')

    def _flush_drag_edge_updates(self):
        dirty = self._dirty_drag_nodes.copy()
        self._dirty_drag_nodes.clear()
        for node_name in dirty:
            if node_name in self.node_items:
                item = self.node_items[node_name]['item']
                for edge_data in item._edges:
                    if hasattr(edge_data, 'update_positions'):
                        edge_data.update_positions()
        if not self._dirty_drag_nodes:
            self._drag_edge_update_timer.stop()

    def _load_cached_properties(self):
        # 禁用节点大小缓存，始终重新计算（避免加载旧的缓存数据导致节点过大）
        return None
        if ConfigManager.get('Graph', 'on_stored', fallback='0') != '1':
            return None
        cached = {}
        max_conn_str = ConfigManager.get('Graph', 'max_connections', fallback=None)
        if not max_conn_str:
            return None
        try:
            cached['max_connections'] = int(max_conn_str)
        except:
            return None
        node_data = {}
        for name in self.node_items:
            conn_str = ConfigManager.get('Graph', f'node_cache_{name}_conn', fallback=None)
            size_str = ConfigManager.get('Graph', f'node_cache_{name}_size', fallback=None)
            if conn_str is not None and size_str is not None:
                try:
                    node_data[name] = {
                        'conn_count': int(conn_str),
                        'size': int(size_str)
                    }
                except:
                    pass
        cached['node_data'] = node_data
        return cached

    def _invalidate_cache(self):
        ConfigManager.set('Graph', 'on_stored', '0')

    def _calculate_max_connections(self):
        max_conn = 0
        for data in self.node_items.values():
            item = data['item']
            conn_count = len(item._edges)
            if conn_count > max_conn:
                max_conn = conn_count
        return max(1, max_conn)

    def load_node_positions(self):
        positions = {}
        for name in list(self.node_items.keys()):
            pos_str = ConfigManager.get('Graph', f'node_pos_{name}', fallback=None)
            if pos_str:
                try:
                    x, y = pos_str.split(',')
                    positions[name] = (float(x), float(y))
                except:
                    pass
        return positions

    def _get_type_colors(self):
        return {
            'character': '#00ff88', 'skill': '#ff4466', 'location': '#00ccff',
            'item': '#ffcc00', 'foreshadowing': '#ff8c42', 'relationship': '#cc66ff',
            'custom': '#88aacc', 'adventure': '#ff8c42', 'faction': '#9933ff',
            'time_point': '#ffd700'
        }
    
    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self._pin_overlays()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._pin_overlays()
        QTimer.singleShot(50, self._refresh_all_caches)
    
    def _refresh_all_caches(self):
        for data in self.node_items.values():
            item = data['item']
            item._update_cache_mode()
    
    MAX_NODES = 200
    LAYOUT_IDEAL_LENGTH = 260.0  # 理想间距稍微增大
    LAYOUT_REPULSION = 100000.0  # 大幅增加斥力，让节点更分散
    LAYOUT_ATTRACTION = 0.012
    LAYOUT_CENTER_GRAVITY = 0.005
    LAYOUT_DAMPING = 0.92
    LAYOUT_ITERATIONS = 150  # 增加迭代次数让布局更稳定
    GRAPH_FONT_SIZE = 14

    def set_graph_font_size(self, size):
        self.GRAPH_FONT_SIZE = size
        SciFiNodeItem.GRAPH_FONT_SIZE = size

    def set_double_click_callback(self, callback):
        self._on_node_double_click = callback
    
    def set_right_click_callback(self, callback):
        self._on_node_right_click = callback
    
    def set_edge_right_click_callback(self, callback):
        self._on_edge_right_click = callback

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
    
    def remove_edge(self, edge):
        if edge in self.edge_items:
            edge.remove_from_scene()
            self.edge_items.remove(edge)
    
    def remove_node(self, node_name):
        if node_name in self.node_items:
            data = self.node_items[node_name]
            item = data['item']
            edges_to_remove = [e for e in self.edge_items if e.from_node is item or e.to_node is item]
            for e in edges_to_remove:
                e.remove_from_scene()
                if e in self.edge_items:
                    self.edge_items.remove(e)
            self.scene.removeItem(item)
            del self.node_items[node_name]
    
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
        painter.fillRect(rect, QColor(self._bg_color))
        
        grid_size = 50
        pen = QPen(QColor(self._grid_color), 1)
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
    
    def _show_background_context_menu(self, global_pos):
        scene_pos = self.mapToScene(self.mapFromGlobal(global_pos))
        self._last_right_click_scene_pos = scene_pos
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {_theme('card_bg', '#FFFFFF')};
                color: {_theme('fg_color', '#212529')};
                border: 1px solid {_theme('border_color', '#DEE2E6')};
                border-radius: 6px;
                padding: 6px;
                font-family: {_theme('font_family', "'Segoe UI', 'Microsoft YaHei', sans-serif")};
                font-size: 13px;
            }}
            QMenu::item {{
                padding: 8px 24px;
                border-radius: 4px;
                margin: 2px 4px;
            }}
            QMenu::item:selected {{
                background-color: {_theme('accent_color', '#0078D4')}30;
                color: {_theme('accent_color', '#0078D4')};
            }}
        """)
        add_action = menu.addAction("＋ 新增节点")
        add_action.triggered.connect(self._on_add_node)
        menu.exec_(global_pos)
    
    def _on_add_node(self):
        types = [
            ('character', '人物'), ('skill', '技能'), ('item', '物品'),
            ('location', '地点'), ('foreshadowing', '伏笔'), ('relationship', '关系'),
            ('adventure', '事件'), ('faction', '组织'), ('time_point', '时间点'), ('custom', '自定义'),
        ]
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {_theme('card_bg', '#FFFFFF')};
                color: {_theme('fg_color', '#212529')};
                border: 1px solid {_theme('border_color', '#DEE2E6')};
                border-radius: 6px;
                padding: 6px;
                font-family: {_theme('font_family', "'Segoe UI', 'Microsoft YaHei', sans-serif")};
                font-size: 13px;
            }}
            QMenu::item {{
                padding: 8px 24px;
                border-radius: 4px;
                margin: 2px 4px;
            }}
            QMenu::item:selected {{
                background-color: {_theme('accent_color', '#0078D4')}30;
                color: {_theme('accent_color', '#0078D4')};
            }}
        """)
        for t, label in types:
            action = menu.addAction(f"[{label}]")
            action.triggered.connect(lambda checked, typ=t: self._create_node(typ))
        menu.exec_(QCursor.pos())
    
    def _create_node(self, node_type):
        name, ok = QInputDialog.getText(self, "新增节点", "节点名称:")
        if not ok or not name.strip():
            return
        name = name.strip()
        keywords = keyword_manager.load_keywords()
        existing = any(kw.get('name') == name for kw in keywords)
        if existing:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, language_manager.tr("duplicate"), f"{language_manager.tr('node_already_exists')}: '{name}'。")
            return
        pos = self._last_right_click_scene_pos if hasattr(self, '_last_right_click_scene_pos') else QPointF(0, 0)
        new_kw = {
            'name': name,
            'type': node_type,
            'description': '',
            'relationships': []
        }
        keywords.append(new_kw)
        keyword_manager.save_keywords(keywords)
        self._add_node_to_graph(new_kw, pos.x(), pos.y())

    def _add_node_to_graph(self, kw, x, y):
        name = kw.get('name', '?')
        t = kw.get('type', 'custom')
        type_colors = {
            'character': '#00ff88', 'skill': '#ff4466', 'location': '#00ccff',
            'item': '#ffcc00', 'foreshadowing': '#ff8c42', 'relationship': '#cc66ff',
            'custom': '#88aacc', 'adventure': '#ff8c42', 'faction': '#9933ff',
            'time_point': '#ffd700'
        }
        color = type_colors.get(t, '#88aacc')
        node = SciFiNodeItem(name, t, color, x, y)
        node._on_double_click = self._on_node_double_click
        node._on_right_click = self._on_node_right_click
        self.scene.addItem(node)
        self.node_items[name] = {'item': node, 'keyword': kw}
        self._invalidate_cache()
        max_conn = self._calculate_max_connections()
        SciFiNodeItem.set_global_max_connections(max_conn)
        for data in self.node_items.values():
            data['item'].update()
        self._cache_node_properties()
        self._index_overlay.refresh()
        self._legend_overlay.refresh(type_colors, self._group_keywords_by_type())
        self.apply_filter()

    def _group_keywords_by_type(self):
        groups = {}
        for info in self.node_items.values():
            kw = info.get('keyword', {})
            t = kw.get('type', 'custom')
            if t not in groups:
                groups[t] = []
            groups[t].append(kw)
        return groups

    def _start_connect_mode(self, from_name):
        self._connect_from_node = from_name
        self.highlight_drag_start(self.node_items[from_name]['item'])

    def _on_connect_target_selected(self, target_name):
        if not self._connect_from_node or self._connect_from_node == target_name:
            self._cancel_connect_mode()
            return
        from_name = self._connect_from_node
        self.clear_drag_highlight()
        self._show_relation_select_menu(from_name, target_name)
        self._connect_from_node = None

    def _cancel_connect_mode(self):
        self._connect_from_node = None
        self.clear_drag_highlight()

    def _show_relation_select_menu(self, from_name, to_name):
        sorted_types = sorted(RELATION_CATEGORIES.items(), key=lambda x: x[1]['label'])
        menu = QMenu(self)
        # 统一的黑客帝国风格菜单样式
        menu.setStyleSheet("""
            QMenu {
                background-color: #0a0f14;
                color: #00ff41;
                border: 2px solid #00AA30;
                border-radius: 6px;
                padding: 6px;
                font-family: 'Microsoft YaHei', 'Consolas', monospace;
                font-size: 13px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
                margin: 2px 4px;
            }
            QMenu::item:selected {
                background-color: #002a10;
                color: #00ff88;
                border: 1px solid #00AA3050;
            }
        """)
        for rel_key, rel_info in sorted_types:
            action = menu.addAction(rel_info['label'])
            action.setData(rel_key)

        chosen = menu.exec_(QCursor.pos())
        if chosen:
            rel_type = chosen.data()
            keyword_manager.add_relationship(from_name, to_name, rel_type, '')
            self.add_edge_incremental(from_name, to_name, rel_type)

    def _on_node_right_click(self, node_name, screen_pos, scene_pos):
        menu = QMenu(self)
        # 统一的黑客帝国风格菜单样式
        menu.setStyleSheet("""
            QMenu {
                background-color: #0a0f14;
                color: #00ff41;
                border: 2px solid #00AA30;
                border-radius: 6px;
                padding: 6px;
                font-family: 'Microsoft YaHei', 'Consolas', monospace;
                font-size: 13px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
                margin: 2px 4px;
            }
            QMenu::item:selected {
                background-color: #002a10;
                color: #00ff88;
                border: 1px solid #00AA3050;
            }
            QMenu::item:disabled {
                color: #556655;
            }
            QMenu::separator {
                height: 2px;
                background-color: #00AA3030;
                margin: 6px 12px;
            }
            QMenu::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        
        info = self.node_items.get(node_name, {})
        kw = info.get('keyword', {}) if info else {}
        ntype = kw.get('type', '?')
        label = NODE_LABELS.get(ntype, ntype)
        
        title = menu.addAction(f"{node_name} [{label}]")
        title.setEnabled(False)
        menu.addSeparator()

        if self._connect_from_node:
            mode_title = menu.addAction(f"正在选择目标 (来自: {self._connect_from_node})")
            mode_title.setEnabled(False)
            if self._connect_from_node != node_name:
                target_action = menu.addAction("选为目标节点")
                target_action.triggered.connect(lambda: self._on_connect_target_selected(node_name))
            cancel_action = menu.addAction("取消选择模式")
            cancel_action.triggered.connect(self._cancel_connect_mode)
            menu.addSeparator()

        connect_action = menu.addAction("建立关联")
        connect_action.triggered.connect(lambda: self._start_connect_mode(node_name))

        type_menu = menu.addMenu("修改类型")
        type_menu.setStyleSheet(menu.styleSheet())
        for type_key, type_label in [('character','人物'),('skill','技能'),('item','物品'),('location','地点'),
                                       ('foreshadowing','伏笔'),('adventure','事件'),('faction','组织'),
                                       ('time_point','时间点'),('custom','自定义')]:
            act = type_menu.addAction(f"[{type_label}]")
            act.setChecked(ntype == type_key)
            act.setCheckable(True)
            act.triggered.connect(lambda checked, tk=type_key: self._change_node_type(node_name, tk))

        desc_action = menu.addAction("修改描述")
        desc_action.triggered.connect(lambda: self._change_node_description(node_name))
        
        menu.addSeparator()
        del_action = menu.addAction("删除节点")
        del_action.triggered.connect(lambda: self._delete_node(node_name))
        menu.exec_(screen_pos)

    def _change_node_type(self, node_name, new_type):
        info = self.node_items.get(node_name, {})
        kw = info.get('keyword', {}) if info else {}
        current_desc = kw.get('description', '')
        current_color = kw.get('color', '')
        
        keyword_manager.update_keyword(node_name, new_type, current_desc, current_color or None)
        if node_name in self.node_items:
            data = self.node_items[node_name]
            kw = data.get('keyword', {})
            kw['type'] = new_type
            data['item'].node_type = new_type
            type_colors = {
                'character': '#00ff88', 'skill': '#ff4466', 'location': '#00ccff',
                'item': '#ffcc00', 'foreshadowing': '#ff8c42', 'relationship': '#cc66ff',
                'custom': '#88aacc', 'adventure': '#ff8c42', 'faction': '#9933ff',
                'time_point': '#ffd700'
            }
            data['item'].base_color = QColor(type_colors.get(new_type, '#88aacc'))
            data['item'].update()
        self._legend_overlay.refresh(self._get_type_colors(), self._group_keywords_by_type())

    def _change_node_description(self, node_name):
        info = self.node_items.get(node_name, {})
        kw = info.get('keyword', {}) if info else {}
        current_desc = kw.get('description', '')
        new_desc, ok = QInputDialog.getMultiLineText(
            self, "修改描述",
            f"节点 [{node_name}] 的描述:",
            current_desc
        )
        if ok:
            keyword_manager.update_keyword(node_name, None, new_desc, None)

    def _delete_node(self, node_name):
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除节点 '{node_name}' 吗？\n同时会删除所有关联关系。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        keyword_manager.delete_keyword(node_name)
        self.remove_node(node_name)
        self._invalidate_cache()
        if self.node_items:
            max_conn = self._calculate_max_connections()
            SciFiNodeItem.set_global_max_connections(max_conn)
            for data in self.node_items.values():
                data['item'].update()
            self._cache_node_properties()
        self._index_overlay.refresh()

    def _on_edge_right_click(self, edge, screen_pos):
        from_node = edge.from_node
        to_node = edge.to_node
        if not from_node or not to_node:
            return
        from_name = None
        to_name = None
        for n, d in self.node_items.items():
            if d['item'] is from_node:
                from_name = n
            if d['item'] is to_node:
                to_name = n

        rel_label = RELATION_CATEGORIES.get(edge.rel_type, {}).get('label', edge.rel_type)
        menu = QMenu(self)
        # 统一的黑客帝国风格菜单样式
        menu.setStyleSheet("""
            QMenu {
                background-color: #0a0f14;
                color: #00ff41;
                border: 2px solid #00AA30;
                border-radius: 6px;
                padding: 6px;
                font-family: 'Microsoft YaHei', 'Consolas', monospace;
                font-size: 13px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
                margin: 2px 4px;
            }
            QMenu::item:selected {
                background-color: #002a10;
                color: #00ff88;
                border: 1px solid #00AA3050;
            }
            QMenu::item:disabled {
                color: #556655;
            }
            QMenu::separator {
                height: 2px;
                background-color: #00AA3030;
                margin: 6px 12px;
            }
            QMenu::indicator {
                width: 16px;
                height: 16px;
            }
        """)

        title = menu.addAction(f"{from_name} -> {to_name} [{rel_label}]")
        title.setEnabled(False)
        menu.addSeparator()

        type_menu = menu.addMenu("修改关系类型")
        type_menu.setStyleSheet(menu.styleSheet())
        for rel_key, rel_info in sorted(RELATION_CATEGORIES.items(), key=lambda x: x[1]['label']):
            act = type_menu.addAction(f"{rel_info['label']}")
            act.setChecked(edge.rel_type == rel_key)
            act.setCheckable(True)
            act.triggered.connect(lambda checked, rk=rel_key: self._change_edge_relation(from_name, to_name, edge.rel_type, rk))

        desc_action = menu.addAction("修改描述")
        desc_action.triggered.connect(lambda: self._change_edge_description(from_name, to_name, edge.rel_type))
        
        menu.addSeparator()
        del_action = menu.addAction("删除关联")
        del_action.triggered.connect(lambda: self._delete_edge_relation(from_name, to_name, edge.rel_type))
        menu.exec_(screen_pos)

    def _change_edge_relation(self, from_name, old_rel_type, new_rel_type):
        info = self.node_items.get(from_name, {})
        kw = info.get('keyword', {}) if info else {}
        target_name = None
        for rel in kw.get('relationships', []):
            if rel.get('type') == old_rel_type:
                target_name = rel.get('target')
                break
        keyword_manager.remove_relationship(from_name, old_rel_type)
        keyword_manager.add_relationship(from_name, new_rel_type, '')
        self.remove_edge_incremental(from_name, target_name or '', old_rel_type)
        if target_name:
            self.add_edge_incremental(from_name, target_name, new_rel_type)

    def _change_edge_description(self, from_name, to_name, rel_type):
        info = self.node_items.get(from_name, {})
        kw = info.get('keyword', {}) if info else {}
        current_desc = ''
        for rel in kw.get('relationships', []):
            if rel.get('target') == to_name and rel.get('type') == rel_type:
                current_desc = rel.get('description', '')
                break
        new_desc, ok = QInputDialog.getText(
            self, "修改描述",
            f"关联 [{from_name}] → [{to_name}] ({rel_type}) 的描述:",
            QLineEdit.Normal,
            current_desc
        )
        if ok:
            keyword_manager.remove_relationship(from_name, to_name, rel_type)
            keyword_manager.add_relationship(from_name, to_name, rel_type, new_desc)

    def _select_node(self, node_item=None):
        # 取消之前选中的节点
        if self._selected_node is not None:
            self._selected_node._selected = False
            self._selected_node.update()
        
        self._selected_node = node_item
        if node_item is not None:
            node_item._selected = True
            node_item.update()
    
    def _delete_edge_relation(self, from_name, to_name, rel_type):
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除关联:\n{from_name} → {to_name}\n类型: {RELATION_CATEGORIES.get(rel_type,{}).get('label',rel_type)}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            keyword_manager.remove_relationship(from_name, to_name, rel_type)
            self.remove_edge_incremental(from_name, to_name, rel_type)
    
    def mousePressEvent(self, event):
        self.setFocus()

        if event.button() == Qt.RightButton and self.itemAt(event.pos()) is None:
            self._show_background_context_menu(event.globalPos())
            return

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

        ctrl_pressed = bool(event.modifiers() & Qt.ControlModifier)

        if event.button() == Qt.LeftButton:
            if ctrl_pressed and node_item is not None:
                if not self._ctrl_held:
                    self._enter_ctrl_mode()
                self._start_ctrl_connect(node_item, event.pos())
                event.accept()
                return

            if node_item is not None:
                self._select_node(node_item)
            else:
                self._select_node(None)
            
            if self._focus_node is not None and node_item is None:
                self.exit_focus_mode()
            
            SciFiEdge.clear_highlight(self.edge_items)
            
            if item is None:
                self._is_panning = True
                self._pan_start = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
                event.accept()
                return
        
        if event.button() == Qt.RightButton and node_item is not None:
            if hasattr(self, '_on_node_right_click') and self._on_node_right_click:
                scene_pos = self.mapToScene(event.pos())
                self._on_node_right_click(node_item.node_name, event.globalPos(), scene_pos)
                event.accept()
                return
            
            if self._on_edge_right_click:
                for edge in self.edge_items:
                    if item is edge.edge_path or item is edge.glow_path or item is edge.hit_area or (edge._arrow_item and item is edge._arrow_item):
                        self._on_edge_right_click(edge, event.screenPos().toPoint())
                        event.accept()
                        return
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self._connect_dragging and self._connect_line and self._connect_source:
            scene_pos = self.mapToScene(event.pos())
            path = QPainterPath()
            path.moveTo(self._connect_source.scenePos())
            path.lineTo(scene_pos)
            self._connect_line.setPath(path)

            items = self.scene.items(scene_pos) if self.scene else []
            hovered = None
            for it in items:
                if isinstance(it, SciFiNodeItem) and it is not self._connect_source:
                    hovered = it
                    break

            if hovered != self._ctrl_hovered_node:
                if self._ctrl_hovered_node and self._ctrl_hovered_node is not self._connect_source:
                    self._ctrl_hovered_node.setOpacity(0.3)
                self._ctrl_hovered_node = hovered
                if hovered:
                    hovered.setOpacity(1.0)
            event.accept()
            return

        ctrl_pressed = bool(event.modifiers() & Qt.ControlModifier)
        if ctrl_pressed and not self._connect_dragging:
            if not self._ctrl_held:
                self._enter_ctrl_mode()
            scene_pos = self.mapToScene(event.pos())
            items = self.scene.items(scene_pos) if self.scene else []
            hovered = None
            for it in items:
                if isinstance(it, SciFiNodeItem):
                    hovered = it
                    break

            if hovered != self._ctrl_hovered_node:
                if self._ctrl_hovered_node:
                    self._ctrl_hovered_node.setOpacity(0.3)
                self._ctrl_hovered_node = hovered
                if hovered:
                    hovered.setOpacity(1.0)
            event.accept()
            return

        if self._ctrl_held and not ctrl_pressed:
            self._exit_ctrl_mode()
            return

        if self._is_panning:
            delta = self._pan_start - event.pos()
            self._pan_start = event.pos()
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(h_bar.value() + delta.x())
            v_bar.setValue(v_bar.value() + delta.y())
            self._pin_overlays()
            event.accept()
            return
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._connect_dragging:
            self._connect_dragging = False

            if self._connect_line and self.scene:
                self.scene.removeItem(self._connect_line)
                self._connect_line = None

            ctrl_still_held = bool(event.modifiers() & Qt.ControlModifier)
            if ctrl_still_held:
                for data in self.node_items.values():
                    data['item'].setOpacity(0.3)
                for edge in self.edge_items:
                    edge.glow_path.setOpacity(0.15)
                    edge.edge_path.setOpacity(0.15)
                if self._connect_source:
                    self._connect_source.setOpacity(1.0)
            else:
                for data in self.node_items.values():
                    data['item'].setOpacity(1.0)
                for edge in self.edge_items:
                    edge.glow_path.setOpacity(1.0)
                    edge.edge_path.setOpacity(1.0)

            scene_pos = self.mapToScene(event.pos())
            items = self.scene.items(scene_pos) if self.scene else []
            target_node = None
            for it in items:
                if isinstance(it, SciFiNodeItem) and it is not self._connect_source:
                    target_node = it
                    break

            from_node = self._connect_source
            self._connect_source = None
            self._ctrl_hovered_node = None

            if target_node and from_node:
                menu = QMenu()
                sorted_types = sorted(RELATION_CATEGORIES.items(), key=lambda x: x[1]['label'])
                for rel_key, rel_info in sorted_types:
                    action = QAction(rel_info['label'], menu)
                    action.setData(rel_key)
                    action.triggered.connect(lambda checked, k=rel_key: self._on_relation_selected(from_node, target_node, k))
                    menu.addAction(action)
                cancel_action = QAction(language_manager.tr("cancel"), menu)
                cancel_action.triggered.connect(lambda: None)
                menu.addAction(cancel_action)
                menu.exec_(event.screenPos().toPoint())
            event.accept()
            return
        
        if self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        
        super().mouseReleaseEvent(event)
    
    def _on_relation_selected(self, from_node, to_node, rel_type):
        self.add_edge_incremental(from_node.node_name, to_node.node_name, rel_type)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control and not event.isAutoRepeat():
            self._ctrl_held = True
            self._enter_ctrl_mode()
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control and not event.isAutoRepeat():
            self._ctrl_held = False
            self._exit_ctrl_mode()
            event.accept()
            return
        super().keyReleaseEvent(event)

    def _enter_ctrl_mode(self):
        for data in self.node_items.values():
            data['item'].setOpacity(0.3)
        for edge in self.edge_items:
            edge.glow_path.setOpacity(0.15)
            edge.edge_path.setOpacity(0.15)
        self._ctrl_hovered_node = None
        self.setCursor(Qt.CrossCursor)

    def _exit_ctrl_mode(self):
        self._cancel_ctrl_connect()
        for data in self.node_items.values():
            data['item'].setOpacity(1.0)
        for edge in self.edge_items:
            edge.glow_path.setOpacity(1.0)
            edge.edge_path.setOpacity(1.0)
        self._ctrl_hovered_node = None
        self.setCursor(Qt.ArrowCursor)
        self.scene.update()

    def _start_ctrl_connect(self, node_item, screen_pos):
        self._ctrl_held = True
        self._connect_source = node_item
        self._connect_dragging = True

        self._connect_line = QGraphicsPathItem()
        pen = QPen(QColor(_theme('accent_color', '#00ff88')))
        pen.setStyle(Qt.DashLine)
        pen.setWidth(2)
        self._connect_line.setPen(pen)
        self._connect_line.setZValue(100)
        scene_pos = self.mapToScene(screen_pos)
        path = QPainterPath()
        path.moveTo(node_item.scenePos())
        path.lineTo(scene_pos)
        self._connect_line.setPath(path)
        self.scene.addItem(self._connect_line)

        self._connect_source.setOpacity(1.0)
        if self._ctrl_hovered_node and self._ctrl_hovered_node is not self._connect_source:
            self._ctrl_hovered_node.setOpacity(0.3)

    def _cancel_ctrl_connect(self):
        self._connect_dragging = False

        if self._connect_line:
            if self.scene:
                self.scene.removeItem(self._connect_line)
            self._connect_line = None

        self._connect_source = None

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
            if self._connect_from_node:
                self._on_connect_target_selected(node_item.node_name)
                event.accept()
                return
            if node_item._on_double_click:
                node_item._on_double_click(node_item.node_name)
            else:
                self.enter_focus_mode(node_item.node_name)
        elif self._connect_from_node:
            self._cancel_connect_mode()
        elif self._focus_node is not None:
            self.exit_focus_mode()
    
    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 0.87
        self.zoom *= factor
        self.scale(factor, factor)
        self._pin_overlays()
    
    def clear_graph(self):
        self.scene.clear()
        self.node_items = {}
        self.edge_items = []
        self._pinned_nodes = set()
        self._focus_node = None
        self._path_highlight_active = False
        self._highlighted_path_nodes = set()
    
    def build_graph(self, keywords, freq_data=None):
        self.clear_graph()
        if not keywords:
            return
        
        if len(keywords) > self.MAX_NODES:
            logger.warning(f"关键词数量 {len(keywords)} 超过限制 {self.MAX_NODES}，仅显示前 {self.MAX_NODES} 个")
            keywords = keywords[:self.MAX_NODES]
        
        freq_words = freq_data.get('words', {}) if freq_data else {}
        is_replace = freq_data.get('is_replace', {}) if freq_data else {}
        max_freq = 1
        for w, info in freq_words.items():
            cnt = info.get('total_occurrences', 0)
            if cnt > max_freq:
                max_freq = cnt
        from math import log1p
        log_max = log1p(max_freq)
        
        type_colors = _theme('node_colors', {
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
        })
        
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
        
        # 先计算每个节点的连接数
        node_degrees = {}
        for name in node_positions:
            node_degrees[name] = 0
        for f, t, _ in edges_list:
            if f in node_degrees:
                node_degrees[f] += 1
            if t in node_degrees:
                node_degrees[t] += 1
        
        # 归一化连接数，用于中心引力权重
        max_deg = max(node_degrees.values()) if node_degrees else 1
        
        try:
            import numpy as np
            has_numpy = True
        except ImportError:
            has_numpy = False
        
        if has_numpy and len(node_positions) > 2:
            names = list(node_positions.keys())
            n = len(names)
            ni = {name: i for i, name in enumerate(names)}
            pos = np.array([[node_positions[n][0], node_positions[n][1]] for n in names], dtype=np.float64)
            min_d = np.array([(node_sizes[n][0] + node_sizes[n][1]) * 0.6 for n in names], dtype=np.float64)
            vel = np.zeros((n, 2), dtype=np.float64)
            el = np.array([(ni[f], ni[t]) for f, t, _ in edges_list], dtype=np.int32)
            
            # 计算每个节点的中心引力权重（连接越多，向中心引力越大）
            gravity_weights = np.zeros(n, dtype=np.float64)
            for i, name in enumerate(names):
                deg = node_degrees.get(name, 0)
                # 大幅提升连接多的节点的中心引力，让它们稳定在图中央
                ratio = deg / max_deg if max_deg > 0 else 0
                gravity_weights[i] = 1.0 + 5.0 * (ratio ** 2)  # 平方关系，让高连接度的明显更靠近中心
            
            for _ in range(iterations):
                diff = pos[:, np.newaxis, :] - pos[np.newaxis, :, :]
                dist_sq = np.sum(diff * diff, axis=2)
                dist = np.sqrt(np.maximum(dist_sq, 1.0))
                
                rep_fm = repulsion_strength / np.maximum(dist_sq, 1.0)
                rep_f = rep_fm[:, :, np.newaxis] * diff / dist[:, :, np.newaxis]
                for i in range(n):
                    rep_f[i, i, :] = 0
                forces = np.sum(rep_f, axis=1)
                
                if len(el) > 0:
                    sf, st = pos[el[:, 0]], pos[el[:, 1]]
                    ed = sf - st
                    ed_sq = np.sum(ed * ed, axis=1)
                    ed_d = np.sqrt(np.maximum(ed_sq, 1.0))
                    att = attraction_strength * (ed_d - ideal_length) / np.maximum(ed_d, 1.0)
                    ef = att[:, np.newaxis] * ed / np.maximum(ed_d, 1.0)[:, np.newaxis]
                    for i in range(len(el)):
                        forces[el[i, 0]] += ef[i]
                        forces[el[i, 1]] -= ef[i]
                
                # 中心引力：连接多的节点向中心的引力更大
                for i in range(n):
                    gw = gravity_weights[i]
                    forces[i] -= center_gravity * gw * pos[i]
                
                fm = np.sqrt(np.sum(forces * forces, axis=1))
                mask = fm > 50.0
                if np.any(mask):
                    forces[mask] = forces[mask] / fm[mask, np.newaxis] * 50.0
                
                vel = (vel + forces) * damping
                pos += vel
            
            node_positions = {names[i]: (float(pos[i, 0]), float(pos[i, 1])) for i in range(n)}
        else:
            velocities = {name: [0.0, 0.0] for name in node_positions}
            # 计算非 NumPy 版本的中心引力权重
            gravity_weights_numpy = {}
            for name in node_positions:
                deg = node_degrees.get(name, 0)
                ratio = deg / max_deg if max_deg > 0 else 0
                gravity_weights_numpy[name] = 1.0 + 5.0 * (ratio ** 2)
            
            for _ in range(iterations):
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
                            forces[n1][0] += fx; forces[n1][1] += fy
                            forces[n2][0] -= fx; forces[n2][1] -= fy
                        repulsion = repulsion_strength / dist_sq
                        fx = repulsion * dx / dist
                        fy = repulsion * dy / dist
                        forces[n1][0] += fx; forces[n1][1] += fy
                        forces[n2][0] -= fx; forces[n2][1] -= fy
                for from_name, to_name, _ in edges_list:
                    x1, y1 = node_positions[from_name]
                    x2, y2 = node_positions[to_name]
                    dx = x2 - x1
                    dy = y2 - y1
                    dist = max((dx * dx + dy * dy) ** 0.5, 1.0)
                    attraction = attraction_strength * (dist - ideal_length)
                    fx = attraction * dx / dist
                    fy = attraction * dy / dist
                    forces[from_name][0] += fx; forces[from_name][1] += fy
                    forces[to_name][0] -= fx; forces[to_name][1] -= fy
                for name in node_positions:
                    x, y = node_positions[name]
                    gw = gravity_weights_numpy[name]
                    forces[name][0] -= center_gravity * gw * x
                    forces[name][1] -= center_gravity * gw * y
                for name in node_positions:
                    fx, fy = forces[name]
                    force_mag = (fx * fx + fy * fy) ** 0.5
                    if force_mag > 50.0:
                        fx = fx / force_mag * 50.0
                        fy = fy / force_mag * 50.0
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
            if freq_data and name in freq_words:
                cnt = freq_words[name].get('total_occurrences', 0)
                for alias, target in is_replace.items():
                    if target == name and alias in freq_words:
                        cnt += freq_words[alias].get('total_occurrences', 0)
                node._heat_factor = min(1.0, log1p(cnt) / log_max) if log_max > 0 else 0
            self.scene.addItem(node)
            self.node_items[name] = {'item': node, 'keyword': kw}
        
        for from_name, to_name, rel_type in edges_list:
            if from_name in self.node_items and to_name in self.node_items:
                self._determine_and_add_edge(from_name, to_name, rel_type)
        
        # 先计算全局最大连接数并设置，再更新节点大小（避免默认值1导致的放大）
        max_conn = self._calculate_max_connections()
        SciFiNodeItem.set_global_max_connections(max_conn)
        
        for name, data in self.node_items.items():
            data['item'].update_connection_count()
        
        cached_props = self._load_cached_properties()
        if cached_props and cached_props.get('max_connections') == max_conn:
            for name, data in self.node_items.items():
                if name in cached_props['node_data']:
                    cache = cached_props['node_data'][name]
                    if len(data['item']._edges) == cache['conn_count']:
                        continue
            self._cache_node_properties()
        else:
            self._invalidate_cache()
            self._cache_node_properties()
        
        for name, data in self.node_items.items():
            data['item'].update()
        
        self._legend_overlay.refresh(type_colors, groups)
        if self._index_overlay:
            self._index_overlay.refresh()
        self._pin_overlays()
        QTimer.singleShot(150, self._center_graph)
        self.apply_filter()
    
    def _center_graph(self):
        if not self.node_items:
            return
        r = self.scene.itemsBoundingRect()
        r.adjust(-60, -60, 60, 60)
        if r.isValid() and not r.isEmpty():
            self.fitInView(r, Qt.KeepAspectRatio)
    
    def _determine_and_add_edge(self, from_name, to_name, rel_type='related_to'):
        from_item = self.node_items[from_name]['item']
        to_item = self.node_items[to_name]['item']
        edge = SciFiEdge(self.scene, from_item, to_item, rel_type)
        self.edge_items.append(edge)
        from_item.add_edge_ref(edge)
        to_item.add_edge_ref(edge)
    
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
        item._heat_factor = 0.5
        item.update()
        QTimer.singleShot(1500, lambda: self._reset_node_glow(item))
        
        return True
    
    def _reset_node_glow(self, item):
        if item and item.scene():
            item.setZValue(10)
            item._heat_factor = 0
            item.update()
    
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
