"""
主题系统 - 统一管理所有UI样式和颜色
"""
from PyQt5.QtGui import QColor, QFont
from typing import Dict, Tuple, Optional


class Colors:
    """统一颜色系统"""
    # Matrix 主色调
    BACKGROUND = QColor('#020804')
    FOREGROUND = QColor('#00FF41')
    BORDER = QColor('#00AA30')
    ACCENT = QColor('#00FF41')
    
    # 组件色彩
    ERROR = QColor('#FF3333')
    WARNING = QColor('#FFAA00')
    SUCCESS = QColor('#00FF41')
    INFO = QColor('#00CCFF')
    
    # 按钮色彩
    BUTTON_BG = QColor('#001a05')
    BUTTON_HOVER = QColor('#003310')
    INPUT_BG = QColor('#000d03')
    
    # 网络图表色彩
    GRAPH_BG = QColor('#060612')
    GRAPH_GRID = QColor('#0a1a10')
    
    # 节点类型色
    NODE_TYPES = {
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
    
    # 关系类型色
    RELATION_TYPES = {
        'related_to': '#88aacc',
        'friendship': '#00ff88',
        'romance': '#ff66bb',
        'hostility': '#ff4444',
        'family': '#ffa500',
        'mentorship': '#ffd700',
        'owns': '#ffcc00',
        'uses': '#ffcc00',
        'masters': '#ff4466',
        'teaches': '#ff4466',
        'located_at': '#00ccff',
        'travels_to': '#00ccff',
        'participates_in': '#ff8c42',
        'triggers': '#ff8c42',
        'carries': '#ff4466',
        'hints_at': '#aaaaaa',
        'connects_to': '#4488ff',
        'contains': '#4488ff',
        'derives_from': '#cc66ff',
        'counters': '#cc66ff',
        'combines_with': '#cc66ff'
    }


class Sizes:
    """统一尺寸系统"""
    # 基础尺寸
    BASE_FONT_SIZE = 18
    BASE_TITLE_SIZE = 22
    BASE_WINDOW_WIDTH = 1100
    BASE_WINDOW_HEIGHT = 975
    MIN_WINDOW_WIDTH = 800
    MIN_WINDOW_HEIGHT = 600
    
    # 图相关
    GRAPH_FONT_SIZE = 14
    NODE_MIN_SIZE = 35
    NODE_MAX_SIZE = 115
    NODE_MIN_BRIGHTNESS = 18
    NODE_MAX_BRIGHTNESS = 55
    NODE_SIZE_PER_CONN = 7
    CONNECT_BTN_SIZE = 16
    
    # 标签页相关
    LOG_FONT_SIZE = 16
    
    # 关键词标签页
    KW_H1_SIZE = 43
    KW_H2_SIZE = 26
    KW_BODY_SIZE = 25
    KW_LINK_SIZE = 35


class Fonts:
    """统一字体系统"""
    @staticmethod
    def get_default_font(size: int = None, family: str = None) -> QFont:
        """获取系统可用的默认字体"""
        from core.font_manager import font_manager
        
        font_family = family or font_manager.get_default_font()
        font_size = size or Sizes.BASE_FONT_SIZE
        font = QFont(font_family)
        font.setPointSize(font_size)
        return font
    
    @staticmethod
    def get_fallback_fonts() -> list:
        """获取字体回退列表"""
        return [
            'Microsoft YaHei', 'SimHei',
            'PingFang SC', 'WenQuanYi Micro Hei',
            'Arial Unicode MS', 'sans-serif'
        ]


class Layout:
    """统一布局参数"""
    # 神经图布局
    IDEAL_LENGTH = 260.0
    REPULSION_STRENGTH = 100000.0
    ATTRACTION_STRENGTH = 0.012
    CENTER_GRAVITY = 0.005
    DAMPING = 0.92
    ITERATIONS = 150
    
    # 最大节点数量
    MAX_NODES = 200
