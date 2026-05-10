"""
Windows DWM 原生接口封装
提供亚克力模糊、Mica、圆角、暗色模式等 Windows 11 原生视觉效果
"""
import ctypes
import ctypes.wintypes
import logging
from enum import IntEnum

logger = logging.getLogger(__name__)

# ==================== Windows 常量定义 ====================

# DWM 窗口属性枚举 (Windows 11 22000+)
class DWMWINDOWATTRIBUTE(IntEnum):
    DWMWA_NCRENDERING_ENABLED = 1
    DWMWA_NCRENDERING_POLICY = 2
    DWMWA_TRANSITIONS_FORCEDISABLED = 3
    DWMWA_ALLOW_NCPAINT = 4
    DWMWA_CAPTION_BUTTON_BOUNDS = 5
    DWMWA_NONCLIENT_RTL_LAYOUT = 6
    DWMWA_FORCE_ICONIC_REPRESENTATION = 7
    DWMWA_FLIP3D_POLICY = 8
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    DWMWA_HAS_ICONIC_BITMAP = 10
    DWMWA_DISALLOW_PEEK = 11
    DWMWA_EXCLUDED_FROM_PEEK = 12
    DWMWA_CLOAK = 13
    DWMWA_CLOAKED = 14
    DWMWA_FREEZE_REPRESENTATION = 15
    DWMWA_PASSIVE_UPDATE_MODE = 16
    DWMWA_USE_HOSTBACKDROPBRUSH = 17
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    DWMWA_WINDOW_CORNER_PREFERENCE = 33
    DWMWA_BORDER_COLOR = 34
    DWMWA_CAPTION_COLOR = 35
    DWMWA_TEXT_COLOR = 36
    DWMWA_VISIBLE_FRAME_BORDER_THICKNESS = 37
    DWMWA_SYSTEMBACKDROP_TYPE = 38
    DWMWA_LAST = 39

# 窗口圆角偏好
class DWM_WINDOW_CORNER_PREFERENCE(IntEnum):
    DWMWCP_DEFAULT = 0
    DWMWCP_DONOTROUND = 1
    DWMWCP_ROUND = 2
    DWMWCP_ROUNDSMALL = 3

# 系统背景类型 (Win11 22621+)
class DWMSBT(IntEnum):
    DWMSBT_AUTO = 0
    DWMSBT_NONE = 1
    DWMSBT_MAINWINDOW = 2  # Mica
    DWMSBT_TABBEDWINDOW = 3  # 亚克力
    DWMSBT_OVERLAY = 4

# 窗口组合属性 (Win10 亚克力)
class WCA(IntEnum):
    WCA_ACCENT_POLICY = 19

# 重音状态
class ACCENT_STATE(IntEnum):
    ACCENT_DISABLED = 0
    ACCENT_ENABLE_GRADIENT = 1
    ACCENT_ENABLE_TRANSPARENTGRADIENT = 2
    ACCENT_ENABLE_BLURBEHIND = 3
    ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
    ACCENT_ENABLE_HOSTBACKDROP = 5

# ==================== 结构体定义 ====================

class ACCENTPOLICY(ctypes.Structure):
    _fields_ = [
        ('AccentState', ctypes.wintypes.DWORD),
        ('AccentFlags', ctypes.wintypes.DWORD),
        ('GradientColor', ctypes.wintypes.DWORD),
        ('AnimationId', ctypes.wintypes.DWORD),
    ]

class WINCOMPATTRDATA(ctypes.Structure):
    _fields_ = [
        ('Attribute', ctypes.wintypes.DWORD),
        ('Data', ctypes.POINTER(ACCENTPOLICY)),
        ('SizeOfData', ctypes.c_size_t),
    ]

class MARGINS(ctypes.Structure):
    _fields_ = [
        ('cxLeftWidth', ctypes.wintypes.INT),
        ('cxRightWidth', ctypes.wintypes.INT),
        ('cyTopHeight', ctypes.wintypes.INT),
        ('cyBottomHeight', ctypes.wintypes.INT),
    ]

# ==================== API 加载 ====================

_dwmapi = ctypes.windll.LoadLibrary('dwmapi.dll')
_user32 = ctypes.windll.LoadLibrary('user32.dll')

DwmSetWindowAttribute = _dwmapi.DwmSetWindowAttribute
DwmSetWindowAttribute.argtypes = [
    ctypes.wintypes.HWND,
    ctypes.wintypes.DWORD,
    ctypes.c_void_p,
    ctypes.wintypes.DWORD,
]
DwmSetWindowAttribute.restype = ctypes.wintypes.LONG

DwmExtendFrameIntoClientArea = _dwmapi.DwmExtendFrameIntoClientArea
DwmExtendFrameIntoClientArea.argtypes = [
    ctypes.wintypes.HWND,
    ctypes.POINTER(MARGINS),
]
DwmExtendFrameIntoClientArea.restype = ctypes.wintypes.LONG

SetWindowCompositionAttribute = _user32.SetWindowCompositionAttribute
SetWindowCompositionAttribute.argtypes = [
    ctypes.wintypes.HWND,
    ctypes.POINTER(WINCOMPATTRDATA),
]
SetWindowCompositionAttribute.restype = ctypes.wintypes.BOOL


# ==================== 公共 API ====================

def _hwnd(widget):
    """从 QWidget 获取 Windows 窗口句柄"""
    try:
        return int(widget.winId())
    except Exception:
        return 0


def set_rounded_corners(widget, prefer_round=True):
    """设置窗口圆角 (Win11 22000+)
    
    Args:
        widget: QWidget 实例
        prefer_round: True=大圆角, False=小圆角
    """
    hwnd = _hwnd(widget)
    if not hwnd:
        return False
    
    try:
        corner = DWM_WINDOW_CORNER_PREFERENCE.DWMWCP_ROUND if prefer_round else DWM_WINDOW_CORNER_PREFERENCE.DWMWCP_ROUNDSMALL
        value = ctypes.wintypes.INT(corner.value)
        DwmSetWindowAttribute(
            hwnd,
            DWMWINDOWATTRIBUTE.DWMWA_WINDOW_CORNER_PREFERENCE.value,
            ctypes.byref(value),
            ctypes.sizeof(value)
        )
        return True
    except Exception as e:
        logger.warning(f"设置圆角失败: {e}")
        return False


def set_dark_mode(widget, enable=True):
    """设置暗色模式标题栏 (Win10 17763+)
    
    Args:
        widget: QWidget 实例
        enable: True=暗色, False=亮色
    """
    hwnd = _hwnd(widget)
    if not hwnd:
        return False
    
    try:
        value = ctypes.wintypes.BOOL(int(enable))
        DwmSetWindowAttribute(
            hwnd,
            DWMWINDOWATTRIBUTE.DWMWA_USE_IMMERSIVE_DARK_MODE.value,
            ctypes.byref(value),
            ctypes.sizeof(value)
        )
        return True
    except Exception as e:
        logger.warning(f"设置暗色模式失败: {e}")
        return False


def set_acrylic_backdrop(widget, enable=True):
    """设置亚克力背景 (Win11 22621+)
    使用 DWMSBT_TABBEDWINDOW 实现亚克力效果
    
    Args:
        widget: QWidget 实例
        enable: True=启用亚克力, False=禁用
    """
    hwnd = _hwnd(widget)
    if not hwnd:
        return False
    
    try:
        value = ctypes.wintypes.INT(
            DWMSBT.DWMSBT_TABBEDWINDOW.value if enable else DWMSBT.DWMSBT_AUTO.value
        )
        DwmSetWindowAttribute(
            hwnd,
            DWMWINDOWATTRIBUTE.DWMWA_SYSTEMBACKDROP_TYPE.value,
            ctypes.byref(value),
            ctypes.sizeof(value)
        )
        return True
    except Exception as e:
        logger.warning(f"设置亚克力背景失败: {e}")
        return False


def set_mica_backdrop(widget, enable=True):
    """设置 Mica 背景 (Win11 22000+)
    Mica 是更轻量的材质，性能优于亚克力
    
    Args:
        widget: QWidget 实例
        enable: True=启用 Mica
    """
    hwnd = _hwnd(widget)
    if not hwnd:
        return False
    
    try:
        value = ctypes.wintypes.INT(
            DWMSBT.DWMSBT_MAINWINDOW.value if enable else DWMSBT.DWMSBT_AUTO.value
        )
        DwmSetWindowAttribute(
            hwnd,
            DWMWINDOWATTRIBUTE.DWMWA_SYSTEMBACKDROP_TYPE.value,
            ctypes.byref(value),
            ctypes.sizeof(value)
        )
        return True
    except Exception as e:
        logger.warning(f"设置 Mica 背景失败: {e}")
        return False


def set_win10_acrylic(widget, color=0x00FFFFFF, enable=True):
    """Win10 亚克力模糊（兼容方案）
    通过 SetWindowCompositionAttribute 实现
    
    Args:
        widget: QWidget 实例
        color: 覆盖色 RGBA (0xAABBGGRR)，默认半透明白
        enable: True=启用模糊
    """
    hwnd = _hwnd(widget)
    if not hwnd:
        return False
    
    try:
        accent = ACCENTPOLICY()
        if enable:
            accent.AccentState = ACCENT_STATE.ACCENT_ENABLE_ACRYLICBLURBEHIND.value
            accent.GradientColor = color
            accent.AccentFlags = 2
        else:
            accent.AccentState = ACCENT_STATE.ACCENT_DISABLED.value
        
        data = WINCOMPATTRDATA()
        data.Attribute = WCA.WCA_ACCENT_POLICY.value
        data.SizeOfData = ctypes.sizeof(accent)
        data.Data = ctypes.pointer(accent)
        
        SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
        return True
    except Exception as e:
        logger.warning(f"设置 Win10 亚克力失败: {e}")
        return False


def extend_frame(widget):
    """扩展窗口框架到客户区（实现全窗口亚克力）
    
    Args:
        widget: QWidget 实例
    """
    hwnd = _hwnd(widget)
    if not hwnd:
        return False
    
    try:
        margins = MARGINS(-1, -1, -1, -1)
        DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
        return True
    except Exception as e:
        logger.warning(f"扩展框架失败: {e}")
        return False


def enable_acrylic(widget, dark_mode=True, use_mica=False):
    """一键启用完整的亚克力效果（自动检测系统版本）
    
    Args:
        widget: QWidget 实例
        dark_mode: 是否暗色模式
        use_mica: 优先使用 Mica（性能更好）
    
    返回:
        tuple (success, method)
        method: 'win11_acrylic', 'win11_mica', 'win10_acrylic', 'none'
    """
    import platform
    
    hwnd = _hwnd(widget)
    if not hwnd:
        return False, 'none'
    
    win_ver = tuple(int(x) for x in platform.version().split('.')[:2])
    is_win11 = win_ver >= (10, 22000)
    is_win11_22621 = win_ver >= (10, 22621)
    
    try:
        # 先设置暗色模式
        set_dark_mode(widget, dark_mode)

        # 扩展窗框到整个客户区（亚克力必需步骤）
        extend_frame(widget)

        if is_win11_22621:
            # Win11 22621+ 使用原生亚克力/Mica
            if use_mica:
                set_mica_backdrop(widget, True)
                set_rounded_corners(widget, True)
                logger.info("启用 Win11 Mica + 圆角")
                return True, 'win11_mica'
            else:
                set_acrylic_backdrop(widget, True)
                set_rounded_corners(widget, True)
                logger.info("启用 Win11 亚克力 + 圆角")
                return True, 'win11_acrylic'
        
        elif is_win11:
            # Win11 22000-22621 仅 Mica + 圆角
            set_mica_backdrop(widget, True)
            set_rounded_corners(widget, True)
            logger.info("启用 Win11 Mica + 圆角 (无亚克力)")
            return True, 'win11_mica'
        
        else:
            # Win10 使用 SetWindowCompositionAttribute
            set_rounded_corners(widget, False)
            set_win10_acrylic(widget, enable=True)
            logger.info("启用 Win10 亚克力")
            return True, 'win10_acrylic'
    
    except Exception as e:
        logger.error(f"启用亚克力失败: {e}")
        return False, 'none'
