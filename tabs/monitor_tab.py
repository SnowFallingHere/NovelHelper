"""
监控管理标签页
提供文件监控、日志查看、章节预览等功能
"""

import os
import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTextBrowser, QTreeWidget, QTreeWidgetItem,
    QSplitter, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor

from .base_tab import BaseTab
from ..core.config_manager import ConfigManager
from ..core.language_manager import language_manager
from ..core.file_manager import get_novel_dir, FileManager
from ..core.theme_manager import theme_manager

logger = logging.getLogger(__name__)


class MonitorTab(BaseTab):
    """监控管理标签页"""
    
    # 信号定义
    monitor_started = pyqtSignal()       # 监控启动时发出
    monitor_stopped = pyqtSignal()       # 监控停止时发出
    summary_requested = pyqtSignal(str)  # 请求自动摘要时发出
    new_chapter_detected = pyqtSignal()  # 检测到新章节时发出
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_name = "监控管理"
        
        # 配置属性
        self._load_config()
        
        # 状态变量
        self.monitor_thread = None
        self._msg_counter = 0
        self.all_messages = []
        
        logger.info(f"[{self.tab_name}] 创建实例")
    
    def _load_config(self):
        """加载配置参数"""
        self.base_title_size = int(ConfigManager.get('UI', 'title_size', fallback='18'))
        self.log_font_size = int(ConfigManager.get('UI', 'log_font_size', fallback='12'))
        
        # 颜色配置
        self.error_color = ConfigManager.get('Colors', 'error_color', fallback='#ff3333')
        self.warn_color = ConfigManager.get('Colors', 'warn_color', fallback='#ffaa00')
    
    def _build_ui(self):
        """构建UI界面"""
        from ..core.theme_manager import theme_manager as tm
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 10)
        
        # ====== 标题 ======
        self._title_label = QLabel(language_manager.tr("monitor_system"))
        self._title_label.setStyleSheet(f"font-size: {self.base_title_size}px; font-weight: bold; color: {tm.get('accent_color', '#0078D4')};")
        main_layout.addWidget(self._title_label)
        
        # ====== 控制按钮 ======
        btn_layout = QHBoxLayout()
        
        self.btn_start = QPushButton(language_manager.tr("start_monitor"))
        self.btn_stop = QPushButton(language_manager.tr("stop_monitor"))
        self.btn_preview = QPushButton(language_manager.tr("chapter_preview_btn"))
        
        self.btn_start.clicked.connect(self.start_monitor)
        self.btn_stop.clicked.connect(self.stop_monitor)
        self.btn_preview.clicked.connect(self._show_chapter_preview)
        
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(self.btn_preview)
        main_layout.addLayout(btn_layout)
        
        # ====== 过滤器 ======
        filter_layout = QHBoxLayout()
        self._filter_label = QLabel(language_manager.tr("log_filter"))
        filter_layout.addWidget(self._filter_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            language_manager.tr("filter_all"),
            language_manager.tr("filter_recent_15"),
            language_manager.tr("filter_recent_30"),
            language_manager.tr("filter_recent_50")
        ])
        self.filter_combo.currentTextChanged.connect(self.filter_logs)
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addStretch()
        main_layout.addLayout(filter_layout)
        
        # ====== 状态标签 ======
        self.status_label = QLabel(language_manager.tr("status_stopped"))
        main_layout.addWidget(self.status_label)
        
        # ====== 分割面板（日志 + 预览） ======
        splitter = QSplitter(Qt.Vertical)
        
        # 日志区域
        self.log_info = QTextBrowser()
        self.log_info.document().setMaximumBlockCount(2000)
        splitter.addWidget(self.log_info)
        
        # 章节预览区域
        self._chapter_preview = QTreeWidget()
        self._chapter_preview.setHeaderLabels([
            language_manager.tr("col_volume_chapter"),
            language_manager.tr("col_title"),
            language_manager.tr("col_word_count"),
            language_manager.tr("col_mod_time")
        ])
        self._chapter_preview.setAlternatingRowColors(False)
        self._chapter_preview.setVisible(True)
        self._chapter_preview.itemDoubleClicked.connect(self._on_preview_item_double_clicked)
        splitter.addWidget(self._chapter_preview)
        
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)
        
        # ====== 定时器 ======
        self._preview_timer = QTimer()
        self._preview_timer.timeout.connect(self._auto_refresh_preview)
        
        logger.debug(f"[{self.tab_name}] UI构建完成")
    
    def _load_data(self):
        """加载数据"""
        pass

    def load_data(self):
        """重新加载数据（小说路径变更时调用）"""
        self.log_info.clear()
        self.all_messages.clear()
        self._msg_counter = 0
        self._chapter_preview.clear()
        self._auto_refresh_preview()
        self.status_label.setText(language_manager.tr("status_stopped"))
    
    def retranslate_ui(self):
        lm = language_manager.tr
        if hasattr(self, '_title_label'):
            self._title_label.setText(lm("monitor_system"))
        if hasattr(self, 'btn_start'):
            self.btn_start.setText(lm("start_monitor"))
        if hasattr(self, 'btn_stop'):
            self.btn_stop.setText(lm("stop_monitor"))
        if hasattr(self, 'btn_preview'):
            self.btn_preview.setText(lm("chapter_preview_btn"))
        if hasattr(self, '_filter_label'):
            self._filter_label.setText(lm("log_filter"))
        if hasattr(self, 'filter_combo'):
            self.filter_combo.clear()
            self.filter_combo.addItems([
                lm("filter_all"),
                lm("filter_recent_15"),
                lm("filter_recent_30"),
                lm("filter_recent_50")
            ])
        if hasattr(self, 'status_label'):
            self.status_label.setText(lm("status_stopped"))
        if hasattr(self, '_chapter_preview'):
            self._chapter_preview.setHeaderLabels([
                lm("col_volume_chapter"),
                lm("col_title"),
                lm("col_word_count"),
                lm("col_mod_time")
            ])
    
    # ====== 监控控制方法 ======
    
    def start_monitor(self):
        """启动监控"""
        if self.monitor_thread and self.monitor_thread.isRunning():
            return
        
        try:
            from ..controllers.monitor_controller import MonitorThread
            
            self.monitor_thread = MonitorThread()
            self.monitor_thread.update_signal.connect(self._on_monitor_update)
            self.monitor_thread.error_signal.connect(self._on_monitor_error)
            self.monitor_thread.run_summary_signal.connect(self._on_auto_summary_request)
            self.monitor_thread.start()
            
            self.status_label.setText(language_manager.tr("monitor_started"))
            self.log_info.append(f"[OK] {language_manager.tr('monitor_started')}")
            
            interval = int(ConfigManager.get('Monitor', 'check_interval', fallback='15')) * 1000
            self._preview_timer.start(interval)
            self._auto_refresh_preview()
            
            self.monitor_started.emit()
            
        except Exception as e:
            logger.error(f"启动监控失败: {e}", exc_info=True)
            self.log_info.append(f"[ERR] 启动监控失败: {e}")
    
    def stop_monitor(self):
        """停止监控"""
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread.wait(3000)
            self.monitor_thread = None
            
            self.status_label.setText(language_manager.tr("monitor_stopped"))
            self.log_info.append(f"[OK] {language_manager.tr('monitor_stopped')}")
        
        self._preview_timer.stop()
        self.monitor_stopped.emit()
    
    # ====== 日志处理方法 ======
    
    def _on_monitor_update(self, folder_states, messages):
        """处理监控更新消息"""
        has_new = False
        for msg in messages:
            self._msg_counter += 1
            self.all_messages.append(msg)
            
            if msg.startswith("[ERR]") or "失败" in msg or "错误" in msg:
                color = self.error_color
            elif msg.startswith("[NEW]") or "新卷" in msg or "创建" in msg or "新增" in msg:
                color = self.warn_color
                has_new = True
            else:
                t = self._msg_counter
                g = max(80, 255 - t * 2)
                r = min(100, t * 3)
                color = f"#{r:02x}{g:02x}30"
            
            self.log_info.append(f"<span style='color:{color};'>{msg}</span>")
        
        if has_new:
            self.new_chapter_detected.emit()
        
        # 限制消息数量，防止内存溢出
        if len(self.all_messages) > 500:
            self.all_messages = self.all_messages[-500:]
    
    def _on_monitor_error(self, err_msg):
        """处理监控错误"""
        logger.error(f"监控线程错误: {err_msg}")
        self.log_info.append(
            f"<span style='color:{self.error_color};font-weight:bold;'>WARNING {err_msg}</span>"
        )
    
    def filter_logs(self):
        """过滤日志显示"""
        self.update_log_display()
    
    def update_log_display(self):
        """更新日志显示内容"""
        if not hasattr(self, 'filter_combo'):
            msg_list = self.all_messages
        else:
            idx = self.filter_combo.currentIndex()
            if idx == 0:
                msg_list = self.all_messages
            elif idx == 1:
                msg_list = self.all_messages[-15:]
            elif idx == 2:
                msg_list = self.all_messages[-30:]
            elif idx == 3:
                msg_list = self.all_messages[-50:]
            else:
                msg_list = self.all_messages
        
        self.log_info.clear()
        for msg in msg_list:
            self.log_info.append(msg)
    
    # ====== 章节预览方法 ======
    
    def _show_chapter_preview(self):
        """显示章节预览"""
        novel_dir = get_novel_dir()
        if not os.path.exists(novel_dir):
            return
        
        self._chapter_preview.clear()
        
        volumes = sorted([
            f for f in os.listdir(novel_dir) 
            if os.path.isdir(os.path.join(novel_dir, f)) 
            and FileManager.is_numeric_volume_folder(f)
        ])
        
        if not volumes:
            self.log_info.append("[WARN] " + language_manager.tr("no_vol_folders_warn"))
            return
        
        for vol in volumes:
            vol_path = os.path.join(novel_dir, vol)
            vol_item = QTreeWidgetItem(self._chapter_preview, [vol, "", "", ""])
            vol_item.setForeground(0, QColor(theme_manager.get('accent_color', '#0078D4')))
            
            chapters = sorted([f for f in os.listdir(vol_path) if f.endswith('.txt')])
            total_words = 0
            
            for ch in chapters:
                ch_path = os.path.join(vol_path, ch)
                try:
                    with open(ch_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    word_count = len(content)
                    total_words += word_count
                    mtime = datetime.fromtimestamp(os.path.getmtime(ch_path)).strftime('%m-%d %H:%M')
                    
                    ch_item = QTreeWidgetItem(
                        vol_item,
                        [f"  {ch}", ch.replace('.txt', ''), str(word_count), mtime]
                    )
                    ch_item.setData(0, Qt.UserRole, ch_path)
                except Exception:
                    ch_item = QTreeWidgetItem(
                        vol_item,
                        [f"  {ch}", ch.replace('.txt', ''), "?", "?"]
                    )
                    ch_item.setData(0, Qt.UserRole, os.path.join(vol_path, ch))
            
            vol_item.setText(2, str(total_words))
            vol_item.setText(3, datetime.fromtimestamp(os.path.getmtime(vol_path)).strftime('%m-%d %H:%M'))
        
        self._chapter_preview.expandAll()
    
    def _auto_refresh_preview(self):
        """自动刷新章节预览"""
        try:
            self._show_chapter_preview()
            interval = int(ConfigManager.get('Monitor', 'check_interval', fallback='15')) * 1000
            if self._preview_timer.interval() != interval:
                self._preview_timer.setInterval(interval)
        except Exception:
            pass
    
    def _on_preview_item_double_clicked(self, item, col):
        """预览项双击事件"""
        path = item.data(0, Qt.UserRole)
        if path and os.path.isfile(path):
            try:
                os.startfile(path)
            except Exception:
                pass
    
    # ====== 自动摘要相关方法 ======
    
    def _on_auto_summary_request(self, novel_dir):
        """自动摘要请求"""
        if not os.path.exists(novel_dir):
            return
        
        min_content_length = int(
            ConfigManager.get('Monitor', 'min_word_count', fallback='20')
        )
        
        try:
            from ..models.summary_generator import SummaryWorker
            
            self._auto_summary_worker = SummaryWorker(novel_dir, 2, min_content_length)
            self._auto_summary_worker.message_signal.connect(
                lambda msg: self.log_info.append(msg)
            )
            self._auto_summary_worker.finished_signal.connect(self._on_auto_summary_finished)
            self._auto_summary_worker.error_signal.connect(
                lambda err: self.log_info.append(f"[ERR] 自动Summary失败: {err}")
            )
            
            self.log_info.append("[SUM] 新卷处理完成，自动运行Summary合并...")
            self._auto_summary_worker.start()
            
            # 发出信号通知主窗口
            self.summary_requested.emit(novel_dir)
            
        except Exception as e:
            logger.error(f"启动自动摘要失败: {e}", exc_info=True)
            self.log_info.append(f"[ERR] 启动自动摘要失败: {e}")
    
    def _on_auto_summary_finished(self, result):
        """自动摘要完成"""
        self.log_info.append(f"[OK] Summary合并完成")
        
        rename_results = result.get('rename_results', [])
        for old, new in rename_results:
            self.log_info.append(f"  重命名: {old} -> {new}")
    
    # ====== 辅助方法 ======
    
    def add_new_volume(self):
        """添加新卷"""
        novel_dir = get_novel_dir()
        if not os.path.exists(novel_dir):
            QMessageBox.warning(
                self, language_manager.tr("error"), "请先设置小说目录"
            )
            return
        
        folders = [
            f for f in os.listdir(novel_dir) 
            if os.path.isdir(os.path.join(novel_dir, f)) 
            and FileManager.is_numeric_volume_folder(f)
        ]
        
        if not folders:
            new_vol_num = 1
        else:
            vol_nums = [
                FileManager.get_volume_number(f) 
                for f in folders 
                if FileManager.get_volume_number(f)
            ]
            new_vol_num = max(vol_nums) + 1 if vol_nums else 1
        
        new_vol_name = str(new_vol_num)
        new_vol_path = os.path.join(novel_dir, new_vol_name)
        
        try:
            os.makedirs(new_vol_path, exist_ok=True)
            self.log_info.append(
                f"[OK] 创建新卷文件夹: {new_vol_name}，监控启动后将自动处理标记"
            )
        except Exception as e:
            self.log_info.append(f"[ERR] 创建新卷失败: {e}")
    
    # ====== 清理资源 ======
    
    def cleanup(self):
        """清理资源"""
        # 停止监控线程
        if self.monitor_thread:
            self.stop_monitor()
        
        # 停止定时器
        if hasattr(self, '_preview_timer'):
            self._preview_timer.stop()
        
        logger.info(f"[{self.tab_name}] 资源已清理")
