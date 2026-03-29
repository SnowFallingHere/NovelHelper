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
    """获取根目录 - NovelStorage目录"""
    script_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(script_path)
    
    while current_dir:
        if os.path.basename(current_dir) == "novel":
            return os.path.dirname(current_dir)
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent
    
    return None

NOVEL_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = get_base_dir() or os.path.dirname(NOVEL_DIR)
ALL_DIR = os.path.join(BASE_DIR, "all") if BASE_DIR else os.path.join(os.path.dirname(NOVEL_DIR), "all")
LOG_DIR = os.path.join(NOVEL_DIR, "log")

UI_REFRESH_INTERVAL = 500

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

log_file = os.path.join(LOG_DIR, f"NovelHelper_{datetime.now().strftime('%Y%m%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    from cn2an import an2cn
except ImportError:
    logger.error("缺少必要的库: cn2an，请运行 pip install cn2an")
    sys.exit(1)

class FileManager:
    @staticmethod
    def get_chapter_number(filename):
        match = re.match(r'^(\d+)', filename)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def find_latest_chapter(folder_path):
        try:
            files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
            if not files:
                return None
            max_num = 0
            latest_file = None
            for f in files:
                num = FileManager.get_chapter_number(f)
                if num and num > max_num:
                    max_num = num
                    latest_file = f
            return max_num, latest_file
        except Exception:
            return None

    @staticmethod
    def find_next_chapter_in_all(target_chapter_num):
        try:
            chinese_num = an2cn(str(target_chapter_num)) + "章"
            target_filename = f"{target_chapter_num}第{chinese_num}_name.txt"
            target_path = os.path.join(ALL_DIR, target_filename)
            if os.path.exists(target_path):
                return target_path, target_chapter_num
            return None, target_chapter_num
        except Exception:
            return None, target_chapter_num

    @staticmethod
    def get_folder_number(folder_name):
        match = re.match(r'^(\d+)\[', folder_name)
        if match:
            return int(match.group(1))
        return None

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

    @staticmethod
    def get_word_count(file_path):
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

    @staticmethod
    def get_folder_files(folder_path):
        try:
            files = sorted([f for f in os.listdir(folder_path) if f.endswith('.txt')], 
                          key=lambda x: (FileManager.get_folder_number(x) is None, FileManager.get_chapter_number(x) or float('inf')))
            return files
        except Exception:
            return []

    @staticmethod
    def copy_and_rename_internal(source_path, dest_folder, chapter_num):
        try:
            chinese_num = an2cn(str(chapter_num)) + "章"
            new_filename = f"{chapter_num}第{chinese_num}_.txt"
            dest_path = os.path.join(dest_folder, new_filename)
            if os.path.exists(dest_path):
                return False, new_filename, "文件已存在"
            shutil.copy2(source_path, dest_path)
            return True, new_filename, None
        except Exception as e:
            return False, None, str(e)

    @staticmethod
    def ensure_ahead_chapters_internal(folder_name, folder_path, current_max, messages, max_ahead_chapters=2):
        added_count = 0
        added_files = []
        for add_num in range(current_max + 1, current_max + max_ahead_chapters + 1):
            chinese_num = an2cn(str(add_num)) + "章"
            target_filename = f"{add_num}第{chinese_num}_.txt"
            target_path = os.path.join(folder_path, target_filename)
            
            if os.path.exists(target_path):
                continue
            
            source_path, _ = FileManager.find_next_chapter_in_all(add_num)
            if source_path:
                success, new_filename, error = FileManager.copy_and_rename_internal(source_path, folder_path, add_num)
                if success:
                    added_count += 1
                    added_files.append(new_filename)
                else:
                    if error == "文件已存在":
                        logger.warning(f"{folder_name}: 复制第{add_num}章失败 - {error}")
                    else:
                        logger.error(f"{folder_name}: 复制第{add_num}章失败 - {error}")
                    messages.append(f"[WARN] {folder_name}: 复制第{add_num}章失败")
        if added_count > 0:
            messages.append(f"[NEW] {folder_name}: 新增{added_count}章")
        return added_count

    @staticmethod
    def num_to_chinese(num):
        """统一数字转中文 - 使用an2cn"""
        return an2cn(str(num))

    @staticmethod
    def convert_num_to_chinese(num):
        """统一数字转中文（带章） - 使用an2cn"""
        return an2cn(str(num)) + "章"
    
    @staticmethod
    def is_numeric_volume_folder(folder_name):
        match = re.match(r'^(\d+)', folder_name)
        return match is not None
    
    @staticmethod
    def get_volume_number(folder_name):
        match = re.match(r'^(\d+)', folder_name)
        if match:
            return int(match.group(1))
        return None
    
    @staticmethod
    def is_old_volume(folder_name):
        return '[old_' in folder_name

class ConfigManager:
    """配置管理器 - 负责加载、缓存和保存应用配置"""
    
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "NovelHelper.ini")
    _config_cache = None
    _cache_dirty = False
    
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
            'min_word_count': '20'
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
        if os.path.exists(cls.CONFIG_FILE):
            config.read(cls.CONFIG_FILE, encoding='utf-8')
        else:
            cls.create_default_config()
            config.read(cls.CONFIG_FILE, encoding='utf-8')
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
        with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
        logger.info(f"已创建默认配置文件: {cls.CONFIG_FILE}")
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
        with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
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
            'no_volume_folders': '未找到任何卷文件夹！',
            'folder_exists': '文件夹 {0} 已存在！',
            'generating_chapters': '正在生成 {0} 章模板...',
            'help_content': """【一、正确的放置位置
-------------------
NovelHelper.py 必须放置在以下结构中：
NovelStorage/
├─ novel/
│  ├─ 你的小说文件夹/
│  │  ├─ 1[第一卷]/
│  │  │  ├─ 1第...txt
│  │  │  └─ ...
│  │  ├─ 2[第二卷]/
│  │  │  └─ ...
│  │  └─ NovelHelper.py  ← 放在这里！
│  └─ ...
└─ all/  ← 素材库文件夹

【二、功能说明
-----------
1. 创建章节
   - 用于在 all 素材库中创建章节模板文件
   - 起始和结束章节必须是正整数
   - 文件后缀默认为 "name"
   - 如果文件已存在会自动跳过

2. Summary合并
   - 统计所有卷目录
   - 合并章节为一个完整文件
   - 可选择是否重命名文件夹（加上字数后缀）

3. 监控管理
   - 自动监控小说文件夹
   - 检测到最新章节被编写后自动新增2章
   - 每到2的倍数章节自动触发Summary
   - 日志可筛选查看数量

【三、注意事项与风险
-------------------
⚠️  重要警告！

1. 文件备份
   - 使用前务必备份重要数据！
   - 建议将整个 NovelStorage 文件夹复制一份
   - 误操作可能导致文件被覆盖

2. 文件夹命名格式
   - 卷文件夹必须符合：数字[卷名]
   - 例如：1[第一卷]、2[第二卷]
   - 不符合格式的文件夹会被忽略

3. 章节文件命名
   - 章节文件必须符合：数字第...txt
   - 例如：1第...txt、2第...txt
   - 不符合格式的章节会被忽略

4. 不要随意删除文件
   - 监控运行时不要随意删除章节文件
   - 删除可能导致监控异常
   - 如需删除请先停止监控

5. 权限问题
   - 确保有文件夹和文件有读写权限
   - 确保磁盘有足够空间

6. Summary功能
   - Summary会生成未定.txt
   - 重命名模式会修改文件夹名
   - 使用前确认备份！

7. 监控功能
   - 监控每15秒检查一次
   - 自动新增领先2章
   - 默认内容字数超过20字触发
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
            'help_content': """1. Correct Placement
-------------------
NovelHelper.py must be placed in the following structure:
NovelStorage/
├─ novel/
│  ├─ your_novel_folder/
│  │  ├─ 1[Volume 1]/
│  │  │  ├─ 1Chapter...txt
│  │  │  └─ ...
│  │  ├─ 2[Volume 2]/
│  │  │  └─ ...
│  │  └─ NovelHelper.py  ← Place here!
│  └─ ...
└─ all/  ← Material library folder

2. Function Description
-------------------
1. Create Chapters
   - Used to create chapter template files in the all material library
   - Start and end chapters must be positive integers
   - Default file suffix is "name"
   - Automatically skips existing files

2. Summary Merge
   - Statistics all volume directories
   - Merges chapters into a complete file
   - Can choose whether to rename folders (add word count suffix)

3. Monitor Management
   - Automatically monitors novel folders
   - Automatically adds 2 chapters when latest chapter is written
   - Auto-triggers Summary at every multiple of 2 chapter
   - Logs can be filtered by count

3. Notes and Risks
-------------------
⚠️  Important Warning!

1. File Backup
   - Always backup important data before use!
   - Recommend copying entire NovelStorage folder
   - Mistakes may overwrite files

2. Folder Naming Format
   - Volume folders must follow: number[volume name]
   - Example: 1[Volume 1], 2[Volume 2]
   - Folders not matching format are ignored

3. Chapter File Naming
   - Chapter files must follow: numberChapter...txt
   - Example: 1Chapter...txt, 2Chapter...txt
   - Chapters not matching format are ignored

4. Don't Delete Files Arbitrarily
   - Don't delete chapter files while monitor is running
   - Deletion may cause monitor anomalies
   - Stop monitor first if you need to delete

5. Permissions Issues
   - Ensure read/write permissions for folders and files
   - Ensure sufficient disk space

6. Summary Function
   - Summary generates pending.txt
   - Rename mode modifies folder names
   - Confirm backup before use!

7. Monitor Function
   - Monitor checks every 15 seconds
   - Auto-adds 2 leading chapters
   - Triggers when default content exceeds 20 words
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
            'help_content': """一、正しい配置場所
-------------------
NovelHelper.py は以下の構造に配置する必要があります：
NovelStorage/
├─ novel/
│  ├─ あなたの小説フォルダ/
│  │  ├─ 1[第一巻]/
│  │  │  ├─ 1第...txt
│  │  │  └─ ...
│  │  ├─ 2[第二巻]/
│  │  │  └─ ...
│  │  └─ NovelHelper.py  ← ここに配置！
│  └─ ...
└─ all/  ← 素材ライブラリフォルダ

二、機能説明
-----------
1. 章作成
   - all 素材ライブラリに章テンプレートファイルを作成するために使用
   - 開始章と終了章は正の整数である必要があります
   - ファイル接尾辞のデフォルトは "name"
   - ファイルが既に存在する場合は自動的にスキップ

2. Summaryマージ
   - すべての巻ディレクトリを統計
   - 章を1つの完全なファイルにマージ
   - フォルダ名を変更するかどうかを選択可能（文字数接尾辞を追加）

3. 監視管理
   - 小説フォルダを自動監視
   - 最新の章が書かれたことを検出すると自動的に2章を追加
   - 2の倍数の章ごとに自動的にSummaryをトリガー
   - ログは件数でフィルタリング可能

三、注意事項とリスク
-------------------
⚠️  重要な警告！

1. ファイルバックアップ
   - 使用前に必ず重要なデータをバックアップしてください！
   - NovelStorage フォルダ全体をコピーすることを推奨
   - 誤操作によりファイルが上書きされる可能性があります

2. フォルダ名の形式
   - 巻フォルダは「数字[巻名]」の形式に従う必要があります
   - 例：1[第一巻]、2[第二巻]
   - 形式に合わないフォルダは無視されます

3. 章ファイルの命名
   - 章ファイルは「数字第...txt」の形式に従う必要があります
   - 例：1第...txt、2第...txt
   - 形式に合わない章は無視されます

4. ファイルを勝手に削除しないでください
   - 監視実行中は章ファイルを勝手に削除しないでください
   - 削除により監視が異常になる可能性があります
   - 削除が必要な場合は先に監視を停止してください

5. 権限の問題
   - フォルダとファイルの読み書き権限があることを確認してください
   - ディスクに十分な空きがあることを確認してください

6. Summary機能
   - Summaryは未定.txtを生成します
   - 名前変更モードはフォルダ名を変更します
   - 使用前にバックアップを確認してください！

7. 監視機能
   - 監視は15秒ごとにチェックします
   - 自動的に2章先まで追加します
   - デフォルトの内容が20文字を超えるとトリガーします
""",
        }
    }
    
    @classmethod
    def generate_ini_file(cls):
        config_path = os.path.join(os.path.dirname(__file__), 'NovelHelper.ini')
        if os.path.exists(config_path):
            return
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write('[Language]\n')
            f.write('current = en_US\n\n')
            
            for lang_code, translations in cls.DEFAULT_TRANSLATIONS.items():
                f.write(f'[Language_{lang_code}]\n')
                for key, value in translations.items():
                    f.write(f'{key} = {value}\n')
                f.write('\n')
    
    @classmethod
    def load_available_languages(cls):
        cls._available_languages = []
        for key in ConfigManager.load_config().sections():
            if key.startswith('Language_') and key != 'Language':
                lang_code = key.replace('Language_', '')
                cls._available_languages.append(lang_code)
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
            folders = sorted(os.listdir(NOVEL_DIR), key=lambda x: (FileManager.get_volume_number(x) is None, FileManager.get_volume_number(x) or float('inf')))
            for folder_name in folders:
                folder_path = os.path.join(NOVEL_DIR, folder_name)
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
            folders = sorted(os.listdir(NOVEL_DIR), key=lambda x: (FileManager.get_volume_number(x) is None, FileManager.get_volume_number(x) or float('inf')))
            
            processed_new_folder = False
            max_ahead_chapters = self.get_max_ahead_chapters()
            
            # 先检查是否有简单数字命名的新文件夹（可能是空的）
            for folder_name in folders:
                folder_path = os.path.join(NOVEL_DIR, folder_name)
                if not os.path.isdir(folder_path):
                    continue
                folder_num = FileManager.get_volume_number(folder_name)
                
                # 条件：简单数字命名（没有[xxx]后缀）
                if folder_num and not ('[' in folder_name and ']' in folder_name):
                    if self.process_new_volume_folder(folder_name, folder_path, folder_num, max_ahead_chapters):
                        processed_new_folder = True
            
            # 重新获取文件夹列表，因为重命名了
            if processed_new_folder:
                folders = sorted(os.listdir(NOVEL_DIR), key=lambda x: (FileManager.get_volume_number(x) is None, FileManager.get_volume_number(x) or float('inf')))
            # 正常处理文件夹
            for folder_name in folders:
                if not self.running:
                    break
                folder_path = os.path.join(NOVEL_DIR, folder_name)
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
            for f in os.listdir(NOVEL_DIR):
                f_path = os.path.join(NOVEL_DIR, f)
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
            
            # 步骤5：从 start_chapter+1 开始复制 max_ahead_chapters 章到新文件夹
            added_count = 0
            for add_num in range(start_chapter + 1, start_chapter + max_ahead_chapters + 1):
                chinese_num = FileManager.num_to_chinese(add_num)
                
                source_filename = f"{add_num}第{chinese_num}章_name.txt"
                source_path = os.path.join(ALL_DIR, source_filename)
                
                dest_filename = f"{add_num}第{chinese_num}章_.txt"
                dest_path = os.path.join(folder_path, dest_filename)
                
                if os.path.exists(source_path):
                    try:
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
                        shutil.copy2(source_path, dest_path)
                        added_count += 1
                        self.messages.append(f"[NEW] {folder_name}: 新增第{add_num}章")
                    except Exception as e:
                        logger.error(f"复制章节失败 {add_num}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                else:
                    logger.error(f"源文件不存在: {source_path}")
            
            # 步骤6：重命名上一卷为 old
            prev_name = os.path.basename(prev_folder)
            if '[new_' in prev_name:
                try:
                    old_name = re.sub(r'\[new_(\d+)\]$', f'[old_{total_words}]', prev_name)
                    new_path = os.path.join(NOVEL_DIR, old_name)
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
            new_folder_final_path = os.path.join(NOVEL_DIR, new_folder_final_name)
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
        if hasattr(self, 'config_language_group'):
            self.config_language_group.setTitle(LanguageManager.tr("language_config"))
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
        self.output_dir.setText(ALL_DIR)
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
        dir_path = QFileDialog.getExistingDirectory(self, LanguageManager.tr("select_directory"), ALL_DIR)
        if dir_path:
            self.output_dir.setText(dir_path)
    
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
                chinese_num = FileManager.convert_num_to_chinese(i)
                filename = f"{i}第{chinese_num}_{suffix}.txt"
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
        if not os.path.exists(ALL_DIR):
            QMessageBox.warning(self, LanguageManager.tr("env_not_initialized"), 
                               f"{LanguageManager.tr('env_init_tip')}\n"
                               f"当前目录：{NOVEL_DIR}\n"
                               f"{LanguageManager.tr('dir_not_exist')}")
            return
        
        mode = 1 if self.mode1.isChecked() else 2
        self.summary_result.clear()
        self.progress_bar.setValue(10)
        
        folder_path = NOVEL_DIR
        folder_name = os.path.basename(NOVEL_DIR)
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
                            chapter_title = f"-----【第{num}章-{chapter_name}】-----"
                            
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
                    chinese_vol = FileManager.num_to_chinese(vol_num)
                    vol_word_count = volume_non_blank_count[vol_num]
                    vol_title = f"-----【第{chinese_vol}卷{f'·{vol_name}' if vol_name else ''}: {vol_word_count}】-----"
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
        self.config_language_note.setStyleSheet("color: #888888; font-size: 12px;")
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
            
            ConfigManager.set('Adaptive', 'area_scale_factor', self.config_area_scale.value())
            ConfigManager.set('Adaptive', 'height_scale_factor', self.config_height_scale.text())
            ConfigManager.set('Adaptive', 'font_increase', self.config_font_increase.value())
            
            selected_lang = self.config_language.currentData()
            if selected_lang:
                ConfigManager.set('Language', 'current', selected_lang)
                LanguageManager._translations = {}
                LanguageManager._current_lang = selected_lang
            
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
            
            ConfigManager.set('Adaptive', 'area_scale_factor', self.config_area_scale.value())
            ConfigManager.set('Adaptive', 'height_scale_factor', self.config_height_scale.text())
            ConfigManager.set('Adaptive', 'font_increase', self.config_font_increase.value())
            
            selected_lang = self.config_language.currentData()
            if selected_lang:
                ConfigManager.set('Language', 'current', selected_lang)
                LanguageManager._translations = {}
                LanguageManager._current_lang = selected_lang
            
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
        if not os.path.exists(ALL_DIR):
            QMessageBox.warning(self, LanguageManager.tr("env_not_initialized"), 
                               f"{LanguageManager.tr('env_init_tip')}\n"
                               f"当前目录：{NOVEL_DIR}\n"
                               f"{LanguageManager.tr('dir_not_exist')}")
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
        reply = QMessageBox.question(self, LanguageManager.tr("confirm_creation"), 
                                     f"{LanguageManager.tr('creating_runtime_env')}\n"
                                     f"{LanguageManager.tr('create_folders')}\n"
                                     f"{LanguageManager.tr('generate_templates')}\n"
                                     f"{LanguageManager.tr('create_title_folder')}\n"
                                     f"{LanguageManager.tr('copy_first_10')}\n\n"
                                     f"{LanguageManager.tr('continue_question')}",
                                     QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        
        try:
            config = ConfigManager.load_config()
            init_chapter_count = config.getint('Environment', 'init_chapter_count', fallback=2000)
            init_copy_count = config.getint('Environment', 'init_copy_count', fallback=10)
            
            current_script = os.path.abspath(__file__)
            current_dir = os.path.dirname(current_script)
            
            base_dir = current_dir
            
            all_dir = os.path.join(base_dir, 'all')
            novel_dir = os.path.join(base_dir, 'novel')
            title_dir = os.path.join(novel_dir, 'title')
            title_log_dir = os.path.join(title_dir, 'log')
            title_volume_dir = os.path.join(title_dir, '1')
            
            if not os.path.exists(all_dir):
                os.makedirs(all_dir)
                logger.info(f"创建目录: {all_dir}")
            
            if not os.path.exists(novel_dir):
                os.makedirs(novel_dir)
                logger.info(f"创建目录: {novel_dir}")
            
            if not os.path.exists(title_dir):
                os.makedirs(title_dir)
                logger.info(f"创建目录: {title_dir}")
            
            if not os.path.exists(title_log_dir):
                os.makedirs(title_log_dir)
                logger.info(f"创建目录: {title_log_dir}")
            
            if not os.path.exists(title_volume_dir):
                os.makedirs(title_volume_dir)
                logger.info(f"创建目录: {title_volume_dir}")
            
            QMessageBox.information(self, LanguageManager.tr("progress"), f"Generating {init_chapter_count} chapter templates...")
            
            for i in range(1, init_chapter_count + 1):
                chinese_num = FileManager.num_to_chinese(i)
                filename = f"{i}第{chinese_num}章_name.txt"
                file_path = os.path.join(all_dir, filename)
                if not os.path.exists(file_path):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(f"第{i}个文件\n")
            
            logger.info(f"已在 all/ 生成 {init_chapter_count} 章模板")
            
            for i in range(1, init_copy_count + 1):
                chinese_num = FileManager.num_to_chinese(i)
                source_filename = f"{i}第{chinese_num}章_name.txt"
                source_path = os.path.join(all_dir, source_filename)
                dest_filename = f"{i}第{chinese_num}章_.txt"
                dest_path = os.path.join(title_volume_dir, dest_filename)
                if os.path.exists(source_path) and not os.path.exists(dest_path):
                    shutil.copy2(source_path, dest_path)
            
            logger.info(f"已复制 {init_copy_count} 章到 {title_volume_dir}")
            
            new_script_path = os.path.join(title_dir, 'NovelHelper.py')
            new_script_name = 'NovelHelper.py'
            current_script_name = os.path.basename(current_script)
            
            if current_script != new_script_path:
                shutil.copy2(current_script, new_script_path)
                logger.info(f"已复制程序到 {new_script_path}")
                
                delete_marker = os.path.join(current_dir, 'NovelHelper_delete_me.py')
                try:
                    if current_script != delete_marker:
                        if os.path.exists(delete_marker):
                            os.remove(delete_marker)
                        os.rename(current_script, delete_marker)
                        ConfigManager.set('Environment', 'pending_delete', '1')
                        ConfigManager.set('Environment', 'old_dir', current_dir)
                        old_ini = os.path.join(current_dir, 'NovelHelper.ini')
                        old_ini_delete = os.path.join(current_dir, 'NovelHelper_delete_me.ini')
                        if os.path.exists(old_ini) and not os.path.exists(old_ini_delete):
                            try:
                                os.rename(old_ini, old_ini_delete)
                                logger.info(f"已将旧ini文件标记为删除: {old_ini_delete}")
                            except Exception as e:
                                logger.warning(f"重命名ini文件失败: {e}")
                        logger.info(f"已将旧程序标记为删除: {delete_marker}")
                except Exception as e:
                    logger.warning(f"标记删除旧程序失败: {e}")
                
                QMessageBox.information(self, LanguageManager.tr("success"), 
                                         f"Runtime environment created successfully!\n\n"
                                         f"Directory structure:\n"
                                         f"  {all_dir}\n"
                                         f"  {novel_dir}\n"
                                         f"  {title_dir}\n"
                                         f"  {title_log_dir}\n"
                                         f"  {title_volume_dir}\n\n"
                                         f"Program moved to: {title_dir}")
                
                reply = QMessageBox.question(self, LanguageManager.tr("start_new_program"), 
                                             LanguageManager.tr("start_program_now_question"),
                                             QMessageBox.Yes | QMessageBox.No,
                                             QMessageBox.No)
                
                if reply == QMessageBox.Yes:
                    try:
                        import subprocess
                        env = os.environ.copy()
                        env['NOVEL_OLD_DIR'] = current_dir
                        subprocess.Popen([sys.executable, new_script_path], 
                                        cwd=title_dir,
                                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                                        env=env)
                        logger.info(f"已启动新程序: {new_script_path}")
                        QTimer.singleShot(500, self.close)
                    except Exception as e:
                        logger.error(f"Failed to start new program: {e}")
                        QMessageBox.critical(self, LanguageManager.tr("error"), f"Failed to start new program: {str(e)}")
            else:
                QMessageBox.information(self, LanguageManager.tr("success"), 
                                         f"Runtime environment created successfully!\n\n"
                                         f"Directory structure:\n"
                                         f"  {all_dir}\n"
                                         f"  {novel_dir}\n"
                                         f"  {title_dir}\n"
                                         f"  {title_log_dir}\n"
                                         f"  {title_volume_dir}\n\n"
                                         f"Program is already in the correct location.")
            
        except Exception as e:
            logger.error(f"Failed to create runtime environment: {e}")
            QMessageBox.critical(self, LanguageManager.tr("error"), f"Failed to create runtime environment: {str(e)}")
    
    def add_new_volume(self):
        """增加新卷功能"""
        try:
            logger.info("=== add_new_volume 开始 ===")
            # 找到当前最大的卷号
            max_vol_num = 0
            folders = os.listdir(NOVEL_DIR)
            for folder_name in folders:
                folder_path = os.path.join(NOVEL_DIR, folder_name)
                if os.path.isdir(folder_path):
                    vol_num = FileManager.get_volume_number(folder_name)
                    if vol_num and vol_num > max_vol_num:
                        max_vol_num = vol_num
            
            if max_vol_num == 0:
                QMessageBox.warning(self, LanguageManager.tr("warning"), "No volume folders found!")
                return
            
            new_vol_num = max_vol_num + 1
            logger.info(f"Current max volume: {max_vol_num}, new volume: {new_vol_num}")
            
            # 创建新卷文件夹（简单数字命名）
            new_folder_name = str(new_vol_num)
            new_folder_path = os.path.join(NOVEL_DIR, new_folder_name)
            
            if os.path.exists(new_folder_path):
                QMessageBox.warning(self, LanguageManager.tr("warning"), f"Folder {new_folder_name} already exists!")
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

def cleanup_old_program():
    old_dir = os.environ.get('NOVEL_OLD_DIR', '')
    
    if not old_dir:
        try:
            config = ConfigManager.load_config()
            old_dir = config.get('Environment', 'old_dir', fallback='')
        except:
            old_dir = ''
    
    if not old_dir:
        print("[CLEANUP] 未找到旧程序目录，跳过清理")
        return
    
    delete_marker = os.path.join(old_dir, 'NovelHelper_delete_me.py')
    
    try:
        config = ConfigManager.load_config()
        pending_delete = config.get('Environment', 'pending_delete', fallback='0')
    except:
        pending_delete = '0'
    
    if pending_delete == '1':
        import time
        import glob
        import shutil
        
        print(f"[CLEANUP] 检测到需要清理旧程序，路径: {old_dir}")
        
        for attempt in range(10):
            try:
                time.sleep(2.0)
                
                success = True
                
                # 1. 删除旧日志文件
                old_logs = glob.glob(os.path.join(old_dir, 'NovelHelper_*.log'))
                for log_file in old_logs:
                    try:
                        os.remove(log_file)
                        print(f"[CLEANUP] 已删除旧日志: {log_file}")
                    except:
                        pass
                
                # 2. 删除标记的旧程序
                old_program = os.path.join(old_dir, 'NovelHelper_delete_me.py')
                if os.path.exists(old_program):
                    try:
                        os.remove(old_program)
                        print(f"[CLEANUP] 已删除旧程序: {old_program}")
                    except PermissionError:
                        print(f"[CLEANUP] 第{attempt+1}次尝试：文件被占用，继续等待...")
                        success = False
                    except Exception as e:
                        print(f"[CLEANUP] 删除程序异常: {e}")
                        time.sleep(1)
                        success = False
                
                # 3. 删除标记的旧ini文件
                old_ini = os.path.join(old_dir, 'NovelHelper_delete_me.ini')
                if os.path.exists(old_ini):
                    try:
                        os.remove(old_ini)
                        print(f"[CLEANUP] 已删除旧ini文件: {old_ini}")
                    except:
                        pass
                
                # 4. 删除旧log文件夹（不管是否重命名）
                old_log_dir = os.path.join(old_dir, 'log')
                if os.path.exists(old_log_dir):
                    try:
                        shutil.rmtree(old_log_dir)
                        print(f"[CLEANUP] 已删除旧log文件夹: {old_log_dir}")
                    except Exception as e:
                        print(f"[CLEANUP] 删除log文件夹异常: {e}")
                # 同时也检查是否有标记的log文件夹
                old_log_dir_delete = os.path.join(old_dir, 'log_delete_me')
                if os.path.exists(old_log_dir_delete):
                    try:
                        shutil.rmtree(old_log_dir_delete)
                        print(f"[CLEANUP] 已删除标记的旧log文件夹: {old_log_dir_delete}")
                    except Exception as e:
                        print(f"[CLEANUP] 删除标记log文件夹异常: {e}")
                
                if success:
                    ConfigManager.set('Environment', 'pending_delete', '0')
                    ConfigManager.set('Environment', 'old_dir', '')
                    print(f"[CLEANUP] 清理完成")
                    break
            except Exception as e:
                if attempt == 9:
                    print(f"[CLEANUP] 清理失败: {e}")
                time.sleep(1)
    else:
        # 清理任何标记为delete的残留文件和文件夹
        try:
            import shutil
            import glob
            # 清理旧程序
            if os.path.exists(delete_marker):
                try:
                    os.remove(delete_marker)
                    print(f"[CLEANUP] 已删除残留旧程序: {delete_marker}")
                except:
                    pass
            # 清理旧ini文件
            old_ini_delete = os.path.join(old_dir, 'NovelHelper_delete_me.ini') if old_dir else ''
            if old_ini_delete and os.path.exists(old_ini_delete):
                try:
                    os.remove(old_ini_delete)
                    print(f"[CLEANUP] 已删除残留旧ini: {old_ini_delete}")
                except:
                    pass
            # 清理旧log文件夹
            old_log_dir = os.path.join(old_dir, 'log') if old_dir else ''
            if old_log_dir and os.path.exists(old_log_dir):
                try:
                    shutil.rmtree(old_log_dir)
                    print(f"[CLEANUP] 已删除残留旧log文件夹: {old_log_dir}")
                except:
                    pass
            old_log_dir_delete = os.path.join(old_dir, 'log_delete_me') if old_dir else ''
            if old_log_dir_delete and os.path.exists(old_log_dir_delete):
                try:
                    shutil.rmtree(old_log_dir_delete)
                    print(f"[CLEANUP] 已删除残留标记log文件夹: {old_log_dir_delete}")
                except:
                    pass
            # 清理旧日志文件
            if old_dir:
                old_logs = glob.glob(os.path.join(old_dir, 'NovelHelper_*.log'))
                for log_file in old_logs:
                    try:
                        os.remove(log_file)
                        print(f"[CLEANUP] 已删除残留旧日志: {log_file}")
                    except:
                        pass
        except:
            pass

if __name__ == "__main__":
    cleanup_old_program()
    LanguageManager.generate_ini_file()
    app = QApplication(sys.argv)
    window = NovelHelper()
    window.show()
    sys.exit(app.exec_())
