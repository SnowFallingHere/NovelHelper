"""
字体管理器 - 提供跨平台的字体配置
根据操作系统自动选择合适的默认字体
"""
import os
import sys
from .config_manager import ConfigManager

class FontManager:
    """字体管理器 - 统一处理所有字体设置"""

    # 默认字体回退链（按优先级）
    FONT_BACKUP_CHAINS = {
        'default': {
            'zh_CN': ['Microsoft YaHei', 'SimHei', 'PingFang SC', 'WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'sans-serif'],
            'en_US': ['Segoe UI', 'San Francisco', 'Ubuntu', 'Cantarell', 'DejaVu Sans', 'Arial', 'sans-serif'],
            'ja_JP': ['Microsoft YaHei', 'Meiryo', 'Hiragino Sans', 'Noto Sans CJK JP', 'sans-serif'],
        },
        'monospace': {
            'zh_CN': ['Consolas', 'Courier New', 'Microsoft YaHei', 'Monaco', 'monospace'],
            'en_US': ['Consolas', 'Courier New', 'Monaco', 'Ubuntu Mono', 'monospace'],
            'ja_JP': ['Consolas', 'Courier New', 'Meiryo', 'monospace'],
        }
    }

    _instance = None
    _initialized = False

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._available_fonts = None

    def get_os_name(self):
        """获取操作系统名称"""
        if sys.platform.startswith('win'):
            return 'windows'
        elif sys.platform.startswith('darwin'):
            return 'macos'
        elif sys.platform.startswith('linux'):
            return 'linux'
        return 'unknown'

    def get_default_font(self, font_type='default', lang=None):
        """
        获取当前系统可用的默认字体

        Args:
            font_type: 'default' | 'monospace'
            lang: 语言代码，默认从配置读取

        Returns:
            字体名称
        """
        if lang is None:
            lang = ConfigManager.get('Language', 'current', fallback='zh_CN')

        chains = self.FONT_BACKUP_CHAINS.get(font_type, self.FONT_BACKUP_CHAINS['default'])
        chain = chains.get(lang, chains['en_US'])

        # 从配置读取用户设置的字体
        config_font = None
        if font_type == 'default':
            config_font = ConfigManager.get('UI', 'kwlist_font_family', fallback=None)
        elif font_type == 'monospace':
            #  monospace 目前没有配置项，用默认回退链
            pass

        if config_font:
            chain = [config_font] + chain

        for font in chain:
            if self._is_font_available(font):
                return font

        return 'sans-serif'

    def _is_font_available(self, font_name):
        """
        检查字体是否在系统上可用

        Args:
            font_name: 字体名称

        Returns:
            bool
        """
        try:
            from PyQt5.QtGui import QFontDatabase
            db = QFontDatabase()
            families = db.families()
            return font_name in families
        except Exception:
            # 如果 PyQt 不可用，根据 OS 简单判断
            os_name = self.get_os_name()
            if os_name == 'windows':
                return font_name in ['Microsoft YaHei', 'SimHei', 'Consolas', 'Courier New', 'Arial']
            elif os_name == 'macos':
                return font_name in ['PingFang SC', 'Hiragino Sans', 'Monaco', 'San Francisco']
            else:
                return font_name in ['WenQuanYi Micro Hei', 'Noto Sans', 'Ubuntu']

    def get_font_family(self, config_value=None, lang=None):
        """
        获取字体族，带回退链

        Args:
            config_value: 配置文件中的字体值
            lang: 语言代码

        Returns:
            str: 可用字体名
        """
        if config_value and self._is_font_available(config_value):
            return config_value

        return self.get_default_font(lang=lang)

# 全局实例
font_manager = FontManager()
