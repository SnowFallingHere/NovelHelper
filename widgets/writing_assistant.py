"""
写作辅助工具
- 写作计时器（番茄钟）
- 字数目标管理
- 写作统计与历史
- 专注模式提醒
"""
import os
import json
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QProgressBar, QSpinBox, QGroupBox, QFormLayout,
    QCheckBox, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont

from core.config_manager import ConfigManager
from core.language_manager import language_manager


class WritingAssistant(QWidget):
    """
    写作辅助控制面板

    功能：
    - 番茄钟计时器 (25分钟专注 + 5分钟休息)
    - 字数目标设置
    - 今日写作统计
    - 写作历史记录
    """

    # 信号：计时器更新
    timer_updated = pyqtSignal(int)  # 剩余秒数
    timer_finished = pyqtSignal(bool)  # True=专注结束，False=休息结束
    goal_progress_updated = pyqtSignal(int, int)  # 当前字数，目标字数

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WritingAssistant")

        # 状态变量
        self._timer_running = False
        self._timer_paused = False
        self._remaining_seconds = 0
        self._is_focus_mode = True  # True=专注，False=休息

        self._today_word_count = 0
        self._daily_goal = ConfigManager.get_int('Writing', 'daily_goal', 2000)

        self._load_history()
        self._build_ui()
        self._connect_signals()

        # 内部计时器
        self._timer = QTimer()
        self._timer.timeout.connect(self._on_timer_tick)

    def _build_ui(self):
        """构建界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # ====== 计时器区域 ======
        timer_group = QGroupBox(language_manager.tr("writing_timer"))
        timer_layout = QVBoxLayout()

        # 显示时间
        self._time_label = QLabel("25:00")
        self._time_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(32)
        font.setBold(True)
        self._time_label.setFont(font)

        # 计时器按钮
        btn_layout = QHBoxLayout()
        self._start_btn = QPushButton(language_manager.tr("start"))
        self._pause_btn = QPushButton(language_manager.tr("pause"))
        self._reset_btn = QPushButton(language_manager.tr("reset"))
        self._skip_btn = QPushButton(language_manager.tr("skip_break"))

        self._pause_btn.setEnabled(False)

        btn_layout.addWidget(self._start_btn)
        btn_layout.addWidget(self._pause_btn)
        btn_layout.addWidget(self._reset_btn)
        btn_layout.addWidget(self._skip_btn)

        # 模式选择
        mode_layout = QHBoxLayout()
        self._focus_check = QCheckBox(language_manager.tr("focus_mode"))
        self._focus_check.setChecked(True)
        self._short_break_check = QCheckBox(language_manager.tr("short_break"))
        self._long_break_check = QCheckBox(language_manager.tr("long_break"))

        mode_layout.addWidget(self._focus_check)
        mode_layout.addWidget(self._short_break_check)
        mode_layout.addWidget(self._long_break_check)

        timer_layout.addWidget(self._time_label)
        timer_layout.addLayout(btn_layout)
        timer_layout.addLayout(mode_layout)
        timer_group.setLayout(timer_layout)
        layout.addWidget(timer_group)

        # ====== 每日目标区域 ======
        goal_group = QGroupBox(language_manager.tr("daily_goal"))
        goal_layout = QFormLayout()

        self._goal_spin = QSpinBox()
        self._goal_spin.setRange(100, 50000)
        self._goal_spin.setSingleStep(100)
        self._goal_spin.setValue(self._daily_goal)
        self._goal_spin.setSuffix(" 字")

        self._today_label = QLabel(f"{self._today_word_count:,} / {self._daily_goal:,}")

        self._goal_progress = QProgressBar()
        self._goal_progress.setRange(0, 100)

        goal_layout.addRow(language_manager.tr("target"), self._goal_spin)
        goal_layout.addRow(language_manager.tr("today"), self._today_label)
        goal_layout.addRow(self._goal_progress)
        goal_group.setLayout(goal_layout)
        layout.addWidget(goal_group)

        # ====== 统计区域 ======
        stat_group = QGroupBox(language_manager.tr("writing_stats"))
        stat_layout = QFormLayout()

        self._stat_days_label = QLabel("0 天")
        self._stat_total_label = QLabel("0 字")
        self._stat_avg_label = QLabel("0 字/天")

        stat_layout.addRow(language_manager.tr("writing_days"), self._stat_days_label)
        stat_layout.addRow(language_manager.tr("total_words"), self._stat_total_label)
        stat_layout.addRow(language_manager.tr("avg_per_day"), self._stat_avg_label)
        stat_group.setLayout(stat_layout)
        layout.addWidget(stat_group)

        layout.addStretch()

        self._update_timer_display()
        self._update_goal_progress()
        self._update_stat_display()

    def _connect_signals(self):
        """连接信号"""
        self._start_btn.clicked.connect(self._on_start)
        self._pause_btn.clicked.connect(self._on_pause)
        self._reset_btn.clicked.connect(self._on_reset)
        self._skip_btn.clicked.connect(self._on_skip_break)

        self._goal_spin.valueChanged.connect(self._on_goal_changed)

        self._focus_check.toggled.connect(self._on_mode_changed)
        self._short_break_check.toggled.connect(self._on_mode_changed)
        self._long_break_check.toggled.connect(self._on_mode_changed)

    def _load_history(self):
        """加载历史记录"""
        self._history_file = os.path.join(
            ConfigManager.get('Environment', 'data_dir', '.'),
            '.writing_history.json'
        )
        self._history = {}
        if os.path.exists(self._history_file):
            try:
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    self._history = json.load(f)
            except Exception:
                pass

        # 今日字数
        today = datetime.now().strftime('%Y-%m-%d')
        self._today_word_count = self._history.get(today, 0)

    def _save_history(self):
        """保存历史记录"""
        try:
            with open(self._history_file, 'w', encoding='utf-8') as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ====== 计时器操作 ======

    def _get_duration_seconds(self):
        """获取当前模式的时长（秒）"""
        if self._focus_check.isChecked():
            return 25 * 60  # 25分钟专注
        elif self._short_break_check.isChecked():
            return 5 * 60  # 5分钟短休息
        elif self._long_break_check.isChecked():
            return 15 * 60  # 15分钟长休息
        return 25 * 60

    def _update_timer_display(self):
        """更新时间显示"""
        mins, secs = divmod(self._remaining_seconds, 60)
        self._time_label.setText(f"{mins:02d}:{secs:02d}")
        self.timer_updated.emit(self._remaining_seconds)

    def _on_start(self):
        """开始计时"""
        if not self._timer_running:
            if self._remaining_seconds <= 0:
                self._remaining_seconds = self._get_duration_seconds()

            self._timer.start(1000)
            self._timer_running = True
            self._timer_paused = False
            self._start_btn.setEnabled(False)
            self._pause_btn.setEnabled(True)

    def _on_pause(self):
        """暂停/继续"""
        if self._timer_paused:
            self._timer.start(1000)
            self._timer_paused = False
            self._pause_btn.setText(language_manager.tr("pause"))
        else:
            self._timer.stop()
            self._timer_paused = True
            self._pause_btn.setText(language_manager.tr("resume"))

    def _on_reset(self):
        """重置"""
        self._timer.stop()
        self._timer_running = False
        self._remaining_seconds = self._get_duration_seconds()
        self._timer_paused = False
        self._pause_btn.setText(language_manager.tr("pause"))
        self._pause_btn.setEnabled(False)
        self._start_btn.setEnabled(True)
        self._update_timer_display()

    def _on_skip_break(self):
        """跳过休息"""
        self._timer.stop()
        self._is_focus_mode = True
        self._remaining_seconds = 25 * 60
        self._focus_check.setChecked(True)
        self._update_timer_display()
        self.timer_finished.emit(True)

    def _on_timer_tick(self):
        """计时器更新"""
        if self._remaining_seconds > 0:
            self._remaining_seconds -= 1
            self._update_timer_display()
        else:
            self._timer.stop()
            self._timer_finished_handler()

    def _timer_finished_handler(self):
        """计时器完成"""
        if self._is_focus_mode:
            # 专注完成，进入休息
            self._is_focus_mode = False
            self._remaining_seconds = 5 * 60
            self._short_break_check.setChecked(True)
            self.timer_finished.emit(True)
        else:
            # 休息完成，回到专注
            self._is_focus_mode = True
            self._remaining_seconds = 25 * 60
            self._focus_check.setChecked(True)
            self.timer_finished.emit(False)

        self._update_timer_display()

    def _on_mode_changed(self, checked):
        """模式切换"""
        if not checked:
            return

        # 确保只有一个选中
        sender = self.sender()
        if sender == self._focus_check:
            self._short_break_check.setChecked(False)
            self._long_break_check.setChecked(False)
        elif sender == self._short_break_check:
            self._focus_check.setChecked(False)
            self._long_break_check.setChecked(False)
        elif sender == self._long_break_check:
            self._focus_check.setChecked(False)
            self._short_break_check.setChecked(False)

        if not self._timer_running:
            self._remaining_seconds = self._get_duration_seconds()
            self._update_timer_display()

    # ====== 字数目标 ======

    def _on_goal_changed(self, value):
        """目标变更"""
        self._daily_goal = value
        ConfigManager.set('Writing', 'daily_goal', str(value))
        self._update_goal_progress()

    def add_word_count(self, delta):
        """增加今日字数（可传入增量，正或负）"""
        today = datetime.now().strftime('%Y-%m-%d')
        self._today_word_count = max(0, self._today_word_count + delta)
        self._history[today] = self._today_word_count
        self._save_history()
        self._today_label.setText(
            f"{self._today_word_count:,} / {self._daily_goal:,}"
        )
        self._update_goal_progress()
        self.goal_progress_updated.emit(self._today_word_count, self._daily_goal)

    def set_word_count(self, count):
        """直接设置今日字数"""
        delta = count - self._today_word_count
        self.add_word_count(delta)

    def _update_goal_progress(self):
        """更新进度条"""
        if self._daily_goal > 0:
            pct = min(100, int((self._today_word_count / self._daily_goal) * 100))
            self._goal_progress.setValue(pct)
        else:
            self._goal_progress.setValue(0)

    def _update_stat_display(self):
        """更新统计显示"""
        days = len(self._history)
        total = sum(self._history.values())
        avg = round(total / max(days, 1))
        self._stat_days_label.setText(f"{days} 天")
        self._stat_total_label.setText(f"{total:,} 字")
        self._stat_avg_label.setText(f"{avg:,} 字/天")
