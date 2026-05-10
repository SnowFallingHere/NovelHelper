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
            'base_font_size': '14',
            'base_title_size': '16',
            'base_width': '1200',
            'base_height': '800',
            'initial_width': '1400',
            'initial_height': '900',
            'min_width': '900',
            'min_height': '600',
            'log_font_size': '12',
            'graph_font_size': '12',
            'kwlist_font_color': '#0078D4',
            'kwlist_font_family': 'Microsoft YaHei UI',
            'link_italic': '1',
            'link_bold': '0',
            'bg_color': '#F8F9FA',
            'fg_color': '#212529',
            'border_color': '#DEE2E6',
            'accent_color': '#0078D4',
            'error_color': '#D13438',
            'warn_color': '#FF8C00',
            'btn_bg_color': '#0078D4',
            'btn_hover_color': '#106EBE',
            'input_bg_color': '#FFFFFF',
            'theme': 'fluent',
            'kw_h1_size': '20',
            'kw_h1_color': '#0078D4',
            'kw_h2_size': '18',
            'kw_h2_color': '#107C10',
            'kw_body_size': '14',
            'kw_body_color': '#606060',
            'kw_link_size': '14',
            'kw_link_color': '#0078D4',
            'enable_font_scaling': '1',
            'scaling_reference_width': '1570',
            'scaling_min': '0.8',
            'scaling_max': '1.5',
            'faction_tree_font_size': '14',
            'family_tree_font_size': '13',
            'enable_animations': '1',
            'enable_acrylic': '1'
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
            'show_grid': '1',
            'node_min_size': '60',
            'node_max_size': '160',
            'node_min_brightness': '15',
            'node_max_brightness': '65',
            'enable_glow': '1',
            'enable_size_sort': '1',
            'enable_brightness_sort': '1'
        },
        'Theme': {
            'graph_bg_color': '#F8F9FA',
            'graph_bg_follow_theme': '1',
            'graph_grid_color': '#E9ECEF',
            'edge_width': '3'
        },
        'Frequency': {
            'min_word_length': '2',
            'min_occurrences': '3',
            'inactive_chapters': '3',
            'auto_scan': '1',
            'filter_stopwords': '1',
            'keywords_only': '0',
            'stale_ratio': '3',
            'stale_gap': '3'
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
        },
        'Stats': {
            'volume_target_words': '100000',
            'daily_target_words': '2000'
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
