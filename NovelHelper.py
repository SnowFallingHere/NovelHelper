import os
import json
import re
import shutil
import time
import sys
import logging
import traceback
import configparser
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QLabel, QPushButton, 
                             QLineEdit, QRadioButton, QTextEdit, QTextBrowser, QProgressBar,
                             QGroupBox, QFormLayout, QMessageBox, QScrollArea,
                             QFrame, QComboBox, QFileDialog, QSplitter, QSizePolicy, QSpinBox,
                             QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, 
                             QGraphicsTextItem, QGraphicsRectItem,
                             QGraphicsPathItem, QGraphicsItem, QMenu, QCheckBox,
                             QSlider, QDialog, QListWidget, QTreeWidget, QTreeWidgetItem,
                             QHeaderView, QDialogButtonBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread, QSettings, QEvent, QPointF, QRectF
from PyQt5.QtGui import (QFont, QColor, QPalette, QPen, QBrush, 
                          QCursor, QPainter, QPainterPath, QLinearGradient, QFontMetrics)

from core.config_manager import ConfigManager
from core.file_manager import file_manager, FileManager, get_novel_dir, get_all_dir, get_base_dir, SCRIPT_DIR
from core.language_manager import language_manager, LanguageManager
from models.keyword_manager import keyword_manager, KeywordManager
from controllers.monitor_controller import MonitorThread, MonitorController
from models.summary_generator import SummaryWorker, SummaryGenerator
from ui.network_graph import SciFiNodeItem, SciFiEdge, NetworkGraphView

logger = logging.getLogger(__name__)


def get_log_dir():
    log_dir = os.path.join(get_base_dir(), "log")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    return log_dir


UI_REFRESH_INTERVAL = 500


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


class NovelHelper(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("NovelHelper", "NovelHelper")
        self.load_config_values()
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.installEventFilter(self)
        self.init_ui()
        self.load_settings()
        self.apply_adaptive()
        logger.info(f"{language_manager.tr('app_title')} started")
    
    def load_config_values(self):
        self.base_font_size = ConfigManager.get_int('UI', 'base_font_size', fallback=20)
        self.base_title_size = ConfigManager.get_int('UI', 'base_title_size', fallback=32)
        self.log_font_size = ConfigManager.get_int('UI', 'log_font_size', fallback=16)
        self.graph_font_size = ConfigManager.get_int('UI', 'graph_font_size', fallback=14)
        self.kwlist_font_size = ConfigManager.get_int('UI', 'kwlist_font_size', fallback=20)
        self.kwlist_title_size = ConfigManager.get_int('UI', 'kwlist_title_size', fallback=18)
        self.kwlist_font_color = ConfigManager.get('UI', 'kwlist_font_color', fallback='#00FF41')
        self.kwlist_font_family = ConfigManager.get('UI', 'kwlist_font_family', fallback='Microsoft YaHei')
        self.card_font_size = ConfigManager.get_int('UI', 'card_font_size', fallback=30)
        self.card_title_size = ConfigManager.get_int('UI', 'card_title_size', fallback=20)
        self.initial_width = ConfigManager.get_int('UI', 'initial_width', fallback=1100)
        self.initial_height = ConfigManager.get_int('UI', 'initial_height', fallback=975)
        self.min_width = ConfigManager.get_int('UI', 'min_width', fallback=800)
        self.min_height = ConfigManager.get_int('UI', 'min_height', fallback=600)
        self.bg_color = ConfigManager.get('UI', 'bg_color', fallback='#020804')
        self.fg_color = ConfigManager.get('UI', 'fg_color', fallback='#00FF41')
        self.border_color = ConfigManager.get('UI', 'border_color', fallback='#00AA30')
        self.accent_color = ConfigManager.get('UI', 'accent_color', fallback='#00FF41')
        self.error_color = ConfigManager.get('UI', 'error_color', fallback='#FF3333')
        self.warn_color = ConfigManager.get('UI', 'warn_color', fallback='#FFAA00')
        self.btn_bg_color = ConfigManager.get('UI', 'btn_bg_color', fallback='#001a05')
        self.btn_hover_color = ConfigManager.get('UI', 'btn_hover_color', fallback='#003310')
        self.input_bg_color = ConfigManager.get('UI', 'input_bg_color', fallback='#000d03')
        self.heartbeat_timeout = ConfigManager.get_int('Monitor', 'heartbeat_timeout', fallback=120)
        self.layout_ideal = ConfigManager.get_int('Graph', 'layout_ideal_length', fallback=200)
        self.node_limit = ConfigManager.get_int('Graph', 'node_limit', fallback=200)
        self.graph_bg = ConfigManager.get('Theme', 'graph_bg_color', fallback='#060612')
        self.grid_color = ConfigManager.get('Theme', 'graph_grid_color', fallback='#0a1a10')
        self.edge_width = ConfigManager.get_int('Theme', 'edge_width', fallback=3)
    
    def init_ui(self):
        self.setWindowTitle(language_manager.tr("app_title"))
        self.setMinimumSize(self.min_width, self.min_height)
        self.resize(self.initial_width, self.initial_height)
        
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, 1)
        
        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(48)
        bottom_bar.setStyleSheet("background-color:#0a0005; border-top:1px solid #300;")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(8, 4, 8, 4)
        
        bottom_layout.addStretch()
        self._save_exit_btn = QPushButton("保存并退出")
        self._save_exit_btn.setFixedHeight(36)
        self._save_exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #220000;
                color: #ff3333;
                border: 2px solid #ff3333;
                border-radius: 3px;
                font-weight: bold;
                font-family: 'Consolas', monospace;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: #330000;
                color: #ff5555;
                border-color: #ff5555;
            }
            QPushButton:pressed {
                background-color: #440000;
            }
        """)
        self._save_exit_btn.clicked.connect(self._save_and_exit)
        bottom_layout.addWidget(self._save_exit_btn)
        main_layout.addWidget(bottom_bar)
        
        self.setCentralWidget(central)
        
        self.create_tab()
        self.summary_tab()
        self.monitor_tab()
        self.config_tab()
        self.help_tab()
        self.keyword_tab()
        
        self.apply_stylesheet()
    
    def apply_stylesheet(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {self.bg_color};
                color: {self.fg_color};
                font-family: 'Consolas', 'Microsoft YaHei', monospace;
            }}
            QTabWidget::pane {{
                border: 1px solid {self.border_color};
                background-color: {self.bg_color};
            }}
            QTabBar::tab {{
                background-color: {self.btn_bg_color};
                color: {self.fg_color};
                border: 1px solid {self.border_color};
                padding: 8px 20px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {self.btn_hover_color};
                border-bottom-color: {self.bg_color};
                color: #00ff41;
                font-weight: bold;
            }}
            QTabBar::tab:hover {{
                background-color: {self.btn_hover_color};
                color: #00ff88;
            }}
            QPushButton {{
                background-color: {self.btn_bg_color};
                color: {self.fg_color};
                border: 1px solid {self.border_color};
                padding: 8px 16px;
                border-radius: 2px;
                font-family: 'Consolas', monospace;
            }}
            QPushButton:hover {{
                background-color: {self.btn_hover_color};
                border-color: #00ff41;
                color: #00ff41;
            }}
            QPushButton:pressed {{
                background-color: #003300;
            }}
            QLineEdit, QTextEdit, QTextBrowser, QSpinBox, QComboBox {{
                background-color: {self.input_bg_color};
                color: {self.fg_color};
                border: 1px solid {self.border_color};
                padding: 6px;
                border-radius: 2px;
                font-family: 'Consolas', 'Microsoft YaHei', monospace;
            }}
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
                border-color: #00ff41;
            }}
            QGroupBox {{
                border: 1px solid {self.border_color};
                border-radius: 2px;
                margin-top: 12px;
                padding-top: 10px;
                color: #00ff41;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #00ff41;
            }}
            QLabel {{
                color: {self.fg_color};
            }}
            QRadioButton {{
                color: {self.fg_color};
            }}
            QCheckBox {{
                color: {self.fg_color};
            }}
            QScrollBar:vertical {{
                background-color: {self.btn_bg_color};
                width: 10px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.border_color};
                border-radius: 2px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #00ff41;
            }}
            QScrollBar:horizontal {{
                background-color: {self.btn_bg_color};
                height: 10px;
                border-radius: 2px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {self.border_color};
                border-radius: 2px;
            }}
            QProgressBar {{
                border: 1px solid {self.border_color};
                background-color: {self.input_bg_color};
                color: {self.fg_color};
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: #00ff41;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.input_bg_color};
                color: {self.fg_color};
                border: 1px solid {self.border_color};
                selection-background-color: #003300;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {self.btn_bg_color};
                border: none;
            }}
        """)
    
    def create_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        title = QLabel("初始化与创建章节")
        title.setStyleSheet(f"font-size: {self.base_title_size}px; font-weight: bold; color: #00FF41;")
        layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # === 初始化指南 ===
        guide_text = QTextBrowser()
        guide_text.setOpenExternalLinks(False)
        guide_text.setMaximumHeight(420)
        guide_text.setStyleSheet(f"background: rgba(0,10,0,0.5); border: 1px solid #0a2a1a; border-radius: 6px; padding: 4px;")
        guide_text.setHtml(f"""
        <style>
        body {{ color:#c0d0c0; font-family:Microsoft YaHei; font-size:14px; line-height:1.5; }}
        h3 {{ color:#00dd66; margin:0.5em 0 0.3em; }}
        h4 {{ color:#44bb88; margin:0.3em 0; }}
        code {{ background:#0a1a0a; color:#88dd88; padding:0 4px; border-radius:3px; font-family:Consolas; }}
        .folder {{ color:#88ccff; }}
        .comment {{ color:#668866; }}
        hr {{ border:0; border-top:1px solid #0a2a1a; margin:0.5em 0; }}
        ol {{ padding-left:1.5em; margin:0.3em 0; }}
        li {{ margin:0.2em 0; }}
        </style>
        
        <h3>程序全自动管理卷和章节</h3>
        <pre style='background:#040a04; padding:8px; border-radius:4px; line-height:1.6;'>
<span class='folder'>your_folder/</span>
 ├─ <span class='folder'>1[old_98765]/</span>   <span class='comment'>← 第一卷（已完结，自动标记旧卷）</span>
 ├─ <span class='folder'>2[new_12345]/</span>    <span class='comment'>← 第二卷（当前活跃，监控自动标记字数）</span>
 ├─ <span class='folder'>3[old_54321]/</span>   <span class='comment'>← 第三卷（已完结，自动标记旧卷）</span>
 └─ <span class='folder'>NovelHelper.ini</span>    <span class='comment'>← 配置文件</span></pre>
        
        <ul>
        <li><b>选定小说目录后自动创建</b> <code>1[new_0]/</code> + 10个空章节</li>
        <li><b>启动监控后</b>，每配置间隔秒数自动检测最新章节：
            <ul>
            <li>最新章节<strong>超过20个中文字符</strong> → 自动新增配置数量的空章节到当前卷</li>
            <li>检测到新文件夹（点击「<span style='color:#00ff88;'>增加新卷</span>」创建纯数字文件夹）：
                <ol>
                <li>清理旧卷中的空章节</li>
                <li>在新卷中承接旧卷最新章节，自动创建规定数量的空章节</li>
                <li>旧卷标记为 <code>[old_字数]</code></li>
                <li>新卷标记为 <code>[new_字数]</code></li>
                <li>自动运行 Summary 合并生成卷文件</li>
                </ol>
            </li>
            </ul>
        </li>
        </ul>
        
        <hr>
        <h4>首次设置步骤：</h4>
        <ol>
        <li>启动程序</li>
        <li>进入「参数配置」标签页</li>
        <li>点击「小说目录」旁边的「选择...」按钮</li>
        <li>选择你要存放小说的文件夹</li>
        <li>如果文件夹为空，程序会询问<strong>是否自动初始化</strong></li>
        <li>选择「是」将自动创建：<br>
            <code>1[new_0]/</code> 目录（第一卷，含10个空章节）</li>
        <li>回到「监控管理」标签页，点击「启动监控」</li>
        <li>之后一切自动：写满20字 → 自动增章；新建卷 → 自动处理+Summary</li>
        </ol>
        <p style='color:#668866; font-size:0.85em;'>* 如需手动创建新卷，点击下方「增加新卷」按钮，监控会自动处理后续步骤。</p>
        """)
        scroll_layout.addWidget(guide_text)
        
        # === 增加新卷按钮 ===
        add_vol_layout = QHBoxLayout()
        self.create_tab_add_vol_btn = QPushButton("📖 增加新卷")
        self.create_tab_add_vol_btn.setStyleSheet("""
            QPushButton{color:#00FF41;border-color:#00AA30;padding:6px 18px;font-size:16px;font-weight:bold;}
            QPushButton:hover{background:#003310;}
        """)
        self.create_tab_add_vol_btn.clicked.connect(self.add_new_volume)
        add_vol_layout.addStretch()
        add_vol_layout.addWidget(self.create_tab_add_vol_btn)
        add_vol_layout.addStretch()
        scroll_layout.addLayout(add_vol_layout)
        
        # === 分隔线 ===
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #0a2a1a;")
        scroll_layout.addWidget(sep)
        sep2 = QLabel("批量创建章节")
        sep2.setStyleSheet(f"font-size: {self.base_font_size}px; font-weight: bold; color: #00cc66; padding: 6px 0;")
        scroll_layout.addWidget(sep2)
        
        # === 批量创建章节表单 ===
        form_layout = QFormLayout()
        
        self.start_chapter = QSpinBox()
        self.start_chapter.setRange(1, 99999)
        self.start_chapter.setValue(1)
        form_layout.addRow(language_manager.tr("start_chapter_label"), self.start_chapter)
        
        self.end_chapter = QSpinBox()
        self.end_chapter.setRange(1, 99999)
        self.end_chapter.setValue(10)
        form_layout.addRow(language_manager.tr("end_chapter_label"), self.end_chapter)
        
        self.name_suffix = QLineEdit()
        cfg_fmt = ConfigManager.get('Format', 'export_format', fallback='')
        if cfg_fmt:
            self.name_suffix.setPlaceholderText(f"当前格式: {cfg_fmt}（{language_manager.tr('enter_file_suffix')}）")
        else:
            self.name_suffix.setPlaceholderText(language_manager.tr("enter_file_suffix"))
        form_layout.addRow(language_manager.tr("file_suffix_label"), self.name_suffix)
        
        self.create_dir_btn = QPushButton(language_manager.tr("select_directory"))
        self.create_dir_path = QLineEdit()
        self.create_dir_path.setText(get_novel_dir())
        self.create_dir_path.setReadOnly(True)
        self.create_dir_btn.clicked.connect(self._select_create_dir)
        
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.create_dir_path)
        dir_layout.addWidget(self.create_dir_btn)
        form_layout.addRow(language_manager.tr("save_directory_label"), dir_layout)
        
        scroll_layout.addLayout(form_layout)
        
        self.create_result = QTextBrowser()
        self.create_result.setMaximumHeight(150)
        scroll_layout.addWidget(QLabel(language_manager.tr("creation_result")))
        scroll_layout.addWidget(self.create_result)
        
        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton(language_manager.tr("start_creation"))
        self.create_btn.clicked.connect(self.create_files)
        btn_layout.addWidget(self.create_btn)
        scroll_layout.addLayout(btn_layout)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        self.tabs.addTab(tab, "初始化与创建章节")
    
    def _select_create_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, language_manager.tr("select_directory"))
        if dir_path:
            self.create_dir_path.setText(dir_path)
            ConfigManager.set('Monitor', 'novel_dir', dir_path)
            if hasattr(self, 'config_novel_dir'):
                self.config_novel_dir.setText(dir_path)
            self.log_info.append(f"[OK] 小说目录已设置: {dir_path}")
            self.refresh_keywords()
            self._check_auto_initialize(dir_path)
    
    def _select_config_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, language_manager.tr("select_directory"))
        if dir_path:
            self.config_novel_dir.setText(dir_path)
            ConfigManager.set('Monitor', 'novel_dir', dir_path)
            self.log_info.append(f"[OK] 小说目录已设置: {dir_path}")
            self.refresh_keywords()
            self._check_auto_initialize(dir_path)
    
    def create_files(self):
        start = self.start_chapter.value()
        end = self.end_chapter.value()
        suffix = self.name_suffix.text()
        output_dir = self.create_dir_path.text()
        
        if start > end:
            QMessageBox.warning(self, language_manager.tr("error"), "起始章节不能大于结束章节")
            return
        
        self.create_result.clear()
        count = 0
        for i in range(start, end + 1):
            filename = file_manager.generate_chapter_name(i, suffix)
            filepath = os.path.join(output_dir, filename)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"第{i}个文件")
                count += 1
                self.create_result.append(f"创建: {filename}")
            except Exception as e:
                self.create_result.append(f"失败: {filename} - {e}")
        
        self.create_result.append(f"\n完成! 共创建 {count} 个文件")
    
    def _check_auto_initialize(self, novel_dir):
        if not os.path.exists(novel_dir):
            return
        items = os.listdir(novel_dir)
        vol_folders = [f for f in items if os.path.isdir(os.path.join(novel_dir, f)) and FileManager.is_numeric_volume_folder(f)]
        has_ini = any(f == 'NovelHelper.ini' for f in items)
        if vol_folders or (has_ini and len(items) > 0):
            return
        reply = QMessageBox.question(self, language_manager.tr("initialize_directory"),
                                     language_manager.tr("initialize_directory_msg"),
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            fmt_reply = QMessageBox.question(
                self, "章节命名格式",
                "是否自定义章节文件命名格式？\n\n"
                "选择「是」→ 进入格式配置\n"
                "选择「否」→ 使用默认格式\n"
                "  默认格式效果：1第一章_.txt\n\n"
                "格式说明：\n"
                "  {num}=数字  {cn.low.Chapter}=第一百五十三章\n"
                "  {title}=标题名  {types:xxx}=后缀\n"
                "  示例：{cn.low.Chapter}{title}{types:markdown}\n"
                "  → 1第一章_title.md",
                QMessageBox.Yes | QMessageBox.No
            )
            if fmt_reply == QMessageBox.Yes:
                self.tabs.setCurrentWidget(self.tabs.widget(3))
            self._do_auto_initialize(novel_dir)
    
    def _do_auto_initialize(self, novel_dir):
        try:
            vol_path = os.path.join(novel_dir, "1[new_0]")
            os.makedirs(vol_path, exist_ok=True)
            for i in range(1, 11):
                filename = file_manager.generate_chapter_name(i, "")
                filepath = os.path.join(vol_path, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"第{i}个文件")
            ConfigManager.create_default_config()
            self.log_info.append(language_manager.tr("initialize_complete"))
            self.log_info.append(f"[OK] 已创建: 1[new_0]/ (10个空章节)")
            self.refresh_keywords()
        except Exception as e:
            self.log_info.append(f"[ERR] {language_manager.tr('initialize_failed')}: {e}")
            logger.error(f"Auto init failed: {e}")
    
    def summary_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        title = QLabel(language_manager.tr("summary_merge_tool"))
        title.setStyleSheet(f"font-size: {self.base_title_size}px; font-weight: bold;")
        layout.addWidget(title)
        
        mode_group = QGroupBox(language_manager.tr("run_mode"))
        mode_layout = QVBoxLayout(mode_group)
        self.mode1 = QRadioButton(language_manager.tr("stats_only"))
        self.mode2 = QRadioButton(language_manager.tr("stats_and_rename"))
        self.mode2.setChecked(True)
        mode_layout.addWidget(self.mode1)
        mode_layout.addWidget(self.mode2)
        layout.addWidget(mode_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(QLabel(language_manager.tr("progress")))
        layout.addWidget(self.progress_bar)
        
        self.summary_result = QTextBrowser()
        layout.addWidget(QLabel(language_manager.tr("execution_result")))
        layout.addWidget(self.summary_result)
        
        self.summary_btn_run = QPushButton(language_manager.tr("execute_summary"))
        self.summary_btn_run.clicked.connect(self.run_summary)
        layout.addWidget(self.summary_btn_run)
        
        self.tabs.addTab(tab, language_manager.tr("summary_merge_tool"))
    
    def run_summary(self):
        novel_dir = get_novel_dir()
        if not os.path.exists(novel_dir):
            QMessageBox.warning(self, language_manager.tr("error"), f"目录不存在: {novel_dir}")
            return
        
        mode = 1 if self.mode1.isChecked() else 2
        self.summary_result.clear()
        self.progress_bar.setValue(10)
        
        folder_path = novel_dir
        folder_name = os.path.basename(novel_dir)
        output_file_path = os.path.join(folder_path, f"{folder_name}.txt")
        
        min_content_length = ConfigManager.get_int('Monitor', 'min_word_count', fallback=20)
        
        if os.path.exists(output_file_path):
            existing_size = os.path.getsize(output_file_path)
            if existing_size > 0:
                reply = QMessageBox.question(
                    self, "合并确认",
                    f"目标文件已存在 ({existing_size} 字节)\n是否备份后继续？",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Cancel:
                    return
                if reply == QMessageBox.Yes:
                    backup_name = f"{folder_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak.txt"
                    backup_path = os.path.join(folder_path, backup_name)
                    try:
                        shutil.copy2(output_file_path, backup_path)
                        self.summary_result.append(f"已备份至: {backup_name}")
                    except Exception as e:
                        self.summary_result.append(f"[ERR] 备份失败: {e}")
                        return
            try:
                open(output_file_path, 'w', encoding='utf-8').close()
            except Exception as e:
                self.summary_result.append(f"[ERR] 清空文件失败: {e}")
                logger.error(f"清空文件失败: {e}")
                return
        
        self.summary_result.append(f"模式: {mode} - {'不重命名' if mode == 1 else '重命名'}")
        self.progress_bar.setValue(20)
        
        self.summary_btn_run.setEnabled(False)
        self._summary_worker = SummaryWorker(folder_path, mode, min_content_length)
        self._summary_worker.progress_signal.connect(self._on_summary_progress)
        self._summary_worker.message_signal.connect(self._on_summary_message)
        self._summary_worker.finished_signal.connect(self._on_summary_finished)
        self._summary_worker.error_signal.connect(self._on_summary_error)
        self._summary_worker.start()
    
    def _on_summary_progress(self, value):
        self.progress_bar.setValue(value)
    
    def _on_summary_message(self, msg):
        self.summary_result.append(msg)
    
    def _on_summary_finished(self, result):
        total_cjk = result.get('total_cjk_count', 0)
        total_non_blank = result.get('total_non_blank_count', 0)
        rename_results = result.get('rename_results', [])
        
        for r in rename_results:
            kind, orig, new_name, err = r
            if kind == 'old':
                msg = f"[OLD] 标记旧卷: {orig} -> {new_name}"
                self.summary_result.append(msg)
                logger.info(f"标记旧卷: {orig} -> {new_name}")
            elif kind == 'old_err':
                msg = f"[ERR] 标记旧卷失败 {orig}: {err}"
                self.summary_result.append(msg)
                logger.error(f"标记旧卷失败 {orig}: {err}")
            elif kind == 'new':
                msg = f"[OK] 重命名: {orig} -> {new_name}"
                self.summary_result.append(msg)
                logger.info(f"重命名: {orig} -> {new_name}")
            elif kind == 'new_err':
                msg = f"[ERR] 重命名失败: {err}"
                self.summary_result.append(msg)
                logger.error(f"重命名失败: {err}")
        
        msg = f"[OK] 完成！CJK字符: {total_cjk}, 非空白字符: {total_non_blank}"
        self.summary_result.append(msg)
        logger.info(msg)
        self.summary_btn_run.setEnabled(True)
        QTimer.singleShot(2000, lambda: self.progress_bar.setValue(0))
    
    def _on_summary_error(self, err_msg):
        self.summary_result.append(f"[ERR] {err_msg}")
        self.summary_btn_run.setEnabled(True)
        QTimer.singleShot(2000, lambda: self.progress_bar.setValue(0))
    
    def monitor_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        title = QLabel(language_manager.tr("monitor_system"))
        title.setStyleSheet(f"font-size: {self.base_title_size}px; font-weight: bold; color: #00ff41;")
        layout.addWidget(title)
        
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton(language_manager.tr("start_monitor"))
        self.btn_stop = QPushButton(language_manager.tr("stop_monitor"))
        self.btn_add_volume = QPushButton(language_manager.tr("add_new_volume_btn"))
        self.btn_preview = QPushButton("章节预览")
        self.btn_start.clicked.connect(self.start_monitor)
        self.btn_stop.clicked.connect(self.stop_monitor)
        self.btn_add_volume.clicked.connect(self.add_new_volume)
        self.btn_preview.clicked.connect(self._show_chapter_preview)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(self.btn_add_volume)
        btn_layout.addWidget(self.btn_preview)
        layout.addLayout(btn_layout)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel(language_manager.tr("log_filter")))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "最近15条", "最近30条", "最近50条"])
        self.filter_combo.currentTextChanged.connect(self.filter_logs)
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self.status_label = QLabel(language_manager.tr("status_stopped"))
        layout.addWidget(self.status_label)

        splitter = QSplitter(Qt.Vertical)
        self.log_info = QTextBrowser()
        self.log_info.document().setMaximumBlockCount(2000)
        splitter.addWidget(self.log_info)

        self._chapter_preview = QTreeWidget()
        self._chapter_preview.setHeaderLabels(["卷/章节", "标题", "字数", "修改时间"])
        self._chapter_preview.setAlternatingRowColors(False)
        self._chapter_preview.setStyleSheet("QTreeWidget{background:#000d03;color:#88cc88;border:1px solid #00AA30;font-family:'Consolas','Microsoft YaHei';}QTreeWidget::item:hover{background:#003300;color:#00ff41;}QHeaderView::section{background:#001a05;color:#00ff41;border:1px solid #00AA30;padding:4px;}")
        self._chapter_preview.setVisible(False)
        self._chapter_preview.itemDoubleClicked.connect(self._on_preview_item_double_clicked)
        splitter.addWidget(self._chapter_preview)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        self.monitor_thread = None
        self._msg_counter = 0
        self.all_messages = []
        self.tabs.addTab(tab, language_manager.tr("monitor_management"))
    
    def _show_chapter_preview(self):
        novel_dir = get_novel_dir()
        if not os.path.exists(novel_dir):
            QMessageBox.warning(self, "错误", "请先设置小说目录")
            return
        self._chapter_preview.clear()
        self._chapter_preview.setVisible(True)
        volumes = sorted([f for f in os.listdir(novel_dir) if os.path.isdir(os.path.join(novel_dir, f)) and FileManager.is_numeric_volume_folder(f)])
        if not volumes:
            self.log_info.append("[WARN] 未找到卷文件夹")
            return
        for vol in volumes:
            vol_path = os.path.join(novel_dir, vol)
            vol_item = QTreeWidgetItem(self._chapter_preview, [vol, "", "", ""])
            vol_item.setForeground(0, QColor("#00ff41"))
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
                    ch_item = QTreeWidgetItem(vol_item, [f"  {ch}", ch.replace('.txt',''), str(word_count), mtime])
                    ch_item.setData(0, Qt.UserRole, ch_path)
                except:
                    ch_item = QTreeWidgetItem(vol_item, [f"  {ch}", ch.replace('.txt',''), "?", "?"])
                    ch_item.setData(0, Qt.UserRole, os.path.join(vol_path, ch))
            vol_item.setText(2, str(total_words))
            vol_item.setText(3, datetime.fromtimestamp(os.path.getmtime(vol_path)).strftime('%m-%d %H:%M'))
        self._chapter_preview.expandAll()
    
    def _on_preview_item_double_clicked(self, item, col):
        path = item.data(0, Qt.UserRole)
        if path and os.path.isfile(path):
            try:
                os.startfile(path)
            except:
                pass
    
    def start_monitor(self):
        if self.monitor_thread and self.monitor_thread.isRunning():
            return
        self.monitor_thread = MonitorThread()
        self.monitor_thread.update_signal.connect(self._on_monitor_update)
        self.monitor_thread.error_signal.connect(self._on_monitor_error)
        self.monitor_thread.run_summary_signal.connect(self._on_auto_summary_request)
        self.monitor_thread.start()
        self.status_label.setText(language_manager.tr("monitor_started"))
        self.log_info.append(f"[OK] {language_manager.tr('monitor_started')}")
    
    def stop_monitor(self):
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread.wait(3000)
            self.monitor_thread = None
            self.status_label.setText(language_manager.tr("monitor_stopped"))
            self.log_info.append(f"[OK] {language_manager.tr('monitor_stopped')}")
    
    def _on_monitor_update(self, folder_states, messages):
        for msg in messages:
            self._msg_counter += 1
            self.all_messages.append(msg)
            if msg.startswith("[ERR]") or "失败" in msg or "错误" in msg:
                color = self.error_color
            elif msg.startswith("[NEW]") or "新卷" in msg or "创建" in msg or "新增" in msg:
                color = self.warn_color
            else:
                t = self._msg_counter
                g = max(80, 255 - t * 2)
                r = min(100, t * 3)
                color = f"#{r:02x}{g:02x}30"
            self.log_info.append(f"<span style='color:{color};'>{msg}</span>")
        if len(self.all_messages) > 500:
            self.all_messages = self.all_messages[-500:]

    def filter_logs(self):
        self.update_log_display()

    def update_log_display(self):
        text = self.filter_combo.currentText() if hasattr(self, 'filter_combo') else "全部"
        if text == "全部":
            filtered = self.all_messages
        elif text == "最近15条":
            filtered = self.all_messages[-15:]
        elif text == "最近30条":
            filtered = self.all_messages[-30:]
        elif text == "最近50条":
            filtered = self.all_messages[-50:]
        else:
            filtered = self.all_messages
        self.log_info.clear()
        for msg in filtered:
            self.log_info.append(msg)
    
    def _on_monitor_error(self, err_msg):
        logger.error(f"监控线程错误: {err_msg}")
        self.log_info.append(f"<span style='color:{self.error_color};font-weight:bold;'>⚠ {err_msg}</span>")
    
    def _on_auto_summary_request(self, novel_dir):
        if not os.path.exists(novel_dir):
            return
        min_content_length = ConfigManager.get_int('Monitor', 'min_word_count', fallback=20)
        self._auto_summary_worker = SummaryWorker(novel_dir, 2, min_content_length)
        self._auto_summary_worker.message_signal.connect(lambda msg: self.log_info.append(msg))
        self._auto_summary_worker.finished_signal.connect(self._on_auto_summary_finished)
        self._auto_summary_worker.error_signal.connect(lambda err: self.log_info.append(f"[ERR] 自动Summary失败: {err}"))
        self.log_info.append(f"[SUM] 新卷处理完成，自动运行Summary合并...")
        self._auto_summary_worker.start()
    
    def _on_auto_summary_finished(self, result):
        self.log_info.append(f"[OK] Summary合并完成")
        self.refresh_keywords()
        rename_results = result.get('rename_results', [])
        for old, new in rename_results:
            self.log_info.append(f"  重命名: {old} -> {new}")
    
    def add_new_volume(self):
        novel_dir = get_novel_dir()
        if not os.path.exists(novel_dir):
            QMessageBox.warning(self, language_manager.tr("error"), "请先设置小说目录")
            return
        
        folders = [f for f in os.listdir(novel_dir) if os.path.isdir(os.path.join(novel_dir, f)) and FileManager.is_numeric_volume_folder(f)]
        if not folders:
            new_vol_num = 1
        else:
            vol_nums = [FileManager.get_volume_number(f) for f in folders if FileManager.get_volume_number(f)]
            new_vol_num = max(vol_nums) + 1 if vol_nums else 1
        
        new_vol_name = str(new_vol_num)
        new_vol_path = os.path.join(novel_dir, new_vol_name)
        
        try:
            os.makedirs(new_vol_path, exist_ok=True)
            self.log_info.append(f"[OK] 创建新卷文件夹: {new_vol_name}，监控启动后将自动处理标记")
        except Exception as e:
            self.log_info.append(f"[ERR] 创建新卷失败: {e}")
    
    def config_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        title = QLabel(language_manager.tr("parameter_config"))
        title.setStyleSheet(f"font-size: {self.base_title_size}px; font-weight: bold; color: #00ff41;")
        layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # === UI ===
        ui_group = QGroupBox(language_manager.tr("ui_size_config"))
        ui_form = QFormLayout(ui_group)
        self.config_base_font = QSpinBox(); self.config_base_font.setRange(8, 48); self.config_base_font.setValue(self.base_font_size)
        ui_form.addRow(language_manager.tr("base_font_size"), self.config_base_font)
        self.config_title_font = QSpinBox(); self.config_title_font.setRange(12, 72); self.config_title_font.setValue(self.base_title_size)
        ui_form.addRow(language_manager.tr("title_font_size"), self.config_title_font)
        self.config_log_font = QSpinBox(); self.config_log_font.setRange(8, 32); self.config_log_font.setValue(self.log_font_size)
        ui_form.addRow(language_manager.tr("log_font_size"), self.config_log_font)
        self.config_initial_width = QSpinBox(); self.config_initial_width.setRange(400, 2000); self.config_initial_width.setValue(self.initial_width)
        ui_form.addRow(language_manager.tr("initial_width"), self.config_initial_width)
        self.config_initial_height = QSpinBox(); self.config_initial_height.setRange(300, 1500); self.config_initial_height.setValue(self.initial_height)
        ui_form.addRow(language_manager.tr("initial_height"), self.config_initial_height)
        self.config_graph_font = QSpinBox(); self.config_graph_font.setRange(8, 32); self.config_graph_font.setValue(self.graph_font_size)
        ui_form.addRow("网络图字号", self.config_graph_font)
        self.config_kwlist_font = QSpinBox(); self.config_kwlist_font.setRange(30, 60); self.config_kwlist_font.setValue(self.kwlist_font_size)
        ui_form.addRow("关键词字号", self.config_kwlist_font)
        self.config_kwlist_title = QSpinBox(); self.config_kwlist_title.setRange(14, 40); self.config_kwlist_title.setValue(self.kwlist_title_size)
        ui_form.addRow("关键词标题字号", self.config_kwlist_title)
        self.config_kwlist_color = QLineEdit(); self.config_kwlist_color.setText(self.kwlist_font_color)
        ui_form.addRow("关键词颜色", self.config_kwlist_color)
        self.config_kwlist_family = QLineEdit(); self.config_kwlist_family.setText(self.kwlist_font_family)
        ui_form.addRow("关键词字体", self.config_kwlist_family)
        self.config_card_font = QSpinBox(); self.config_card_font.setRange(30, 60); self.config_card_font.setValue(self.card_font_size)
        ui_form.addRow("人物卡字号", self.config_card_font)
        self.config_card_title = QSpinBox(); self.config_card_title.setRange(14, 40); self.config_card_title.setValue(self.card_title_size)
        ui_form.addRow("人物卡标题字号", self.config_card_title)
        scroll_layout.addWidget(ui_group)
        
        # === Colors ===
        color_group = QGroupBox("色彩方案")
        color_form = QFormLayout(color_group)
        self.config_bg_color = QLineEdit(); self.config_bg_color.setText(self.bg_color)
        color_form.addRow("背景色", self.config_bg_color)
        self.config_fg_color = QLineEdit(); self.config_fg_color.setText(self.fg_color)
        color_form.addRow("前景/文字色", self.config_fg_color)
        self.config_border_color = QLineEdit(); self.config_border_color.setText(self.border_color)
        color_form.addRow("边框色", self.config_border_color)
        self.config_error_color = QLineEdit(); self.config_error_color.setText(self.error_color)
        color_form.addRow("错误色", self.config_error_color)
        self.config_warn_color = QLineEdit(); self.config_warn_color.setText(self.warn_color)
        color_form.addRow("警告色", self.config_warn_color)
        scroll_layout.addWidget(color_group)
        
        # === Monitor ===
        monitor_group = QGroupBox(language_manager.tr("monitor_config"))
        monitor_form = QFormLayout(monitor_group)
        self.config_check_interval = QSpinBox(); self.config_check_interval.setRange(1, 300); self.config_check_interval.setValue(ConfigManager.get_int('Monitor', 'check_interval', fallback=15))
        monitor_form.addRow(language_manager.tr("monitor_interval"), self.config_check_interval)
        self.config_max_ahead = QSpinBox(); self.config_max_ahead.setRange(0, 10); self.config_max_ahead.setValue(ConfigManager.get_int('Monitor', 'max_ahead_chapters', fallback=2))
        monitor_form.addRow(language_manager.tr("pregenerate_chapters"), self.config_max_ahead)
        self.config_min_word = QSpinBox(); self.config_min_word.setRange(1, 1000); self.config_min_word.setValue(ConfigManager.get_int('Monitor', 'min_word_count', fallback=20))
        monitor_form.addRow(language_manager.tr("trigger_word_count"), self.config_min_word)
        self.config_heartbeat = QSpinBox(); self.config_heartbeat.setRange(30, 600); self.config_heartbeat.setValue(self.heartbeat_timeout)
        monitor_form.addRow("心跳超时(秒)", self.config_heartbeat)
        self.config_novel_dir_btn = QPushButton(language_manager.tr("select_directory"))
        self.config_novel_dir = QLineEdit(); self.config_novel_dir.setText(ConfigManager.get('Monitor', 'novel_dir', fallback=''))
        self.config_novel_dir.setReadOnly(True); self.config_novel_dir_btn.clicked.connect(self._select_config_dir)
        dir_layout = QHBoxLayout(); dir_layout.addWidget(self.config_novel_dir); dir_layout.addWidget(self.config_novel_dir_btn)
        monitor_form.addRow(language_manager.tr("novel_dir_label"), dir_layout)
        scroll_layout.addWidget(monitor_group)
        
        # === Graph ===
        graph_group = QGroupBox("神经网络图")
        graph_form = QFormLayout(graph_group)
        self.config_layout_ideal = QSpinBox(); self.config_layout_ideal.setRange(50, 500); self.config_layout_ideal.setValue(self.layout_ideal)
        graph_form.addRow("布局理想长度", self.config_layout_ideal)
        self.config_node_limit = QSpinBox(); self.config_node_limit.setRange(50, 500); self.config_node_limit.setValue(self.node_limit)
        graph_form.addRow("节点上限", self.config_node_limit)
        self.config_edge_width = QSpinBox(); self.config_edge_width.setRange(1, 10); self.config_edge_width.setValue(self.edge_width)
        graph_form.addRow("连线宽度", self.config_edge_width)
        self.config_auto_layout = QCheckBox("自动保存布局"); self.config_auto_layout.setChecked(ConfigManager.get_int('Graph', 'auto_save_layout', fallback=1)==1)
        graph_form.addRow("", self.config_auto_layout)
        scroll_layout.addWidget(graph_group)
        
        # === Frequency ===
        freq_group = QGroupBox("频度追踪")
        freq_form = QFormLayout(freq_group)
        self.config_freq_min_len = QSpinBox(); self.config_freq_min_len.setRange(1, 10); self.config_freq_min_len.setValue(ConfigManager.get_int('Frequency', 'min_word_length', fallback=2))
        freq_form.addRow("最小词长", self.config_freq_min_len)
        self.config_freq_min_occ = QSpinBox(); self.config_freq_min_occ.setRange(1, 20); self.config_freq_min_occ.setValue(ConfigManager.get_int('Frequency', 'min_occurrences', fallback=3))
        freq_form.addRow("最少出现次数", self.config_freq_min_occ)
        self.config_freq_inactive = QSpinBox(); self.config_freq_inactive.setRange(1, 50); self.config_freq_inactive.setValue(ConfigManager.get_int('Frequency', 'inactive_chapters', fallback=3))
        freq_form.addRow("暂隐阈值(章)", self.config_freq_inactive)
        self.config_freq_auto = QCheckBox("自动扫描"); self.config_freq_auto.setChecked(ConfigManager.get_int('Frequency', 'auto_scan', fallback=1)==1)
        freq_form.addRow("", self.config_freq_auto)
        scroll_layout.addWidget(freq_group)
        
        # === Language ===
        lang_group = QGroupBox(language_manager.tr("language_settings"))
        lang_form = QFormLayout(lang_group)
        self.config_language = QComboBox()
        self.config_language.addItem("简体中文", "zh_CN"); self.config_language.addItem("English", "en_US"); self.config_language.addItem("日本語", "ja_JP")
        current_lang = language_manager.get_current_language()
        for i in range(self.config_language.count()):
            if self.config_language.itemData(i) == current_lang: self.config_language.setCurrentIndex(i); break
        self._lang_label = QLabel(language_manager.tr("language"))
        lang_form.addRow(self._lang_label, self.config_language)
        scroll_layout.addWidget(lang_group)
        
        # === Format ===
        format_group = QGroupBox(language_manager.tr("format_config"))
        format_form = QFormLayout(format_group)
        
        self.config_export_format = QLineEdit()
        self.config_export_format.setText(ConfigManager.get('Format', 'export_format', fallback=''))
        self.config_export_format.textChanged.connect(self.update_format_preview)
        format_form.addRow(language_manager.tr("export_filename_format"), self.config_export_format)
        
        self._format_help_font_size = ConfigManager.get_int('Format', 'format_help_font_size', fallback=20)
        
        self.config_export_format_help = QLabel(language_manager.tr("format_help_filename"))
        self.config_export_format_help.setStyleSheet(f"color: #888888; font-size: {self._format_help_font_size}px;")
        self.config_export_format_help.setWordWrap(True)
        format_form.addRow("", self.config_export_format_help)
        
        self.config_export_format_preview = QLabel("")
        self.config_export_format_preview.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;")
        format_form.addRow("", self.config_export_format_preview)
        
        self.config_export_volume_format = QLineEdit()
        self.config_export_volume_format.setText(ConfigManager.get('Format', 'export_volume_format', fallback=''))
        self.config_export_volume_format.textChanged.connect(self.update_format_preview)
        format_form.addRow(language_manager.tr("export_volume_format"), self.config_export_volume_format)
        
        self.config_export_volume_help = QLabel(language_manager.tr("format_help_volume"))
        self.config_export_volume_help.setStyleSheet(f"color: #888888; font-size: {self._format_help_font_size}px;")
        self.config_export_volume_help.setWordWrap(True)
        format_form.addRow("", self.config_export_volume_help)
        
        self.config_export_volume_preview = QLabel("")
        self.config_export_volume_preview.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;")
        format_form.addRow("", self.config_export_volume_preview)
        
        self.config_export_chapter_format = QLineEdit()
        self.config_export_chapter_format.setText(ConfigManager.get('Format', 'export_chapter_format', fallback=''))
        self.config_export_chapter_format.textChanged.connect(self.update_format_preview)
        format_form.addRow(language_manager.tr("export_chapter_format"), self.config_export_chapter_format)
        
        self.config_export_chapter_help = QLabel(language_manager.tr("format_help_chapter"))
        self.config_export_chapter_help.setStyleSheet(f"color: #888888; font-size: {self._format_help_font_size}px;")
        self.config_export_chapter_help.setWordWrap(True)
        format_form.addRow("", self.config_export_chapter_help)
        
        self.config_export_chapter_preview = QLabel("")
        self.config_export_chapter_preview.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;")
        format_form.addRow("", self.config_export_chapter_preview)
        
        self.config_preview_color = QLineEdit()
        self.config_preview_color.setText(ConfigManager.get('Format', 'preview_color', fallback='#FFFFFF'))
        self.config_preview_color.textChanged.connect(self._update_format_preview_style)
        format_form.addRow(language_manager.tr("preview_color"), self.config_preview_color)
        
        self.config_preview_font_size = QSpinBox()
        self.config_preview_font_size.setRange(12, 48)
        self.config_preview_font_size.setValue(ConfigManager.get_int('Format', 'preview_font_size', fallback=23))
        self.config_preview_font_size.valueChanged.connect(self._update_format_preview_style)
        format_form.addRow(language_manager.tr("preview_font_size"), self.config_preview_font_size)
        
        self.config_format_help_font = QSpinBox()
        self.config_format_help_font.setRange(14, 36)
        self.config_format_help_font.setValue(self._format_help_font_size)
        self.config_format_help_font.valueChanged.connect(self._update_format_help_style)
        format_form.addRow("格式帮助字号", self.config_format_help_font)
        
        scroll_layout.addWidget(format_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton(language_manager.tr("confirm")); save_btn.clicked.connect(self.save_config)
        btn_layout.addWidget(save_btn)
        self._config_apply_btn = QPushButton(language_manager.tr("save_and_apply")); self._config_apply_btn.clicked.connect(self.save_and_apply_config)
        btn_layout.addWidget(self._config_apply_btn)
        self._config_reload_btn = QPushButton(language_manager.tr("reload_config")); self._config_reload_btn.clicked.connect(self.reload_config)
        btn_layout.addWidget(self._config_reload_btn)
        reset_btn = QPushButton("恢复默认"); reset_btn.clicked.connect(self._reset_config_default)
        reset_btn.setStyleSheet("QPushButton{color:#FFAA00;border-color:#FFAA00;}QPushButton:hover{background:#332200;}")
        btn_layout.addWidget(reset_btn)
        layout.addLayout(btn_layout)
        self.tabs.addTab(tab, language_manager.tr("parameter_config"))
        self.update_format_preview()
        self._update_format_preview_style()
        self._update_format_help_style()
    
    def _write_config_to_file(self):
        ConfigManager.set('UI', 'base_font_size', self.config_base_font.value())
        ConfigManager.set('UI', 'base_title_size', self.config_title_font.value())
        ConfigManager.set('UI', 'log_font_size', self.config_log_font.value())
        ConfigManager.set('UI', 'initial_width', self.config_initial_width.value())
        ConfigManager.set('UI', 'initial_height', self.config_initial_height.value())
        ConfigManager.set('UI', 'graph_font_size', self.config_graph_font.value())
        ConfigManager.set('UI', 'kwlist_font_size', self.config_kwlist_font.value())
        ConfigManager.set('UI', 'kwlist_title_size', self.config_kwlist_title.value())
        ConfigManager.set('UI', 'kwlist_font_color', self.config_kwlist_color.text())
        ConfigManager.set('UI', 'kwlist_font_family', self.config_kwlist_family.text())
        ConfigManager.set('UI', 'card_font_size', self.config_card_font.value())
        ConfigManager.set('UI', 'card_title_size', self.config_card_title.value())
        ConfigManager.set('UI', 'bg_color', self.config_bg_color.text())
        ConfigManager.set('UI', 'fg_color', self.config_fg_color.text())
        ConfigManager.set('UI', 'border_color', self.config_border_color.text())
        ConfigManager.set('UI', 'error_color', self.config_error_color.text())
        ConfigManager.set('UI', 'warn_color', self.config_warn_color.text())
        ConfigManager.set('Monitor', 'check_interval', self.config_check_interval.value())
        ConfigManager.set('Monitor', 'max_ahead_chapters', self.config_max_ahead.value())
        ConfigManager.set('Monitor', 'min_word_count', self.config_min_word.value())
        ConfigManager.set('Monitor', 'novel_dir', self.config_novel_dir.text())
        ConfigManager.set('Monitor', 'heartbeat_timeout', self.config_heartbeat.value())
        ConfigManager.set('Graph', 'layout_ideal_length', self.config_layout_ideal.value())
        ConfigManager.set('Graph', 'node_limit', self.config_node_limit.value())
        ConfigManager.set('Graph', 'auto_save_layout', '1' if self.config_auto_layout.isChecked() else '0')
        ConfigManager.set('Theme', 'edge_width', self.config_edge_width.value())
        ConfigManager.set('Frequency', 'min_word_length', self.config_freq_min_len.value())
        ConfigManager.set('Frequency', 'min_occurrences', self.config_freq_min_occ.value())
        ConfigManager.set('Frequency', 'inactive_chapters', self.config_freq_inactive.value())
        ConfigManager.set('Frequency', 'auto_scan', '1' if self.config_freq_auto.isChecked() else '0')
        selected_lang = self.config_language.currentData()
        if selected_lang:
            ConfigManager.set('Language', 'current', selected_lang)
            language_manager._current_lang = selected_lang
            file_manager.set_language(selected_lang)
        ConfigManager.set('Format', 'export_format', self.config_export_format.text())
        ConfigManager.set('Format', 'export_volume_format', self.config_export_volume_format.text())
        ConfigManager.set('Format', 'export_chapter_format', self.config_export_chapter_format.text())
        ConfigManager.set('Format', 'preview_color', self.config_preview_color.text())
        ConfigManager.set('Format', 'preview_font_size', self.config_preview_font_size.value())
        ConfigManager.set('Format', 'format_help_font_size', self.config_format_help_font.value())
    
    def _reset_config_default(self):
        if QMessageBox.question(self, "确认", "恢复到黑客帝国默认配色?\n(背景黑墨色、亮绿字体)", QMessageBox.Yes|QMessageBox.No) == QMessageBox.No:
            return
        self.config_bg_color.setText('#020804')
        self.config_fg_color.setText('#00FF41')
        self.config_border_color.setText('#00AA30')
        self.config_error_color.setText('#FF3333')
        self.config_warn_color.setText('#FFAA00')
        self.config_base_font.setValue(20)
        self.config_title_font.setValue(32)
        self.config_log_font.setValue(16)
        self.config_graph_font.setValue(14)
        self.config_kwlist_font.setValue(20)
        self.config_kwlist_title.setValue(18)
        self.config_kwlist_color.setText('#00FF41')
        self.config_kwlist_family.setText('Microsoft YaHei')
        self.config_card_font.setValue(30)
        self.config_card_title.setValue(20)
        self.config_layout_ideal.setValue(200)
        self.config_node_limit.setValue(200)
        self.config_edge_width.setValue(3)
        self.config_freq_min_len.setValue(2)
        self.config_freq_min_occ.setValue(3)
        self.config_freq_inactive.setValue(3)
        self.config_auto_layout.setChecked(True)
        self.config_freq_auto.setChecked(True)
        self._write_config_to_file()
        self.load_config_values()
        self.apply_stylesheet()
        self._sync_keyword_browser_font()
        QMessageBox.information(self, "OK", "已恢复默认黑客帝国配色")
    
    def save_config(self):
        try:
            self._write_config_to_file()
            file_manager._load_custom_formats()
            self.update_ui_language()
            QMessageBox.information(self, language_manager.tr("success"), language_manager.tr("config_saved_applied"))
            logger.info("Configuration saved")
        except Exception as e:
            QMessageBox.critical(self, language_manager.tr("error"), f"{language_manager.tr('save_config_failed')}: {str(e)}")
            logger.error(f"保存配置失败: {e}")
    
    def save_and_apply_config(self):
        try:
            self._write_config_to_file()
            file_manager._load_custom_formats()
            self.load_config_values()
            self.apply_stylesheet()
            self.update_ui_language()
            self._sync_keyword_browser_font()
            self.update_format_preview()
            self._update_format_preview_style()
            self._update_format_help_style()
            QMessageBox.information(self, language_manager.tr("success"), language_manager.tr("config_saved_applied"))
            logger.info("Configuration saved and applied")
        except Exception as e:
            QMessageBox.critical(self, language_manager.tr("error"), f"{language_manager.tr('save_apply_failed')}: {str(e)}")
            logger.error(f"Save and apply failed: {e}")
    
    def reload_config(self):
        self.load_config_values()
        self.config_base_font.setValue(self.base_font_size)
        self.config_title_font.setValue(self.base_title_size)
        self.config_log_font.setValue(self.log_font_size)
        self.config_initial_width.setValue(self.initial_width)
        self.config_initial_height.setValue(self.initial_height)
        self.config_export_format.setText(ConfigManager.get('Format', 'export_format', fallback=''))
        self.config_export_volume_format.setText(ConfigManager.get('Format', 'export_volume_format', fallback=''))
        self.config_export_chapter_format.setText(ConfigManager.get('Format', 'export_chapter_format', fallback=''))
        self.config_preview_color.setText(ConfigManager.get('Format', 'preview_color', fallback='#FFFFFF'))
        self.config_preview_font_size.setValue(ConfigManager.get_int('Format', 'preview_font_size', fallback=23))
        file_manager._load_custom_formats()
        self.update_format_preview()
        self._update_format_preview_style()
        self._update_format_help_style()
    
    def update_ui_language(self):
        self.setWindowTitle(language_manager.tr("app_title"))
        self.tabs.setTabText(0, "初始化与创建章节")
        self.tabs.setTabText(1, language_manager.tr("summary_merge_tool"))
        self.tabs.setTabText(2, language_manager.tr("monitor_management"))
        self.tabs.setTabText(3, language_manager.tr("parameter_config"))
        self.tabs.setTabText(4, language_manager.tr("user_guide"))
        self.tabs.setTabText(5, language_manager.tr("keyword_manager"))
        
        if hasattr(self, '_config_apply_btn'):
            self._config_apply_btn.setText(language_manager.tr("save_and_apply"))
        if hasattr(self, '_config_reload_btn'):
            self._config_reload_btn.setText(language_manager.tr("reload_config"))
        if hasattr(self, '_lang_label'):
            self._lang_label.setText(language_manager.tr("language"))
        if hasattr(self, 'config_export_format_help'):
            self.config_export_format_help.setText(language_manager.tr("format_help_filename"))
        if hasattr(self, 'config_export_volume_help'):
            self.config_export_volume_help.setText(language_manager.tr("format_help_volume"))
        if hasattr(self, 'config_export_chapter_help'):
            self.config_export_chapter_help.setText(language_manager.tr("format_help_chapter"))
    
    def update_format_preview(self):
        filename_fmt = self.config_export_format.text().strip()
        if filename_fmt:
            try:
                preview = file_manager._format_chapter(filename_fmt, 3, "name")
                self.config_export_format_preview.setText(f"预览: {preview}")
            except Exception:
                self.config_export_format_preview.setText("格式错误")
        else:
            # 无自定义格式时，显示默认格式的预览
            default_fmt = "{num}{cn.low.Chapter}_{title}"
            try:
                preview = file_manager._format_chapter(default_fmt, 3, "name")
                self.config_export_format_preview.setText(f"默认: {preview}")
            except Exception:
                self.config_export_format_preview.setText("")

        vol_fmt = self.config_export_volume_format.text().strip()
        if vol_fmt:
            try:
                preview = file_manager._format_export(vol_fmt, 1, "潜龙在渊", 37523)
                self.config_export_volume_preview.setText(f"预览: {preview}")
            except Exception:
                self.config_export_volume_preview.setText("格式错误")
        else:
            self.config_export_volume_preview.setText("")

        chapter_fmt = self.config_export_chapter_format.text().strip()
        if chapter_fmt:
            try:
                preview = file_manager._format_export(chapter_fmt, 3, "回家")
                self.config_export_chapter_preview.setText(f"预览: {preview}")
            except Exception:
                self.config_export_chapter_preview.setText("格式错误")
        else:
            self.config_export_chapter_preview.setText("")

    def _update_format_preview_style(self):
        color = self.config_preview_color.text().strip() or "#FFFFFF"
        font_size = self.config_preview_font_size.value()
        style = f"color: {color}; font-size: {font_size}px; font-weight: bold;"
        self.config_export_format_preview.setStyleSheet(style)
        self.config_export_volume_preview.setStyleSheet(style)
        self.config_export_chapter_preview.setStyleSheet(style)
    
    def _update_format_help_style(self):
        fs = self.config_format_help_font.value()
        style = f"color: #888888; font-size: {fs}px;"
        self.config_export_format_help.setStyleSheet(style)
        self.config_export_volume_help.setStyleSheet(style)
        self.config_export_chapter_help.setStyleSheet(style)
    
    def help_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        help_text = QTextBrowser()
        help_text.setOpenExternalLinks(True)
        help_text.setHtml(f"""
        <style>
        body {{ background:#020804; color:#c0d0c0; font-family:Microsoft YaHei; padding:1em 1.5em; line-height:1.7; }}
        h2 {{ color:#00FF41; border-bottom:2px solid #00AA30; padding-bottom:6px; margin-top:0; }}
        h3 {{ color:#00dd66; margin-top:1.5em; }}
        h4 {{ color:#44bb88; }}
        hr {{ border:0; border-top:1px solid #0a2a1a; }}
        code {{ background:#0a1a0a; color:#88dd88; padding:1px 5px; border-radius:3px; font-family:Consolas; }}
        blockquote {{ border-left:3px solid #00AA30; margin:0.5em 0; padding:0.3em 1em; background:#040e08; }}
        ul {{ padding-left:1.5em; }}
        li {{ margin:0.3em 0; }}
        .tag {{ display:inline-block; background:#0a2a1a; color:#88dd88; padding:0 6px; border-radius:3px; font-size:0.85em; }}
        </style>
        
        <h2>{language_manager.tr('app_title')} — 完整使用手册</h2>
        
        <h3>一、概览</h3>
        <p>本工具是专为网络小说作者设计的写作辅助系统，集成了<strong>章节管理</strong>、<strong>剧情摘要</strong>、<strong>实时监控</strong>、<strong>关键词管理</strong>与<strong>关系图谱</strong>五大核心功能。</p>
        
        <hr>
        
        <h3>二、创建章节 <span class="tag">Create</span></h3>
        <p>用于在选定的小说目录下批量创建章节文件模板。</p>
        <ul>
        <li><b>起始章节 / 结束章节</b>：指定章节编号范围（须为正整数）</li>
        <li><b>章节前缀</b>：可自定义章节文件名的前缀文字（如 "Chapter"、"第" 等）</li>
        <li>点击「创建」按钮后，程序会在当前卷目录下批量生成对应数量的章节文件</li>
        <li>文件命名格式：<code>{{前缀}}{{编号}}.txt</code></li>
        </ul>
        
        <hr>
        
        <h3>三、Summary合并 <span class="tag">Merge</span></h3>
        <p>将某个卷下的所有章节文件合并为一个总览文件，方便通读与校对。</p>
        <ul>
        <li><b>选择卷</b>：下拉选择要合并的卷目录</li>
        <li>合并后的文件会保存在该卷目录下，文件名包含合并时间戳</li>
        <li>支持过滤空章节、按章节编号排序</li>
        </ul>
        
        <hr>
        
        <h3>四、监控管理 <span class="tag">Monitor</span></h3>
        <p>实时监控小说目录的变化，包括新增章节、文件修改等，并记录详细日志。监控是整个自动流程的核心引擎。</p>
        <ul>
        <li><b>启动监控</b>：开始监视选定目录</li>
        <li><b>停止监控</b>：暂停监视</li>
        <li><b>检查间隔</b>：每多少秒检测一次变化（可在参数配置中调整）</li>
        <li><b>心跳超时</b>：超过指定时间无响应则判定监控异常</li>
        <li><b>日志区</b>：按时间倒序显示所有监控事件，<span style='color:#00FF41'>成功信息为绿色</span>，<span style='color:#FFAA00'>警告为黄色</span>，<span style='color:#FF3333'>错误为红色</span></li>
        </ul>
        
        <h4>自动增章机制</h4>
        <ul>
        <li>每检测周期检查所有卷的最新章节</li>
        <li>如果最新章节内容<strong>超过配置的最少字数</strong>（默认20个中文字符），且不是默认模板内容：</li>
        <ul>
        <li>自动在该卷末尾新增配置数量（默认2章）的空章节供继续写作</li>
        <li>每到2的倍数章节触发Summary日志记录</li>
        </ul>
        </ul>
        
        <h4>自动增卷与旧卷处理</h4>
        <ul>
        <li>当用户手动创建新卷文件夹（纯数字文件夹，如 <code>2</code>、<code>3</code>）后，监控自动检测并执行完整流程：</li>
        <ol>
        <li><b>清理旧卷</b>：扫描上一卷，删除所有无内容的空章节</li>
        <li><b>承接章节</b>：找到上一卷最后一个有内容的章节号，在新卷中从该号+1开始创建规定数量的空章节</li>
        <li><b>统计字数</b>：计算旧卷总字数</li>
        <li><b>标记旧卷</b>：上一卷重命名为 <code>1[old_98765]</code></li>
        <li><b>标记新卷</b>：新卷重命名为 <code>2[new_12345]</code></li>
        <li><b>自动Summary</b>：自动运行一次Summary合并（模式2：统计并重命名），生成卷合并文件</li>
        </ol>
        <li>之后监控继续跟踪新卷，重复自动增章流程</li>
        </ul>
        
        <hr>
        
        <h3>五、参数配置 <span class="tag">Config</span></h3>
        <p>集中管理程序的各项参数。</p>
        <ul>
        <li><b>UI尺寸</b>：基础字号、标题字号、日志字号、网络图字号、关键词字号、关键词标题字号、人物卡字号、人物卡标题字号</li>
        <li><b>窗口尺寸</b>：初始宽度/高度</li>
        <li><b>色彩方案</b>：背景色、前景色、边框色、错误色、警告色等</li>
        <li><b>监控配置</b>：检查间隔、预读取章节数、最单词数、小说目录路径、心跳超时</li>
        <li><b>图谱配置</b>：布局理想长度、节点上限、自动保存布局</li>
        <li><b>词频配置</b>：最小词长、最小出现次数、非活跃章节数、自动扫描</li>
        <li><b>主题</b>：图谱背景色、网格色、连线宽度</li>
        <li>修改后点击「保存并应用」生效；点击「恢复默认」还原为Matrix风格配色</li>
        </ul>
        
        <hr>
        
        <h3>六、关键词管理 <span class="tag">Keywords</span></h3>
        <p>结构化地管理小说中的核心元素：人物、技能、物品、地点、伏笔、势力关系等。</p>
        
        <h4>6.1 关键词列表视图</h4>
        <ul>
        <li>以列表形式展示所有关键词，显示名称、类型和简介</li>
        <li>不同类型以不同颜色高亮：<span style='color:#00ff88'>人物</span>、<span style='color:#ff4466'>技能</span>、<span style='color:#00ccff'>地点</span>、<span style='color:#ffcc00'>物品</span>、<span style='color:#ff8c42'>伏笔</span>、<span style='color:#cc66ff'>关系</span> 等</li>
        <li>格式：<code>[名称][类型] - 简介</code></li>
        <li>支持自定义字号、颜色、字体（在参数配置中调整）</li>
        </ul>
        
        <h4>6.2 人物卡视图 <span class="tag">Card</span></h4>
        <ul>
        <li>点击人物列表中的姓名，进入该人物的专属详情页（人物卡）</li>
        <li>人物卡展示：人物描述、关联技能、关联物品、关联地点、关联关系、关联伏笔</li>
        <li>支持双向关联：在人物卡中点击关联项可跳转到对应的人物卡</li>
        <li>底部显示"被以下人物提及"的反向引用列表</li>
        </ul>
        
        <h4>6.3 神经网络视图 <span class="tag">Graph</span></h4>
        <ul>
        <li>以力导向图方式展示所有关键词之间的关系网络</li>
        <li><b>节点类型</b>：不同颜色圆角矩形代表不同类型的关键词</li>
        <li><b>关系线</b>：
            <span style='color:#00ff88'>━━ 实线</span> 表示密切关系（友谊/恋情/敌对），
            <span style='color:#00ff88'>- - 虚线</span> 表示间接关系（掌握/传授/背负），
            <span style='color:#00ff88'>· · 点线</span> 表示暗示/推测关系，
            <span style='color:#00ff88'>-· -· 点划线</span> 表示空间关系（位于/连接/包含）</li>
        <li><b>交互操作</b>：
            <ul>
            <li>滚轮缩放图谱</li>
            <li>拖拽空白区域平移视图</li>
            <li>点击节点高亮该节点及其关联线</li>
            <li>双击节点跳转到对应的人物卡</li>
            <li>右键节点可查看详细菜单</li>
            </ul>
        </li>
        <li><b>节点导航</b>：右上角面板可通过复选框筛选显示/隐藏特定类型的节点</li>
        <li><b>图例</b>：左上角显示节点类型和关系线类型的颜色对照表</li>
        <li><b>布局控制</b>：支持保存/重置布局、导出为PNG、隔离显示选中节点</li>
        </ul>
        
        <h4>6.4 词频统计视图 <span class="tag">Frequency</span></h4>
        <ul>
        <li>自动统计关键词在章节文本中出现的频率</li>
        <li>支持设置最小词长、最小出现次数以过滤低价值数据</li>
        <li>可设定非活跃章节数，自动标记长期未出现的关键词</li>
        <li>词频数据用于辅助分析角色出场率、主题词热度变化等</li>
        </ul>
        
        <hr>
        
        <h3>七、快捷键与操作提示</h3>
        <ul>
        <li><b>保存并退出</b>：任意页面底部红色按钮，安全终止所有进程后关闭程序</li>
        <li><b>标签页切换</b>：点击顶部标签栏可在各功能模块间切换</li>
        <li>图谱区域支持鼠标右键菜单查看更多操作</li>
        </ul>
        
        <hr>
        
        <h3>八、数据文件说明</h3>
        <ul>
        <li><b>配置文件</b>：<code>NovelHelper.ini</code> — 存储所有UI配置、监控参数、图谱布局设置</li>
        <li><b>关键词文件</b>：<code>keywords.json</code> — 存储关键词及其关系和属性数据</li>
        <li><b>图谱布局文件</b>：<code>graph_layout.json</code> — 存储节点的手动布局位置</li>
        <li>建议定期备份上述文件以防数据丢失</li>
        </ul>
        
        <hr>
        <p style='text-align:center; color:#556655; font-size:0.85em;'>
        {language_manager.tr('app_title')} — 祝您写作顺利 🚀
        </p>
        """)
        layout.addWidget(help_text)
        
        self.tabs.addTab(tab, language_manager.tr("user_guide"))
    
    def keyword_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        title = QLabel(language_manager.tr("keyword_tab_title"))
        title.setStyleSheet(f"font-size: {self.base_title_size}px; font-weight: bold;")
        layout.addWidget(title)
        
        toolbar = QHBoxLayout()
        
        self.keyword_view_combo = QComboBox()
        self.keyword_view_combo.addItem("列表视图", "list")
        self.keyword_view_combo.addItem("人物卡", "card")
        self.keyword_view_combo.addItem("神经网络图", "neural")
        self.keyword_view_combo.addItem("频度仪表盘", "frequency")
        self.keyword_view_combo.currentIndexChanged.connect(self.refresh_keywords)
        toolbar.addWidget(self.keyword_view_combo)
        
        refresh_btn = QPushButton(language_manager.tr("refresh_btn"))
        refresh_btn.clicked.connect(self.refresh_keywords)
        toolbar.addWidget(refresh_btn)
        
        self._layout_save_btn = QPushButton("保存布局")
        self._layout_save_btn.clicked.connect(self._save_graph_layout)
        self._layout_save_btn.setVisible(False)
        toolbar.addWidget(self._layout_save_btn)
        
        self._layout_reset_btn = QPushButton("重置布局")
        self._layout_reset_btn.clicked.connect(self._reset_graph_layout)
        self._layout_reset_btn.setVisible(False)
        toolbar.addWidget(self._layout_reset_btn)
        
        self._isolated_btn = QPushButton("孤立检测")
        self._isolated_btn.clicked.connect(self._detect_isolated_nodes)
        self._isolated_btn.setVisible(False)
        toolbar.addWidget(self._isolated_btn)
        
        self._export_png_btn = QPushButton("导出PNG")
        self._export_png_btn.clicked.connect(self._export_graph_png)
        self._export_png_btn.setVisible(False)
        toolbar.addWidget(self._export_png_btn)
        
        layout.addLayout(toolbar)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("搜索节点... (Enter 定位)")
        self.search_bar.returnPressed.connect(self._on_graph_search)
        self.search_bar.setVisible(False)
        layout.addWidget(self.search_bar)
        
        self._filter_panel = QWidget()
        self._filter_panel.setVisible(False)
        filter_layout = QHBoxLayout(self._filter_panel)
        filter_layout.setContentsMargins(0, 2, 0, 2)
        self._filter_checkboxes = {}
        node_types = [
            ('character', '人物'), ('skill', '技能'), ('location', '地点'),
            ('item', '物品'), ('foreshadowing', '伏笔'), ('adventure', '事件'),
            ('faction', '组织'), ('time_point', '时间点'), ('relationship', '关系'),
        ]
        for key, label in node_types:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.stateChanged.connect(lambda s, k=key: self._on_filter_changed(k, s))
            filter_layout.addWidget(cb)
            self._filter_checkboxes[key] = cb
        layout.addWidget(self._filter_panel)
        
        self.keyword_list_text = QTextBrowser()
        self.keyword_list_text.setOpenLinks(False)
        self.keyword_list_text.anchorClicked.connect(self._on_keyword_clicked)
        self._sync_keyword_browser_font()
        layout.addWidget(self.keyword_list_text)
        
        self.network_graph_view = NetworkGraphView()
        self.network_graph_view.setVisible(False)
        layout.addWidget(self.network_graph_view)
        
        self.tabs.addTab(tab, language_manager.tr("keyword_manager"))
        
        self.refresh_keywords()
    
    def refresh_keywords(self):
        view_mode = self.keyword_view_combo.currentData()
        
        if view_mode == "list":
            self.render_list_view()
        elif view_mode == "card":
            self.render_card_view()
        elif view_mode == "neural":
            self.render_neural_view()
        elif view_mode == "frequency":
            self.render_frequency_view()
    
    def render_list_view(self):
        self.keyword_list_text.setVisible(True)
        self.network_graph_view.setVisible(False)
        self.search_bar.setVisible(False)
        self._filter_panel.setVisible(False)
        self._layout_save_btn.setVisible(False)
        self._layout_reset_btn.setVisible(False)
        self._isolated_btn.setVisible(False)
        self._export_png_btn.setVisible(False)
        
        kw_font = QFont(self.kwlist_font_family, self.kwlist_font_size)
        self.keyword_list_text.document().setDefaultFont(kw_font)
        
        keywords = keyword_manager.load_keywords()
        if not keywords:
            self.keyword_list_text.setHtml(f"<p style='color:{self.kwlist_font_color};font-size:{self.kwlist_font_size}px;font-family:{self.kwlist_font_family};'>暂无关键词，请创建配置文件</p>")
            return
        
        fs = self.kwlist_font_size
        fc = self.kwlist_font_color
        ff = self.kwlist_font_family
        fs_title = self.kwlist_title_size
        
        type_colors = {'character':'#00ff88','skill':'#ff4466','location':'#00ccff','item':'#ffcc00',
                       'foreshadowing':'#ff8c42','adventure':'#ff66cc','faction':'#88ccff',
                       'time_point':'#ffd700','relationship':'#cc66ff','custom':'#88aacc'}
        
        html = f"<h3 style='color:{fc};font-size:{fs_title}px;font-family:{ff};'>关键词列表</h3><ul style='list-style:none;padding-left:0;'>"
        for kw in keywords:
            name = kw.get('name', '?')
            kw_type = kw.get('type', 'custom')
            desc = kw.get('description', '')
            tc = type_colors.get(kw_type, '#88aacc')
            html += f"<li style='padding:1px 0;border-bottom:1px solid #0a1a0a;'>"
            html += f"<span style='color:{fc};font-size:{fs}px;font-family:{ff};font-weight:bold;'>{name}</span> "
            html += f"<span style='color:{tc};font-size:{fs}px;font-family:{ff};'>[{kw_type}]</span>"
            if desc:
                html += f"<span style='color:{fc}aa;font-size:{fs}px;font-family:{ff};'> - {desc}</span>"
            html += "</li>"
        html += "</ul>"
        
        self.keyword_list_text.setHtml(html)
    
    def _sync_keyword_browser_font(self):
        if self.keyword_view_combo.currentData() == "card":
            font = QFont(self.kwlist_font_family, self.card_font_size)
        else:
            font = QFont(self.kwlist_font_family, self.kwlist_font_size)
        self.keyword_list_text.document().setDefaultFont(font)
        scale = self.kwlist_font_size / 16.0
        if hasattr(self, 'network_graph_view'):
            self.network_graph_view.update_navigator_font(scale)
            self.network_graph_view.set_graph_font_size(self.graph_font_size)
    
    def render_card_view(self):
        self.keyword_list_text.setVisible(True)
        self.network_graph_view.setVisible(False)
        self.search_bar.setVisible(False)
        self._filter_panel.setVisible(False)
        self._layout_save_btn.setVisible(False)
        self._layout_reset_btn.setVisible(False)
        self._isolated_btn.setVisible(False)
        self._export_png_btn.setVisible(False)
        self._card_selected_name = None
        card_font = QFont(self.kwlist_font_family, self.card_font_size)
        self.keyword_list_text.document().setDefaultFont(card_font)
        self._render_character_list()
    
    def _render_character_list(self):
        keywords = keyword_manager.load_keywords()
        if not keywords:
            self.keyword_list_text.setHtml("<p>暂无关键词</p>")
            return
        
        characters = [kw for kw in keywords if kw.get('type') == 'character']
        if not characters:
            self.keyword_list_text.setHtml("<p>暂无人物关键词</p>")
            return
        
        fs = self.card_font_size
        fs_title = self.card_title_size
        fs_small = int(fs * 0.8)
        
        html = f"""
        <h3 style='font-size: {fs_title}px;'>人物列表</h3>
        <p style='color: #6688aa; font-size: {fs_small}px;'>点击人名查看详细人物卡</p>
        <hr style='border-color: #1a4a5a;'>
        <table style='width: 100%; border-collapse: collapse; font-size: {fs}px;'>
        """
        for char in characters:
            name = char.get('name', '?')
            desc = char.get('description', '')
            short_desc = desc[:60] + '...' if len(desc) > 60 else desc
            html += f"""
            <tr style='border-bottom: 1px solid #1a3a4a;'>
                <td style='padding: 0.2em 0.4em; width: 30%;'>
                    <a href="card:{name}" style='color: #00ff88; font-size: {fs}px; font-weight: bold; text-decoration: none;'>{name}</a>
                </td>
                <td style='padding: 0.2em 0.4em; color: #88aacc; font-size: {fs_small}px;'>{short_desc}</td>
            </tr>"""
        html += "</table>"
        self.keyword_list_text.setHtml(html)
    
    def _render_character_card(self, char_name):
        keywords = keyword_manager.load_keywords()
        if not keywords:
            self.keyword_list_text.setHtml("<p>暂无关键词</p>")
            return
        
        char_kw = None
        for kw in keywords:
            if kw.get('type') == 'character' and kw.get('name') == char_name:
                char_kw = kw
                break
        
        if not char_kw:
            self._render_character_list()
            return
        
        name = char_kw.get('name', '?')
        desc = char_kw.get('description', '')
        related_names = [rel.get('target') for rel in char_kw.get('relationships', [])]
        
        related_skills = []
        related_items = []
        related_locations = []
        related_relations = []
        related_foreshadowing = []
        related_characters = []
        
        for r_name in related_names:
            for kw in keywords:
                if kw.get('name') == r_name:
                    t = kw.get('type', 'custom')
                    entry = (r_name, kw.get('description', ''))
                    if t == 'skill':
                        related_skills.append(entry)
                    elif t == 'item':
                        related_items.append(entry)
                    elif t == 'location':
                        related_locations.append(entry)
                    elif t == 'relationship':
                        related_relations.append(entry)
                    elif t == 'foreshadowing':
                        related_foreshadowing.append(entry)
                    else:
                        related_characters.append(entry)
                    break
        
        referenced_by = []
        for kw in keywords:
            if kw.get('name') == char_name:
                continue
            if kw.get('type') == 'character' and any(rel.get('target') == name for rel in kw.get('relationships', [])):
                referenced_by.append(kw.get('name', '?'))
        
        html = f"""
        <div style='margin-bottom: 0.5em;'>
            <a href="back:list" style='color: #00ff88; font-size: {int(self.card_font_size*0.85)}px; text-decoration: none;'>&lt; 返回人物列表</a>
        </div>
        
        <div style='border: 2px solid #00ff88; padding: 1.2em; border-radius: 12px; background: rgba(0,255,136,0.03);'>
            <h2 style='color: #00ff88; margin: 0 0 0.3em 0; font-size: {int(self.card_font_size*1.3)}px;'>{name}</h2>
            <hr style='border-color: #1a4a5a; margin: 0.6em 0;'>
            <p style='color: #88aacc; line-height: 1.6; font-size: {self.card_font_size}px;'>{desc}</p>
        </div>
        """
        
        fs = self.card_font_size
        fs_small = int(fs * 0.85)
        fs_desc = int(fs * 0.75)
        
        sections = [
            ('技 能', related_skills, '#ffe66d'),
            ('物 品', related_items, '#dda0dd'),
            ('地 点', related_locations, '#00ccff'),
            ('关 系', related_relations, '#cc66ff'),
            ('伏 笔', related_foreshadowing, '#ff8c42'),
            ('关联人物', related_characters, '#00ff88'),
        ]
        
        for section_title, items, color in sections:
            if items:
                html += f"""
                <div style='border: 1px solid {color}40; padding: 0.7em 1em; margin-top: 0.7em; border-radius: 8px; background: rgba(0,0,0,0.2);'>
                    <h4 style='color: {color}; margin: 0 0 0.5em 0; font-size: {fs}px;'>- {section_title}</h4>
                """
                for item_name, item_desc in items:
                    html += f"""
                    <div style='padding: 0.25em 0; border-bottom: 1px solid #1a3a4a30;'>
                        <a href="card:{item_name}" style='color: {color}; font-size: {fs_small}px; text-decoration: none;'><b>{item_name}</b></a>
                        <span style='color: #6688aa; font-size: {fs_desc}px; margin-left: 0.5em;'>{item_desc}</span>
                    </div>"""
                html += "</div>"
        
        if referenced_by:
            html += f"""
            <div style='border: 1px solid #00ff8840; padding: 0.7em 1em; margin-top: 0.7em; border-radius: 8px; background: rgba(0,0,0,0.2);'>
                <h4 style='color: #00ff88; margin: 0 0 0.5em 0; font-size: {fs}px;'>- 被以下人物提及</h4>
            """
            for ref_name in referenced_by:
                html += f"""
                <div style='padding: 0.15em 0;'>
                    <a href="card:{ref_name}" style='color: #00ff88; font-size: {fs_small}px; text-decoration: none;'>&gt; {ref_name}</a>
                </div>"""
            html += "</div>"
        
        self.keyword_list_text.setHtml(html)
    
    def _render_location_card(self, location_name):
        keywords = keyword_manager.load_keywords()
        loc_kw = None
        for kw in keywords:
            if kw.get('type') == 'location' and kw.get('name') == location_name:
                loc_kw = kw
                break
        if not loc_kw:
            self._render_character_list()
            return
        
        name = loc_kw.get('name', '?')
        desc = loc_kw.get('description', '')
        region = loc_kw.get('region', '')
        related = [rel.get('target') for rel in loc_kw.get('relationships', []) if isinstance(rel, dict)]
        
        # 分类关联：人物、事件、其他地点
        related_chars = []
        related_events = []
        related_others = []
        for kw in keywords:
            r_name = kw.get('name', '')
            if r_name in related:
                t = kw.get('type', '')
                if t == 'character':
                    related_chars.append(r_name)
                elif t == 'adventure':
                    related_events.append(r_name)
                elif t == 'location':
                    related_others.append(r_name)
        
        html = f"""
        <div style='margin-bottom: 0.5em;'>
            <a href="back:list" style='color: #00ff88; font-size: 0.85em; text-decoration: none;'>&lt; 返回人物列表</a>
        </div>
        <div style='border: 2px solid #00ccff; padding: 1.2em; border-radius: 12px; background: rgba(0,204,255,0.03);'>
            <h2 style='color: #00ccff; margin: 0 0 0.3em 0;'>{name}</h2>
            <hr style='border-color: #1a4a5a; margin: 0.6em 0;'>
            <p style='color: #88aacc; line-height: 1.6;'>{desc}</p>
        </div>
        """
        if region:
            html += f"<p style='color: #6688aa;'><b>所属区域:</b> {region}</p>"
        # 关联人物
        if related_chars:
            html += "<div style='border:1px solid #00ff8840; padding:0.7em 1em; margin-top:0.7em; border-radius:8px;'><h4 style='color:#00ff88;'>- 关联人物</h4>"
            for c in related_chars:
                html += f"<div style='padding:0.15em 0;'><a href='card:{c}' style='color:#00ff88; font-size:0.95em;'>&gt; {c}</a></div>"
            html += "</div>"
        if related_events:
            html += "<div style='border:1px solid #ff8c4240; padding:0.7em 1em; margin-top:0.7em; border-radius:8px;'><h4 style='color:#ff8c42;'>- 关联事件</h4>"
            for e in related_events:
                html += f"<div style='padding:0.15em 0;'><span style='color:#ff8c42;'>&gt; {e}</span></div>"
            html += "</div>"
        
        self.keyword_list_text.setHtml(html)
    
    def _render_timeline_point_card(self, point_name):
        keywords = keyword_manager.load_keywords()
        tp_kw = None
        for kw in keywords:
            if kw.get('type') == 'time_point' and kw.get('name') == point_name:
                tp_kw = kw
                break
        if not tp_kw:
            self._render_character_list()
            return
        
        name = tp_kw.get('name', '?')
        kw_type = tp_kw.get('type', 'time_point')
        desc = tp_kw.get('description', '')
        status = tp_kw.get('status', '')
        related = [rel.get('target') for rel in tp_kw.get('relationships', []) if isinstance(rel, dict)]
        
        related_chars = []
        related_events = []
        related_foreshadowing = []
        for kw in keywords:
            r_name = kw.get('name', '')
            if r_name in related:
                t = kw.get('type', '')
                if t == 'character':
                    related_chars.append(r_name)
                elif t == 'adventure':
                    related_events.append(r_name)
                elif t == 'foreshadowing':
                    related_foreshadowing.append(r_name)
        
        html = f"""
        <div style='margin-bottom: 0.5em;'>
            <a href="back:list" style='color: #00ff88; font-size: 0.85em; text-decoration: none;'>&lt; 返回人物列表</a>
        </div>
        <div style='border: 2px solid #ffd700; padding: 1.2em; border-radius: 12px; background: rgba(255,215,0,0.03);'>
            <h2 style='color: #ffd700; margin: 0 0 0.3em 0;'>{name}</h2>
            <hr style='border-color: #5a4a1a; margin: 0.6em 0;'>
            <p style='color: #ccaa88; line-height: 1.6;'>{desc}</p>
        </div>
        """
        if status:
            html += f"<p style='color: #aa8866;'><b>进度状态:</b> {status}</p>"
        if related_chars:
            html += "<div style='border:1px solid #00ff8840; padding:0.7em 1em; margin-top:0.7em; border-radius:8px;'><h4 style='color:#00ff88;'>- 关联人物</h4>"
            for c in related_chars:
                html += f"<div style='padding:0.15em 0;'><a href='card:{c}' style='color:#00ff88; font-size:0.95em;'>&gt; {c}</a></div>"
            html += "</div>"
        if related_events:
            html += "<div style='border:1px solid #ff8c4240; padding:0.7em 1em; margin-top:0.7em; border-radius:8px;'><h4 style='color:#ff8c42;'>- 关联事件</h4>"
            for e in related_events:
                html += f"<div style='padding:0.15em 0;'><span style='color:#ff8c42;'>&gt; {e}</span></div>"
            html += "</div>"
        if related_foreshadowing:
            html += "<div style='border:1px solid #ff6b6b40; padding:0.7em 1em; margin-top:0.7em; border-radius:8px;'><h4 style='color:#ff6b6b;'>- 关联伏笔</h4>"
            for f in related_foreshadowing:
                html += f"<div style='padding:0.15em 0;'><span style='color:#ff6b6b;'>&gt; {f}</span></div>"
            html += "</div>"
        
        self.keyword_list_text.setHtml(html)
    
    def _render_item_card(self, item_name):
        keywords = keyword_manager.load_keywords()
        it_kw = None
        for kw in keywords:
            if kw.get('type') in ('item', 'weapon') and kw.get('name') == item_name:
                it_kw = kw; break
        if not it_kw:
            self._render_character_list(); return
        name = it_kw.get('name', '?')
        kw_type = it_kw.get('type', 'item')
        desc = it_kw.get('description', '')
        owner = it_kw.get('owner', '')
        grade = it_kw.get('grade', '')
        related = [rel.get('target') for rel in it_kw.get('relationships', []) if isinstance(rel, dict)]
        related_chars = []; related_items = []
        for kw in keywords:
            r_name = kw.get('name', '')
            if r_name in related:
                t = kw.get('type', '')
                if t == 'character': related_chars.append(r_name)
                elif t in ('item', 'weapon'): related_items.append(r_name)
        type_label = "武 器" if kw_type == 'weapon' else "物 品"
        border_color = "#ff4466" if kw_type == 'weapon' else "#ffcc00"
        html = f"""
        <div style='margin-bottom:0.5em;'><a href="back:list" style='color:#00ff88;font-size:0.85em;text-decoration:none;'>&lt; 返回列表</a></div>
        <div style='border:2px solid {border_color}; padding:1.2em; border-radius:12px; background: rgba({border_color[1:3]},{border_color[3:5]},{border_color[5:7]},0.03);'>
            <h2 style='color:{border_color}; margin:0 0 0.3em 0;'>[{type_label}] {name}</h2>
            <hr style='border-color:#1a4a5a; margin:0.6em 0;'>
            <p style='color:#88aacc; line-height:1.6;'>{desc}</p>
        </div>"""
        if owner: html += f"<p style='color:#88aacc;'><b>持有者:</b> {owner}</p>"
        if grade: html += f"<p style='color:#ffcc00;'><b>等级/品阶:</b> {grade}</p>"
        if related_chars:
            html += "<div style='border:1px solid #00ff8840;padding:0.7em 1em;margin-top:0.7em;border-radius:8px;'><h4 style='color:#00ff88;'>- 关联人物</h4>"
            for c in related_chars:
                html += f"<div style='padding:0.15em 0;'><a href='card:{c}' style='color:#00ff88;font-size:0.95em;'>&gt; {c}</a></div>"
            html += "</div>"
        if related_items:
            html += "<div style='border:1px solid #ffcc0040;padding:0.7em 1em;margin-top:0.7em;border-radius:8px;'><h4 style='color:#ffcc00;'>- 关联物品</h4>"
            for i in related_items:
                html += f"<div style='padding:0.15em 0;'><a href='card:{i}' style='color:#ffcc00;font-size:0.95em;'>&gt; {i}</a></div>"
            html += "</div>"
        self.keyword_list_text.setHtml(html)
    
    def _render_skill_card(self, skill_name):
        keywords = keyword_manager.load_keywords()
        sk_kw = None
        for kw in keywords:
            if kw.get('type') in ('skill', 'technique') and kw.get('name') == skill_name:
                sk_kw = kw; break
        if not sk_kw:
            self._render_character_list(); return
        name = sk_kw.get('name', '?')
        kw_type = sk_kw.get('type', 'skill')
        desc = sk_kw.get('description', '')
        grade = sk_kw.get('grade', '')
        element = sk_kw.get('element', '')
        related = [rel.get('target') for rel in sk_kw.get('relationships', []) if isinstance(rel, dict)]
        related_chars = []
        for kw in keywords:
            r_name = kw.get('name', '')
            if r_name in related and kw.get('type') == 'character':
                related_chars.append(r_name)
        type_label = "功 法" if kw_type == 'technique' else "技 能"
        border_color = "#ff66cc" if kw_type == 'technique' else "#ffd700"
        html = f"""
        <div style='margin-bottom:0.5em;'><a href="back:list" style='color:#00ff88;font-size:0.85em;text-decoration:none;'>&lt; 返回列表</a></div>
        <div style='border:2px solid {border_color}; padding:1.2em; border-radius:12px; background:rgba(255,102,204,0.03);'>
            <h2 style='color:{border_color}; margin:0 0 0.3em 0;'>[{type_label}] {name}</h2>
            <hr style='border-color:#1a4a5a; margin:0.6em 0;'>
            <p style='color:#88aacc; line-height:1.6;'>{desc}</p>
        </div>"""
        if grade: html += f"<p style='color:#ffcc00;'><b>等级/品阶:</b> {grade}</p>"
        if element: html += f"<p style='color:#66ccff;'><b>属性:</b> {element}</p>"
        if related_chars:
            html += "<div style='border:1px solid #00ff8840;padding:0.7em 1em;margin-top:0.7em;border-radius:8px;'><h4 style='color:#00ff88;'>- 修炼/使用者</h4>"
            for c in related_chars:
                html += f"<div style='padding:0.15em 0;'><a href='card:{c}' style='color:#00ff88;font-size:0.95em;'>&gt; {c}</a></div>"
            html += "</div>"
        self.keyword_list_text.setHtml(html)
    
    def render_frequency_view(self):
        self.keyword_list_text.setVisible(True)
        self.network_graph_view.setVisible(False)
        self.search_bar.setVisible(False)
        self._filter_panel.setVisible(False)
        self._layout_save_btn.setVisible(False)
        self._layout_reset_btn.setVisible(False)
        self._isolated_btn.setVisible(True)
        self._export_png_btn.setVisible(False)
        novel_dir = get_novel_dir()
        if not os.path.exists(novel_dir):
            self.keyword_list_text.setHtml("<p style='color:#FFAA00;'>请先设置小说目录</p>"); return
        html = "<h2 style='color:#00ff41;'>频度仪表盘</h2>"
        html += "<p style='color:#88aacc;'>手动触发扫描所有章节文件，统计词频和分布</p>"
        html += f"<p><a href='freq:scan' style='color:#00ff88;'>[▶ 开始全量扫描]</a></p>"
        html += "<hr style='border-color:#1a4a5a;'>"
        freq_file = os.path.join(novel_dir, ".frequency.json")
        if os.path.exists(freq_file):
            try:
                with open(freq_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                html += f"<p style='color:#00ff41;'>上次扫描: {data.get('scan_time','?')} | 章节数: {data.get('total_chapters',0)} | 词条数: {len(data.get('words',{}))}</p>"
                html += "<table style='width:100%;border-collapse:collapse;color:#88aacc;'>"
                html += "<tr style='color:#00ff41;'><th>词条</th><th>类型</th><th>出现章数</th><th>总次数</th><th>状态</th></tr>"
                words = data.get('words', {})
                sorted_words = sorted(words.items(), key=lambda x: x[1].get('total_occurrences',0), reverse=True)[:50]
                for word, info in sorted_words:
                    wtype = info.get('type', '?')
                    ch_count = len(info.get('chapters', {}))
                    total = info.get('total_occurrences', 0)
                    status = info.get('status', '?')
                    sc = {'active':'#00ff41','inactive':'#FFAA00','closed':'#666666'}.get(status, '#88aacc')
                    html += f"<tr><td style='color:#{sc[1:]}'>{word}</td><td>{wtype}</td><td>{ch_count}</td><td>{total}</td><td style='color:{sc}'>{status}</td></tr>"
                html += "</table>"
            except:
                html += "<p style='color:#FF3333;'>频度文件损坏，请重新扫描</p>"
        else:
            html += "<p style='color:#666;'>暂无频度数据，请先扫描</p>"
        self.keyword_list_text.setHtml(html)
    
    def render_neural_view(self):
        self.keyword_list_text.setVisible(False)
        self.network_graph_view.setVisible(True)
        self.search_bar.setVisible(False)
        self._filter_panel.setVisible(True)
        self._layout_save_btn.setVisible(True)
        self._layout_reset_btn.setVisible(True)
        self._isolated_btn.setVisible(True)
        self._export_png_btn.setVisible(True)
        keywords = keyword_manager.load_keywords()
        self.network_graph_view.set_double_click_callback(self._on_graph_node_double_clicked)
        self.network_graph_view.set_right_click_callback(self._on_graph_node_right_click)
        self.network_graph_view.build_graph(keywords)
        self.network_graph_view.load_layout(self._get_graph_layout_path())
        logger.info("神经网络图已构建")
    
    def _get_graph_layout_path(self):
        return os.path.join(get_base_dir(), "graph_layout.json")
    
    def _save_graph_layout(self):
        path = self._get_graph_layout_path()
        if self.network_graph_view.save_layout(path):
            self.log_info.append("[OK] 布局已保存")
    
    def _reset_graph_layout(self):
        path = self._get_graph_layout_path()
        if os.path.exists(path):
            os.remove(path)
        keywords = keyword_manager.load_keywords()
        self.network_graph_view.build_graph(keywords)
        self.log_info.append("[OK] 布局已重置，重新计算力导向位置")
    
    def _detect_isolated_nodes(self):
        isolated = self.network_graph_view.get_isolated_nodes()
        if not isolated:
            self.log_info.append("[OK] 没有孤立节点，所有节点都有连线")
            return
        all_kw = keyword_manager.load_keywords()
        kw_map = {k.get('name', ''): k for k in all_kw} if all_kw else {}
        self.log_info.append(f"[WARN] 发现 {len(isolated)} 个孤立节点:")
        for name in isolated:
            kw = kw_map.get(name, {})
            desc = kw.get('description', '') if kw else ''
            self.log_info.append(f"  - {name}: {desc}")
    
    def _export_graph_png(self):
        default_name = os.path.join(get_novel_dir(), "graph_export.png")
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出神经网络图为PNG", default_name, "PNG (*.png)")
        if filepath:
            if self.network_graph_view.export_to_png(filepath):
                self.log_info.append(f"[OK] 已导出: {filepath}")
            else:
                self.log_info.append("[ERR] 导出失败")
    
    def _on_filter_changed(self, node_type, state):
        visible = state == Qt.Checked
        self.network_graph_view.toggle_node_filter(node_type, visible)
        self.network_graph_view.apply_filter()
    
    def _on_graph_search(self):
        text = self.search_bar.text().strip()
        if not text:
            self.network_graph_view.clear_path_highlight()
            return
        if "->" in text:
            parts = [p.strip() for p in text.split("->")]
            if len(parts) == 2:
                a, b = parts
                path = self.network_graph_view.find_shortest_path(a, b)
                if path:
                    self.network_graph_view.highlight_path(path)
                    self.log_info.append(f"[OK] 路径: {' → '.join(path)}")
                else:
                    self.log_info.append(f"[WARN] 未找到 {a} 到 {b} 的路径")
            return
        self.network_graph_view.focus_on_node(text)
    
    def _on_graph_node_right_click(self, node_name, screen_pos, scene_pos):
        menu = QMenu()
        view_card = menu.addAction(f"查看人物卡: {node_name}")
        pin_node = menu.addAction("钉选/取消钉选")
        menu.addSeparator()
        locate = menu.addAction("跳转到最近出现章节")
        menu.addSeparator()
        hide = menu.addAction("临时隐藏")
        
        action = menu.exec_(screen_pos)
        if action == view_card:
            for i in range(self.keyword_view_combo.count()):
                if self.keyword_view_combo.itemData(i) == "card":
                    self.keyword_view_combo.setCurrentIndex(i)
                    break
            self.refresh_keywords()
            QTimer.singleShot(300, lambda: self._render_character_card(node_name))
        elif action == pin_node:
            self.network_graph_view.toggle_pin_node(node_name)
        elif action == locate:
            self.log_info.append(f"[INFO] 定位功能 - {node_name} (待实现)")
        elif action == hide:
            if node_name in self.network_graph_view.node_items:
                self.network_graph_view.node_items[node_name]['item'].setVisible(False)
    
    def _on_graph_node_double_clicked(self, node_name):
        keywords = keyword_manager.load_keywords()
        node_type = None
        for kw in keywords:
            if kw.get('name') == node_name:
                node_type = kw.get('type')
                break

        for i in range(self.keyword_view_combo.count()):
            if self.keyword_view_combo.itemData(i) == "card":
                self.keyword_view_combo.setCurrentIndex(i)
                break
        self.refresh_keywords()

        if node_type == 'location':
            QTimer.singleShot(300, lambda: self._render_location_card(node_name))
        elif node_type == 'time_point':
            QTimer.singleShot(300, lambda: self._render_timeline_point_card(node_name))
        elif node_type in ('item', 'weapon'):
            QTimer.singleShot(300, lambda: self._render_item_card(node_name))
        elif node_type in ('skill', 'technique'):
            QTimer.singleShot(300, lambda: self._render_skill_card(node_name))
        elif node_type == 'character':
            QTimer.singleShot(300, lambda: self._render_character_card(node_name))
        else:
            QTimer.singleShot(300, lambda: self._render_character_card(node_name))
    
    def _on_keyword_clicked(self, url):
        url_str = url.toString()
        if url_str.startswith("card:"):
            target_name = url_str[5:]
            keywords = keyword_manager.load_keywords()
            target_type = None
            for kw in keywords:
                if kw.get('name') == target_name:
                    target_type = kw.get('type')
                    break
            if target_type == 'location':
                self._render_location_card(target_name)
            elif target_type == 'time_point':
                self._render_timeline_point_card(target_name)
            elif target_type in ('item', 'weapon'):
                self._render_item_card(target_name)
            elif target_type in ('skill', 'technique'):
                self._render_skill_card(target_name)
            else:
                self._render_character_card(target_name)
        elif url_str == "back:list":
            self._render_character_list()
        elif url_str == "freq:scan":
            self._run_frequency_scan()
        else:
            self.log_info.append(f"点击: {url_str}")
    
    def _run_frequency_scan(self):
        novel_dir = get_novel_dir()
        if not os.path.exists(novel_dir):
            self.keyword_list_text.setHtml("<p style='color:#FF3333;'>目录不存在</p>"); return
        self.keyword_list_text.setHtml("<p style='color:#00ff41;'>▶ 正在全量扫描... (这可能需要一些时间)</p>")
        QApplication.processEvents()
        freq_data = keyword_manager.scan_frequency(novel_dir, ConfigManager.get_int('Frequency','min_word_length',fallback=2), ConfigManager.get_int('Frequency','min_occurrences',fallback=3))
        freq_file = os.path.join(novel_dir, ".frequency.json")
        with open(freq_file, 'w', encoding='utf-8') as f:
            json.dump(freq_data, f, ensure_ascii=False, indent=2)
        self.render_frequency_view()
    
    def apply_adaptive(self):
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            area_scale = ConfigManager.get_float('Adaptive', 'area_scale_factor', fallback=2.0)
            base_area = 1006 * 975
            current_area = screen_geometry.width() * screen_geometry.height()
            scale_factor = (current_area / base_area) ** 0.5 / area_scale
            
            if scale_factor > 1.2:
                font_increase = ConfigManager.get_int('Adaptive', 'font_increase', fallback=4)
                new_font_size = int(self.base_font_size * scale_factor)
                self.setStyleSheet(self.styleSheet() + f"* {{ font-size: {new_font_size}px; }}")
        self._sync_keyword_browser_font()

    def load_settings(self):
        suffix = self.settings.value("create/name_suffix", "")
        if suffix and hasattr(self, 'name_suffix'):
            self.name_suffix.setText(suffix)
        mode = self.settings.value("create/summary_mode", "2")
        if mode == "1" and hasattr(self, 'mode1'):
            self.mode1.setChecked(True)
        elif mode == "2" and hasattr(self, 'mode2'):
            self.mode2.setChecked(True)

    def save_settings(self):
        if hasattr(self, 'name_suffix'):
            self.settings.setValue("create/name_suffix", self.name_suffix.text())
        if hasattr(self, 'mode1') and hasattr(self, 'mode2'):
            mode = "1" if self.mode1.isChecked() else "2"
            self.settings.setValue("create/summary_mode", mode)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adaptive_scale()

    def adaptive_scale(self):
        area_factor = ConfigManager.get_float('Adaptive', 'area_scale_factor', fallback=2.0)
        height_factor = ConfigManager.get_float('Adaptive', 'height_scale_factor', fallback=1.2)
        base_area = 1006 * 975
        current_area = self.width() * self.height()
        area_level = int((current_area / base_area) ** 0.5 / area_factor * 10)
        height_level = int(self.height() / 975 / height_factor * 10)
        if not hasattr(self, '_last_area_level'):
            self._last_area_level = -1
            self._last_height_level = -1
        if area_level != self._last_area_level or height_level != self._last_height_level:
            self._last_area_level = area_level
            self._last_height_level = height_level
            self.apply_adaptive()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
                self.show()
            else:
                self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
                self.show()
        return super().eventFilter(obj, event)

    def _save_and_exit(self):
        reply = QMessageBox.question(
            self, language_manager.tr("confirm_exit"),
            language_manager.tr("exit_confirm_msg"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        self._save_exit_btn.setText("保存中...")
        self._save_exit_btn.setEnabled(False)
        QApplication.processEvents()

        if hasattr(self, 'config_novel_dir'):
            try:
                self._write_config_to_file()
            except Exception as e:
                logger.error(f"保存配置失败: {e}")

        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
            self.log_info.append("[OK] 等待监控线程结束...")
            QApplication.processEvents()
            self.monitor_thread.wait(3000)

        QApplication.processEvents()
        self.save_settings()
        self.close()
    
    def closeEvent(self, event):
        self.save_settings()
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread.wait(3000)
        event.accept()


if __name__ == "__main__":
    language_manager.generate_ini_file()
    app = QApplication(sys.argv)
    window = NovelHelper()
    window.show()
    sys.exit(app.exec_())
