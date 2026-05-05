import os
import re
import traceback
import logging
from collections import defaultdict
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
from core.config_manager import ConfigManager
from core.file_manager import file_manager, get_novel_dir
from core.language_manager import language_manager

logger = logging.getLogger(__name__)

class SummaryWorker(QThread):
    progress_signal = pyqtSignal(int)
    message_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, folder_path, mode, min_content_length):
        super().__init__()
        self.folder_path = folder_path
        self.mode = mode
        self.min_content_length = min_content_length

    def run(self):
        try:
            from collections import defaultdict
            folder_path = self.folder_path
            folder_name = os.path.basename(folder_path)
            output_file_path = os.path.join(folder_path, f"{folder_name}.txt")

            volume_content = defaultdict(list)
            total_cjk_count = 0
            total_non_blank_count = 0
            volume_non_blank_count = defaultdict(int)
            volume_folder_paths = dict()

            VOLUME_RE = re.compile(r'^(\d+)(.*?)(?:\[.*\])?$')
            FILE_NUM_RE = re.compile(r'^(\d+)')

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
                            if len(content) < self.min_content_length:
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
                            chapter_title = file_manager.format_chapter_title(num, chapter_name)

                            volume_content[volume_num].append((chapter_title, content, volume_name))
                    except Exception as e:
                        self.message_signal.emit(f"[WARN] 读取失败 {file}: {e}")
                        logger.warning(f"读取失败 {file}: {e}")

                processed += 1
                progress = 20 + int((processed / max(total_folders, 1)) * 50)
                self.progress_signal.emit(progress)

            self.progress_signal.emit(70)

            with open(output_file_path, 'a', encoding='utf-8') as outfile:
                buffer = []
                for vol_num in sorted(volume_content):
                    chapters = volume_content[vol_num]
                    vol_name = chapters[0][2]
                    vol_word_count = volume_non_blank_count[vol_num]
                    vol_title = file_manager.format_volume_title_export(vol_num, vol_name, vol_word_count)
                    buffer.extend(["\n\n", vol_title, "\n\n"])
                    for title, content, _ in chapters:
                        buffer.extend(["\n\n", title, "\n\n", content, "\n"])
                outfile.write(''.join(buffer))

            self.progress_signal.emit(90)

            rename_results = []
            if self.mode == 2:
                all_volume_nums = sorted(volume_content.keys())
                max_vol = all_volume_nums[-1] if all_volume_nums else 0

                has_new_volume_content = max_vol in volume_non_blank_count and volume_non_blank_count[max_vol] > 0

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
                                    rename_results.append(('old', orig_dir_name, new_dir_name, None))
                                except Exception as e:
                                    rename_results.append(('old_err', orig_dir_name, None, str(e)))

                for vol_num, (folder_path_abs, orig_dir_name) in volume_folder_paths.items():
                    if vol_num == max_vol:
                        word_count = volume_non_blank_count[vol_num]
                        new_dir_name = re.sub(r'\[(new_|old_)?\d+\]$', '', orig_dir_name)
                        new_dir_name = f"{new_dir_name}[new_{word_count}]"
                        if orig_dir_name != new_dir_name:
                            new_folder_path = os.path.join(os.path.dirname(folder_path_abs), new_dir_name)
                            try:
                                os.rename(folder_path_abs, new_folder_path)
                                rename_results.append(('new', orig_dir_name, new_dir_name, None))
                            except Exception as e:
                                rename_results.append(('new_err', orig_dir_name, None, str(e)))

            self.progress_signal.emit(100)
            self.finished_signal.emit({
                'total_cjk_count': total_cjk_count,
                'total_non_blank_count': total_non_blank_count,
                'rename_results': rename_results,
            })

        except Exception as e:
            self.error_signal.emit(str(e))
            logger.error(f"{language_manager.tr('summary_execute_failed')}: {e}\n{traceback.format_exc()}")

class SummaryGenerator:
    def __init__(self):
        self._worker = None
    
    def generate(self, folder_path, mode, min_content_length, on_progress, on_message, on_finished, on_error):
        if self._worker and self._worker.isRunning():
            return False
        self._worker = SummaryWorker(folder_path, mode, min_content_length)
        if on_progress:
            self._worker.progress_signal.connect(on_progress)
        if on_message:
            self._worker.message_signal.connect(on_message)
        if on_finished:
            self._worker.finished_signal.connect(on_finished)
        if on_error:
            self._worker.error_signal.connect(on_error)
        self._worker.start()
        return True
    
    def is_running(self):
        return self._worker and self._worker.isRunning()
