import os
import re
import time
import traceback
import logging
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from core.config_manager import ConfigManager
from core.file_manager import file_manager, get_novel_dir
from core.language_manager import language_manager

logger = logging.getLogger(__name__)

class MonitorThread(QThread):
    update_signal = pyqtSignal(dict, list)
    error_signal = pyqtSignal(str)
    heartbeat_signal = pyqtSignal()
    run_summary_signal = pyqtSignal(str)
    
    _HEARTBEAT_TIMEOUT = 120
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.folder_states = {}
        self.folder_mtimes = {}
        self.last_summary_chapter = {}
        self.messages = []
        self.file_cache = {}
        self._last_check_time = 0
        self._timer = None
    
    def get_check_interval(self):
        return ConfigManager.get_int('Monitor', 'check_interval', fallback=15)
    
    def get_max_ahead_chapters(self):
        return ConfigManager.get_int('Monitor', 'max_ahead_chapters', fallback=2)
    
    def get_min_word_count(self):
        return ConfigManager.get_int('Monitor', 'min_word_count', fallback=20)
    
    def run(self):
        try:
            self.init_folders()
            self._timer = QTimer()
            self._timer.timeout.connect(self._check_cycle)
            interval_ms = self.get_check_interval() * 1000
            self._timer.start(interval_ms)
            self.exec_()
        except Exception as e:
            err_msg = f"{language_manager.tr('monitor_fatal_error')}: {e}"
            logger.critical(err_msg + "\n" + traceback.format_exc())
            self.error_signal.emit(err_msg)
            self.running = False
    
    def stop(self):
        self.running = False
        if self._timer:
            self._timer.stop()
        self.quit()
        self.wait(3000)
    
    def _check_cycle(self):
        if not self.running:
            if self._timer:
                self._timer.stop()
            return
        try:
            self._last_check_time = time.time()
            self.heartbeat_signal.emit()
            self.check_folders()
            self.update_signal.emit(self.folder_states, self.messages)
            self.messages = []
            interval_ms = self.get_check_interval() * 1000
            if self._timer.interval() != interval_ms:
                self._timer.setInterval(interval_ms)
        except Exception as e:
            err_msg = f"{language_manager.tr('monitor_check_error')}: {e}"
            logger.error(err_msg + "\n" + traceback.format_exc())
            self.error_signal.emit(err_msg)
    
    def init_folders(self):
        try:
            folders = sorted(os.listdir(get_novel_dir()), key=lambda x: (file_manager.get_volume_number(x) is None, file_manager.get_volume_number(x) or float('inf')))
            for folder_name in folders:
                folder_path = os.path.join(get_novel_dir(), folder_name)
                if not os.path.isdir(folder_path):
                    continue
                
                if not file_manager.is_numeric_volume_folder(folder_name) or file_manager.is_old_volume(folder_name):
                    continue
                
                latest = file_manager.find_latest_chapter(folder_path)
                if latest is None:
                    continue
                
                current_max = latest[0]
                latest_file = latest[1]
                latest_file_path = os.path.join(folder_path, latest_file)
                
                current_word_count, _ = file_manager.get_word_count(latest_file_path)
                current_is_default = file_manager.is_default_content(latest_file_path)
                
                self.folder_states[folder_name] = {
                    'current_max': current_max,
                    'word_count': current_word_count,
                    'is_default': current_is_default,
                    'status': '初始化',
                    'ahead_count': 0,
                    'files': file_manager.get_folder_files(folder_path),
                    'latest_file': latest_file
                }
                self.folder_mtimes[folder_name] = file_manager.get_file_mtime(latest_file_path)
                self.last_summary_chapter[folder_name] = current_max
                self.file_cache[folder_name] = self.folder_states[folder_name]['files']
                
                min_word_count = self.get_min_word_count()
                max_ahead_chapters = self.get_max_ahead_chapters()
                if not current_is_default and current_word_count > min_word_count:
                    added = file_manager.ensure_ahead_chapters_internal(folder_name, folder_path, current_max, self.messages, max_ahead_chapters)
                    self.folder_states[folder_name]['ahead_count'] = added
                    self.folder_states[folder_name]['status'] = '就绪'
                else:
                    self.folder_states[folder_name]['status'] = '等待写入'
        except Exception as e:
            logger.error(f"{language_manager.tr('init_folders_failed')}: {e}")

    def check_folders(self):
        try:
            folders = sorted(os.listdir(get_novel_dir()), key=lambda x: (file_manager.get_volume_number(x) is None, file_manager.get_volume_number(x) or float('inf')))
            
            processed_new_folder = False
            max_ahead_chapters = self.get_max_ahead_chapters()
            
            # 先检查是否有简单数字命名的新文件夹（可能是空的）
            for folder_name in folders:
                folder_path = os.path.join(get_novel_dir(), folder_name)
                if not os.path.isdir(folder_path):
                    continue
                folder_num = file_manager.get_volume_number(folder_name)
                
                # 条件：简单数字命名（没有[xxx]后缀）
                if folder_num and not ('[' in folder_name and ']' in folder_name):
                    if self.process_new_volume_folder(folder_name, folder_path, folder_num, max_ahead_chapters):
                        processed_new_folder = True
                        self.run_summary_signal.emit(get_novel_dir())
            
            # 重新获取文件夹列表，因为重命名了
            if processed_new_folder:
                folders = sorted(os.listdir(get_novel_dir()), key=lambda x: (file_manager.get_volume_number(x) is None, file_manager.get_volume_number(x) or float('inf')))
            # 正常处理文件夹
            for folder_name in folders:
                if not self.running:
                    break
                folder_path = os.path.join(get_novel_dir(), folder_name)
                if not os.path.isdir(folder_path):
                    continue
                
                if not file_manager.is_numeric_volume_folder(folder_name) or file_manager.is_old_volume(folder_name):
                    continue
                
                latest = file_manager.find_latest_chapter(folder_path)
                if latest is None:
                    continue
                
                current_max = latest[0]
                latest_file = latest[1]
                latest_file_path = os.path.join(folder_path, latest_file)
                
                current_mtime = file_manager.get_file_mtime(latest_file_path)
                current_word_count, _ = file_manager.get_word_count(latest_file_path)
                current_is_default = file_manager.is_default_content(latest_file_path)
                
                if folder_name not in self.folder_states:
                    logger.info(f"{language_manager.tr('new_folder_state')}: {folder_name}")
                    files = file_manager.get_folder_files(folder_path)
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
                
                current_files = file_manager.get_folder_files(folder_path)
                if current_files != self.file_cache.get(folder_name, []):
                    state['files'] = current_files
                    self.file_cache[folder_name] = current_files
                
                state['latest_file'] = latest_file
                
                min_word_count = self.get_min_word_count()
                max_ahead_chapters = self.get_max_ahead_chapters()
                if not current_is_default and current_word_count > min_word_count:
                    state['status'] = '活跃'
                    added = file_manager.ensure_ahead_chapters_internal(folder_name, folder_path, current_max, self.messages, max_ahead_chapters)
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
            logger.error(f"{language_manager.tr('monitor_error')}: {e}")
    
    def process_new_volume_folder(self, folder_name, folder_path, folder_num, max_ahead_chapters):
        """处理新卷文件夹的独立方法"""
        try:
            # 检查新文件夹是否为空
            new_folder_files = file_manager.get_folder_files(folder_path)
            
            prev_num = folder_num - 1
            if prev_num <= 0:
                return False
            
            # 查找上一卷
            prev_folder = None
            for f in os.listdir(get_novel_dir()):
                f_path = os.path.join(get_novel_dir(), f)
                if os.path.isdir(f_path):
                    f_num = file_manager.get_volume_number(f)
                    if f_num == prev_num:
                        prev_folder = f_path
                        break
            
            if not prev_folder:
                logger.warning(language_manager.tr('prev_volume_not_found'))
                return False
            
            # 步骤1：找到上一卷中有内容和无内容的章节
            min_word_count = ConfigManager.get_int('Monitor', 'min_word_count', fallback=20)
            prev_files = file_manager.get_folder_files(prev_folder)
            
            real_latest_num = 0
            real_latest_file = None
            empty_chapters = []
            
            for f in prev_files:
                f_path = os.path.join(prev_folder, f)
                wc, _ = file_manager.get_word_count(f_path)
                is_default = file_manager.is_default_content(f_path)
                f_num = file_manager.get_chapter_number(f)
                
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
                    logger.warning(f"{language_manager.tr('delete_empty_chapter_failed')} {empty_path}: {e}")
            
            # 步骤3：确定从哪一章开始复制
            # 如果有有内容的章节，从那里+1开始；否则从上一卷最新章节+1开始
            prev_latest = file_manager.find_latest_chapter(prev_folder)
            start_chapter = real_latest_num if real_latest_num > 0 else (prev_latest[0] if prev_latest else 0)
            if start_chapter == 0:
                logger.warning(language_manager.tr('cannot_determine_start_chapter'))
                return False
            
            # 步骤4：计算上一卷的总字数（只计算有内容的）
            total_words = 0
            prev_files_after_del = file_manager.get_folder_files(prev_folder)
            for f in prev_files_after_del:
                f_path = os.path.join(prev_folder, f)
                wc, _ = file_manager.get_word_count(f_path)
                total_words += wc
            
            # 步骤5：从 start_chapter+1 开始创建 max_ahead_chapters 个空章节
            added_count = 0
            for add_num in range(start_chapter + 1, start_chapter + max_ahead_chapters + 1):
                dest_filename = file_manager.generate_chapter_name(add_num, "")
                dest_path = os.path.join(folder_path, dest_filename)
                
                try:
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    with open(dest_path, 'w', encoding='utf-8') as f:
                        f.write('')
                    added_count += 1
                    self.messages.append(f"[NEW] {folder_name}: 新增第{add_num}章")
                except Exception as e:
                    logger.error(f"{language_manager.tr('create_chapter_failed')} {add_num}: {e}")
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
                    logger.warning(f"{language_manager.tr('mark_old_volume_failed')}: {e}")
            
            # 步骤7：统计新卷字数并重命名为 [new_字数]
            new_folder_word_count = 0
            new_files = file_manager.get_folder_files(folder_path)
            for f in new_files:
                f_path = os.path.join(folder_path, f)
                wc, _ = file_manager.get_word_count(f_path)
                new_folder_word_count += wc
            
            # 步骤8：重命名当前卷为 new
            new_folder_final_name = f"{folder_num}[new_{new_folder_word_count}]"
            new_folder_final_path = os.path.join(get_novel_dir(), new_folder_final_name)
            try:
                os.rename(folder_path, new_folder_final_path)
                self.messages.append(f"[NEW] 自动标记新卷: {folder_name} -> {new_folder_final_name}")
                return True
            except Exception as e:
                logger.warning(f"{language_manager.tr('mark_new_volume_failed')}: {e}")
                return False
            
        except Exception as e:
            logger.error(f"{language_manager.tr('process_new_volume_failed')}: {e}")
            logger.error(traceback.format_exc())
            return False

class MonitorController:
    def __init__(self):
        self._thread = None
        self._on_update = None
        self._on_error = None
    
    def set_callbacks(self, on_update, on_error):
        self._on_update = on_update
        self._on_error = on_error
    
    def start(self):
        if self._thread and self._thread.isRunning():
            return False
        self._thread = MonitorThread()
        if self._on_update:
            self._thread.update_signal.connect(self._on_update)
        if self._on_error:
            self._thread.error_signal.connect(self._on_error)
        self._thread.start()
        return True
    
    def stop(self):
        if self._thread and self._thread.isRunning():
            self._thread.stop()
            self._thread.wait(3000)
            return True
        return False
    
    def is_running(self):
        return self._thread and self._thread.isRunning()
    
    def get_last_heartbeat(self):
        if self._thread:
            return self._thread._last_check_time
        return 0
