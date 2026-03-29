import os
import re
import shutil
import time
import sys
import logging
import configparser
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QLabel, QPushButton, 
                             QLineEdit, QRadioButton, QTextEdit, QProgressBar,
                             QGroupBox, QFormLayout, QMessageBox, QScrollArea,
                             QFrame, QComboBox, QFileDialog, QSplitter, QSizePolicy, QSpinBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread, QSize, QSettings, QEvent
from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QPalette

def get_base_dir():
    """获取程序根目录 - 脚本所在目录，兼容打包环境"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        script_path = os.path.abspath(__file__)
        return os.path.dirname(script_path)

SCRIPT_DIR = get_base_dir()

def get_log_dir():
    """获取日志目录"""
    log_dir = os.path.join(get_base_dir(), "log")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    return log_dir

UI_REFRESH_INTERVAL = 500

# 延迟初始化日志配置
def setup_logging():
    log_dir = get_log_dir()
    log_file = os.path.join(log_dir, f"NovelHelper_{datetime.now().strftime('%Y%m%d')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

setup_logging()
logger = logging.getLogger(__name__)

def get_novel_dir():
    """获取小说目录 - 优先从配置读取，否则使用脚本所在目录"""
    try:
        config = ConfigManager.load_config()
        custom_novel_dir = config.get('Monitor', 'novel_dir', fallback='')
        if custom_novel_dir and os.path.isdir(custom_novel_dir):
            return custom_novel_dir
    except Exception:
        pass
    return SCRIPT_DIR

def get_all_dir():
    """获取 all/ 目录 - 在小说目录下"""
    novel_dir = get_novel_dir()
    return os.path.join(novel_dir, "all")

try:
    from cn2an import an2cn
except ImportError:
    logger.error("缺少必要的库: cn2an，请运行 pip install cn2an")
    sys.exit(1)

class FileManager:
    _current_lang = 'zh_CN'
    _custom_export_format = None
    _custom_detect_formats = None
    _custom_export_volume_format = None
    _custom_export_chapter_format = None

    @classmethod
    def set_language(cls, lang):
        cls._current_lang = lang
        cls._load_custom_formats()

    @classmethod
    def _load_custom_formats(cls):
        """从配置文件加载自定义格式"""
        config = ConfigManager.load_config()
        cls._custom_export_format = config.get('Format', 'export_format', fallback=None)
        detect_str = config.get('Format', 'detect_formats', fallback=None)
        if detect_str:
            cls._custom_detect_formats = [f.strip() for f in detect_str.split('|')]
        else:
            cls._custom_detect_formats = None
        cls._custom_export_volume_format = config.get('Format', 'export_volume_format', fallback=None)
        cls._custom_export_chapter_format = config.get('Format', 'export_chapter_format', fallback=None)

    @classmethod
    def get_chapter_number(cls, filename):
        match = re.match(r'^(\d+)', filename)
        if match:
            return int(match.group(1))
        return None

    @classmethod
    def find_latest_chapter(cls, folder_path):
        try:
            files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
            if not files:
                return None
            max_num = 0
            latest_file = None
            for f in files:
                num = cls.get_chapter_number(f)
                if num and num > max_num:
                    max_num = num
                    latest_file = f
            return max_num, latest_file
        except Exception:
            return None

    @classmethod
    def _format_chapter(cls, fmt, chapter_num, name=""):
        """根据格式字符串格式化章节名
        格式：
        {num}=阿拉伯数字(硬编码)
        {cn.up.Chapter}=第壹佰伍拾叁章
        {cn.low.Chapter}=第一百五十三章
        {cn.num.Chapter}=第153章
        {en.Chapter}=Chapter153
        {jp.Chapter}=第一百五十三章
        {name}=后缀
        """
        num_str = str(chapter_num)
        zh_num_low = cls.num_to_chinese(chapter_num)  # 小写：一百五十三
        zh_num_up = cls.num_to_chinese_upper(chapter_num)  # 大写：壹佰伍拾叁

        # 先替换语言格式
        result = fmt.replace('{cn.up.Chapter}', f'第{zh_num_up}章')
        result = result.replace('{cn.low.Chapter}', f'第{zh_num_low}章')
        result = result.replace('{cn.num.Chapter}', f'第{num_str}章')
        result = result.replace('{en.Chapter}', f'Chapter{num_str}')
        result = result.replace('{jp.Chapter}', f'第{zh_num_low}章')

        # 替换 {num} 在最前面
        result = num_str + result.replace('{num}', '')

        # 替换 {name} 为后缀
        if name:
            if '{name}' in result:
                result = result.replace('{name}', name)
            elif '_' in result:
                # 如果有下划线，在下划线后加后缀
                if not result.rstrip().endswith('_'):
                    result = result + name
            else:
                # 没有下划线也没有{name}，直接加下划线+后缀
                result = result + '_' + name
        else:
            # 没有后缀，移除末尾的下划线
            result = result.rstrip('_')

        return result

    @classmethod
    def generate_chapter_name(cls, chapter_num, name="", include_prefix=True):
        """根据当前语言生成章节名称，支持自定义格式"""
        if cls._custom_export_format:
            fmt = cls._custom_export_format
            result = cls._format_chapter(fmt, chapter_num, name)
            if not include_prefix:
                # 移除开头的数字
                import re
                result = re.sub(r'^\d+', '', result)
            return result

        lang = cls._current_lang
        num_str = str(chapter_num)

        if lang == 'zh_CN':
            chapter_word = cls.num_to_chinese(chapter_num) + "章"
            prefix = f"{num_str}第" if include_prefix else ""
            return f"{prefix}{chapter_word}_{name}"
        elif lang == 'en_US':
            chapter_word = f"Chapter{chapter_num}"
            prefix = f"{num_str}[" if include_prefix else "["
            suffix = f"]{name}" if name else "]"
            return f"{prefix}{chapter_word}{suffix}"
        elif lang == 'ja_JP':
            chapter_word = cls.num_to_chinese(chapter_num) + "章"
            prefix = f"{num_str}第" if include_prefix else ""
            return f"{prefix}{chapter_word}_{name}"
        else:
            chapter_word = cls.num_to_chinese(chapter_num) + "章"
            prefix = f"{num_str}第" if include_prefix else ""
            return f"{prefix}{chapter_word}_{name}"

    @classmethod
    def _format_export(cls, fmt, num, name="", word_count=None):
        """导出格式化方法
        格式变量：{cn.up.Volume},{cn.low.Volume},{cn.num.Volume},{en.Volume},{jp.Volume}
                  {cn.up.Chapter},{cn.low.Chapter},{cn.num.Chapter},{en.Chapter},{jp.Chapter}
                  {num},{name},{word_count}
        特殊：_ 在语言格式和 name 之间时自动转为 ·
        """
        num_str = str(num)
        zh_num_low = cls.num_to_chinese(num)
        zh_num_up = cls.num_to_chinese_upper(num)

        result = fmt
        result = result.replace('{cn.up.Volume}', f'第{zh_num_up}卷')
        result = result.replace('{cn.low.Volume}', f'第{zh_num_low}卷')
        result = result.replace('{cn.num.Volume}', f'第{num_str}卷')
        result = result.replace('{en.Volume}', f'Volume{num_str}')
        result = result.replace('{jp.Volume}', f'第{zh_num_low}巻')

        result = result.replace('{cn.up.Chapter}', f'第{zh_num_up}章')
        result = result.replace('{cn.low.Chapter}', f'第{zh_num_low}章')
        result = result.replace('{cn.num.Chapter}', f'第{num_str}章')
        result = result.replace('{en.Chapter}', f'Chapter{num_str}')
        result = result.replace('{jp.Chapter}', f'第{zh_num_low}章')

        result = result.replace('{num}', num_str)

        if word_count is not None:
            result = result.replace('{word_count}', str(word_count))

        if name:
            result = result.replace('{name}', name)
            result = result.replace('_', '·')
        else:
            result = result.replace('{name}', '')
            result = result.replace('_', '·')

        return result

    @classmethod
    def format_volume_title_export(cls, volume_num, volume_name, word_count):
        """导出卷标题格式化"""
        export_fmt = cls._custom_export_volume_format
        if export_fmt:
            return cls._format_export(export_fmt, volume_num, volume_name, word_count)
        return f'-----【第{volume_num}卷·{volume_name}:{word_count}】-----'

    @classmethod
    def format_chapter_title_export(cls, chapter_num, chapter_name):
        """导出章节标题格式化"""
        export_fmt = cls._custom_export_chapter_format
        if export_fmt:
            return cls._format_export(export_fmt, chapter_num, chapter_name)
        return f'-----【第{chapter_num}章-{chapter_name}】-----'

    @classmethod
    def find_next_chapter_in_all(cls, target_chapter_num):
        """在 all 目录中查找指定章节的模板文件，支持自定义检测格式"""
        try:
            possible_filenames = []

            if cls._custom_detect_formats:
                for fmt in cls._custom_detect_formats:
                    filename = cls._format_chapter(fmt, target_chapter_num, "name")
                    if not filename.endswith('.txt'):
                        filename += '.txt'
                    possible_filenames.append(filename)
            else:
                lang = cls._current_lang
                if lang == 'zh_CN':
                    chinese_num = cls.num_to_chinese(target_chapter_num) + "章"
                    possible_filenames.append(f"{target_chapter_num}第{chinese_num}_name.txt")
                    possible_filenames.append(f"{target_chapter_num}第{chinese_num}_.txt")
                elif lang == 'en_US':
                    possible_filenames.append(f"{target_chapter_num}[Chapter{target_chapter_num}]_name.txt")
                    possible_filenames.append(f"{target_chapter_num}[Chapter{target_chapter_num}]_.txt")
                elif lang == 'ja_JP':
                    chinese_num = cls.num_to_chinese(target_chapter_num) + "章"
                    possible_filenames.append(f"{target_chapter_num}第{chinese_num}_name.txt")
                    possible_filenames.append(f"{target_chapter_num}第{chinese_num}_.txt")

            for filename in possible_filenames:
                target_path = os.path.join(get_all_dir(), filename)
                if os.path.exists(target_path):
                    return target_path, target_chapter_num

            if lang != 'zh_CN':
                chinese_num = cls.num_to_chinese(target_chapter_num) + "章"
                target_filename = f"{target_chapter_num}第{chinese_num}_name.txt"
                target_path = os.path.join(get_all_dir(), target_filename)
                if os.path.exists(target_path):
                    return target_path, target_chapter_num

            return None, target_chapter_num
        except Exception:
            return None, target_chapter_num

    @classmethod
    def get_folder_number(cls, folder_name):
        match = re.match(r'^(\d+)\[', folder_name)
        if match:
            return int(match.group(1))
        return None

    @classmethod
    def extract_volume_name(cls, folder_name):
        """从文件夹名提取卷名称（如 '第一卷' 或 'Volume One'）"""
        match = re.search(r'\[(.+?)\]', folder_name)
        if match:
            return match.group(1)
        return None

    @classmethod
    def format_chapter_title(cls, chapter_num, chapter_name=""):
        """根据当前语言格式化章节标题"""
        lang = cls._current_lang

        if lang == 'zh_CN':
            chinese_num = cls.num_to_chinese(chapter_num)
            return f"-----【第{chapter_num}章-{chapter_name}】-----"
        elif lang == 'en_US':
            return f"-----【Chapter {chapter_num}-{chapter_name}】-----"
        elif lang == 'ja_JP':
            japanese_num = cls.num_to_chinese(chapter_num)
            return f"-----【第{chapter_num}章-{chapter_name}】-----"
        else:
            return f"-----【第{chapter_num}章-{chapter_name}】-----"

    @classmethod
    def replace_dash_with_space(cls, text):
        """将 '-' 替换为空格（用于英文格式）"""
        return text.replace('-', ' ')

    @staticmethod
    def is_default_content(file_path):
        if not os.path.exists(file_path):
            return False
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                match = re.match(r'^第\d+个文件$', content)
                return match is not None
        except Exception:
            return False

    @classmethod
    def get_word_count(cls, file_path):
        if not os.path.exists(file_path):
            return 0, "文件不存在"
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return len(f.read()), None
        except Exception as e:
            return 0, str(e)

    @staticmethod
    def get_file_mtime(file_path):
        if not os.path.exists(file_path):
            return 0
        try:
            return os.path.getmtime(file_path)
        except Exception:
            return 0

    @classmethod
    def get_folder_files(cls, folder_path):
        try:
            files = sorted([f for f in os.listdir(folder_path) if f.endswith('.txt')],
                          key=lambda x: (cls.get_folder_number(x) is None, cls.get_chapter_number(x) or float('inf')))
            return files
        except Exception:
            return []

    @classmethod
    def copy_and_rename_internal(cls, source_path, dest_folder, chapter_num):
        try:
            new_filename = cls.generate_chapter_name(chapter_num, "", include_prefix=True)
            new_filename = new_filename.rstrip('_') + '_.txt'
            dest_path = os.path.join(dest_folder, new_filename)
            if os.path.exists(dest_path):
                return False, new_filename, "文件已存在"
            shutil.copy2(source_path, dest_path)
            return True, new_filename, None
        except Exception as e:
            return False, None, str(e)

    @classmethod
    def ensure_ahead_chapters_internal(cls, folder_name, folder_path, current_max, messages, max_ahead_chapters=2):
        added_count = 0
        added_files = []
        for add_num in range(current_max + 1, current_max + max_ahead_chapters + 1):
            target_filename = cls.generate_chapter_name(add_num, "", include_prefix=True).rstrip('_') + '_.txt'
            target_path = os.path.join(folder_path, target_filename)

            if os.path.exists(target_path):
                continue

            try:
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write('')
                added_count += 1
                added_files.append(target_filename)
                messages.append(f"[NEW] {folder_name}: 新增第{add_num}章")
            except Exception as e:
                logger.error(f"{folder_name}: 创建第{add_num}章失败 - {e}")
                messages.append(f"[WARN] {folder_name}: 创建第{add_num}章失败")

        if added_count > 0:
            messages.append(f"[NEW] {folder_name}: 新增{added_count}章")
        return added_count

    @staticmethod
    def num_to_chinese(num):
        """统一数字转中文 - 使用an2cn"""
        return an2cn(str(num))

    @staticmethod
    def num_to_chinese_upper(num):
        """数字转中文大写"""
        chinese_lower = an2cn(str(num))
        mapping = {
            '零': '零', '一': '壹', '二': '贰', '三': '叁', '四': '肆',
            '五': '伍', '六': '陆', '七': '柒', '八': '捌', '九': '玖',
            '十': '拾', '百': '佰', '千': '仟', '万': '萬', '亿': '億'
        }
        result = ""
        for char in chinese_lower:
            result += mapping.get(char, char)
        return result

    @staticmethod
    def convert_num_to_chinese(num):
        """统一数字转中文（带章） - 使用an2cn"""
        return an2cn(str(num)) + "章"

    @classmethod
    def is_numeric_volume_folder(cls, folder_name):
        match = re.match(r'^(\d+)', folder_name)
        return match is not None

    @classmethod
    def get_volume_number(cls, folder_name):
        match = re.match(r'^(\d+)', folder_name)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def is_old_volume(folder_name):
        return '[old_' in folder_name

class ConfigManager:
    """配置管理器 - 负责加载、缓存和保存应用配置"""
    
    _config_cache = None
    _cache_dirty = False
    
    @staticmethod
    def get_config_file_path():
        """获取配置文件路径 - 兼容打包和开发环境"""
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
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
            'initial_width': '1006',
            'initial_height': '975',
            'min_width': '800',
            'min_height': '600',
            'log_font_size': '16',
            'bg_color': '#0D0208',
            'fg_color': '#00FF41',
            'border_color': '#00FF41',
            'accent_color': '#00FF41',
            'error_color': '#FF4444',
            'btn_bg_color': '#001100',
            'btn_hover_color': '#003300',
            'input_bg_color': '#001100'
        },
        'Monitor': {
            'check_interval': '15',
            'max_ahead_chapters': '2',
            'min_word_count': '20',
            'novel_dir': ''
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
        if cls._config_cache is None or cls._cache_dirty:
            cls._config_cache = cls._load_config_internal()
            cls._cache_dirty = False
        return cls._config_cache
    
    @classmethod
    def create_default_config(cls):
        config = configparser.ConfigParser()
        for section, values in cls.DEFAULT_CONFIG.items():
            config[section] = values
        config_file = cls._get_config_file()
        with open(config_file, 'w', encoding='utf-8') as f:
            config.write(f)
        logger.info(f"已创建默认配置文件: {config_file}")
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
        config = cls._load_config_internal()
        if config.has_option(section, key):
            config.remove_option(section, key)
            config_file = cls._get_config_file()
            with open(config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            cls._cache_dirty = True


class LanguageManager:
    _current_lang = None
    _translations = {}
    _available_languages = []
    
    DEFAULT_TRANSLATIONS = {
        'zh_CN': {
            'app_title': '小说助手',
            'monitor_started': '监控已启动',
            'monitor_stopped': '监控已停止',
            'new_chapter_detected': '检测到新章节',
            'chapter_updated': '章节已更新',
            'new_folder_detected': '发现新文件夹',
            'new_chapters_added': '新增章节',
            'empty_chapters_deleted': '删除无内容章节',
            'old_volume_marked': '自动标记旧卷',
            'new_volume_marked': '自动标记新卷',
            'summary_triggered': '触发Summary',
            'waiting_for_write': '等待写入',
            'active': '活跃',
            'new': '新增',
            'volume_word_count': '本卷字数',
            'chapter_1': '第一章',
            'add_new_volume_btn': '增加新卷',
            'execute_summary': '执行 Summary',
            'parameter_config': '参数配置',
            'summary_merge_tool': 'Summary 合并工具',
            'create_chapters': '创建章节',
            'monitor_management': '监控管理',
            'user_guide': '使用说明',
            'create_runtime_env': '⚙ 创建运行环境',
            'exit_program': '⏻ 退出程序',
            'chapter_template_tool': '=== 章节模板创建工具 ===',
            'enter_start_chapter': '输入起始章节号',
            'enter_end_chapter': '输入结束章节号',
            'enter_file_suffix': '输入文件名后缀',
            'start_chapter_label': '起始章节',
            'end_chapter_label': '结束章节',
            'file_suffix_label': '文件后缀:',
            'start_creation': '开始创建',
            'select_directory': '选择目录',
            'save_directory_label': '保存目录:',
            'creation_result': '创建结果',
            'run_mode': '运行模式',
            'stats_only': '1. 仅统计并收集（不重命名文件夹）',
            'stats_and_rename': '2. 统计并重命名文件夹（默认）',
            'progress': '进度',
            'execution_result': '执行结果',
            'param_config_page': '=== 参数配置 ===',
            'ui_size_config': 'UI 尺寸配置',
            'base_font_size': '基础字号',
            'title_font_size': '标题字号',
            'log_font_size': '日志字号',
            'initial_width': '初始宽度',
            'initial_height': '初始高度',
            'min_width': '最小宽度',
            'min_height': '最小高度',
            'ui_color_config': 'UI 颜色配置',
            'bg_color': '背景颜色',
            'fg_color': '字体颜色',
            'border_color': '边框颜色',
            'error_color': '错误颜色',
            'btn_bg': '按钮背景',
            'btn_hover': '按钮悬停',
            'input_bg': '输入框背景',
            'monitor_config': '监控配置',
            'monitor_interval': '监控间隔',
            'pregenerate_chapters': '预生成章节数',
            'trigger_word_count': '触发字数',
            'adaptive_config': '自适应配置',
            'area_scale': '面积缩放倍数',
            'height_scale': '高度缩放倍数',
            'font_increment': '字号增加量',
            'format_config': '格式配置',
            'export_filename_format': '文件名格式',
            'export_volume_format': '卷标题格式',
            'export_chapter_format': '章节标题格式',
            'format_help_filename': '格式：{num}=数字、{cn.up.Chapter}=第壹佰伍拾叁章、{cn.low.Chapter}=第一百五十三章、{cn.num.Chapter}=第153章、{en.Chapter}=Chapter153、{jp.Chapter}=第一百五十三章、{name}=后缀',
            'format_help_volume': '格式：{cn.up.Volume}=第壹佰伍拾叁卷、{cn.low.Volume}=第一百五十三卷、{cn.num.Volume}=第153卷、{en.Volume}=Volume153、{jp.Volume}=第一百五十三巻、{name}=卷名、{word_count}=字数 | _在语言格式和{name}之间时自动转为·',
            'format_help_chapter': '格式：{cn.up.Chapter}=第壹佰伍拾叁章、{cn.low.Chapter}=第一百五十三章、{cn.num.Chapter}=第153章、{en.Chapter}=Chapter153、{jp.Chapter}=第一百五十三章、{name}=后缀 | _在语言格式和{name}之间时自动转为·',
            'preview_color': '预览颜色',
            'preview_font_size': '预览字号',
            'language_config': '语言配置',
            'select_language': '选择语言',
            'tip_change_language': '提示：切换语言后点击「保存并应用」生效',
            'save_and_apply': '保存并应用',
            'save_config': '保存配置',
            'reload': '重新加载',
            'user_guide_page': '=== 使用说明 ===',
            'monitor_system': '=== 监控管理系统 ===',
            'status_stopped': '状态: 已停止',
            'status_running': '状态: 运行中',
            'log_filter': '日志筛选',
            'folder_status': '文件夹状态',
            'recent_operations': '最近操作',
            'add_new_volume': '📖 增加新卷',
            'start_monitor': '启动监控',
            'stop_monitor': '停止监控',
            'confirm': '确认',
            'cancel': '取消',
            'confirm_exit': '确认退出',
            'exit_confirm_msg': '确定要退出程序吗？\n所有线程将会安全停止。',
            'env_not_initialized': '环境未初始化',
            'env_init_tip': '请先点击「创建运行环境」按钮！',
            'success': '成功',
            'error': '错误',
            'warning': '警告',
            'config_saved_restart': '配置已保存！\n重启程序后生效。',
            'config_saved_applied': '配置已保存并应用！',
            'config_reloaded': '配置已重新加载！',
            'save_config_failed': '保存配置失败',
            'save_apply_failed': '保存并应用失败',
            'reload_failed': '重新加载配置失败',
            'confirm_creation': '确认创建',
            'creating_runtime_env': '即将创建运行环境：',
            'create_folders': '1. 在当前目录创建 /all, /novel, /log 文件夹',
            'generate_templates': '2. 在 /all 生成章节模板',
            'create_title_folder': '3. 在 /novel 创建 title 文件夹',
            'copy_first_10': '4. 复制前10章到 /novel/title/1',
            'continue_question': '是否继续？',
            'new_volume_created': '已创建新卷',
            'add_volume_failed': '增加新卷失败',
            'monitor_auto_process': '监控正在运行，将自动处理新卷。',
            'start_monitor_process': '请启动监控来处理新卷。',
            'dir_not_exist': '目录不存在',
            'dir_not_exist_question': '目录不存在：{0}\n是否创建？',
            'create_question': '是否创建？',
            'create_dir_failed': '创建目录失败',
            'dir_not_writable': '目录不可写',
            'start_must_gt_zero': '起始章节必须大于0',
            'end_must_gt_zero': '结束章节必须大于0',
            'start_lt_end': '起始章节不能大于结束章节',
            'enter_valid_int': '请输入有效的正整数',
            'skipped_existing': '跳过已存在的',
            'files_unit': '个文件',
            'created_successfully': '成功创建',
            'clear_file_failed': '清空文件失败',
            'read_failed': '读取失败',
            'completed_cjk': '完成！CJK字符',
            'non_whitespace': '非空白字符',
            'filter_all': '全部',
            'filter_recent_15': '最近15条',
            'filter_recent_30': '最近30条',
            'filter_recent_50': '最近50条',
            'start_new_program': '启动新程序',
            'start_program_now_question': '是否立即启动新程序？',
            'create_env_failed': '创建运行环境失败',
            'start_program_failed': '启动新程序失败',
            'no_volume_folders': '没有找到卷文件夹！',
            'folder_exists': '文件夹 {0} 已存在！',
            'generating_chapters': '正在生成 {0} 章模板...',
            'novel_dir': '小说目录:',
            'select': '选择...',
            'select_novel_directory': '选择小说目录',
            'initialize_directory': '初始化目录',
            'initialize_directory_msg': '目录为空或没有找到卷文件夹，是否自动初始化？\n\n将创建：\n  - 1[new_0]/ 目录（第一卷）\n  - 10个无内容章节\n\n继续吗？',
            'check_directory_failed': '检查目录失败',
            'initialize_complete': '目录初始化完成！',
            'initialize_failed': '初始化目录失败',
            'help_content': """【一、灵活的目录选择
====================
★ 程序可以放在任意位置，无需固定目录结构
★ 通过GUI选择任意文件夹作为小说目录
★ 自动初始化会在选定目录创建必要结构

【二、首次设置步骤
==================
1. 启动程序
2. 进入「参数配置」标签页
3. 点击「小说目录」旁边的「选择...」按钮
4. 选择你要存放小说的文件夹
5. 如果文件夹为空，程序会询问是否自动初始化
6. 选择「是」将自动创建：
   - 1[new_0]/ 目录（第一卷，含10个空章节）

【三、功能说明
=============
1. 创建章节
   - 用于在小说目录中创建章节模板文件
   - 起始和结束章节必须是正整数
   - 文件后缀默认为 "name"
   - 如果文件已存在会自动跳过

2. Summary合并
   - 统计所有卷目录
   - 合并章节为一个完整文件
   - 可选择是否重命名文件夹（加上字数后缀）
   - 可自定义导出格式（见参数配置）

3. 监控管理
   - 自动监控小说文件夹
   - 检测到最新章节被编写后自动新增2章
   - 每到2的倍数章节自动触发Summary
   - 日志可筛选查看数量

4. 自动卷管理
   - 创建新卷文件夹（点击「增加新卷」）
   - 用字数标签标记旧卷 [old_XXXX]
   - 用字数标签标记新卷 [new_XXXX]

【四、目录结构
=============
程序可以适应任意目录结构。自动初始化后会创建：

  your_folder/
  ├─ 1[new_0]/         ← 第一卷（含10个空章节）
  └─ NovelHelper.ini    ← 配置文件

【五、文件夹命名规则
====================
卷文件夹：数字[卷名]
  例如：1[第一卷]、2[第二卷]、1[new_0]、2[old_12345]

章节文件：数字第...txt
  例如：1第一章_name.txt、2第二章_.txt

【六、注意事项与风险
====================
⚠️  重要警告！

1. 文件备份
   - 使用前务必备份重要数据！
   - 误操作可能导致文件被覆盖

2. 不要随意删除文件
   - 监控运行时不要随意删除章节文件
   - 删除可能导致监控异常
   - 如需删除请先停止监控

3. 权限问题
   - 确保有文件夹和文件有读写权限
   - 选择具有适当权限的目录

4. Summary功能
   - 会生成合并后的文本文件
   - 重命名模式会修改文件夹名
   - 使用前确认备份！

5. 监控功能
   - 监控每15秒检查一次（可配置）
   - 自动新增领先2章（可配置）
   - 默认内容字数超过20字触发（可配置）

【七、多语言支持
===============
内置语言：简体中文、English、日本語

在「参数配置」标签页切换语言，然后保存并重启生效。
""",
        },
        'en_US': {
            'app_title': 'Novel Helper',
            'monitor_started': 'Monitor Started',
            'monitor_stopped': 'Monitor Stopped',
            'new_chapter_detected': 'New Chapter Detected',
            'chapter_updated': 'Chapter Updated',
            'new_folder_detected': 'New Folder Detected',
            'new_chapters_added': 'New Chapters Added',
            'empty_chapters_deleted': 'Empty Chapters Deleted',
            'old_volume_marked': 'Old Volume Marked',
            'new_volume_marked': 'New Volume Marked',
            'summary_triggered': 'Summary Triggered',
            'waiting_for_write': 'Waiting for Write',
            'active': 'Active',
            'new': 'New',
            'volume_word_count': 'Volume Word Count',
            'chapter_1': 'Chapter 1',
            'add_new_volume_btn': 'Add New Volume',
            'execute_summary': 'Execute Summary',
            'parameter_config': 'Parameter Configuration',
            'summary_merge_tool': 'Summary Merge Tool',
            'create_chapters': 'Create Chapters',
            'monitor_management': 'Monitor Management',
            'user_guide': 'User Guide',
            'create_runtime_env': '⚙ Create Runtime Environment',
            'exit_program': '⏻ Exit Program',
            'chapter_template_tool': '=== Chapter Template Creation Tool ===',
            'enter_start_chapter': 'Enter Start Chapter',
            'enter_end_chapter': 'Enter End Chapter',
            'enter_file_suffix': 'Enter File Name Suffix',
            'start_chapter_label': 'Start Chapter',
            'end_chapter_label': 'End Chapter',
            'file_suffix_label': 'File Suffix:',
            'start_creation': 'Start Creation',
            'select_directory': 'Select Directory',
            'save_directory_label': 'Save Directory:',
            'creation_result': 'Creation Result',
            'run_mode': 'Run Mode',
            'stats_only': '1. Statistics Only (No Rename)',
            'stats_and_rename': '2. Statistics And Rename',
            'progress': 'Progress',
            'execution_result': 'Execution Result',
            'param_config_page': '=== Parameter Configuration ===',
            'ui_size_config': 'UI Size Configuration',
            'base_font_size': 'Base Font Size',
            'title_font_size': 'Title Font Size',
            'log_font_size': 'Log Font Size',
            'initial_width': 'Initial Width',
            'initial_height': 'Initial Height',
            'min_width': 'Minimum Width',
            'min_height': 'Minimum Height',
            'ui_color_config': 'UI Color Configuration',
            'bg_color': 'Background Color',
            'fg_color': 'Font Color',
            'border_color': 'Border Color',
            'error_color': 'Error Color',
            'btn_bg': 'Button Background',
            'btn_hover': 'Button Hover',
            'input_bg': 'Input Background',
            'monitor_config': 'Monitor Configuration',
            'monitor_interval': 'Monitor Interval',
            'pregenerate_chapters': 'Pre-generate Chapters',
            'trigger_word_count': 'Trigger Word Count',
            'adaptive_config': 'Adaptive Configuration',
            'area_scale': 'Area Scale Factor',
            'height_scale': 'Height Scale Factor',
            'font_increment': 'Font Size Increment',
            'format_config': 'Format Configuration',
            'export_filename_format': 'Filename Format',
            'export_volume_format': 'Volume Title Format',
            'export_chapter_format': 'Chapter Title Format',
            'format_help_filename': 'Format: {num}=num, {cn.up.Chapter}=第壹佰伍拾叁章, {cn.low.Chapter}=第一百五十三章, {cn.num.Chapter}=第153章, {en.Chapter}=Chapter153, {jp.Chapter}=第一百五十三章, {name}=suffix',
            'format_help_volume': 'Format: {cn.up.Volume}=第壹佰伍拾叁卷, {cn.low.Volume}=第一百五十三卷, {cn.num.Volume}=第153卷, {en.Volume}=Volume153, {jp.Volume}=第一百五十三巻, {name}=name, {word_count}=count | _ between lang format and {name} auto to ·',
            'format_help_chapter': 'Format: {cn.up.Chapter}=第壹佰伍拾叁章, {cn.low.Chapter}=第一百五十三章, {cn.num.Chapter}=第153章, {en.Chapter}=Chapter153, {jp.Chapter}=第一百五十三章, {name}=suffix | _ between lang format and {name} auto to ·',
            'preview_color': 'Preview Color',
            'preview_font_size': 'Preview Font Size',
            'language_config': 'Language Configuration',
            'select_language': 'Select Language',
            'tip_change_language': 'Tip: Click Save & Apply after changing language',
            'save_and_apply': 'Save & Apply',
            'save_config': 'Save Configuration',
            'reload': 'Reload',
            'user_guide_page': '=== User Guide ===',
            'monitor_system': '=== Monitor Management System ===',
            'status_stopped': 'Status: Stopped',
            'status_running': 'Status: Running',
            'log_filter': 'Log Filter',
            'folder_status': 'Folder Status',
            'recent_operations': 'Recent Operations',
            'add_new_volume': '📖 Add New Volume',
            'start_monitor': 'Start Monitor',
            'stop_monitor': 'Stop Monitor',
            'confirm': 'Confirm',
            'cancel': 'Cancel',
            'confirm_exit': 'Confirm Exit',
            'exit_confirm_msg': 'Are you sure to exit? All threads will stop safely.',
            'env_not_initialized': 'Environment Not Initialized',
            'env_init_tip': 'Please click Create Runtime Environment first!',
            'success': 'Success',
            'error': 'Error',
            'warning': 'Warning',
            'config_saved_restart': 'Configuration saved! Restart to take effect.',
            'config_saved_applied': 'Configuration saved and applied!',
            'config_reloaded': 'Configuration reloaded!',
            'save_config_failed': 'Save configuration failed',
            'save_apply_failed': 'Save and apply failed',
            'reload_failed': 'Reload configuration failed',
            'confirm_creation': 'Confirm Creation',
            'creating_runtime_env': 'Creating runtime environment:',
            'create_folders': '1. Create /all, /novel, /log folders in current directory',
            'generate_templates': '2. Generate chapter templates in /all',
            'create_title_folder': '3. Create title folder in /novel',
            'copy_first_10': '4. Copy first 10 chapters to /novel/title/1',
            'continue_question': 'Continue?',
            'new_volume_created': 'New volume created',
            'add_volume_failed': 'Add new volume failed',
            'monitor_auto_process': 'Monitor is running, will process automatically.',
            'start_monitor_process': 'Please start monitor to process new volume.',
            'dir_not_exist': 'Directory does not exist',
            'dir_not_exist_question': 'Directory does not exist: {0}\nCreate it?',
            'create_question': 'Create?',
            'create_dir_failed': 'Create directory failed',
            'dir_not_writable': 'Directory not writable',
            'start_must_gt_zero': 'Start chapter must be greater than 0',
            'end_must_gt_zero': 'End chapter must be greater than 0',
            'start_lt_end': 'Start cannot be greater than end',
            'enter_valid_int': 'Please enter a valid positive integer',
            'skipped_existing': 'Skipped existing',
            'files_unit': 'files',
            'created_successfully': 'Successfully created',
            'clear_file_failed': 'Clear file failed',
            'read_failed': 'Read failed',
            'completed_cjk': 'Completed! CJK characters',
            'non_whitespace': 'Non-whitespace characters',
            'filter_all': 'All',
            'filter_recent_15': 'Recent 15',
            'filter_recent_30': 'Recent 30',
            'filter_recent_50': 'Recent 50',
            'start_new_program': 'Start New Program',
            'start_program_now_question': 'Start the new program now?',
            'create_env_failed': 'Failed to create runtime environment',
            'start_program_failed': 'Failed to start new program',
            'no_volume_folders': 'No volume folders found!',
            'folder_exists': 'Folder {0} already exists!',
            'generating_chapters': 'Generating {0} chapter templates...',
            'novel_dir': 'Novel Directory:',
            'select': 'Select...',
            'select_novel_directory': 'Select Novel Directory',
            'initialize_directory': 'Initialize Directory',
            'initialize_directory_msg': 'Directory is empty or no volume folders found. Auto-initialize?\n\nWill create:\n  - 1[new_0]/ (Volume 1)\n  - 10 empty chapters\n\nContinue?',
            'check_directory_failed': 'Check directory failed',
            'initialize_complete': 'Directory initialization complete!',
            'initialize_failed': 'Initialize directory failed',
            'help_content': """【一、Flexible Directory Selection
========================================
★ Program can be placed anywhere - no fixed directory structure required
★ Select any folder as your novel directory via GUI
★ Auto-initialization creates necessary structure in selected directory

【二、First Time Setup
=====================
1. Launch the program
2. Go to "Parameter Configuration" tab
3. Click "Select..." button next to "Novel Directory"
4. Choose your novel storage folder
5. If the folder is empty, click "Yes" to auto-initialize
6. Program will automatically create:
   - 1[new_0]/ (Volume 1 with 10 empty chapters)

【三、Function Description
==========================
1. Create Chapters
   - Used to create chapter template files in the novel directory
   - Start and end chapters must be positive integers
   - Default file suffix is "name"
   - Automatically skips existing files

2. Summary Merge
   - Statistics all volume directories
   - Merges chapters into a complete file
   - Can choose whether to rename folders (add word count suffix)
   - Customizable export format (see Parameter Configuration)

3. Monitor Management
   - Automatically monitors novel folders
   - Automatically adds 2 chapters when latest chapter is written
   - Auto-triggers Summary at every multiple of 2 chapter
   - Logs can be filtered by count

4. Auto Volume Management
   - Create new volume folders (click "Add New Volume")
   - Mark old volumes with word count tags [old_XXXX]
   - Mark new volumes with word count tags [new_XXXX]

【四、Directory Structure
========================
Program works with any directory. After auto-initialization:

  your_folder/
  ├─ 1[new_0]/         ← Volume 1 (with 10 empty chapters)
  └─ NovelHelper.ini    ← Configuration file

【五、Folder Naming Rules
==========================
Volume folders: number[volume name]
  Example: 1[Volume 1]、2[Volume 2]、1[new_0]、2[old_12345]

Chapter files: numberChapter...txt
  Example: 1Chapter_name.txt、2Chapter_.txt

【六、Notes and Risks
=====================
⚠️  Important Warning!

1. File Backup
   - Always backup important data before use!
   - Mistakes may overwrite files

2. Don't Delete Files Arbitrarily
   - Don't delete chapter files while monitor is running
   - Deletion may cause monitor anomalies
   - Stop monitor first if you need to delete

3. Permissions Issues
   - Ensure read/write permissions for folders and files
   - Choose a directory with proper permissions

4. Summary Function
   - Generates merged text file
   - Rename mode modifies folder names
   - Confirm backup before use!

5. Monitor Function
   - Monitor checks every 15 seconds (configurable)
   - Auto-adds 2 leading chapters (configurable)
   - Triggers when default content exceeds 20 words (configurable)

【七、Multi-Language Support
=============================
Built-in languages: English, 简体中文, 日本語

Switch language in "Parameter Configuration" tab, then save and restart.
""",
        },
        'ja_JP': {
            'app_title': '小説ヘルパー',
            'monitor_started': '監視開始',
            'monitor_stopped': '監視停止',
            'new_chapter_detected': '新規章検出',
            'chapter_updated': '章更新',
            'new_folder_detected': '新規フォルダ検出',
            'new_chapters_added': '新規章追加',
            'empty_chapters_deleted': '空章削除',
            'old_volume_marked': '旧巻マーク',
            'new_volume_marked': '新巻マーク',
            'summary_triggered': 'Summaryトリガー',
            'waiting_for_write': '書き込み待ち',
            'active': 'アクティブ',
            'new': '新規',
            'volume_word_count': '巻字数',
            'chapter_1': '第1章',
            'add_new_volume_btn': '新規巻追加',
            'execute_summary': 'Summary実行',
            'parameter_config': 'パラメータ設定',
            'summary_merge_tool': 'Summaryマージツール',
            'create_chapters': '章作成',
            'monitor_management': '監視管理',
            'user_guide': '使用説明',
            'create_runtime_env': '⚙ 実行環境作成',
            'exit_program': '⏻ プログラム終了',
            'chapter_template_tool': '=== 章テンプレート作成ツール ===',
            'enter_start_chapter': '開始章を入力',
            'enter_end_chapter': '終了章を入力',
            'enter_file_suffix': 'ファイル名接尾辞を入力',
            'start_chapter_label': '開始章',
            'end_chapter_label': '終了章',
            'file_suffix_label': 'ファイル接尾辞:',
            'start_creation': '作成開始',
            'select_directory': 'ディレクトリを選択',
            'save_directory_label': '保存ディレクトリ:',
            'creation_result': '作成結果',
            'run_mode': '実行モード',
            'stats_only': '1. 統計のみ（フォルダ名変更なし）',
            'stats_and_rename': '2. 統計してフォルダ名変更',
            'progress': '進捗',
            'execution_result': '実行結果',
            'param_config_page': '=== パラメータ設定 ===',
            'ui_size_config': 'UIサイズ設定',
            'base_font_size': '基本フォントサイズ',
            'title_font_size': 'タイトルフォントサイズ',
            'log_font_size': 'ログフォントサイズ',
            'initial_width': '初期幅',
            'initial_height': '初期高さ',
            'min_width': '最小幅',
            'min_height': '最小高さ',
            'ui_color_config': 'UI色設定',
            'bg_color': '背景色',
            'fg_color': 'フォント色',
            'border_color': 'ボーダー色',
            'error_color': 'エラー色',
            'btn_bg': 'ボタンバックグラウンド',
            'btn_hover': 'ボタンホバー',
            'input_bg': '入力框バックグラウンド',
            'monitor_config': '監視設定',
            'monitor_interval': '監視間隔',
            'pregenerate_chapters': '予生成章数',
            'trigger_word_count': 'トリガー文字数',
            'adaptive_config': '適応設定',
            'area_scale': '面積倍率',
            'height_scale': '高さ倍率',
            'font_increment': 'フォントサイズ増分',
            'format_config': 'フォーマット設定',
            'export_filename_format': 'ファイル名形式',
            'export_volume_format': '巻タイトル形式',
            'export_chapter_format': '章タイトル形式',
            'format_help_filename': '形式：{num}=数字、{cn.up.Chapter}=第壹佰伍拾叁章、{cn.low.Chapter}=第一百五十三章、{cn.num.Chapter}=第153章、{en.Chapter}=Chapter153、{jp.Chapter}=第一百五十三章、{name}=接尾辞',
            'format_help_volume': '形式：{cn.up.Volume}=第壹佰伍拾叁巻、{cn.low.Volume}=第一百五十三巻、{cn.num.Volume}=第153巻、{en.Volume}=Volume153、{jp.Volume}=第一百五十三巻、{name}=巻名、{word_count}=文字数 | _ は言語形式と{name}の間で自動的に·に変換',
            'format_help_chapter': '形式：{cn.up.Chapter}=第壹佰伍拾叁章、{cn.low.Chapter}=第一百五十三章、{cn.num.Chapter}=第153章、{en.Chapter}=Chapter153、{jp.Chapter}=第一百五十三章、{name}=接尾辞 | _ は言語形式と{name}の間で自動的に·に変換',
            'preview_color': 'プレビュー色',
            'preview_font_size': 'プレビューフォントサイズ',
            'language_config': '言語設定',
            'select_language': '言語を選択',
            'tip_change_language': 'ヒント：言語変更後は「保存して適用」をクリック',
            'save_and_apply': '保存して適用',
            'save_config': '設定を保存',
            'reload': '再読み込み',
            'user_guide_page': '=== 使用説明 ===',
            'monitor_system': '=== 監視管理システム ===',
            'status_stopped': '状態：停止',
            'status_running': '状態：実行中',
            'log_filter': 'ログフィルター',
            'folder_status': 'フォルダ状態',
            'recent_operations': '最近の操作',
            'add_new_volume': '📖 新規巻追加',
            'start_monitor': '監視開始',
            'stop_monitor': '監視停止',
            'confirm': '確認',
            'cancel': 'キャンセル',
            'confirm_exit': '終了確認',
            'exit_confirm_msg': '終了してもよろしいですか？全スレッドが安全に停止します。',
            'env_not_initialized': '環境未初期化',
            'env_init_tip': '「実行環境作成」ボタンをクリックしてください！',
            'success': '成功',
            'error': 'エラー',
            'warning': '警告',
            'config_saved_restart': '設定が保存されました！再起動後に有効になります。',
            'config_saved_applied': '設定が保存され適用されました！',
            'config_reloaded': '設定が再読み込みされました！',
            'save_config_failed': '設定の保存に失敗しました',
            'save_apply_failed': '保存と適用に失敗しました',
            'reload_failed': '再読み込みに失敗しました',
            'confirm_creation': '作成確認',
            'creating_runtime_env': '実行環境を作成中：',
            'create_folders': '1. 現在のディレクトリに /all, /novel, /log フォルダを作成',
            'generate_templates': '2. /all に章テンプレートを生成',
            'create_title_folder': '3. /novel に title フォルダを作成',
            'copy_first_10': '4. 最初の10章を /novel/title/1 にコピー',
            'continue_question': '続行しますか？',
            'new_volume_created': '新規巻を作成しました',
            'add_volume_failed': '新規巻の追加に失敗しました',
            'monitor_auto_process': '監視が実行中です。自動的に処理されます。',
            'start_monitor_process': '監視を開始して新規巻を処理してください。',
            'dir_not_exist': 'ディレクトリが存在しません',
            'dir_not_exist_question': 'ディレクトリが存在しません: {0}\n作成しますか？',
            'create_question': '作成しますか？',
            'create_dir_failed': 'ディレクトリの作成に失敗しました',
            'dir_not_writable': 'ディレクトリは書き込めません',
            'start_must_gt_zero': '開始章は0より大きくなければなりません',
            'end_must_gt_zero': '終了章は0より大きくなければなりません',
            'start_lt_end': '開始章は終了章より大きくできません',
            'enter_valid_int': '有効な正整数を入力してください',
            'skipped_existing': '既存をスキップ',
            'files_unit': 'ファイル',
            'created_successfully': '作成成功',
            'clear_file_failed': 'ファイルのクリアに失敗しました',
            'read_failed': '読み込みに失敗しました',
            'completed_cjk': '完成！CJK文字',
            'non_whitespace': '非空白文字',
            'filter_all': 'すべて',
            'filter_recent_15': '最近15件',
            'filter_recent_30': '最近30件',
            'filter_recent_50': '最近50件',
            'start_new_program': '新規プログラム起動',
            'start_program_now_question': '新規プログラムを起動しますか？',
            'create_env_failed': '実行環境作成に失敗しました',
            'start_program_failed': '新規プログラム起動に失敗しました',
            'no_volume_folders': '巻フォルダが見つかりません！',
            'folder_exists': 'フォルダ {0} が既に存在します！',
            'generating_chapters': '{0} 章テンプレートを生成中...',
            'novel_dir': '小説ディレクトリ:',
            'select': '選択...',
            'select_novel_directory': '小説ディレクトリを選択',
            'initialize_directory': 'ディレクトリを初期化',
            'initialize_directory_msg': 'ディレクトリが空か巻フォルダが見つかりません。自動的に初期化しますか？\n\n作成内容：\n  - 1[new_0]/（第一巻）\n  - 10個の空き章\n\n続行しますか？',
            'check_directory_failed': 'ディレクトリのチェックに失敗しました',
            'initialize_complete': 'ディレクトリの初期化が完了しました！',
            'initialize_failed': 'ディレクトリの初期化に失敗しました',
            'help_content': """一、柔軟なディレクトリ選択
==========================================
★ プログラムは任意の位置に配置可能 - 固定ディレクトリ構造不要
★ GUIを通じて任意フォルダを小説ディレクトリとして選択
★ 自動初期化を選択ディレクトリに作成

二、初めての設定手順
=====================
1. プログラムを起動
2.「パラメータ設定」タブを開く
3.「小説ディレクトリ」の横の「選択...」ボタンをクリック
4. 小説を保存するフォルダを選択
5. フォルダが空の場合、プログラムは自動初期化を尋ねます
6.「はい」を選択すると自動作成：
   - 1[new_0]/（第一巻、10個の空の章を含む）

三、機能説明
=============
1. 章作成
   - 小説ディレクトリに章テンプレートファイルを作成するために使用
   - 開始章と終了章は正の整数である必要があります
   - ファイル接尾辞のデフォルトは "name"
   - ファイルが既に存在する場合は自動的にスキップ

2. Summaryマージ
   - すべての巻ディレクトリを統計
   - 章を1つの完全なファイルにマージ
   - フォルダ名を変更するかどうかを選択可能（文字数接尾辞を追加）
   - カスタムエクスポート形式（パラメータ設定を参照）

3. 監視管理
   - 小説フォルダを自動監視
   - 最新の章が書かれたことを検出すると自動的に2章を追加
   - 2の倍数の章ごとに自動的にSummaryをトリガー
   - ログは件数でフィルタリング可能

4. 自動巻管理
   - 新規巻フォルダを作成（「新規巻追加」をクリック）
   - 旧巻を文字数タグでマーク [old_XXXX]
   - 新巻を文字数タグでマーク [new_XXXX]

四、ディレクトリ構造
====================
プログラムは任意ディレクトリ対応。自動初期化後：

  your_folder/
  ├─ 1[new_0]/         ← 第一巻（10個の空の章を含む）
  └─ NovelHelper.ini    ← 設定ファイル

五、フォルダ命名規則
====================
巻フォルダ：数字[巻名]
  例：1[第一巻]、2[第二巻]、1[new_0]、2[old_12345]

章ファイル：数字第...txt
  例：1第一章_name.txt、2第二章_.txt

六、注意事項とリスク
====================
⚠️  重要な警告！

1. ファイルバックアップ
   - 使用前に必ず重要なデータをバックアップしてください！
   - 誤操作によりファイルが上書きされる可能性があります

2. ファイルを勝手に削除しないでください
   - 監視実行中は章ファイルを勝手に削除しないでください
   - 削除により監視が異常になる可能性があります
   - 削除が必要な場合は先に監視を停止してください

3. 権限の問題
   - フォルダとファイルの読み書き権限があることを確認してください
   - 適切な権限を持つディレクトリを選択してください

4. Summary機能
   - マージされたテキストファイルを生成
   - 名前変更モードはフォルダ名を変更します
   - 使用前にバックアップを確認してください！

5. 監視機能
   - 監視は15秒ごとにチェック（設定可能）
   - 自動的に2章先まで追加（設定可能）
   - デフォルトの内容が20文字を超えるとトリガー（設定可能）

七、多言語サポート
==================
組み込み言語：English、简体中文、日本語

「パラメータ設定」タブで言語を切り替え、保存して再起動すると有効になります。
""",
        }
    }
    
    @classmethod
    def generate_ini_file(cls):
        """只创建基础配置文件，翻译内容已硬编码在代码中"""
        config_path = ConfigManager.get_config_file_path()
        if os.path.exists(config_path):
            return
        
        # 只创建基础配置，翻译内容不需要写入INI文件
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write('[UI]\n')
            f.write('base_font_size = 20\n')
            f.write('base_title_size = 32\n')
            f.write('initial_width = 1006\n')
            f.write('initial_height = 975\n')
            f.write('min_width = 800\n')
            f.write('min_height = 600\n')
            f.write('log_font_size = 16\n')
            f.write('bg_color = #0D0208\n')
            f.write('fg_color = #00FF41\n')
            f.write('border_color = #00FF41\n')
            f.write('accent_color = #00FF41\n')
            f.write('error_color = #FF4444\n')
            f.write('btn_bg_color = #001100\n')
            f.write('btn_hover_color = #003300\n')
            f.write('input_bg_color = #001100\n\n')
            f.write('[Monitor]\n')
            f.write('check_interval = 15\n')
            f.write('max_ahead_chapters = 2\n')
            f.write('min_word_count = 20\n')
            f.write('novel_dir = \n\n')
            f.write('[Adaptive]\n')
            f.write('area_scale_factor = 2\n')
            f.write('height_scale_factor = 1.2\n')
            f.write('font_increase = 4\n\n')
            f.write('[Environment]\n')
            f.write('init_chapter_count = 2000\n')
            f.write('init_copy_count = 10\n')
            f.write('pending_delete = 0\n\n')
            f.write('[Language]\n')
            f.write('current = zh_CN\n')
    
    @classmethod
    def load_available_languages(cls):
        cls._available_languages = list(cls.DEFAULT_TRANSLATIONS.keys())
        return cls._available_languages
    
    @classmethod
    def get_current_language(cls):
        if cls._current_lang is None:
            cls._current_lang = ConfigManager.get('Language', 'current', fallback='zh_CN')
        return cls._current_lang
    
    @classmethod
    def set_current_language(cls, lang_code):
        cls._current_lang = lang_code
        ConfigManager.set('Language', 'current', lang_code)
        cls._translations = {}
    
    @classmethod
    def get_available_languages(cls):
        if not cls._available_languages:
            cls.load_available_languages()
        return cls._available_languages
    
    @classmethod
    def get_translation(cls, key):
        current_lang = cls.get_current_language()
        if current_lang in cls.DEFAULT_TRANSLATIONS:
            if key in cls.DEFAULT_TRANSLATIONS[current_lang]:
                return cls.DEFAULT_TRANSLATIONS[current_lang][key]
        config = ConfigManager.load_config()
        section = f'Language_{current_lang}'
        if config.has_section(section):
            if config.has_option(section, key):
                return config.get(section, key)
        return key
    
    @classmethod
    def tr(cls, key):
        return cls.get_translation(key)


class MonitorThread(QThread):
    update_signal = pyqtSignal(dict, list)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.folder_states = {}
        self.folder_mtimes = {}
        self.last_summary_chapter = {}
        self.messages = []
        self.file_cache = {}
    
    def get_check_interval(self):
        return ConfigManager.get_int('Monitor', 'check_interval', fallback=15)
    
    def get_max_ahead_chapters(self):
        return ConfigManager.get_int('Monitor', 'max_ahead_chapters', fallback=2)
    
    def get_min_word_count(self):
        return ConfigManager.get_int('Monitor', 'min_word_count', fallback=20)
    
    def run(self):
        self.init_folders()
        while self.running:
            self.check_folders()
            self.update_signal.emit(self.folder_states, self.messages)
            check_interval = self.get_check_interval()
            for _ in range(check_interval * 10):
                if not self.running:
                    break
                time.sleep(0.1)
    
    def init_folders(self):
        try:
            folders = sorted(os.listdir(get_novel_dir()), key=lambda x: (FileManager.get_volume_number(x) is None, FileManager.get_volume_number(x) or float('inf')))
            for folder_name in folders:
                folder_path = os.path.join(get_novel_dir(), folder_name)
                if not os.path.isdir(folder_path):
                    continue
                
                if not FileManager.is_numeric_volume_folder(folder_name) or FileManager.is_old_volume(folder_name):
                    continue
                
                latest = FileManager.find_latest_chapter(folder_path)
                if latest is None:
                    continue
                
                current_max = latest[0]
                latest_file = latest[1]
                latest_file_path = os.path.join(folder_path, latest_file)
                
                current_word_count, _ = FileManager.get_word_count(latest_file_path)
                current_is_default = FileManager.is_default_content(latest_file_path)
                
                self.folder_states[folder_name] = {
                    'current_max': current_max,
                    'word_count': current_word_count,
                    'is_default': current_is_default,
                    'status': '初始化',
                    'ahead_count': 0,
                    'files': FileManager.get_folder_files(folder_path),
                    'latest_file': latest_file
                }
                self.folder_mtimes[folder_name] = FileManager.get_file_mtime(latest_file_path)
                self.last_summary_chapter[folder_name] = current_max
                self.file_cache[folder_name] = self.folder_states[folder_name]['files']
                
                min_word_count = self.get_min_word_count()
                max_ahead_chapters = self.get_max_ahead_chapters()
                if not current_is_default and current_word_count > min_word_count:
                    added = FileManager.ensure_ahead_chapters_internal(folder_name, folder_path, current_max, self.messages, max_ahead_chapters)
                    self.folder_states[folder_name]['ahead_count'] = added
                    self.folder_states[folder_name]['status'] = '就绪'
                else:
                    self.folder_states[folder_name]['status'] = '等待写入'
        except Exception as e:
            logger.error(f"初始化文件夹失败: {e}")
    
    def stop(self):
        self.running = False
    
    def check_folders(self):
        try:
            folders = sorted(os.listdir(get_novel_dir()), key=lambda x: (FileManager.get_volume_number(x) is None, FileManager.get_volume_number(x) or float('inf')))
            
            processed_new_folder = False
            max_ahead_chapters = self.get_max_ahead_chapters()
            
            # 先检查是否有简单数字命名的新文件夹（可能是空的）
            for folder_name in folders:
                folder_path = os.path.join(get_novel_dir(), folder_name)
                if not os.path.isdir(folder_path):
                    continue
                folder_num = FileManager.get_volume_number(folder_name)
                
                # 条件：简单数字命名（没有[xxx]后缀）
                if folder_num and not ('[' in folder_name and ']' in folder_name):
                    if self.process_new_volume_folder(folder_name, folder_path, folder_num, max_ahead_chapters):
                        processed_new_folder = True
            
            # 重新获取文件夹列表，因为重命名了
            if processed_new_folder:
                folders = sorted(os.listdir(get_novel_dir()), key=lambda x: (FileManager.get_volume_number(x) is None, FileManager.get_volume_number(x) or float('inf')))
            # 正常处理文件夹
            for folder_name in folders:
                if not self.running:
                    break
                folder_path = os.path.join(get_novel_dir(), folder_name)
                if not os.path.isdir(folder_path):
                    continue
                
                if not FileManager.is_numeric_volume_folder(folder_name) or FileManager.is_old_volume(folder_name):
                    continue
                
                latest = FileManager.find_latest_chapter(folder_path)
                if latest is None:
                    continue
                
                current_max = latest[0]
                latest_file = latest[1]
                latest_file_path = os.path.join(folder_path, latest_file)
                
                current_mtime = FileManager.get_file_mtime(latest_file_path)
                current_word_count, _ = FileManager.get_word_count(latest_file_path)
                current_is_default = FileManager.is_default_content(latest_file_path)
                
                if folder_name not in self.folder_states:
                    logger.info(f"发现新文件夹状态: {folder_name}")
                    files = FileManager.get_folder_files(folder_path)
                    self.folder_states[folder_name] = {
                        'current_max': current_max,
                        'word_count': current_word_count,
                        'is_default': current_is_default,
                        'status': '新增',
                        'ahead_count': 0,
                        'files': files,
                        'latest_file': latest_file
                    }
                    self.folder_mtimes[folder_name] = current_mtime
                    self.last_summary_chapter[folder_name] = current_max
                    self.file_cache[folder_name] = files
                    self.messages.append(f"[NEW] 发现新文件夹: {folder_name}")
                    continue
                
                state = self.folder_states[folder_name]
                
                if state['current_max'] != current_max:
                    self.messages.append(f"[CHG] {folder_name}: 检测到新章节 - 第{current_max}章")
                    state['current_max'] = current_max
                
                if self.folder_mtimes.get(folder_name, 0) != current_mtime:
                    self.messages.append(f"[UPD] {folder_name}: 第{current_max}章已更新 (字数: {current_word_count})")
                    self.folder_mtimes[folder_name] = current_mtime
                
                state['word_count'] = current_word_count
                state['is_default'] = current_is_default
                
                current_files = FileManager.get_folder_files(folder_path)
                if current_files != self.file_cache.get(folder_name, []):
                    state['files'] = current_files
                    self.file_cache[folder_name] = current_files
                
                state['latest_file'] = latest_file
                
                min_word_count = self.get_min_word_count()
                max_ahead_chapters = self.get_max_ahead_chapters()
                if not current_is_default and current_word_count > min_word_count:
                    state['status'] = '活跃'
                    added = FileManager.ensure_ahead_chapters_internal(folder_name, folder_path, current_max, self.messages, max_ahead_chapters)
                    if added > 0:
                        state['ahead_count'] = added
                    
                    prev_chapter = self.last_summary_chapter.get(folder_name, 0)
                    if current_max > prev_chapter and current_max % 2 == 0:
                        self.last_summary_chapter[folder_name] = current_max
                        self.messages.append(f"[SUM] {folder_name}: 触发Summary（第{current_max}章）")
                else:
                    state['status'] = '等待写入'
                
                if len(self.messages) > 50:
                    self.messages = self.messages[-50:]
        except Exception as e:
            logger.error(f"监控线程错误: {e}")
    
    def process_new_volume_folder(self, folder_name, folder_path, folder_num, max_ahead_chapters):
        """处理新卷文件夹的独立方法"""
        try:
            # 检查新文件夹是否为空
            new_folder_files = FileManager.get_folder_files(folder_path)
            
            prev_num = folder_num - 1
            if prev_num <= 0:
                return False
            
            # 查找上一卷
            prev_folder = None
            for f in os.listdir(get_novel_dir()):
                f_path = os.path.join(get_novel_dir(), f)
                if os.path.isdir(f_path):
                    f_num = FileManager.get_volume_number(f)
                    if f_num == prev_num:
                        prev_folder = f_path
                        break
            
            if not prev_folder:
                logger.warning(f"未找到上一卷")
                return False
            
            # 步骤1：找到上一卷中有内容和无内容的章节
            min_word_count = ConfigManager.get_int('Monitor', 'min_word_count', fallback=20)
            prev_files = FileManager.get_folder_files(prev_folder)
            
            real_latest_num = 0
            real_latest_file = None
            empty_chapters = []
            
            for f in prev_files:
                f_path = os.path.join(prev_folder, f)
                wc, _ = FileManager.get_word_count(f_path)
                is_default = FileManager.is_default_content(f_path)
                f_num = FileManager.get_chapter_number(f)
                
                if not is_default and wc > min_word_count:
                    if f_num and f_num > real_latest_num:
                        real_latest_num = f_num
                        real_latest_file = f
                elif is_default or wc <= min_word_count:
                    if f_num:
                        empty_chapters.append((f_num, f, f_path))
            
            # 步骤2：删除上一卷中的无内容章节
            for empty_num, empty_name, empty_path in empty_chapters:
                try:
                    os.remove(empty_path)
                    self.messages.append(f"[DEL] {prev_num}卷: 删除无内容章节 {empty_num}")
                except Exception as e:
                    logger.warning(f"删除无内容章节失败 {empty_path}: {e}")
            
            # 步骤3：确定从哪一章开始复制
            # 如果有有内容的章节，从那里+1开始；否则从上一卷最新章节+1开始
            prev_latest = FileManager.find_latest_chapter(prev_folder)
            start_chapter = real_latest_num if real_latest_num > 0 else (prev_latest[0] if prev_latest else 0)
            if start_chapter == 0:
                logger.warning("无法确定开始章节，跳过")
                return False
            
            # 步骤4：计算上一卷的总字数（只计算有内容的）
            total_words = 0
            prev_files_after_del = FileManager.get_folder_files(prev_folder)
            for f in prev_files_after_del:
                f_path = os.path.join(prev_folder, f)
                wc, _ = FileManager.get_word_count(f_path)
                total_words += wc
            
            # 步骤5：从 start_chapter+1 开始创建 max_ahead_chapters 个空章节
            added_count = 0
            for add_num in range(start_chapter + 1, start_chapter + max_ahead_chapters + 1):
                dest_filename = FileManager.generate_chapter_name(add_num, "", include_prefix=True).rstrip('_') + '_.txt'
                dest_path = os.path.join(folder_path, dest_filename)
                
                try:
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    with open(dest_path, 'w', encoding='utf-8') as f:
                        f.write('')
                    added_count += 1
                    self.messages.append(f"[NEW] {folder_name}: 新增第{add_num}章")
                except Exception as e:
                    logger.error(f"创建章节失败 {add_num}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # 步骤6：重命名上一卷为 old
            prev_name = os.path.basename(prev_folder)
            if '[new_' in prev_name:
                try:
                    old_name = re.sub(r'\[new_(\d+)\]$', f'[old_{total_words}]', prev_name)
                    new_path = os.path.join(get_novel_dir(), old_name)
                    os.rename(prev_folder, new_path)
                    self.messages.append(f"[OLD] 自动标记旧卷: {prev_name} -> {old_name}")
                    # 移除旧卷状态
                    if prev_name in self.folder_states:
                        del self.folder_states[prev_name]
                    if prev_name in self.folder_mtimes:
                        del self.folder_mtimes[prev_name]
                    if prev_name in self.last_summary_chapter:
                        del self.last_summary_chapter[prev_name]
                    if prev_name in self.file_cache:
                        del self.file_cache[prev_name]
                except Exception as e:
                    logger.warning(f"自动标记旧卷失败: {e}")
            
            # 步骤7：统计新卷字数并重命名为 [new_字数]
            new_folder_word_count = 0
            new_files = FileManager.get_folder_files(folder_path)
            for f in new_files:
                f_path = os.path.join(folder_path, f)
                wc, _ = FileManager.get_word_count(f_path)
                new_folder_word_count += wc
            
            # 步骤8：重命名当前卷为 new
            new_folder_final_name = f"{folder_num}[new_{new_folder_word_count}]"
            new_folder_final_path = os.path.join(get_novel_dir(), new_folder_final_name)
            try:
                os.rename(folder_path, new_folder_final_path)
                self.messages.append(f"[NEW] 自动标记新卷: {folder_name} -> {new_folder_final_name}")
                return True
            except Exception as e:
                logger.warning(f"自动标记新卷失败: {e}")
                return False
            
        except Exception as e:
            logger.error(f"处理新卷文件夹失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

STYLE = """
QWidget {
    background-color: #0D0208;
    color: #00FF41;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 18px;
}
QMainWindow {
    background-color: #0D0208;
}
QLabel {
    color: #00FF41;
    border: none;
    font-size: 18px;
}
QPushButton {
    background-color: #001100;
    color: #00FF41;
    border: 2px solid #00FF41;
    padding: 12px 24px;
    font-family: "Consolas", "Courier New", monospace;
    font-weight: bold;
    font-size: 18px;
}
QPushButton:hover {
    background-color: #003300;
    border: 2px solid #00FF00;
}
QPushButton:pressed {
    background-color: #00FF41;
    color: #0D0208;
}
QPushButton:disabled {
    color: #005500;
    border-color: #005500;
}
QLineEdit {
    background-color: #001100;
    color: #00FF41;
    border: 2px solid #00FF41;
    padding: 8px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 18px;
}
QLineEdit:focus {
    border: 2px solid #00FF00;
}
QTextEdit {
    background-color: #001100;
    color: #00FF41;
    border: 2px solid #00FF41;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 16px;
}
QProgressBar {
    background-color: #001100;
    border: 2px solid #00FF41;
    text-align: center;
    color: #00FF41;
}
QProgressBar::chunk {
    background-color: #00FF41;
}
QTabWidget::pane {
    border: 2px solid #00FF41;
    background-color: #0D0208;
    padding: 0px;
}
QTabWidget > QWidget {
    padding: 0px;
}
QTabBar::tab {
    background-color: #001100;
    color: #00FF41;
    border: 2px solid #00FF41;
    padding: 8px 16px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #00FF41;
    color: #0D0208;
}
QTabBar::tab:hover {
    background-color: #003300;
}
QRadioButton {
    color: #00FF41;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #00FF41;
    border-radius: 0px;
}
QRadioButton::indicator:checked {
    background-color: #00FF41;
}
QGroupBox {
    border: 2px solid #00FF41;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
}
QGroupBox::title {
    color: #00FF41;
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QScrollBar:vertical {
    background: #001100;
    border: 1px solid #00FF41;
    width: 12px;
}
QScrollBar::handle:vertical {
    background: #00FF41;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QSplitter::handle {
    background-color: #00FF41;
}
QSplitter::handle:hover {
    background-color: #00FF00;
}
QSplitter::handle:pressed {
    background-color: #FFFF00;
}
QComboBox {
    background-color: #001100;
    color: #00FF41;
    border: 2px solid #00FF41;
    padding: 5px;
}
QComboBox QAbstractItemView {
    background-color: #001100;
    color: #00FF41;
    selection-background-color: #003300;
}
"""

class NovelHelper(QMainWindow):
    def __init__(self):
        super().__init__()
        self.monitor_thread = None
        self.all_widgets = []
        self.language_widgets = {}
        self.load_config_values()
        FileManager.set_language(LanguageManager.get_current_language())
        self.current_area_level = 0
        self.current_height_level = 0
        self.all_messages = []
        self.settings = QSettings("NovelHelper", "NovelHelper")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.was_minimized = False
        self.installEventFilter(self)
        self.init_ui()
        self.load_settings()
        self.apply_adaptive(0, 0)
        self.setWindowTitle(LanguageManager.tr("app_title"))
        logger.info("NovelHelper 启动成功")
    
    def update_format_preview(self):
        filename_fmt = self.config_export_format.text().strip()
        if filename_fmt:
            try:
                preview = FileManager._format_chapter(filename_fmt, 3, "name") + ".txt"
                self.config_export_format_preview.setText(f"预览: {preview}")
            except Exception:
                self.config_export_format_preview.setText("格式错误")
        else:
            self.config_export_format_preview.setText("")

        vol_fmt = self.config_export_volume_format.text().strip()
        if vol_fmt:
            try:
                preview = FileManager._format_export(vol_fmt, 1, "潜龙在渊", 37523)
                self.config_export_volume_preview.setText(f"预览: {preview}")
            except Exception:
                self.config_export_volume_preview.setText("格式错误")
        else:
            self.config_export_volume_preview.setText("")

        chapter_fmt = self.config_export_chapter_format.text().strip()
        if chapter_fmt:
            try:
                preview = FileManager._format_export(chapter_fmt, 3, "回家")
                self.config_export_chapter_preview.setText(f"预览: {preview}")
            except Exception:
                self.config_export_chapter_preview.setText("格式错误")
        else:
            self.config_export_chapter_preview.setText("")

    def update_preview_style(self):
        color = self.config_preview_color.text().strip() or "#FFFFFF"
        font_size = self.config_preview_font_size.value()
        style = f"color: {color}; font-size: {font_size}px; font-weight: bold;"
        self.config_export_format_preview.setStyleSheet(style)
        self.config_export_volume_preview.setStyleSheet(style)
        self.config_export_chapter_preview.setStyleSheet(style)

    def update_ui_language(self):
        self.setWindowTitle(LanguageManager.tr("app_title"))
        self.btn_create_env.setText(LanguageManager.tr("create_runtime_env"))
        self.btn_exit.setText(LanguageManager.tr("exit_program"))
        
        self.tabs.setTabText(0, LanguageManager.tr("create_chapters"))
        self.tabs.setTabText(1, LanguageManager.tr("summary_merge_tool"))
        self.tabs.setTabText(2, LanguageManager.tr("monitor_management"))
        self.tabs.setTabText(3, LanguageManager.tr("parameter_config"))
        self.tabs.setTabText(4, LanguageManager.tr("user_guide"))
        
        if hasattr(self, 'create_tab_title'):
            self.create_tab_title.setText(LanguageManager.tr("chapter_template_tool"))
        if hasattr(self, 'create_start_label'):
            self.create_start_label.setText(LanguageManager.tr("start_chapter_label"))
        if hasattr(self, 'start_chapter'):
            self.start_chapter.setPlaceholderText(LanguageManager.tr("enter_start_chapter"))
        if hasattr(self, 'create_end_label'):
            self.create_end_label.setText(LanguageManager.tr("end_chapter_label"))
        if hasattr(self, 'end_chapter'):
            self.end_chapter.setPlaceholderText(LanguageManager.tr("enter_end_chapter"))
        if hasattr(self, 'create_suffix_label'):
            self.create_suffix_label.setText(LanguageManager.tr("file_suffix_label"))
        if hasattr(self, 'name_suffix'):
            self.name_suffix.setPlaceholderText(LanguageManager.tr("enter_file_suffix"))
        if hasattr(self, 'create_savedir_label'):
            self.create_savedir_label.setText(LanguageManager.tr("save_directory_label"))
        if hasattr(self, 'create_dir_btn'):
            self.create_dir_btn.setText(LanguageManager.tr("select_directory"))
        if hasattr(self, 'create_result_label'):
            self.create_result_label.setText(LanguageManager.tr("creation_result"))
        if hasattr(self, 'create_btn'):
            self.create_btn.setText(LanguageManager.tr("start_creation"))
        
        if hasattr(self, 'summary_tab_title'):
            self.summary_tab_title.setText(LanguageManager.tr("summary_merge_tool"))
        if hasattr(self, 'summary_mode_group'):
            self.summary_mode_group.setTitle(LanguageManager.tr("run_mode"))
        if hasattr(self, 'mode1'):
            self.mode1.setText(LanguageManager.tr("stats_only"))
        if hasattr(self, 'mode2'):
            self.mode2.setText(LanguageManager.tr("stats_and_rename"))
        if hasattr(self, 'summary_progress_label'):
            self.summary_progress_label.setText(LanguageManager.tr("progress"))
        if hasattr(self, 'summary_result_label'):
            self.summary_result_label.setText(LanguageManager.tr("execution_result"))
        if hasattr(self, 'summary_btn_run'):
            self.summary_btn_run.setText(LanguageManager.tr("execute_summary"))
        
        if hasattr(self, 'monitor_tab_title'):
            self.monitor_tab_title.setText(LanguageManager.tr("monitor_system"))
        if hasattr(self, 'btn_start'):
            self.btn_start.setText(LanguageManager.tr("start_monitor"))
        if hasattr(self, 'btn_stop'):
            self.btn_stop.setText(LanguageManager.tr("stop_monitor"))
        if hasattr(self, 'btn_add_volume'):
            self.btn_add_volume.setText(LanguageManager.tr("add_new_volume"))
        if hasattr(self, 'status_label'):
            if self.status_label.text().startswith("Status:") or self.status_label.text().startswith("状态:"):
                self.status_label.setText(LanguageManager.tr("status_stopped"))
        if hasattr(self, 'monitor_filter_label'):
            self.monitor_filter_label.setText(LanguageManager.tr("log_filter"))
        if hasattr(self, 'filter_combo'):
            current_data = self.filter_combo.itemData(self.filter_combo.currentIndex())
            self.filter_combo.clear()
            self.filter_combo.addItem(LanguageManager.tr("filter_all"), "all")
            self.filter_combo.addItem(LanguageManager.tr("filter_recent_15"), "15")
            self.filter_combo.addItem(LanguageManager.tr("filter_recent_30"), "30")
            self.filter_combo.addItem(LanguageManager.tr("filter_recent_50"), "50")
            for i in range(self.filter_combo.count()):
                if self.filter_combo.itemData(i) == current_data:
                    self.filter_combo.setCurrentIndex(i)
                    break
        if hasattr(self, 'monitor_folder_status_label'):
            self.monitor_folder_status_label.setText(LanguageManager.tr("folder_status"))
        if hasattr(self, 'monitor_recent_label'):
            self.monitor_recent_label.setText(LanguageManager.tr("recent_operations"))
        
        if hasattr(self, 'config_tab_title'):
            self.config_tab_title.setText(LanguageManager.tr("param_config_page"))
        if hasattr(self, 'config_ui_group'):
            self.config_ui_group.setTitle(LanguageManager.tr("ui_size_config"))
        if hasattr(self, 'config_base_font_label'):
            self.config_base_font_label.setText(LanguageManager.tr("base_font_size"))
        if hasattr(self, 'config_title_font_label'):
            self.config_title_font_label.setText(LanguageManager.tr("title_font_size"))
        if hasattr(self, 'config_log_font_label'):
            self.config_log_font_label.setText(LanguageManager.tr("log_font_size"))
        if hasattr(self, 'config_initial_width_label'):
            self.config_initial_width_label.setText(LanguageManager.tr("initial_width"))
        if hasattr(self, 'config_initial_height_label'):
            self.config_initial_height_label.setText(LanguageManager.tr("initial_height"))
        if hasattr(self, 'config_min_width_label'):
            self.config_min_width_label.setText(LanguageManager.tr("min_width"))
        if hasattr(self, 'config_min_height_label'):
            self.config_min_height_label.setText(LanguageManager.tr("min_height"))
        if hasattr(self, 'config_color_group'):
            self.config_color_group.setTitle(LanguageManager.tr("ui_color_config"))
        if hasattr(self, 'config_bg_color_label'):
            self.config_bg_color_label.setText(LanguageManager.tr("bg_color"))
        if hasattr(self, 'config_fg_color_label'):
            self.config_fg_color_label.setText(LanguageManager.tr("fg_color"))
        if hasattr(self, 'config_border_color_label'):
            self.config_border_color_label.setText(LanguageManager.tr("border_color"))
        if hasattr(self, 'config_error_color_label'):
            self.config_error_color_label.setText(LanguageManager.tr("error_color"))
        if hasattr(self, 'config_btn_bg_label'):
            self.config_btn_bg_label.setText(LanguageManager.tr("btn_bg"))
        if hasattr(self, 'config_btn_hover_label'):
            self.config_btn_hover_label.setText(LanguageManager.tr("btn_hover"))
        if hasattr(self, 'config_input_bg_label'):
            self.config_input_bg_label.setText(LanguageManager.tr("input_bg"))
        if hasattr(self, 'config_monitor_group'):
            self.config_monitor_group.setTitle(LanguageManager.tr("monitor_config"))
        if hasattr(self, 'config_check_interval_label'):
            self.config_check_interval_label.setText(LanguageManager.tr("monitor_interval"))
        if hasattr(self, 'config_max_ahead_label'):
            self.config_max_ahead_label.setText(LanguageManager.tr("pregenerate_chapters"))
        if hasattr(self, 'config_min_word_label'):
            self.config_min_word_label.setText(LanguageManager.tr("trigger_word_count"))
        if hasattr(self, 'config_adaptive_group'):
            self.config_adaptive_group.setTitle(LanguageManager.tr("adaptive_config"))
        if hasattr(self, 'config_area_scale_label'):
            self.config_area_scale_label.setText(LanguageManager.tr("area_scale"))
        if hasattr(self, 'config_height_scale_label'):
            self.config_height_scale_label.setText(LanguageManager.tr("height_scale"))
        if hasattr(self, 'config_font_increase_label'):
            self.config_font_increase_label.setText(LanguageManager.tr("font_increment"))
        if hasattr(self, 'config_format_group'):
            self.config_format_group.setTitle(LanguageManager.tr("format_config"))
        if hasattr(self, 'config_export_format_label'):
            self.config_export_format_label.setText(LanguageManager.tr("export_filename_format"))
        if hasattr(self, 'config_export_volume_format_label'):
            self.config_export_volume_format_label.setText(LanguageManager.tr("export_volume_format"))
        if hasattr(self, 'config_export_chapter_format_label'):
            self.config_export_chapter_format_label.setText(LanguageManager.tr("export_chapter_format"))
        if hasattr(self, 'config_export_format_help'):
            self.config_export_format_help.setText(LanguageManager.tr("format_help_filename"))
        if hasattr(self, 'config_export_volume_help'):
            self.config_export_volume_help.setText(LanguageManager.tr("format_help_volume"))
        if hasattr(self, 'config_export_chapter_help'):
            self.config_export_chapter_help.setText(LanguageManager.tr("format_help_chapter"))
        if hasattr(self, 'config_preview_color_label'):
            self.config_preview_color_label.setText(LanguageManager.tr("preview_color"))
        if hasattr(self, 'config_preview_font_size_label'):
            self.config_preview_font_size_label.setText(LanguageManager.tr("preview_font_size"))
        if hasattr(self, 'config_language_group'):
            self.config_language_group.setTitle(LanguageManager.tr("language_config"))
        if hasattr(self, 'config_format_preview'):
            self.update_format_preview()
        if hasattr(self, 'config_language_label'):
            self.config_language_label.setText(LanguageManager.tr("select_language"))
        if hasattr(self, 'config_language_note'):
            self.config_language_note.setText(LanguageManager.tr("tip_change_language"))
        if hasattr(self, 'config_btn_save_apply'):
            self.config_btn_save_apply.setText(LanguageManager.tr("save_and_apply"))
        if hasattr(self, 'config_btn_save'):
            self.config_btn_save.setText(LanguageManager.tr("save_config"))
        if hasattr(self, 'config_btn_reload'):
            self.config_btn_reload.setText(LanguageManager.tr("reload"))
        
        if hasattr(self, 'help_tab_title'):
            self.help_tab_title.setText(LanguageManager.tr("user_guide_page"))
        if hasattr(self, 'help_text'):
            self.help_text.setText(LanguageManager.tr("help_content"))
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.WindowStateChange and obj == self:
            if self.windowState() & Qt.WindowMinimized:
                self.was_minimized = True
                self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
                self.show()
        return super().eventFilter(obj, event)
    
    def load_config_values(self):
        config = ConfigManager.load_config()
        self.base_font_size = config.getint('UI', 'base_font_size', fallback=20)
        self.base_title_size = config.getint('UI', 'base_title_size', fallback=32)
        initial_width = config.getint('UI', 'initial_width', fallback=1006)
        initial_height = config.getint('UI', 'initial_height', fallback=975)
        min_width = config.getint('UI', 'min_width', fallback=800)
        min_height = config.getint('UI', 'min_height', fallback=600)
        self.base_area = initial_width * initial_height
        self.base_height = initial_height
        self.initial_width = initial_width
        self.initial_height = initial_height
        self.min_width = min_width
        self.min_height = min_height
        self.area_scale_factor = config.getfloat('Adaptive', 'area_scale_factor', fallback=2.0)
        self.height_scale_factor = config.getfloat('Adaptive', 'height_scale_factor', fallback=1.2)
        self.font_increase = config.getint('Adaptive', 'font_increase', fallback=4)
        self.log_font_size = config.getint('UI', 'log_font_size', fallback=16)
        self.bg_color = config.get('UI', 'bg_color', fallback='#0D0208')
        self.fg_color = config.get('UI', 'fg_color', fallback='#00FF41')
        self.border_color = config.get('UI', 'border_color', fallback='#00FF41')
        self.accent_color = config.get('UI', 'accent_color', fallback='#00FF41')
        self.error_color = config.get('UI', 'error_color', fallback='#FF4444')
        self.btn_bg_color = config.get('UI', 'btn_bg_color', fallback='#001100')
        self.btn_hover_color = config.get('UI', 'btn_hover_color', fallback='#003300')
        self.input_bg_color = config.get('UI', 'input_bg_color', fallback='#001100')
    
    def load_settings(self):
        suffix = self.settings.value("name_suffix", "name")
        mode = self.settings.value("summary_mode", 2, type=int)
        if hasattr(self, 'name_suffix'):
            self.name_suffix.setText(suffix)
        if mode == 1 and hasattr(self, 'mode1'):
            self.mode1.setChecked(True)
        elif hasattr(self, 'mode2'):
            self.mode2.setChecked(True)
    
    def save_settings(self):
        if hasattr(self, 'name_suffix'):
            self.settings.setValue("name_suffix", self.name_suffix.text())
        if hasattr(self, 'mode1') and hasattr(self, 'mode2'):
            mode = 1 if self.mode1.isChecked() else 2
            self.settings.setValue("summary_mode", mode)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adaptive_scale()
    
    def adaptive_scale(self):
        width = self.width()
        height = self.height()
        current_area = width * height
        
        area_ratio = current_area / self.base_area
        height_ratio = height / self.base_height
        
        new_area_level = 0
        while area_ratio >= (self.area_scale_factor ** (new_area_level + 1)):
            new_area_level += 1
        
        new_height_level = 0
        while height_ratio >= (self.height_scale_factor ** (new_height_level + 1)):
            new_height_level += 1
        
        area_changed = new_area_level != self.current_area_level
        height_changed = new_height_level != self.current_height_level
        
        if area_changed:
            self.current_area_level = new_area_level
        if height_changed:
            self.current_height_level = new_height_level
        
        if area_changed or height_changed:
            self.apply_adaptive(self.current_area_level, self.current_height_level)
    
    def apply_adaptive(self, area_level, height_level):
        font_increase = self.font_increase * area_level
        text_size = self.base_font_size + font_increase
        title_size = self.base_title_size + font_increase
        base_padding = 12 + 4 * area_level
        btn_padding_h = 24 + 8 * area_level
        btn_padding_v = 12 + 4 * area_level
        input_padding = 8 + 3 * area_level
        log_text_size = self.log_font_size + font_increase
        
        font_scale_style = f"""
        QWidget {{
            font-size: {text_size}px;
        }}
        QLabel {{
            font-size: {text_size}px;
        }}
        QPushButton {{
            font-size: {text_size}px;
            padding: {btn_padding_v}px {btn_padding_h}px;
        }}
        QLineEdit {{
            font-size: {text_size}px;
            padding: {input_padding}px;
        }}
        QTextEdit {{
            font-size: {log_text_size}px;
        }}
        QRadioButton {{
            font-size: {text_size}px;
        }}
        QGroupBox {{
            font-size: {text_size}px;
        }}
        """
        combined_style = self.build_dynamic_style(font_scale_style)
        self.setStyleSheet(combined_style)
        
        for widget in self.all_widgets:
            if hasattr(widget, 'font_scale_factor'):
                widget.setStyleSheet(f"font-size: {title_size}px; font-weight: bold; padding: {int(8 + 3 * area_level)}px;")
        
        if hasattr(self, 'splitter') and hasattr(self, 'splitter_stretch'):
            scale = 1.3 ** area_level
            height_scale = 1.2 ** height_level
            for i in range(len(self.splitter_stretch)):
                self.splitter.setStretchFactor(i, int(self.splitter_stretch[i] * scale))
    
    def build_dynamic_style(self, extra_style=""):
        return f"""
QWidget {{
    background-color: {self.bg_color};
    color: {self.fg_color};
    font-family: "Consolas", "Courier New", monospace;
    font-size: {self.base_font_size}px;
}}
QMainWindow {{
    background-color: {self.bg_color};
}}
QLabel {{
    color: {self.fg_color};
    border: none;
    font-size: {self.base_font_size}px;
}}
QPushButton {{
    background-color: {self.btn_bg_color};
    color: {self.fg_color};
    border: 2px solid {self.border_color};
    padding: 12px 24px;
    font-family: "Consolas", "Courier New", monospace;
    font-weight: bold;
    font-size: {self.base_font_size}px;
}}
QPushButton:hover {{
    background-color: {self.btn_hover_color};
    border: 2px solid {self.accent_color};
}}
QPushButton:pressed {{
    background-color: {self.fg_color};
    color: {self.bg_color};
}}
QPushButton:disabled {{
    color: {self.btn_hover_color};
    border-color: {self.btn_hover_color};
}}
QLineEdit {{
    background-color: {self.input_bg_color};
    color: {self.fg_color};
    border: 2px solid {self.border_color};
    padding: 8px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: {self.base_font_size}px;
}}
QLineEdit:focus {{
    border: 2px solid {self.accent_color};
}}
QTextEdit {{
    background-color: {self.input_bg_color};
    color: {self.fg_color};
    border: 2px solid {self.border_color};
    font-family: "Consolas", "Courier New", monospace;
    font-size: {self.log_font_size}px;
}}
QProgressBar {{
    background-color: {self.input_bg_color};
    border: 2px solid {self.border_color};
    text-align: center;
    color: {self.fg_color};
}}
QProgressBar::chunk {{
    background-color: {self.accent_color};
}}
QTabWidget::pane {{
    border: 2px solid {self.border_color};
    background-color: {self.bg_color};
    padding: 0px;
}}
QTabWidget > QWidget {{
    padding: 0px;
}}
QTabBar::tab {{
    background-color: {self.btn_bg_color};
    color: {self.fg_color};
    border: 2px solid {self.border_color};
    padding: 8px 16px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {self.fg_color};
    color: {self.bg_color};
}}
QTabBar::tab:hover {{
    background-color: {self.btn_hover_color};
}}
QRadioButton {{
    color: {self.fg_color};
    spacing: 8px;
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {self.border_color};
    border-radius: 0px;
}}
QRadioButton::indicator:checked {{
    background-color: {self.accent_color};
}}
QGroupBox {{
    border: 2px solid {self.border_color};
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
}}
QGroupBox::title {{
    color: {self.fg_color};
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}}
QScrollBar:vertical {{
    background: {self.btn_bg_color};
    border: 1px solid {self.border_color};
    width: 12px;
}}
QScrollBar::handle:vertical {{
    background: {self.accent_color};
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QSplitter::handle {{
    background-color: {self.border_color};
}}
QSplitter::handle:hover {{
    background-color: {self.accent_color};
}}
QSplitter::handle:pressed {{
    background-color: {self.error_color};
}}
QComboBox {{
    background-color: {self.btn_bg_color};
    color: {self.fg_color};
    border: 2px solid {self.border_color};
    padding: 5px;
}}
QComboBox QAbstractItemView {{
    background-color: {self.btn_bg_color};
    color: {self.fg_color};
    selection-background-color: {self.btn_hover_color};
}}
{extra_style}
"""
    
    def apply_stylesheet(self):
        style = self.build_dynamic_style()
        self.setStyleSheet(style)
        for widget in self.all_widgets:
            if hasattr(widget, 'font_scale_factor'):
                widget.setStyleSheet(f"font-size: {self.base_title_size}px; font-weight: bold; padding: 8px;")
    
    def init_ui(self):
        self.setWindowTitle(LanguageManager.tr("app_title"))
        self.setGeometry(100, 100, self.initial_width, self.initial_height)
        self.setMinimumSize(self.min_width, self.min_height)
        self.setStyleSheet(self.build_dynamic_style())
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(3, 3, 3, 3)
        main_layout.setSpacing(5)
        
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.setSpacing(0)
        
        top_bar_layout.addStretch()
        
        self.btn_create_env = QPushButton(LanguageManager.tr("create_runtime_env"))
        self.btn_create_env.setMinimumWidth(220)
        self.btn_create_env.setStyleSheet("""
            QPushButton {
                background-color: #001133;
                color: #00FF41;
                border: 2px solid #00FF41;
                padding: 16px 40px;
                font-family: "Consolas", "Courier New", monospace;
                font-weight: bold;
                font-size: 20px;
                min-height: 60px;
            }
            QPushButton:hover {
                background-color: #002244;
                border: 2px solid #00FF00;
            }
            QPushButton:pressed {
                background-color: #00FF41;
                color: #0D0208;
            }
        """)
        self.btn_create_env.clicked.connect(self.create_environment)
        top_bar_layout.addWidget(self.btn_create_env)
        
        self.btn_exit = QPushButton(LanguageManager.tr("exit_program"))
        self.btn_exit.setMinimumWidth(220)
        self.btn_exit.setStyleSheet("""
            QPushButton {
                background-color: #330000;
                color: #FF4444;
                border: 2px solid #FF4444;
                padding: 16px 40px;
                font-family: "Consolas", "Courier New", monospace;
                font-weight: bold;
                font-size: 20px;
                min-height: 60px;
            }
            QPushButton:hover {
                background-color: #550000;
                border: 2px solid #FF0000;
            }
            QPushButton:pressed {
                background-color: #FF0000;
                color: #0D0208;
            }
        """)
        self.btn_exit.clicked.connect(self.safe_exit)
        top_bar_layout.addWidget(self.btn_exit)
        
        main_layout.addWidget(top_bar)
        
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_tab(), LanguageManager.tr("create_chapters"))
        self.tabs.addTab(self.summary_tab(), LanguageManager.tr("summary_merge_tool"))
        self.tabs.addTab(self.monitor_tab(), LanguageManager.tr("monitor_management"))
        self.tabs.addTab(self.config_tab(), LanguageManager.tr("parameter_config"))
        self.tabs.addTab(self.help_tab(), LanguageManager.tr("user_guide"))
        
        main_layout.addWidget(self.tabs)
    
    def create_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(5)
        
        self.create_tab_title = QLabel(LanguageManager.tr("chapter_template_tool"))
        self.create_tab_title.font_scale_factor = 1.0
        self.all_widgets.append(self.create_tab_title)
        self.create_tab_title.setStyleSheet("font-size: 32px; font-weight: bold; padding: 8px;")
        layout.addWidget(self.create_tab_title)
        
        form = QFormLayout()
        
        self.start_chapter = QLineEdit()
        self.start_chapter.setPlaceholderText(LanguageManager.tr("enter_start_chapter"))
        self.create_start_label = QLabel(LanguageManager.tr("start_chapter_label"))
        form.addRow(self.create_start_label, self.start_chapter)
        
        self.end_chapter = QLineEdit()
        self.end_chapter.setPlaceholderText(LanguageManager.tr("enter_end_chapter"))
        self.create_end_label = QLabel(LanguageManager.tr("end_chapter_label"))
        form.addRow(self.create_end_label, self.end_chapter)
        
        self.name_suffix = QLineEdit()
        self.name_suffix.setPlaceholderText(LanguageManager.tr("enter_file_suffix"))
        self.name_suffix.setText("name")
        self.create_suffix_label = QLabel(LanguageManager.tr("file_suffix_label"))
        form.addRow(self.create_suffix_label, self.name_suffix)
        
        self.output_dir = QLineEdit()
        self.output_dir.setText(get_novel_dir())
        self.create_dir_btn = QPushButton(LanguageManager.tr("select_directory"))
        self.create_dir_btn.clicked.connect(self.select_directory)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.output_dir)
        dir_layout.addWidget(self.create_dir_btn)
        self.create_savedir_label = QLabel(LanguageManager.tr("save_directory_label"))
        form.addRow(self.create_savedir_label, dir_layout)
        
        layout.addLayout(form)
        
        self.create_result = QTextEdit()
        self.create_result.setReadOnly(True)
        self.create_result_label = QLabel(LanguageManager.tr("creation_result"))
        layout.addWidget(self.create_result_label)
        layout.addWidget(self.create_result)
        
        self.create_btn = QPushButton(LanguageManager.tr("start_creation"))
        self.create_btn.clicked.connect(self.create_files)
        layout.addWidget(self.create_btn)
        
        return widget
    
    def select_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, LanguageManager.tr("select_directory"), get_novel_dir())
        if dir_path:
            self.output_dir.setText(dir_path)
    
    def select_novel_directory(self):
        current_dir = self.config_novel_dir.text() or os.path.dirname(os.path.abspath(__file__))
        dir_path = QFileDialog.getExistingDirectory(self, LanguageManager.tr("select_novel_directory"), current_dir)
        if dir_path:
            self.config_novel_dir.setText(dir_path)
            # 立即保存到配置文件
            ConfigManager.set('Monitor', 'novel_dir', dir_path)
            self.check_and_initialize_novel_dir(dir_path)
    
    def check_and_initialize_novel_dir(self, dir_path):
        """检查并初始化空的小说目录"""
        try:
            items = os.listdir(dir_path)
            has_volume = False
            for item in items:
                item_path = os.path.join(dir_path, item)
                if os.path.isdir(item_path) and FileManager.get_volume_number(item):
                    has_volume = True
                    break
            
            if has_volume:
                logger.info(f"目录 {dir_path} 已包含卷文件夹，无需初始化")
                return
            
            reply = QMessageBox.question(self, LanguageManager.tr("initialize_directory"), 
                                         LanguageManager.tr("initialize_directory_msg"),
                                         QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.Yes)
            if reply != QMessageBox.Yes:
                return
            
            self.initialize_novel_directory(dir_path)
            
        except Exception as e:
            logger.error(f"{LanguageManager.tr('check_directory_failed')}: {e}")
    
    def initialize_novel_directory(self, dir_path):
        """初始化小说目录"""
        try:
            # 首先检查目录是否存在且可写
            if not os.path.exists(dir_path):
                QMessageBox.critical(self, LanguageManager.tr("error"), 
                                    f"{LanguageManager.tr('dir_not_exist')}: {dir_path}")
                return
            
            # 检查写权限
            test_file = os.path.join(dir_path, '.test_write_permission')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
            except Exception as e:
                QMessageBox.critical(self, LanguageManager.tr("error"), 
                                    f"目录不可写！请检查权限或选择其他目录。\n\n错误: {str(e)}")
                return
            
            config = ConfigManager.load_config()
            init_copy_count = config.getint('Environment', 'init_copy_count', fallback=10)
            
            volume_dir = os.path.join(dir_path, '1[new_0]')
            
            if not os.path.exists(volume_dir):
                os.makedirs(volume_dir)
                logger.info(f"创建目录: {volume_dir}")
            
            for i in range(1, init_copy_count + 1):
                dest_filename = FileManager.generate_chapter_name(i, "", include_prefix=True).rstrip('_') + '_.txt'
                dest_path = os.path.join(volume_dir, dest_filename)
                if not os.path.exists(dest_path):
                    with open(dest_path, 'w', encoding='utf-8') as f:
                        f.write('')
            
            logger.info(f"已在 {volume_dir} 创建 {init_copy_count} 个空章节")
            
            QMessageBox.information(self, LanguageManager.tr("success"), 
                                   LanguageManager.tr("initialize_complete") + f"\n\n  - {volume_dir}")
            
        except Exception as e:
            logger.error(f"{LanguageManager.tr('initialize_failed')}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, LanguageManager.tr("error"), f"{LanguageManager.tr('initialize_failed')}: {str(e)}")
    
    def create_files(self):
        try:
            start = int(self.start_chapter.text())
            end = int(self.end_chapter.text())
            suffix = self.name_suffix.text() or "name"
            output = self.output_dir.text()
            
            if start < 1:
                self.create_result.append("[ERR] 起始章节必须大于0")
                return
            if end < 1:
                self.create_result.append("[ERR] 结束章节必须大于0")
                return
            if start > end:
                self.create_result.append("[ERR] 起始章节不能大于结束章节")
                return
            
            if not os.path.exists(output):
                reply = QMessageBox.question(self, LanguageManager.tr("confirm"), 
                                            LanguageManager.tr("dir_not_exist_question").format(output),
                                            QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    try:
                        os.makedirs(output, exist_ok=True)
                    except Exception as e:
                        self.create_result.append(f"[ERR] 创建目录失败: {e}")
                        logger.error(f"创建目录失败: {e}")
                        return
                else:
                    return
            
            if not os.access(output, os.W_OK):
                self.create_result.append(f"[ERR] 目录不可写: {output}")
                return
            
            count = 0
            existing_count = 0
            for i in range(start, end + 1):
                filename = FileManager.generate_chapter_name(i, suffix) + ".txt"
                file_path = os.path.join(output, filename)
                
                if os.path.exists(file_path):
                    existing_count += 1
                    continue
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"第{i}个文件\n")
                count += 1
            
            if existing_count > 0:
                self.create_result.append(f"[INFO] 跳过已存在的 {existing_count} 个文件")
            
            msg = f"[OK] 成功创建 {count} 个文件"
            self.create_result.append(msg)
            logger.info(msg)
            self.save_settings()
        except ValueError:
            self.create_result.append("[ERR] 请输入有效的正整数")
        except Exception as e:
            self.create_result.append(f"[ERR] {str(e)}")
            logger.error(f"创建文件失败: {e}")
    
    def summary_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(5)
        
        self.summary_tab_title = QLabel(LanguageManager.tr("summary_merge_tool"))
        self.summary_tab_title.font_scale_factor = 1.0
        self.all_widgets.append(self.summary_tab_title)
        self.summary_tab_title.setStyleSheet("font-size: 32px; font-weight: bold; padding: 8px;")
        layout.addWidget(self.summary_tab_title)
        
        self.summary_mode_group = QGroupBox(LanguageManager.tr("run_mode"))
        mode_layout = QVBoxLayout()
        self.mode1 = QRadioButton(LanguageManager.tr("stats_only"))
        self.mode2 = QRadioButton(LanguageManager.tr("stats_and_rename"))
        self.mode2.setChecked(True)
        mode_layout.addWidget(self.mode1)
        mode_layout.addWidget(self.mode2)
        self.summary_mode_group.setLayout(mode_layout)
        layout.addWidget(self.summary_mode_group)
        
        self.summary_progress_label = QLabel(LanguageManager.tr("progress"))
        layout.addWidget(self.summary_progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        self.summary_result = QTextEdit()
        self.summary_result.setReadOnly(True)
        self.summary_result_label = QLabel(LanguageManager.tr("execution_result"))
        layout.addWidget(self.summary_result_label)
        layout.addWidget(self.summary_result)
        
        self.summary_btn_run = QPushButton(LanguageManager.tr("execute_summary"))
        self.summary_btn_run.clicked.connect(self.run_summary)
        layout.addWidget(self.summary_btn_run)
        
        return widget
    
    def run_summary(self):
        novel_dir = get_novel_dir()
        if not os.path.exists(novel_dir):
            QMessageBox.warning(self, LanguageManager.tr("env_not_initialized"), 
                               f"{LanguageManager.tr('env_init_tip')}\n"
                               f"当前目录：{novel_dir}\n"
                               f"{LanguageManager.tr('dir_not_exist')}")
            return
        
        mode = 1 if self.mode1.isChecked() else 2
        self.summary_result.clear()
        self.progress_bar.setValue(10)
        
        folder_path = novel_dir
        folder_name = os.path.basename(novel_dir)
        output_file_path = os.path.join(folder_path, f"{folder_name}.txt")
        
        min_content_length = ConfigManager.get_int('Monitor', 'min_word_count', fallback=20)
        
        if os.path.exists(output_file_path):
            try:
                open(output_file_path, 'w', encoding='utf-8').close()
            except Exception as e:
                self.summary_result.append(f"[ERR] 清空文件失败: {e}")
                logger.error(f"清空文件失败: {e}")
                return
        
        self.summary_result.append(f"模式: {mode} - {'不重命名' if mode == 1 else '重命名'}")
        self.progress_bar.setValue(20)
        
        from collections import defaultdict
        volume_content = defaultdict(list)
        total_cjk_count = 0
        total_non_blank_count = 0
        volume_non_blank_count = defaultdict(int)
        volume_folder_paths = dict()
        
        VOLUME_RE = re.compile(r'^(\d+)(.*?)(?:\[.*\])?$')
        FILE_NUM_RE = re.compile(r'^(\d+)')
        
        try:
            folders = os.listdir(folder_path)
            total_folders = len([f for f in folders if os.path.isdir(os.path.join(folder_path, f)) and VOLUME_RE.match(f)])
            processed = 0
            
            for root, _, files in os.walk(folder_path):
                dir_name = os.path.basename(root)
                volume_match = VOLUME_RE.match(dir_name)
                if not volume_match:
                    continue
                
                volume_num = int(volume_match.group(1))
                volume_name = volume_match.group(2).strip()
                volume_folder_paths[volume_num] = (root, dir_name)
                
                valid_files = []
                for f in files:
                    if not f.lower().endswith('.txt'):
                        continue
                    num_match = FILE_NUM_RE.match(f)
                    if num_match:
                        num = int(num_match.group(1))
                        valid_files.append((num, num_match.group(1), f))
                
                valid_files.sort(key=lambda x: x[0])
                
                for num, num_str, file in valid_files:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if len(content) < min_content_length:
                                continue
                            
                            cjk_count = 0
                            non_blank_count = 0
                            for char in content:
                                if 0x4E00 <= ord(char) <= 0x9FFF:
                                    cjk_count += 1
                                if not char.isspace():
                                    non_blank_count += 1
                            total_cjk_count += cjk_count
                            total_non_blank_count += non_blank_count
                            volume_non_blank_count[volume_num] += non_blank_count
                            
                            file_base = os.path.splitext(file)[0]
                            chapter_name = file_base[len(num_str):].strip()
                            chapter_title = FileManager.format_chapter_title(num, chapter_name)
                            
                            volume_content[volume_num].append((chapter_title, content, volume_name))
                    except Exception as e:
                        self.summary_result.append(f"[WARN] 读取失败 {file}: {e}")
                        logger.warning(f"读取失败 {file}: {e}")
                
                processed += 1
                progress = 20 + int((processed / total_folders) * 50)
                self.progress_bar.setValue(progress)
            
            self.progress_bar.setValue(70)
            
            with open(output_file_path, 'a', encoding='utf-8') as outfile:
                buffer = []
                for vol_num in sorted(volume_content):
                    chapters = volume_content[vol_num]
                    vol_name = chapters[0][2]
                    vol_word_count = volume_non_blank_count[vol_num]
                    folder_path_abs, dir_name = volume_folder_paths[vol_num]
                    vol_title = FileManager.format_volume_title_export(vol_num, vol_name, vol_word_count)
                    buffer.extend(["\n\n", vol_title, "\n\n"])
                    for title, content, _ in chapters:
                        buffer.extend(["\n\n", title, "\n\n", content, "\n"])
                outfile.write(''.join(buffer))
            
            self.progress_bar.setValue(90)
            
            if mode == 2:
                all_volume_nums = sorted(volume_content.keys())
                max_vol = all_volume_nums[-1] if all_volume_nums else 0
                
                has_new_volume_content = False
                if max_vol in volume_non_blank_count and volume_non_blank_count[max_vol] > 0:
                    has_new_volume_content = True
                
                if has_new_volume_content:
                    for vol_num, (folder_path_abs, orig_dir_name) in volume_folder_paths.items():
                        if vol_num < max_vol:
                            word_count = volume_non_blank_count[vol_num]
                            new_dir_name = re.sub(r'\[(new_|old_)?\d+\]$', '', orig_dir_name)
                            new_dir_name = f"{new_dir_name}[old_{word_count}]"
                            if orig_dir_name != new_dir_name:
                                new_folder_path = os.path.join(os.path.dirname(folder_path_abs), new_dir_name)
                                try:
                                    os.rename(folder_path_abs, new_folder_path)
                                    self.summary_result.append(f"[OLD] 标记旧卷: {orig_dir_name} -> {new_dir_name}")
                                    logger.info(f"标记旧卷: {orig_dir_name} -> {new_dir_name}")
                                except Exception as e:
                                    self.summary_result.append(f"[ERR] 标记旧卷失败 {orig_dir_name}: {e}")
                                    logger.error(f"标记旧卷失败 {orig_dir_name}: {e}")
                
                for vol_num, (folder_path_abs, orig_dir_name) in volume_folder_paths.items():
                    if vol_num == max_vol:
                        word_count = volume_non_blank_count[vol_num]
                        new_dir_name = re.sub(r'\[(new_|old_)?\d+\]$', '', orig_dir_name)
                        new_dir_name = f"{new_dir_name}[new_{word_count}]"
                        if orig_dir_name != new_dir_name:
                            new_folder_path = os.path.join(os.path.dirname(folder_path_abs), new_dir_name)
                            try:
                                os.rename(folder_path_abs, new_folder_path)
                                self.summary_result.append(f"[OK] 重命名: {orig_dir_name} -> {new_dir_name}")
                                logger.info(f"重命名: {orig_dir_name} -> {new_dir_name}")
                            except Exception as e:
                                self.summary_result.append(f"[ERR] 重命名失败: {e}")
                                logger.error(f"重命名失败: {e}")
            
            self.progress_bar.setValue(100)
            msg = f"[OK] 完成！CJK字符: {total_cjk_count}, 非空白字符: {total_non_blank_count}"
            self.summary_result.append(msg)
            logger.info(msg)
            self.save_settings()
            
            QTimer.singleShot(2000, lambda: self.progress_bar.setValue(0))
            
        except Exception as e:
            self.summary_result.append(f"[ERR] {str(e)}")
            logger.error(f"Summary执行失败: {e}")
            QTimer.singleShot(2000, lambda: self.progress_bar.setValue(0))
    
    def config_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(5)
        
        self.config_tab_title = QLabel(LanguageManager.tr("param_config_page"))
        self.config_tab_title.font_scale_factor = 1.0
        self.all_widgets.append(self.config_tab_title)
        self.config_tab_title.setStyleSheet("font-size: 32px; font-weight: bold; padding: 8px;")
        layout.addWidget(self.config_tab_title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        config_layout.setContentsMargins(5, 5, 5, 5)
        config_layout.setSpacing(10)
        
        self.config_ui_group = QGroupBox(LanguageManager.tr("ui_size_config"))
        ui_form = QFormLayout()
        
        self.config_base_font = QSpinBox()
        self.config_base_font.setRange(8, 48)
        self.config_base_font.setValue(self.base_font_size)
        self.config_base_font_label = QLabel(LanguageManager.tr("base_font_size"))
        ui_form.addRow(self.config_base_font_label, self.config_base_font)
        
        self.config_title_font = QSpinBox()
        self.config_title_font.setRange(12, 72)
        self.config_title_font.setValue(self.base_title_size)
        self.config_title_font_label = QLabel(LanguageManager.tr("title_font_size"))
        ui_form.addRow(self.config_title_font_label, self.config_title_font)
        
        self.config_log_font = QSpinBox()
        self.config_log_font.setRange(8, 36)
        self.config_log_font.setValue(self.log_font_size)
        self.config_log_font_label = QLabel(LanguageManager.tr("log_font_size"))
        ui_form.addRow(self.config_log_font_label, self.config_log_font)
        
        self.config_initial_width = QSpinBox()
        self.config_initial_width.setRange(600, 3840)
        self.config_initial_width.setValue(self.initial_width)
        self.config_initial_width_label = QLabel(LanguageManager.tr("initial_width"))
        ui_form.addRow(self.config_initial_width_label, self.config_initial_width)
        
        self.config_initial_height = QSpinBox()
        self.config_initial_height.setRange(400, 2160)
        self.config_initial_height.setValue(self.initial_height)
        self.config_initial_height_label = QLabel(LanguageManager.tr("initial_height"))
        ui_form.addRow(self.config_initial_height_label, self.config_initial_height)
        
        self.config_min_width = QSpinBox()
        self.config_min_width.setRange(400, 1920)
        self.config_min_width.setValue(self.min_width)
        self.config_min_width_label = QLabel(LanguageManager.tr("min_width"))
        ui_form.addRow(self.config_min_width_label, self.config_min_width)
        
        self.config_min_height = QSpinBox()
        self.config_min_height.setRange(300, 1080)
        self.config_min_height.setValue(self.min_height)
        self.config_min_height_label = QLabel(LanguageManager.tr("min_height"))
        ui_form.addRow(self.config_min_height_label, self.config_min_height)
        
        self.config_ui_group.setLayout(ui_form)
        config_layout.addWidget(self.config_ui_group)
        
        self.config_color_group = QGroupBox(LanguageManager.tr("ui_color_config"))
        color_form = QFormLayout()
        
        self.config_bg_color = QLineEdit()
        self.config_bg_color.setText(self.bg_color)
        self.config_bg_color_label = QLabel(LanguageManager.tr("bg_color"))
        color_form.addRow(self.config_bg_color_label, self.config_bg_color)
        
        self.config_fg_color = QLineEdit()
        self.config_fg_color.setText(self.fg_color)
        self.config_fg_color_label = QLabel(LanguageManager.tr("fg_color"))
        color_form.addRow(self.config_fg_color_label, self.config_fg_color)
        
        self.config_border_color = QLineEdit()
        self.config_border_color.setText(self.border_color)
        self.config_border_color_label = QLabel(LanguageManager.tr("border_color"))
        color_form.addRow(self.config_border_color_label, self.config_border_color)
        
        self.config_error_color = QLineEdit()
        self.config_error_color.setText(self.error_color)
        self.config_error_color_label = QLabel(LanguageManager.tr("error_color"))
        color_form.addRow(self.config_error_color_label, self.config_error_color)
        
        self.config_btn_bg = QLineEdit()
        self.config_btn_bg.setText(self.btn_bg_color)
        self.config_btn_bg_label = QLabel(LanguageManager.tr("btn_bg"))
        color_form.addRow(self.config_btn_bg_label, self.config_btn_bg)
        
        self.config_btn_hover = QLineEdit()
        self.config_btn_hover.setText(self.btn_hover_color)
        self.config_btn_hover_label = QLabel(LanguageManager.tr("btn_hover"))
        color_form.addRow(self.config_btn_hover_label, self.config_btn_hover)
        
        self.config_input_bg = QLineEdit()
        self.config_input_bg.setText(self.input_bg_color)
        self.config_input_bg_label = QLabel(LanguageManager.tr("input_bg"))
        color_form.addRow(self.config_input_bg_label, self.config_input_bg)
        
        self.config_color_group.setLayout(color_form)
        config_layout.addWidget(self.config_color_group)
        
        self.config_monitor_group = QGroupBox(LanguageManager.tr("monitor_config"))
        monitor_form = QFormLayout()
        
        self.config_novel_dir = QLineEdit()
        self.config_novel_dir.setText(ConfigManager.get('Monitor', 'novel_dir', fallback=''))
        self.config_novel_dir_label = QLabel(LanguageManager.tr("novel_dir"))
        self.config_novel_dir_btn = QPushButton(LanguageManager.tr("select"))
        self.config_novel_dir_btn.setStyleSheet("""
            QPushButton {
                background-color: #001100;
                color: #00FF41;
                border: 2px solid #00FF41;
                padding: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #003300;
            }
        """)
        self.config_novel_dir_btn.clicked.connect(self.select_novel_directory)
        
        novel_dir_layout = QHBoxLayout()
        novel_dir_layout.addWidget(self.config_novel_dir)
        novel_dir_layout.addWidget(self.config_novel_dir_btn)
        monitor_form.addRow(self.config_novel_dir_label, novel_dir_layout)
        
        self.config_check_interval = QSpinBox()
        self.config_check_interval.setRange(1, 300)
        self.config_check_interval.setValue(ConfigManager.get_int('Monitor', 'check_interval', fallback=15))
        self.config_check_interval_label = QLabel(LanguageManager.tr("monitor_interval"))
        monitor_form.addRow(self.config_check_interval_label, self.config_check_interval)
        
        self.config_max_ahead = QSpinBox()
        self.config_max_ahead.setRange(0, 10)
        self.config_max_ahead.setValue(ConfigManager.get_int('Monitor', 'max_ahead_chapters', fallback=2))
        self.config_max_ahead_label = QLabel(LanguageManager.tr("pregenerate_chapters"))
        monitor_form.addRow(self.config_max_ahead_label, self.config_max_ahead)
        
        self.config_min_word = QSpinBox()
        self.config_min_word.setRange(1, 1000)
        self.config_min_word.setValue(ConfigManager.get_int('Monitor', 'min_word_count', fallback=20))
        self.config_min_word_label = QLabel(LanguageManager.tr("trigger_word_count"))
        monitor_form.addRow(self.config_min_word_label, self.config_min_word)
        
        self.config_monitor_group.setLayout(monitor_form)
        config_layout.addWidget(self.config_monitor_group)
        
        self.config_adaptive_group = QGroupBox(LanguageManager.tr("adaptive_config"))
        adaptive_form = QFormLayout()
        
        self.config_area_scale = QSpinBox()
        self.config_area_scale.setRange(1, 10)
        self.config_area_scale.setSingleStep(1)
        self.config_area_scale.setValue(int(self.area_scale_factor))
        self.config_area_scale_label = QLabel(LanguageManager.tr("area_scale"))
        adaptive_form.addRow(self.config_area_scale_label, self.config_area_scale)
        
        self.config_height_scale = QLineEdit()
        self.config_height_scale.setText(str(self.height_scale_factor))
        self.config_height_scale_label = QLabel(LanguageManager.tr("height_scale"))
        adaptive_form.addRow(self.config_height_scale_label, self.config_height_scale)
        
        self.config_font_increase = QSpinBox()
        self.config_font_increase.setRange(0, 20)
        self.config_font_increase.setValue(self.font_increase)
        self.config_font_increase_label = QLabel(LanguageManager.tr("font_increment"))
        adaptive_form.addRow(self.config_font_increase_label, self.config_font_increase)
        
        self.config_adaptive_group.setLayout(adaptive_form)
        config_layout.addWidget(self.config_adaptive_group)

        self.config_format_group = QGroupBox(LanguageManager.tr("format_config"))
        format_form = QFormLayout()

        self.config_export_format = QLineEdit()
        self.config_export_format.setText(ConfigManager.get('Format', 'export_format', fallback=''))
        self.config_export_format.textChanged.connect(self.update_format_preview)
        self.config_export_format_label = QLabel(LanguageManager.tr("export_filename_format"))
        format_form.addRow(self.config_export_format_label, self.config_export_format)

        self.config_export_format_help = QLabel(LanguageManager.tr("format_help_filename"))
        self.config_export_format_help.setStyleSheet("color: #888888; font-size: 23px;")
        self.config_export_format_help.setWordWrap(True)
        format_form.addRow("", self.config_export_format_help)

        self.config_export_format_preview = QLabel("")
        self.config_export_format_preview.setStyleSheet("color: #FFFFFF; font-size: 23px; font-weight: bold;")
        format_form.addRow("", self.config_export_format_preview)

        self.config_export_volume_format = QLineEdit()
        self.config_export_volume_format.setText(ConfigManager.get('Format', 'export_volume_format', fallback=''))
        self.config_export_volume_format.textChanged.connect(self.update_format_preview)
        self.config_export_volume_format_label = QLabel(LanguageManager.tr("export_volume_format"))
        format_form.addRow(self.config_export_volume_format_label, self.config_export_volume_format)

        self.config_export_volume_help = QLabel(LanguageManager.tr("format_help_volume"))
        self.config_export_volume_help.setStyleSheet("color: #888888; font-size: 23px;")
        self.config_export_volume_help.setWordWrap(True)
        format_form.addRow("", self.config_export_volume_help)

        self.config_export_volume_preview = QLabel("")
        self.config_export_volume_preview.setStyleSheet("color: #FFFFFF; font-size: 23px; font-weight: bold;")
        format_form.addRow("", self.config_export_volume_preview)

        self.config_export_chapter_format = QLineEdit()
        self.config_export_chapter_format.setText(ConfigManager.get('Format', 'export_chapter_format', fallback=''))
        self.config_export_chapter_format.textChanged.connect(self.update_format_preview)
        self.config_export_chapter_format_label = QLabel(LanguageManager.tr("export_chapter_format"))
        format_form.addRow(self.config_export_chapter_format_label, self.config_export_chapter_format)

        self.config_export_chapter_help = QLabel(LanguageManager.tr("format_help_chapter"))
        self.config_export_chapter_help.setStyleSheet("color: #888888; font-size: 23px;")
        self.config_export_chapter_help.setWordWrap(True)
        format_form.addRow("", self.config_export_chapter_help)

        self.config_export_chapter_preview = QLabel("")
        self.config_export_chapter_preview.setStyleSheet("color: #FFFFFF; font-size: 23px; font-weight: bold;")
        format_form.addRow("", self.config_export_chapter_preview)

        self.config_preview_color = QLineEdit()
        self.config_preview_color.setText(ConfigManager.get('Format', 'preview_color', fallback='#FFFFFF'))
        self.config_preview_color.textChanged.connect(self.update_preview_style)
        self.config_preview_color_label = QLabel(LanguageManager.tr("preview_color"))
        format_form.addRow(self.config_preview_color_label, self.config_preview_color)

        self.config_preview_font_size = QSpinBox()
        self.config_preview_font_size.setRange(12, 48)
        self.config_preview_font_size.setValue(ConfigManager.get_int('Format', 'preview_font_size', fallback=23))
        self.config_preview_font_size.valueChanged.connect(self.update_preview_style)
        self.config_preview_font_size_label = QLabel(LanguageManager.tr("preview_font_size"))
        format_form.addRow(self.config_preview_font_size_label, self.config_preview_font_size)

        self.config_format_group.setLayout(format_form)
        config_layout.addWidget(self.config_format_group)

        self.config_language_group = QGroupBox(LanguageManager.tr("language_config"))
        language_form = QFormLayout()
        
        self.config_language = QComboBox()
        languages = LanguageManager.get_available_languages()
        lang_display_names = {
            'zh_CN': '简体中文',
            'en_US': 'English',
            'ja_JP': '日本語'
        }
        for lang in languages:
            display_name = lang_display_names.get(lang, lang)
            self.config_language.addItem(display_name, lang)
        
        current_lang = LanguageManager.get_current_language()
        current_index = self.config_language.findData(current_lang)
        if current_index >= 0:
            self.config_language.setCurrentIndex(current_index)
        
        self.config_language_label = QLabel(LanguageManager.tr("select_language"))
        language_form.addRow(self.config_language_label, self.config_language)
        
        self.config_language_note = QLabel(LanguageManager.tr("tip_change_language"))
        self.config_language_note.setStyleSheet("color: #888888; font-size: 23px;")
        language_form.addRow("", self.config_language_note)
        
        self.config_language_group.setLayout(language_form)
        config_layout.addWidget(self.config_language_group)
        
        btn_layout = QHBoxLayout()
        self.config_btn_save_apply = QPushButton(LanguageManager.tr("save_and_apply"))
        self.config_btn_save_apply.clicked.connect(self.save_and_apply_config)
        self.config_btn_save = QPushButton(LanguageManager.tr("save_config"))
        self.config_btn_save.clicked.connect(self.save_config)
        self.config_btn_reload = QPushButton(LanguageManager.tr("reload"))
        self.config_btn_reload.clicked.connect(self.reload_config)
        btn_layout.addWidget(self.config_btn_save_apply)
        btn_layout.addWidget(self.config_btn_save)
        btn_layout.addWidget(self.config_btn_reload)
        
        config_layout.addLayout(btn_layout)
        config_layout.addStretch()
        
        scroll.setWidget(config_widget)
        layout.addWidget(scroll)
        
        # 初始化预览
        self.update_format_preview()
        self.update_preview_style()
        
        return widget
    
    def save_config(self):
        try:
            ConfigManager.set('UI', 'base_font_size', self.config_base_font.value())
            ConfigManager.set('UI', 'base_title_size', self.config_title_font.value())
            ConfigManager.set('UI', 'log_font_size', self.config_log_font.value())
            ConfigManager.set('UI', 'initial_width', self.config_initial_width.value())
            ConfigManager.set('UI', 'initial_height', self.config_initial_height.value())
            ConfigManager.set('UI', 'min_width', self.config_min_width.value())
            ConfigManager.set('UI', 'min_height', self.config_min_height.value())
            
            ConfigManager.set('UI', 'bg_color', self.config_bg_color.text())
            ConfigManager.set('UI', 'fg_color', self.config_fg_color.text())
            ConfigManager.set('UI', 'border_color', self.config_border_color.text())
            ConfigManager.set('UI', 'error_color', self.config_error_color.text())
            ConfigManager.set('UI', 'btn_bg_color', self.config_btn_bg.text())
            ConfigManager.set('UI', 'btn_hover_color', self.config_btn_hover.text())
            ConfigManager.set('UI', 'input_bg_color', self.config_input_bg.text())
            
            ConfigManager.set('Monitor', 'check_interval', self.config_check_interval.value())
            ConfigManager.set('Monitor', 'max_ahead_chapters', self.config_max_ahead.value())
            ConfigManager.set('Monitor', 'min_word_count', self.config_min_word.value())
            ConfigManager.set('Monitor', 'novel_dir', self.config_novel_dir.text())
            
            ConfigManager.set('Adaptive', 'area_scale_factor', self.config_area_scale.value())
            ConfigManager.set('Adaptive', 'height_scale_factor', self.config_height_scale.text())
            ConfigManager.set('Adaptive', 'font_increase', self.config_font_increase.value())

            export_fmt = self.config_export_format.text().strip()
            export_vol_fmt = self.config_export_volume_format.text().strip()
            export_chapter_fmt = self.config_export_chapter_format.text().strip()
            preview_color = self.config_preview_color.text().strip()
            preview_font_size = self.config_preview_font_size.value()
            if export_fmt:
                ConfigManager.set('Format', 'export_format', export_fmt)
            else:
                ConfigManager.remove_option('Format', 'export_format')
            if export_vol_fmt:
                ConfigManager.set('Format', 'export_volume_format', export_vol_fmt)
            else:
                ConfigManager.remove_option('Format', 'export_volume_format')
            if export_chapter_fmt:
                ConfigManager.set('Format', 'export_chapter_format', export_chapter_fmt)
            else:
                ConfigManager.remove_option('Format', 'export_chapter_format')
            ConfigManager.set('Format', 'preview_color', preview_color)
            ConfigManager.set('Format', 'preview_font_size', preview_font_size)

            FileManager._load_custom_formats()

            selected_lang = self.config_language.currentData()
            if selected_lang:
                ConfigManager.set('Language', 'current', selected_lang)
                LanguageManager._translations = {}
                LanguageManager._current_lang = selected_lang
                FileManager.set_language(selected_lang)
            
            QMessageBox.information(self, LanguageManager.tr("success"), LanguageManager.tr("config_saved_restart"))
            logger.info("Configuration saved")
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("error"), f"{LanguageManager.tr('save_config_failed')}: {str(e)}")
            logger.error(f"保存配置失败: {e}")
    
    def save_and_apply_config(self):
        try:
            ConfigManager.set('UI', 'base_font_size', self.config_base_font.value())
            ConfigManager.set('UI', 'base_title_size', self.config_title_font.value())
            ConfigManager.set('UI', 'log_font_size', self.config_log_font.value())
            ConfigManager.set('UI', 'initial_width', self.config_initial_width.value())
            ConfigManager.set('UI', 'initial_height', self.config_initial_height.value())
            ConfigManager.set('UI', 'min_width', self.config_min_width.value())
            ConfigManager.set('UI', 'min_height', self.config_min_height.value())
            
            ConfigManager.set('UI', 'bg_color', self.config_bg_color.text())
            ConfigManager.set('UI', 'fg_color', self.config_fg_color.text())
            ConfigManager.set('UI', 'border_color', self.config_border_color.text())
            ConfigManager.set('UI', 'error_color', self.config_error_color.text())
            ConfigManager.set('UI', 'btn_bg_color', self.config_btn_bg.text())
            ConfigManager.set('UI', 'btn_hover_color', self.config_btn_hover.text())
            ConfigManager.set('UI', 'input_bg_color', self.config_input_bg.text())
            
            ConfigManager.set('Monitor', 'check_interval', self.config_check_interval.value())
            ConfigManager.set('Monitor', 'max_ahead_chapters', self.config_max_ahead.value())
            ConfigManager.set('Monitor', 'min_word_count', self.config_min_word.value())
            ConfigManager.set('Monitor', 'novel_dir', self.config_novel_dir.text())
            
            ConfigManager.set('Adaptive', 'area_scale_factor', self.config_area_scale.value())
            ConfigManager.set('Adaptive', 'height_scale_factor', self.config_height_scale.text())
            ConfigManager.set('Adaptive', 'font_increase', self.config_font_increase.value())

            export_fmt = self.config_export_format.text().strip()
            export_vol_fmt = self.config_export_volume_format.text().strip()
            export_chapter_fmt = self.config_export_chapter_format.text().strip()
            preview_color = self.config_preview_color.text().strip()
            preview_font_size = self.config_preview_font_size.value()
            if export_fmt:
                ConfigManager.set('Format', 'export_format', export_fmt)
            else:
                ConfigManager.remove_option('Format', 'export_format')
            if export_vol_fmt:
                ConfigManager.set('Format', 'export_volume_format', export_vol_fmt)
            else:
                ConfigManager.remove_option('Format', 'export_volume_format')
            if export_chapter_fmt:
                ConfigManager.set('Format', 'export_chapter_format', export_chapter_fmt)
            else:
                ConfigManager.remove_option('Format', 'export_chapter_format')
            ConfigManager.set('Format', 'preview_color', preview_color)
            ConfigManager.set('Format', 'preview_font_size', preview_font_size)

            FileManager._load_custom_formats()

            selected_lang = self.config_language.currentData()
            if selected_lang:
                ConfigManager.set('Language', 'current', selected_lang)
                LanguageManager._translations = {}
                LanguageManager._current_lang = selected_lang
                FileManager.set_language(selected_lang)
            
            self.load_config_values()
            self.apply_stylesheet()
            self.update_ui_language()
            QMessageBox.information(self, LanguageManager.tr("success"), LanguageManager.tr("config_saved_applied"))
            logger.info("Configuration saved and applied")
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("error"), f"{LanguageManager.tr('save_apply_failed')}: {str(e)}")
            logger.error(f"Save and apply failed: {e}")
    
    def reload_config(self):
        self.load_config_values()
        self.config_base_font.setValue(self.base_font_size)
        self.config_title_font.setValue(self.base_title_size)
        self.config_log_font.setValue(self.log_font_size)
        self.config_initial_width.setValue(self.initial_width)
        self.config_initial_height.setValue(self.initial_height)
        self.config_min_width.setValue(self.min_width)
        self.config_min_height.setValue(self.min_height)
        self.config_bg_color.setText(self.bg_color)
        self.config_fg_color.setText(self.fg_color)
        self.config_border_color.setText(self.border_color)
        self.config_error_color.setText(self.error_color)
        self.config_btn_bg.setText(self.btn_bg_color)
        self.config_btn_hover.setText(self.btn_hover_color)
        self.config_input_bg.setText(self.input_bg_color)
        self.config_check_interval.setValue(ConfigManager.get_int('Monitor', 'check_interval', fallback=15))
        self.config_max_ahead.setValue(ConfigManager.get_int('Monitor', 'max_ahead_chapters', fallback=2))
        self.config_min_word.setValue(ConfigManager.get_int('Monitor', 'min_word_count', fallback=20))
        self.config_area_scale.setValue(int(self.area_scale_factor))
        self.config_height_scale.setText(str(self.height_scale_factor))
        self.config_font_increase.setValue(self.font_increase)
        
        current_lang = LanguageManager.get_current_language()
        current_index = self.config_language.findData(current_lang)
        if current_index >= 0:
            self.config_language.setCurrentIndex(current_index)
        
        QMessageBox.information(self, LanguageManager.tr("success"), LanguageManager.tr("config_reloaded"))
        logger.info("Configuration reloaded")
    
    def help_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(5)
        
        self.help_tab_title = QLabel(LanguageManager.tr("user_guide_page"))
        self.help_tab_title.font_scale_factor = 1.0
        self.all_widgets.append(self.help_tab_title)
        self.help_tab_title.setStyleSheet("font-size: 32px; font-weight: bold; padding: 8px;")
        layout.addWidget(self.help_tab_title)
        
        self.help_text = QTextEdit()
        self.help_text.setReadOnly(True)
        self.help_text.setText(LanguageManager.tr("help_content"))
        layout.addWidget(self.help_text)
        
        return widget
    
    def monitor_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(3, 3, 3, 3)
        top_layout.setSpacing(5)
        
        self.monitor_tab_title = QLabel(LanguageManager.tr("monitor_system"))
        self.monitor_tab_title.font_scale_factor = 1.0
        self.all_widgets.append(self.monitor_tab_title)
        self.monitor_tab_title.setStyleSheet("font-size: 32px; font-weight: bold; padding: 8px;")
        top_layout.addWidget(self.monitor_tab_title)
        
        control_layout = QHBoxLayout()
        self.btn_start = QPushButton(LanguageManager.tr("start_monitor"))
        self.btn_start.clicked.connect(self.start_monitor)
        self.btn_stop = QPushButton(LanguageManager.tr("stop_monitor"))
        self.btn_stop.clicked.connect(self.stop_monitor)
        self.btn_stop.setEnabled(False)
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        self.status_label = QLabel(LanguageManager.tr("status_stopped"))
        self.status_label.setStyleSheet("color: #FF4444; font-weight: bold;")
        control_layout.addWidget(self.status_label)
        control_layout.addStretch()
        top_layout.addLayout(control_layout)
        
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(3, 0, 3, 3)
        bottom_layout.setSpacing(0)
        
        filter_layout = QHBoxLayout()
        self.monitor_filter_label = QLabel(LanguageManager.tr("log_filter"))
        filter_layout.addWidget(self.monitor_filter_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItem(LanguageManager.tr("filter_all"), "all")
        self.filter_combo.addItem(LanguageManager.tr("filter_recent_15"), "15")
        self.filter_combo.addItem(LanguageManager.tr("filter_recent_30"), "30")
        self.filter_combo.addItem(LanguageManager.tr("filter_recent_50"), "50")
        self.filter_combo.setCurrentIndex(1)
        self.filter_combo.currentIndexChanged.connect(self.filter_logs)
        filter_layout.addWidget(self.filter_combo)
        
        filter_layout.addStretch()
        bottom_layout.addLayout(filter_layout)
        
        splitter_h = QSplitter(Qt.Horizontal)
        self.splitter = splitter_h
        splitter_h.setHandleWidth(8)
        splitter_h.setChildrenCollapsible(False)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(3)
        
        left_title_layout = QHBoxLayout()
        self.monitor_folder_status_label = QLabel(LanguageManager.tr("folder_status"))
        left_title_layout.addWidget(self.monitor_folder_status_label)
        left_title_layout.addStretch()
        left_layout.addLayout(left_title_layout)
        
        self.folder_info = QTextEdit()
        self.folder_info.setReadOnly(True)
        left_layout.addWidget(self.folder_info)
        left_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(3)
        
        right_title_layout = QHBoxLayout()
        self.monitor_recent_label = QLabel(LanguageManager.tr("recent_operations"))
        right_title_layout.addWidget(self.monitor_recent_label)
        right_title_layout.addStretch()
        
        self.btn_add_volume = QPushButton(LanguageManager.tr("add_new_volume"))
        self.btn_add_volume.setStyleSheet("""
            QPushButton {
                background-color: #003300;
                color: #00FF41;
                border: 2px solid #00FF41;
                padding: 8px 16px;
                font-family: "Consolas", "Courier New", monospace;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #005500;
                border: 2px solid #00FF00;
            }
            QPushButton:pressed {
                background-color: #00FF41;
                color: #0D0208;
            }
        """)
        self.btn_add_volume.clicked.connect(self.add_new_volume)
        right_title_layout.addWidget(self.btn_add_volume)
        right_layout.addLayout(right_title_layout)
        
        self.log_info = QTextEdit()
        self.log_info.setReadOnly(True)
        right_layout.addWidget(self.log_info)
        right_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        splitter_h.addWidget(left_widget)
        splitter_h.addWidget(right_widget)
        self.splitter_stretch = [6, 4]
        splitter_h.setStretchFactor(0, 6)
        splitter_h.setStretchFactor(1, 4)
        
        bottom_layout.addWidget(splitter_h)
        
        splitter_v = QSplitter(Qt.Vertical)
        self.splitter_v = splitter_v
        splitter_v.setHandleWidth(6)
        splitter_v.setChildrenCollapsible(False)
        splitter_v.addWidget(top_widget)
        splitter_v.addWidget(bottom_widget)
        splitter_v.setStretchFactor(0, 1)
        splitter_v.setStretchFactor(1, 5)
        
        layout.addWidget(splitter_v)
        
        return widget
    
    def filter_logs(self):
        self.update_log_display()
    
    def update_log_display(self):
        filter_type = self.filter_combo.itemData(self.filter_combo.currentIndex())
        self.log_info.clear()
        
        if filter_type == "all":
            display_messages = self.all_messages
        elif filter_type == "15":
            display_messages = self.all_messages[-15:]
        elif filter_type == "30":
            display_messages = self.all_messages[-30:]
        elif filter_type == "50":
            display_messages = self.all_messages[-50:]
        else:
            display_messages = self.all_messages[-15:]
        
        for msg in display_messages:
            self.log_info.append(msg)
    
    def start_monitor(self):
        # 检查小说目录
        novel_dir = get_novel_dir()
        if not os.path.exists(novel_dir):
            QMessageBox.warning(self, LanguageManager.tr("env_not_initialized"), 
                               f"{LanguageManager.tr('env_init_tip')}\n"
                               f"小说目录：{novel_dir}\n"
                               f"{LanguageManager.tr('dir_not_exist')}")
            return
        
        # 检查是否有卷文件夹
        has_volumes = False
        for item in os.listdir(novel_dir):
            item_path = os.path.join(novel_dir, item)
            if os.path.isdir(item_path) and FileManager.get_volume_number(item):
                has_volumes = True
                break
        
        if not has_volumes:
            QMessageBox.warning(self, LanguageManager.tr("warning"), 
                               f"未找到卷文件夹！\n"
                               f"请先在「参数配置」中选择正确的小说目录，或初始化目录。")
            return
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_label.setText(LanguageManager.tr("status_running"))
        self.status_label.setStyleSheet("color: #00FF41; font-weight: bold;")
        
        self.monitor_thread = MonitorThread()
        self.monitor_thread.update_signal.connect(self.update_monitor_display)
        self.monitor_thread.start()
        
        logger.info("监控已启动")
        self.all_messages.append("[OK] 监控已启动")
        self.update_log_display()
    
    def stop_monitor(self):
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread.wait()
        
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText(LanguageManager.tr("status_stopped"))
        self.status_label.setStyleSheet("color: #FF4444; font-weight: bold;")
        
        logger.info("监控已停止")
        self.all_messages.append("[OK] 监控已停止")
        self.update_log_display()
    
    def update_monitor_display(self, folder_states, messages):
        self.folder_info.clear()
        for folder_name, state in folder_states.items():
            current_max = state['current_max']
            word_count = state.get('word_count', 0)
            is_default = state.get('is_default', True)
            status = state.get('status', '监控中')
            ahead = state.get('ahead_count', 0)
            files = state.get('files', [])
            latest_file = state.get('latest_file', '')
            
            min_word_count = ConfigManager.get_int('Monitor', 'min_word_count', fallback=20)
            status_text = "[OK]" if (not is_default and word_count > min_word_count) else "[--]"
            
            self.folder_info.append(f">>> {folder_name}")
            self.folder_info.append(f"    章: 第{current_max}章 {status_text} | 字数: {word_count}")
            self.folder_info.append(f"    状态: {status} (领先{ahead}章)")
            self.folder_info.append(f"    文件列表:")
            for f in files:
                marker = " <<<" if f == latest_file else ""
                self.folder_info.append(f"      - {f}{marker}")
            self.folder_info.append("")
        
        for msg in messages:
            if msg not in self.all_messages:
                self.all_messages.append(msg)
        
        if len(self.all_messages) > 100:
            self.all_messages = self.all_messages[-100:]
        
        self.update_log_display()
    
    def create_environment(self):
        """创建运行环境 - 已简化，现在直接跳转到参数配置选择目录"""
        QMessageBox.information(self, LanguageManager.tr("parameter_config"), 
                               f"请使用「参数配置」标签页中的「小说目录」功能！\n\n"
                               f"1. 点击「参数配置」标签\n"
                               f"2. 点击「小说目录」旁边的「选择...」按钮\n"
                               f"3. 选择你要存放小说的文件夹\n"
                               f"4. 如果文件夹为空，程序会询问是否自动初始化")
        # 切换到参数配置标签
        self.tabs.setCurrentIndex(3)
    
    def add_new_volume(self):
        """增加新卷功能"""
        try:
            logger.info("=== add_new_volume 开始 ===")
            
            novel_dir = get_novel_dir()
            logger.info(f"当前小说目录: {novel_dir}")
            
            # 检查小说目录是否存在
            if not os.path.exists(novel_dir):
                QMessageBox.warning(self, LanguageManager.tr("warning"), 
                                   f"小说目录不存在！\n目录: {novel_dir}\n请先在「参数配置」中选择正确的目录。")
                return
            
            # 找到当前最大的卷号
            max_vol_num = 0
            try:
                folders = os.listdir(novel_dir)
                logger.info(f"目录内容: {folders}")
            except Exception as e:
                QMessageBox.warning(self, LanguageManager.tr("warning"), 
                                   f"无法读取目录内容！请检查权限。\n错误: {str(e)}")
                return
            
            for folder_name in folders:
                folder_path = os.path.join(novel_dir, folder_name)
                if os.path.isdir(folder_path):
                    vol_num = FileManager.get_volume_number(folder_name)
                    logger.info(f"检查文件夹: {folder_name}, 卷号: {vol_num}")
                    if vol_num and vol_num > max_vol_num:
                        max_vol_num = vol_num
            
            if max_vol_num == 0:
                QMessageBox.warning(self, LanguageManager.tr("warning"), 
                                   f"没有找到卷文件夹！\n"
                                   f"当前目录: {novel_dir}\n"
                                   f"请确认这是正确的小说目录，或先初始化目录。")
                return
            
            new_vol_num = max_vol_num + 1
            logger.info(f"Current max volume: {max_vol_num}, new volume: {new_vol_num}")
            
            # 创建新卷文件夹（简单数字命名）
            new_folder_name = str(new_vol_num)
            new_folder_path = os.path.join(novel_dir, new_folder_name)
            
            if os.path.exists(new_folder_path):
                QMessageBox.warning(self, LanguageManager.tr("warning"), 
                                   LanguageManager.tr("folder_exists").format(new_folder_name))
                return
            
            os.makedirs(new_folder_path)
            self.all_messages.append(f"[NEW] 创建新卷文件夹: {new_folder_name}")
            logger.info(f"创建新卷文件夹: {new_folder_path}")
            
            # 如果监控正在运行，让它自动处理
            if self.monitor_thread and self.monitor_thread.isRunning():
                QMessageBox.information(self, LanguageManager.tr("success"), 
                    f"New volume {new_vol_num} created!\n"
                    f"{LanguageManager.tr('monitor_auto_process')}")
            else:
                QMessageBox.information(self, LanguageManager.tr("success"), 
                    f"New volume {new_vol_num} created!\n"
                    f"{LanguageManager.tr('start_monitor_process')}")
            
            self.update_log_display()
            
        except Exception as e:
            logger.error(f"Failed to add new volume: {e}")
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, LanguageManager.tr("error"), f"{LanguageManager.tr('add_volume_failed')}: {str(e)}")
    
    def safe_exit(self):
        reply = QMessageBox.question(self, LanguageManager.tr("confirm_exit"), 
                                     LanguageManager.tr("exit_confirm_msg"),
                                     QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()
    
    def closeEvent(self, event):
        self.save_settings()
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
            self.monitor_thread.wait()
        logger.info("NovelHelper 关闭")
        event.accept()

if __name__ == "__main__":
    LanguageManager.generate_ini_file()
    app = QApplication(sys.argv)
    window = NovelHelper()
    window.show()
    sys.exit(app.exec_())
