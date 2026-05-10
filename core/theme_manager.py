"""
主题管理器
从 themes/*.json 加载主题定义，支持热添加新风格
只需在 themes/ 目录放入 JSON 文件即可注册新主题
"""
import os
import json
import logging
from PyQt5.QtGui import QColor
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

_THEMES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'themes')


def _load_theme_from_json(path: str) -> Optional[dict]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'name' in data:
            return data
    except Exception as e:
        logger.warning(f"加载主题失败: {path} — {e}")
    return None


def _discover_themes() -> Dict[str, dict]:
    themes = {}
    if not os.path.isdir(_THEMES_DIR):
        return themes
    for fname in os.listdir(_THEMES_DIR):
        if fname.endswith('.json'):
            path = os.path.join(_THEMES_DIR, fname)
            theme = _load_theme_from_json(path)
            if theme:
                themes[theme['name']] = theme
    return themes


_ALL_THEMES = _discover_themes()
if not _ALL_THEMES:
    _ALL_THEMES['fluent'] = {'name': 'fluent', 'display_name': 'Fluent (fallback)'}
logger.info(f"已发现 {len(_ALL_THEMES)} 个主题: {list(_ALL_THEMES.keys())}")


class ThemeManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._current = 'fluent'
            cls._instance._runtime = {}
        return cls._instance

    # ── 重新发现主题（热加载） ──
    @staticmethod
    def reload_themes():
        global _ALL_THEMES
        _ALL_THEMES = _discover_themes()
        if not _ALL_THEMES:
            _ALL_THEMES['fluent'] = {'name': 'fluent', 'display_name': 'Fluent (fallback)'}
        logger.info(f"重新发现 {len(_ALL_THEMES)} 个主题")

    # ── 基本信息 ──
    @property
    def current_theme_name(self) -> str:
        return self._current

    def get_current_theme(self) -> dict:
        return _ALL_THEMES.get(self._current, _ALL_THEMES.get('fluent', {}))

    # ── 读写 ──
    def set_theme(self, theme_name: str) -> bool:
        if theme_name in _ALL_THEMES:
            self._current = theme_name
            logger.info(f"主题切换为: {theme_name}")
            return True
        logger.warning(f"未知主题: {theme_name}，可用: {list(_ALL_THEMES.keys())}")
        return False

    def get(self, key: str, fallback: Any = None) -> Any:
        if key in self._runtime:
            return self._runtime[key]
        return self.get_current_theme().get(key, fallback)

    def set(self, key: str, value: Any):
        self._runtime[key] = value

    def qcolor(self, key: str, fallback: str = '#000000') -> QColor:
        return QColor(self.get(key, fallback))

    @classmethod
    def list_themes(cls) -> list:
        return [{'id': k, 'name': v['display_name']} for k, v in _ALL_THEMES.items()]

    def theme_css(self) -> str:
        """生成内联CSS字符串，用于QTextBrowser等HTML内容"""
        t = self.get_current_theme()
        bg = t.get('bg_color', '#F8F9FA')
        fg = t.get('fg_color', '#212529')
        accent = t.get('accent_color', '#0078D4')
        font = t.get('font_family', "'Segoe UI', 'Microsoft YaHei', sans-serif")
        return f"body{{background-color:{bg};color:{fg};font-family:{font};}}a{{color:{accent};text-decoration:none;}}a:hover{{color:{accent};text-decoration:underline;}}"

theme_manager = ThemeManager()
