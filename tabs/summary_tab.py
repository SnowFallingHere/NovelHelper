"""
摘要与合并工具标签页
提供卷统计、重命名、合并等功能
"""

import os
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QRadioButton, QGroupBox,
    QProgressBar, QTextBrowser, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

from .base_tab import BaseTab
from ..core.config_manager import ConfigManager
from ..core.language_manager import language_manager
from ..core.file_manager import get_novel_dir, FileManager

logger = logging.getLogger(__name__)


class SummaryTab(BaseTab):
    """摘要与合并工具标签页"""
    
    # 信号定义
    summary_completed = pyqtSignal(list)  # 摘要完成时发出
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_name = "摘要与合并工具"
        
        # 配置属性
        self.base_title_size = int(ConfigManager.get('UI', 'title_size', fallback='18'))
        
        # 状态变量
        self._summary_volumes = []
        self._summary_mode = 2
        self._summary_idx = 0
        self._summary_all_results = []
        self._current_summary_worker = None
        
        logger.info(f"[{self.tab_name}] 创建实例")
    
    def _build_ui(self):
        """构建UI界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(15, 10, 15, 10)
        content_layout.setSpacing(12)

        # ====== 标题 ======
        self._title_label = QLabel(language_manager.tr("volume_merge_title"))
        self._title_label.setStyleSheet(f"font-size: {self.base_title_size}px; font-weight: bold;")
        self._title_label.setMinimumHeight(28)
        content_layout.addWidget(self._title_label)

        # ====== 运行模式 ======
        self._summary_mode_group = QGroupBox(language_manager.tr("run_mode"))
        mode_layout = QVBoxLayout(self._summary_mode_group)
        mode_layout.setSpacing(6)

        self.mode1 = QRadioButton(language_manager.tr("stats_only"))
        self.mode1.setMinimumHeight(36)
        self.mode2 = QRadioButton(language_manager.tr("stats_and_rename"))
        self.mode2.setMinimumHeight(36)
        self.mode2.setChecked(True)

        mode_layout.addWidget(self.mode1)
        mode_layout.addWidget(self.mode2)
        self._summary_mode_group.setMinimumHeight(90)
        content_layout.addWidget(self._summary_mode_group)

        # ====== 卷选择标签 ======
        self._vol_label = QLabel(language_manager.tr("select_volumes_label"))
        self._vol_label.setMinimumHeight(24)
        content_layout.addWidget(self._vol_label)

        # ====== 卷控制按钮 ======
        vol_ctrl_layout = QHBoxLayout()

        self._select_all_btn = QPushButton(language_manager.tr("select_all_btn"))
        self._select_all_btn.setMinimumHeight(34)
        self._select_all_btn.setMinimumWidth(100)
        self._select_all_btn.clicked.connect(self._select_all_volumes)

        self._deselect_all_btn = QPushButton(language_manager.tr("deselect_all_btn"))
        self._deselect_all_btn.setMinimumHeight(34)
        self._deselect_all_btn.setMinimumWidth(100)
        self._deselect_all_btn.clicked.connect(self._deselect_all_volumes)

        vol_ctrl_layout.addWidget(self._select_all_btn)
        vol_ctrl_layout.addWidget(self._deselect_all_btn)
        vol_ctrl_layout.addStretch()
        content_layout.addLayout(vol_ctrl_layout)

        # ====== 卷列表 ======
        self._volume_list = QListWidget()
        self._volume_list.setSelectionMode(QListWidget.NoSelection)
        self._volume_list.setMinimumHeight(120)
        content_layout.addWidget(self._volume_list, stretch=1)
        self._refresh_volume_list()

        # ====== 进度条 ======
        self._progress_label = QLabel(language_manager.tr("progress"))
        self._progress_label.setMinimumHeight(24)
        content_layout.addWidget(self._progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(24)
        content_layout.addWidget(self.progress_bar)

        # ====== 结果显示区域 ======
        self._result_label = QLabel(language_manager.tr("execution_result"))
        self._result_label.setMinimumHeight(24)
        content_layout.addWidget(self._result_label)
        self.summary_result = QTextBrowser()
        self.summary_result.setMinimumHeight(120)
        content_layout.addWidget(self.summary_result, stretch=2)

        # ====== 执行按钮 ======
        self.summary_btn_run = QPushButton(language_manager.tr("merge_selected_volumes"))
        self.summary_btn_run.setMinimumHeight(38)
        self.summary_btn_run.setMinimumWidth(140)
        self.summary_btn_run.clicked.connect(self.run_summary)
        content_layout.addWidget(self.summary_btn_run)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        logger.debug(f"[{self.tab_name}] UI构建完成")

    def retranslate_ui(self):
        lm = language_manager.tr
        if hasattr(self, '_title_label'):
            self._title_label.setText(lm("volume_merge_title"))
        if hasattr(self, '_summary_mode_group'):
            self._summary_mode_group.setTitle(lm("run_mode"))
        if hasattr(self, 'mode1'):
            self.mode1.setText(lm("stats_only"))
        if hasattr(self, 'mode2'):
            self.mode2.setText(lm("stats_and_rename"))
        if hasattr(self, '_vol_label'):
            self._vol_label.setText(lm("select_volumes_label"))
        if hasattr(self, '_select_all_btn'):
            self._select_all_btn.setText(lm("select_all_btn"))
        if hasattr(self, '_deselect_all_btn'):
            self._deselect_all_btn.setText(lm("deselect_all_btn"))
        if hasattr(self, '_progress_label'):
            self._progress_label.setText(lm("progress"))
        if hasattr(self, '_result_label'):
            self._result_label.setText(lm("execution_result"))
        if hasattr(self, 'summary_btn_run'):
            self.summary_btn_run.setText(lm("merge_selected_volumes"))
    
    def _load_data(self):
        """加载数据"""
        pass
    
    # ====== 卷列表管理方法 ======
    
    def _refresh_volume_list(self):
        """刷新卷列表"""
        self._volume_list.clear()
        novel_dir = get_novel_dir()
        if not os.path.exists(novel_dir):
            return
        
        volumes = sorted([
            f for f in os.listdir(novel_dir) 
            if os.path.isdir(os.path.join(novel_dir, f)) 
            and FileManager.is_numeric_volume_folder(f)
        ])
        
        for vol in volumes:
            item = QListWidgetItem(vol)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self._volume_list.addItem(item)
    
    def _select_all_volumes(self):
        """全选所有卷"""
        for i in range(self._volume_list.count()):
            self._volume_list.item(i).setCheckState(Qt.Checked)
    
    def _deselect_all_volumes(self):
        """取消全选"""
        for i in range(self._volume_list.count()):
            self._volume_list.item(i).setCheckState(Qt.Unchecked)
    
    def _get_selected_volumes(self):
        """获取选中的卷列表"""
        selected = []
        novel_dir = get_novel_dir()
        
        for i in range(self._volume_list.count()):
            item = self._volume_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append((item.text(), os.path.join(novel_dir, item.text())))
        
        return selected
    
    # ====== 摘要执行方法 ======
    
    def run_summary(self):
        """执行摘要操作"""
        novel_dir = get_novel_dir()
        if not os.path.exists(novel_dir):
            QMessageBox.warning(
                self, 
                language_manager.tr("error"),
                language_manager.tr("dir_not_exist_err") + ": " + novel_dir
            )
            return
        
        selected = self._get_selected_volumes()
        if not selected:
            QMessageBox.warning(self, language_manager.tr("prompt"), language_manager.tr("please_select_at_least_one_volume"))
            return
        
        # 确定运行模式
        mode = 1 if self.mode1.isChecked() else 2
        
        # 初始化状态
        self.summary_result.clear()
        self.progress_bar.setValue(5)
        
        min_content_length = int(
            ConfigManager.get('Monitor', 'min_word_count', fallback='20')
        )
        
        self.summary_result.append(
            f"模式: {mode} - {'不重命名' if mode == 1 else '重命名'}"
        )
        self.summary_result.append(f"选中卷数: {len(selected)}")
        
        for vol_name, vol_path in selected:
            self.summary_result.append(f"  - {vol_name}")
        
        # 禁用按钮，防止重复点击
        self.summary_btn_run.setEnabled(False)
        
        # 设置状态变量
        self._summary_volumes = selected
        self._summary_mode = mode
        self._summary_idx = 0
        self._summary_all_results = []
        
        # 开始处理第一个卷
        self._run_next_volume_summary()
    
    def _run_next_volume_summary(self):
        """处理下一个卷的摘要"""
        if self._summary_idx >= len(self._summary_volumes):
            self._on_all_summaries_finished()
            return
        
        vol_name, vol_path = self._summary_volumes[self._summary_idx]
        self.summary_result.append(f"\n--- 正在处理: {vol_name} ---")
        
        progress_value = 10 + int(80 * self._summary_idx / len(self._summary_volumes))
        self.progress_bar.setValue(progress_value)
        
        try:
            from ..models.summary_generator import SummaryWorker
            
            min_content_length = int(
                ConfigManager.get('Monitor', 'min_word_count', fallback='20')
            )
            
            self._current_summary_worker = SummaryWorker(
                vol_path, 
                self._summary_mode, 
                min_content_length
            )
            
            self._current_summary_worker.progress_signal.connect(self._on_summary_progress)
            self._current_summary_worker.message_signal.connect(self._on_summary_message)
            self._current_summary_worker.finished_signal.connect(self._on_single_summary_finished)
            self._current_summary_worker.error_signal.connect(self._on_summary_error)
            self._current_summary_worker.start()
            
        except Exception as e:
            logger.error(f"创建摘要工作线程失败: {e}", exc_info=True)
            self.summary_result.append(f"[ERR] 创建摘要线程失败: {e}")
            self._summary_idx += 1
            self._run_next_volume_summary()
    
    def _on_single_summary_finished(self, result):
        """单个卷摘要完成"""
        vol_name, vol_path = self._summary_volumes[self._summary_idx]
        
        total_cjk = result.get('total_cjk_count', 0)
        total_non_blank = result.get('total_non_blank_count', 0)
        rename_results = result.get('rename_results', [])
        
        # 处理重命名结果
        for r in rename_results:
            kind, orig, new_name, err = r
            if kind == 'old':
                self.summary_result.append(f"[OLD] 标记旧卷: {orig} -> {new_name}")
            elif kind == 'old_err':
                self.summary_result.append(f"[ERR] 标记旧卷失败 {orig}: {err}")
            elif kind == 'new':
                self.summary_result.append(f"[OK] 重命名: {orig} -> {new_name}")
            elif kind == 'new_err':
                self.summary_result.append(f"[ERR] 重命名失败: {err}")
        
        self.summary_result.append(
            f"[OK] {vol_name} 完成！CJK: {total_cjk}, 非空白: {total_non_blank}"
        )
        
        # 保存结果
        self._summary_all_results.append((vol_name, result))
        
        # 处理下一个卷
        self._summary_idx += 1
        self._run_next_volume_summary()
    
    def _on_all_summaries_finished(self):
        """所有卷摘要完成"""
        total_cjk = sum(r.get('total_cjk_count', 0) for _, r in self._summary_all_results)
        total_non_blank = sum(r.get('total_non_blank_count', 0) for _, r in self._summary_all_results)
        
        self.summary_result.append(
            f"\n[OK] 全部完成！总CJK: {total_cjk}, 总非空白: {total_non_blank}"
        )
        
        # 恢复按钮状态
        self.summary_btn_run.setEnabled(True)
        
        # 更新进度条
        self.progress_bar.setValue(100)
        QTimer.singleShot(3000, lambda: self.progress_bar.setValue(0))
        
        # 刷新卷列表（反映重命名后的变化）
        self._refresh_volume_list()
        
        # 发出信号通知主窗口
        self.summary_completed.emit(self._summary_all_results)
        
        logger.info(f"[{self.tab_name}] 所有卷摘要完成")
    
    def _on_summary_progress(self, value):
        """摘要进度更新"""
        self.progress_bar.setValue(value)
    
    def _on_summary_message(self, msg):
        """摘要消息更新"""
        self.summary_result.append(msg)
    
    def _on_summary_error(self, err_msg):
        """摘要错误处理"""
        self.summary_result.append(f"[ERR] {err_msg}")
        self._summary_idx += 1
        self._run_next_volume_summary()
    
    # ====== 公共接口方法 ======
    
    def refresh_data(self):
        """刷新数据（供外部调用）"""
        self._refresh_volume_list()
