"""
动效管理系统
提供：
- 页面切换动画（水平急缓滑动 + 淡入淡出）
- 元素淡入浮现（错序淡入）
- 悬停弹跳反馈（按钮缩放 + 回弹）
- 悬浮阴影
"""
import logging
from PyQt5.QtWidgets import QWidget, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QPropertyAnimation, QParallelAnimationGroup, \
    QSequentialAnimationGroup, QEasingCurve, QPoint, QAbstractAnimation
from PyQt5.QtGui import QColor

from ..core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class AnimationConfig:
    """动效配置"""
    # 缓动曲线：急出缓入
    EASE_OUT_CUBIC = QEasingCurve.OutCubic
    EASE_OUT_BOUNCE = QEasingCurve.OutBack
    EASE_IN_OUT = QEasingCurve.InOutCubic
    
    # 页面切换
    PAGE_SLIDE_DURATION = 350
    PAGE_FADE_DURATION = 300
    
    # 元素淡入
    STAGGER_DELAY = 60
    FADE_IN_DURATION = 250
    
    # 悬停弹跳
    HOVER_SCALE = 1.05
    HOVER_DURATION = 200
    HOVER_RETURN_DURATION = 150


def is_animation_enabled() -> bool:
    """检查动效是否开启"""
    return ConfigManager.get_int('UI', 'enable_animations', fallback=1) == 1


def create_opacity_effect(widget, start=0.0, end=1.0, duration=300, parent=None):
    """创建透明度动画"""
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(start)
    widget.setGraphicsEffect(effect)
    
    anim = QPropertyAnimation(effect, b"opacity", parent or widget)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setDuration(duration)
    anim.setEasingCurve(AnimationConfig.EASE_OUT_CUBIC)
    return anim


def create_position_animation(widget, start_pos, end_pos, duration=350, parent=None):
    """创建位置移动动画"""
    anim = QPropertyAnimation(widget, b"pos", parent or widget)
    anim.setStartValue(start_pos)
    anim.setEndValue(end_pos)
    anim.setDuration(duration)
    anim.setEasingCurve(AnimationConfig.EASE_OUT_CUBIC)
    return anim


class PageSwitchAnimation(QSequentialAnimationGroup):
    """页面切换动画组（滑出旧页 + 滑入新页）"""
    
    def __init__(self, old_page: QWidget, new_page: QWidget, parent=None):
        super().__init__(parent)
        
        if not is_animation_enabled():
            old_page.hide()
            new_page.show()
            return
        
        cfg = AnimationConfig()
        container_w = new_page.parent().width() if new_page.parent() else 800
        
        # 旧页向右滑出 + 淡出
        old_fade = create_opacity_effect(old_page, 1.0, 0.0, cfg.PAGE_FADE_DURATION)
        old_slide = create_position_animation(
            old_page,
            old_page.pos(),
            QPoint(container_w, old_page.pos().y()),
            cfg.PAGE_SLIDE_DURATION
        )
        old_group = QParallelAnimationGroup(self)
        old_group.addAnimation(old_fade)
        old_group.addAnimation(old_slide)
        self.addAnimation(old_group)
        
        # 新页从右侧滑入 + 淡入
        new_page.move(container_w, new_page.pos().y())
        new_page.show()
        new_page.raise_()
        
        new_fade = create_opacity_effect(new_page, 0.0, 1.0, cfg.PAGE_FADE_DURATION)
        new_slide = create_position_animation(
            new_page,
            QPoint(container_w, new_page.pos().y()),
            QPoint(0, new_page.pos().y()),
            cfg.PAGE_SLIDE_DURATION
        )
        new_group = QParallelAnimationGroup(self)
        new_group.addAnimation(new_fade)
        new_group.addAnimation(new_slide)
        self.addAnimation(new_group)
        
        self.finished.connect(lambda: old_page.hide())


class StaggeredFadeIn(QSequentialAnimationGroup):
    """错序淡入浮现（容器内子控件依次淡入）"""
    
    def __init__(self, container: QWidget, items: list[QWidget], parent=None):
        super().__init__(parent)
        
        if not is_animation_enabled():
            for item in items:
                item.show()
            return
        
        cfg = AnimationConfig()
        
        for item in items:
            item.setGraphicsEffect(None)
            anim = create_opacity_effect(item, 0.0, 1.0, cfg.FADE_IN_DURATION)
            anim.setStartDelay(cfg.STAGGER_DELAY)
            self.addAnimation(anim)

    def stop(self):
        pass


class HoverBounceEffect:
    """鼠标悬停弹跳效果
    使用说明：
        btn = QPushButton(...)
        HoverBounceEffect.apply(btn)
    """
    
    @staticmethod
    def apply(widget):
        """为控件添加悬停弹跳效果"""
        from PyQt5.QtCore import QPropertyAnimation, QPointF
        
        if not is_animation_enabled():
            return
        
        original_style = widget.styleSheet()
        
        def on_enter(event):
            if not widget.isEnabled():
                return
            # 添加阴影
            shadow = QGraphicsDropShadowEffect(widget)
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(0, 0, 0, 60))
            shadow.setOffset(0, 4)
            widget.setGraphicsEffect(shadow)
            event.accept()
        
        def on_leave(event):
            widget.setGraphicsEffect(None)
            event.accept()
        
        widget.enterEvent = on_enter
        widget.leaveEvent = on_leave
    
    @staticmethod
    def apply_with_scale(widget, scale=1.05):
        """悬浮时缩放 + 阴影"""
        from PyQt5.QtCore import QPropertyAnimation, QPointF
        
        if not is_animation_enabled():
            return
        
        orig_geo = None
        
        def on_enter(event):
            nonlocal orig_geo
            if not widget.isEnabled():
                return
            orig_geo = widget.geometry()
            
            # 缩放
            w, h = orig_geo.width(), orig_geo.height()
            new_w, new_h = int(w * scale), int(h * scale)
            dx, dy = (new_w - w) // 2, (new_h - h) // 2
            
            anim = QPropertyAnimation(widget, b"geometry")
            anim.setEndValue(orig_geo.adjusted(-dx, -dy, dx, dy))
            anim.setDuration(AnimationConfig.HOVER_DURATION)
            anim.setEasingCurve(AnimationConfig.EASE_OUT_BOUNCE)
            anim.start()
            
            # 阴影
            shadow = QGraphicsDropShadowEffect(widget)
            shadow.setBlurRadius(25)
            shadow.setColor(QColor(0, 0, 0, 80))
            shadow.setOffset(0, 6)
            widget.setGraphicsEffect(shadow)
            
            event.accept()
        
        def on_leave(event):
            if orig_geo:
                anim = QPropertyAnimation(widget, b"geometry")
                anim.setEndValue(orig_geo)
                anim.setDuration(AnimationConfig.HOVER_RETURN_DURATION)
                anim.setEasingCurve(AnimationConfig.EASE_OUT_CUBIC)
                anim.start()
            
            widget.setGraphicsEffect(None)
            event.accept()
        
        widget.enterEvent = on_enter
        widget.leaveEvent = on_leave


def animate_widget_appear(widget, delay=0):
    """让控件以淡入方式出现"""
    if not is_animation_enabled():
        widget.show()
        return
    
    old_opacity = getattr(widget, '_opacity_effect', None)
    if old_opacity:
        widget.setGraphicsEffect(None)
    
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    widget._opacity_effect = effect
    
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setDuration(AnimationConfig.FADE_IN_DURATION)
    anim.setEasingCurve(AnimationConfig.EASE_OUT_CUBIC)
    anim.setStartDelay(delay)
    anim.start()
