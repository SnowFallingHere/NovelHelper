import os
import sys
import re
import shutil
import logging
from cn2an import an2cn
from .config_manager import ConfigManager

logger = logging.getLogger(__name__)


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCRIPT_DIR = get_base_dir()


def get_novel_dir():
    try:
        config = ConfigManager.load_config()
        custom_novel_dir = config.get('Monitor', 'novel_dir', fallback='')
        if custom_novel_dir and os.path.isdir(custom_novel_dir):
            return custom_novel_dir
    except Exception:
        pass
    return SCRIPT_DIR


def get_all_dir():
    novel_dir = get_novel_dir()
    return os.path.join(novel_dir, "all")


class FileManager:
    def __init__(self, lang='zh_CN'):
        self._current_lang = lang
        self._custom_export_format = None
        self._custom_detect_formats = None
        self._custom_export_volume_format = None
        self._custom_export_chapter_format = None
        self._load_custom_formats()

    def set_language(self, lang):
        self._current_lang = lang
        self._load_custom_formats()

    def _load_custom_formats(self):
        config = ConfigManager.load_config()
        self._custom_export_format = config.get('Format', 'export_format', fallback=None)
        detect_str = config.get('Format', 'detect_formats', fallback=None)
        if detect_str:
            self._custom_detect_formats = [f.strip() for f in detect_str.split('|')]
        else:
            self._custom_detect_formats = None
        self._custom_export_volume_format = config.get('Format', 'export_volume_format', fallback=None)
        self._custom_export_chapter_format = config.get('Format', 'export_chapter_format', fallback=None)

    def get_chapter_number(self, filename):
        match = re.match(r'^(\d+)', filename)
        if match:
            return int(match.group(1))
        return None

    def find_latest_chapter(self, folder_path):
        try:
            files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
            if not files:
                return None
            max_num = 0
            latest_file = None
            for f in files:
                num = self.get_chapter_number(f)
                if num and num > max_num:
                    max_num = num
                    latest_file = f
            return max_num, latest_file
        except Exception:
            return None

    def _format_chapter(self, fmt, chapter_num, title=""):
        num_str = str(chapter_num)
        zh_num_low = self.num_to_chinese(chapter_num)
        zh_num_up = self.num_to_chinese_upper(chapter_num)

        result = fmt

        if '{num}' not in fmt:
            result = '{num}' + result

        result = result.replace('{cn.up.Chapter}', f'第{zh_num_up}章')
        result = result.replace('{cn.low.Chapter}', f'第{zh_num_low}章')
        result = result.replace('{cn.num.Chapter}', f'第{num_str}章')
        result = result.replace('{en.Chapter}', f'Chapter{num_str}')
        result = result.replace('{jp.Chapter}', f'第{zh_num_low}章')

        if title:
            result = result.replace('{title}', f'_{title}')
            result = result.replace('{name}', f'_{title}')
        else:
            if '{title}' in result:
                result = result.replace('{title}', '_')
            if '{name}' in result:
                result = result.replace('{name}', '_')

        result = result.replace('{num}', num_str)

        types_match = re.search(r'\{types:([^}]+)\}', result)
        if types_match:
            ext_raw = types_match.group(1)
            EXT_MAP = {'markdown': 'md', 'mdown': 'md', 'text': 'txt'}
            ext = EXT_MAP.get(ext_raw.lower(), ext_raw)
            result = result.replace(f'{{types:{ext_raw}}}', f'.{ext}')
        else:
            result = result + '.txt'

        return result

    def generate_chapter_name(self, chapter_num, title=""):
        if self._custom_export_format:
            return self._format_chapter(self._custom_export_format, chapter_num, title)

        lang = self._current_lang
        num_str = str(chapter_num)
        if lang == 'en_US':
            chapter_word = f"Chapter{chapter_num}"
            return f"{num_str}[{chapter_word}]_{title}.txt"
        else:
            chapter_word = self.num_to_chinese(chapter_num) + "章"
            return f"{num_str}第{chapter_word}_{title}.txt"

    def _format_export(self, fmt, num, name="", word_count=None):
        num_str = str(num)
        zh_num_low = self.num_to_chinese(num)
        zh_num_up = self.num_to_chinese_upper(num)

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

    def format_volume_title_export(self, volume_num, volume_name, word_count):
        export_fmt = self._custom_export_volume_format
        if export_fmt:
            return self._format_export(export_fmt, volume_num, volume_name, word_count)
        return f'-----【第{volume_num}卷·{volume_name}:{word_count}】-----'

    def format_chapter_title_export(self, chapter_num, chapter_name):
        export_fmt = self._custom_export_chapter_format
        if export_fmt:
            return self._format_export(export_fmt, chapter_num, chapter_name)
        return f'-----【第{chapter_num}章-{chapter_name}】-----'

    def find_next_chapter_in_all(self, target_chapter_num):
        try:
            possible_filenames = []

            if self._custom_detect_formats:
                for fmt in self._custom_detect_formats:
                    filename = self._format_chapter(fmt, target_chapter_num, "name")
                    if not filename.endswith('.txt'):
                        filename += '.txt'
                    possible_filenames.append(filename)
            else:
                lang = self._current_lang
                if lang == 'zh_CN':
                    chinese_num = self.num_to_chinese(target_chapter_num) + "章"
                    possible_filenames.append(f"{target_chapter_num}第{chinese_num}_name.txt")
                    possible_filenames.append(f"{target_chapter_num}第{chinese_num}_.txt")
                elif lang == 'en_US':
                    possible_filenames.append(f"{target_chapter_num}[Chapter{target_chapter_num}]_name.txt")
                    possible_filenames.append(f"{target_chapter_num}[Chapter{target_chapter_num}]_.txt")
                elif lang == 'ja_JP':
                    chinese_num = self.num_to_chinese(target_chapter_num) + "章"
                    possible_filenames.append(f"{target_chapter_num}第{chinese_num}_name.txt")
                    possible_filenames.append(f"{target_chapter_num}第{chinese_num}_.txt")

            for filename in possible_filenames:
                target_path = os.path.join(get_all_dir(), filename)
                if os.path.exists(target_path):
                    return target_path, target_chapter_num

            lang = self._current_lang
            if lang != 'zh_CN':
                chinese_num = self.num_to_chinese(target_chapter_num) + "章"
                target_filename = f"{target_chapter_num}第{chinese_num}_name.txt"
                target_path = os.path.join(get_all_dir(), target_filename)
                if os.path.exists(target_path):
                    return target_path, target_chapter_num

            return None, target_chapter_num
        except Exception:
            return None, target_chapter_num

    def get_folder_number(self, folder_name):
        match = re.match(r'^(\d+)\[', folder_name)
        if match:
            return int(match.group(1))
        return None

    def extract_volume_name(self, folder_name):
        match = re.search(r'\[(.+?)\]', folder_name)
        if match:
            return match.group(1)
        return None

    def format_chapter_title(self, chapter_num, chapter_name=""):
        lang = self._current_lang

        if lang == 'zh_CN':
            return f"-----【第{chapter_num}章-{chapter_name}】-----"
        elif lang == 'en_US':
            return f"-----【Chapter {chapter_num}-{chapter_name}】-----"
        elif lang == 'ja_JP':
            return f"-----【第{chapter_num}章-{chapter_name}】-----"
        else:
            return f"-----【第{chapter_num}章-{chapter_name}】-----"

    def replace_dash_with_space(self, text):
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

    def get_word_count(self, file_path):
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

    def get_folder_files(self, folder_path):
        try:
            files = sorted([f for f in os.listdir(folder_path) if f.endswith('.txt')],
                          key=lambda x: (self.get_folder_number(x) is None, self.get_chapter_number(x) or float('inf')))
            return files
        except Exception:
            return []

    def copy_and_rename_internal(self, source_path, dest_folder, chapter_num):
        try:
            new_filename = self.generate_chapter_name(chapter_num, "")
            dest_path = os.path.join(dest_folder, new_filename)
            if os.path.exists(dest_path):
                return False, new_filename, "文件已存在"
            shutil.copy2(source_path, dest_path)
            return True, new_filename, None
        except Exception as e:
            return False, None, str(e)

    def ensure_ahead_chapters_internal(self, folder_name, folder_path, current_max, messages, max_ahead_chapters=2):
        added_count = 0
        added_files = []
        for add_num in range(current_max + 1, current_max + max_ahead_chapters + 1):
            target_filename = self.generate_chapter_name(add_num, "")
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
        return an2cn(str(num))

    @staticmethod
    def num_to_chinese_upper(num):
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


file_manager = FileManager()
