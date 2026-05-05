import os
import sys
import threading
import configparser
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    _config_cache = None
    _cache_dirty = False
    _lock = threading.Lock()
    
    @staticmethod
    def get_config_file_path():
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "NovelHelper.ini")
    
    CONFIG_FILE = None
    
    @classmethod
    def _get_config_file(cls):
        if cls.CONFIG_FILE is None:
            cls.CONFIG_FILE = cls.get_config_file_path()
        return cls.CONFIG_FILE
    
    DEFAULT_CONFIG = {
        'UI': {
            'base_font_size': '20',
            'base_title_size': '32',
            'initial_width': '1100',
            'initial_height': '975',
            'min_width': '800',
            'min_height': '600',
            'log_font_size': '16',
            'graph_font_size': '14',
            'kwlist_font_size': '20',
            'kwlist_title_size': '18',
            'kwlist_font_color': '#00FF41',
            'kwlist_font_family': 'Microsoft YaHei',
            'card_font_size': '30',
            'card_title_size': '20',
            'bg_color': '#020804',
            'fg_color': '#00FF41',
            'border_color': '#00AA30',
            'accent_color': '#00FF41',
            'error_color': '#FF3333',
            'warn_color': '#FFAA00',
            'btn_bg_color': '#001a05',
            'btn_hover_color': '#003310',
            'input_bg_color': '#000d03',
            'theme': 'matrix'
        },
        'Monitor': {
            'check_interval': '15',
            'max_ahead_chapters': '2',
            'min_word_count': '20',
            'novel_dir': '',
            'heartbeat_timeout': '120',
            'log_buffer_size': '100'
        },
        'Adaptive': {
            'area_scale_factor': '2',
            'height_scale_factor': '1.2',
            'font_increase': '4'
        },
        'Environment': {
            'init_chapter_count': '2000',
            'init_copy_count': '10',
            'pending_delete': '0'
        },
        'Graph': {
            'layout_ideal_length': '200',
            'repulsion_strength': '50000',
            'node_limit': '200',
            'auto_save_layout': '1',
            'show_grid': '1'
        },
        'Theme': {
            'graph_bg_color': '#060612',
            'graph_grid_color': '#0a1a10',
            'edge_width': '3'
        },
        'Frequency': {
            'min_word_length': '2',
            'min_occurrences': '3',
            'inactive_chapters': '3',
            'auto_scan': '1'
        },
        'Language': {
            'current': 'zh_CN'
        },
        'Format': {
            'export_format': '',
            'detect_formats': '',
            'export_volume_format': '',
            'export_chapter_format': '',
            'preview_color': '#FFFFFF',
            'preview_font_size': '23',
            'format_help_font_size': '20'
        }
    }
    
    @classmethod
    def _load_config_internal(cls):
        config = configparser.ConfigParser()
        config_file = cls._get_config_file()
        if os.path.exists(config_file):
            config.read(config_file, encoding='utf-8')
        else:
            cls.create_default_config()
            config.read(config_file, encoding='utf-8')
        return config
    
    @classmethod
    def load_config(cls):
        with cls._lock:
            if cls._config_cache is None or cls._cache_dirty:
                cls._config_cache = cls._load_config_internal()
                cls._cache_dirty = False
            return cls._config_cache
    
    @classmethod
    def create_default_config(cls):
        config_file = cls._get_config_file()
        if os.path.exists(config_file):
            return
        config = configparser.ConfigParser()
        for section, values in cls.DEFAULT_CONFIG.items():
            config[section] = values
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            logger.info(f"已创建默认配置文件: {config_file}")
        except Exception:
            pass
        cls._cache_dirty = True
    
    @classmethod
    def get(cls, section, key, fallback=None):
        config = cls.load_config()
        if config.has_option(section, key):
            return config.get(section, key)
        return fallback
    
    @classmethod
    def get_int(cls, section, key, fallback=0):
        try:
            return int(cls.get(section, key, fallback))
        except (ValueError, TypeError):
            return fallback
    
    @classmethod
    def get_float(cls, section, key, fallback=0.0):
        try:
            return float(cls.get(section, key, fallback))
        except (ValueError, TypeError):
            return fallback
    
    @classmethod
    def set(cls, section, key, value):
        with cls._lock:
            config = cls._load_config_internal()
            if not config.has_section(section):
                config.add_section(section)
            config.set(section, key, str(value))
            config_file = cls._get_config_file()
            with open(config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            cls._cache_dirty = True

    @classmethod
    def remove_option(cls, section, key):
        with cls._lock:
            config = cls._load_config_internal()
            if config.has_option(section, key):
                config.remove_option(section, key)
                config_file = cls._get_config_file()
                with open(config_file, 'w', encoding='utf-8') as f:
                    config.write(f)
                cls._cache_dirty = True
