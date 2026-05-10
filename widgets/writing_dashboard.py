"""
写作数据仪表板组件
提供实时的写作进度、统计数据和可视化展示

功能：
- 总字数统计（按卷/章节）
- 日均写作速度追踪
- 写作目标进度条
- 章节完成度饼图（文本版）
- 最近活跃度热力图
- 关键词覆盖率分析
- 导出统计报告

使用示例：
    dashboard = WritingDashboard(parent=self)
    dashboard.set_novel_dir('./my_novel')
    dashboard.refresh_data()
    
    layout.addWidget(dashboard)
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QProgressBar, QFrame, QGroupBox, QTextBrowser,
    QComboBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRect
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPainterPath

from ..core.config_manager import ConfigManager
from ..core.language_manager import language_manager

logger = logging.getLogger(__name__)


class StatCard(QFrame):
    """统计卡片组件，支持悬浮高亮效果"""
    
    def __init__(self, title: str, value: str, subtitle: str = "", 
                 color: str = "#0078D4", parent=None):
        super().__init__(parent)
        
        self._color = color
        self._is_hovered = False
        self.setCursor(Qt.PointingHandCursor)
        
        from ..core.theme_manager import theme_manager
        t = theme_manager.get_current_theme()
        self._bg_color = t.get('card_bg', '#FFFFFF')
        self._border_color = t.get('card_border', '#E5E5E5')
        fg_color = t.get('fg_color', '#212529')

        self._apply_style()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {fg_color}; font-size: 13px; font-weight: bold; border: none;")
        layout.addWidget(title_label)
        
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            f"color: {color}; font-size: 28px; font-weight: bold; border: none;"
        )
        self.value_label.setMinimumHeight(34)
        layout.addWidget(self.value_label)
        
        if subtitle:
            sub_label = QLabel(subtitle)
            sub_label.setStyleSheet(f"color: {fg_color}; font-size: 12px; border: none;")
            layout.addWidget(sub_label)
        
        layout.addStretch()
    
    def _apply_style(self):
        """刷新样式"""
        if self._is_hovered:
            bg = QColor(self._bg_color).darker(102).name()
        else:
            bg = self._bg_color
        border_c = self._color if self._is_hovered else self._border_color
        border_w = "2px" if self._is_hovered else "1px"
        self.setStyleSheet(f"""
            StatCard {{
                background-color: {bg};
                border: {border_w} solid {border_c};
                border-radius: 12px;
            }}
        """)
    
    def enterEvent(self, event):
        self._is_hovered = True
        self._apply_style()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._is_hovered = False
        self._apply_style()
        super().leaveEvent(event)
    
    def update_value(self, value: str, subtitle: str = ""):
        """更新数值"""
        self.value_label.setText(value)
        if subtitle:
            if self.layout().count() > 2:
                self.layout().itemAt(2).widget().setText(subtitle)


class WritingDashboard(QWidget):
    """
    写作数据仪表板
    
    展示内容：
    - 总体统计卡片（总字数、总章节数、总卷数、日均字数）
    - 各卷进度对比
    - 写作趋势图（最近7天/30天）
    - 目标达成率
    - 关键词使用情况
    """
    
    # 信号定义
    data_refreshed = pyqtSignal(dict)  # 数据刷新时发出
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.novel_dir = None
        self._chapter_cache = None
        self._freq_cache = None
        
        # 统计数据
        self._stats_data = {}
        
        # 自动刷新定时器（每5分钟）
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self.refresh_data)
        self._refresh_timer.start(300000)  # 5分钟
        
        logger.info("[WritingDashboard] 初始化")
        self._build_ui()
    
    def _build_ui(self):
        """构建UI界面"""
        from ..core.theme_manager import theme_manager
        t = theme_manager.get_current_theme()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # ====== 核心指标卡片区 ======
        stats_grid = QGridLayout()
        stats_grid.setSpacing(15)
        
        # 创建统计卡片
        self.total_words_card = StatCard("总字数", "0", "累计写作量", t.get('accent_color', '#0078D4'))
        self.total_chapters_card = StatCard("总章节数", "0", "已创建章节", t.get('accent_color', '#0078D4'))
        self.total_volumes_card = StatCard("总卷数", "0", "已完成卷", t.get('accent_color', '#0078D4'))
        self.daily_avg_card = StatCard("日均字数", "0", "近7天平均", t.get('accent_color', '#0078D4'))
        
        stats_grid.addWidget(self.total_words_card, 0, 0)
        stats_grid.addWidget(self.total_chapters_card, 0, 1)
        stats_grid.addWidget(self.total_volumes_card, 0, 2)
        stats_grid.addWidget(self.daily_avg_card, 0, 3)
        
        main_layout.addLayout(stats_grid)

        # ====== 每日打卡进度条 ======
        checkin_layout = QHBoxLayout()
        checkin_layout.setContentsMargins(0, 0, 0, 0)

        checkin_frame = QFrame()
        checkin_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {t.get('card_bg', '#FFFFFF')};
                border: 1px solid {t.get('border_color', '#DEE2E6')};
                border-radius: {t.get('card_radius', '10px')};
            }}
        """)
        checkin_inner = QHBoxLayout(checkin_frame)
        checkin_inner.setContentsMargins(16, 10, 16, 10)
        checkin_inner.setSpacing(12)

        checkin_label = QLabel("今日打卡")
        checkin_label.setStyleSheet(
            f"color: {t.get('fg_color', '#212529')}; font-size: 14px; font-weight: bold; border: none;"
        )
        checkin_inner.addWidget(checkin_label)

        self._today_progress = QProgressBar()
        self._today_progress.setRange(0, 100)
        self._today_progress.setValue(0)
        self._today_progress.setFixedWidth(200)
        self._today_progress.setFixedHeight(18)
        self._today_progress.setTextVisible(False)
        self._today_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {t.get('border_color', '#DEE2E6')};
                border: none;
                border-radius: 9px;
            }}
            QProgressBar::chunk {{
                background-color: {t.get('accent_color', '#0078D4')};
                border-radius: 9px;
            }}
        """)
        checkin_inner.addWidget(self._today_progress)

        self._today_label = QLabel("0 / 2000 字")
        self._today_label.setStyleSheet(
            f"color: {t.get('fg_color', '#212529')}; font-size: 13px; border: none;"
        )
        checkin_inner.addWidget(self._today_label)

        checkin_inner.addStretch()

        self._daily_target_btn = QPushButton("修改目标")
        self._daily_target_btn.setFixedHeight(28)
        self._daily_target_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.get('accent_color', '#0078D4')}18;
                color: {t.get('accent_color', '#0078D4')};
                border: 1px solid {t.get('accent_color', '#0078D4')}40;
                border-radius: 4px;
                padding: 4px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {t.get('accent_color', '#0078D4')}30;
            }}
        """)
        self._daily_target_btn.clicked.connect(self._on_change_daily_target)
        checkin_inner.addWidget(self._daily_target_btn)

        checkin_layout.addWidget(checkin_frame)
        main_layout.addLayout(checkin_layout)

        # ====== 详细信息区域 ======
        detail_layout = QHBoxLayout()
        
        # 左侧：各卷统计
        volumes_group = QGroupBox(language_manager.tr("volume_details"))
        bg = t.get('card_bg', '#FFFFFF')
        border = t.get('border_color', '#DEE2E6')
        fg = t.get('fg_color', '#212529')
        radius = t.get('card_radius', '12px')
        volumes_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: {radius};
                padding: 24px 16px 12px 16px;
                font-weight: 600;
                font-family: {t.get('font_family', "'Segoe UI', 'Microsoft YaHei UI', sans-serif")};
                font-size: 13px;
            }}
            QGroupBox::title {{
                subcontrol-origin: padding;
                left: 16px;
                top: 6px;
                padding: 0 6px;
                color: {fg};
            }}
        """)
        volumes_layout = QVBoxLayout(volumes_group)
        
        self.volumes_info = QTextBrowser()
        self.volumes_info.setMinimumHeight(300)
        self.volumes_info.setMaximumHeight(600)
        self.volumes_info.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.volumes_info.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {t.get('input_bg_color', '#FFFFFF')};
                color: {t.get('fg_color', '#212529')};
                border: none;
                font-size: 13px;
                padding: 8px;
            }}
            QTextBrowser QScrollBar:vertical {{
                width: 6px;
                background: transparent;
            }}
            QTextBrowser QScrollBar::handle:vertical {{
                background: {t.get('text_secondary', '#888')};
                border-radius: 3px;
                min-height: 20px;
            }}
            QTextBrowser QScrollBar::add-line:vertical {{
                height: 0px;
            }}
            QTextBrowser QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        volumes_layout.addWidget(self.volumes_info)
        
        detail_layout.addWidget(volumes_group, 1)
        
        # 右侧：关键词覆盖
        keywords_group = QGroupBox("关键词覆盖")
        keywords_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: {radius};
                padding: 24px 16px 12px 16px;
                font-weight: 600;
                font-family: {t.get('font_family', "'Segoe UI', 'Microsoft YaHei UI', sans-serif")};
                font-size: 13px;
            }}
            QGroupBox::title {{
                subcontrol-origin: padding;
                left: 16px;
                top: 6px;
                padding: 0 6px;
                color: {fg};
            }}
        """)
        keywords_layout = QVBoxLayout(keywords_group)
        
        self.keywords_info = QTextBrowser()
        self.keywords_info.setMinimumHeight(200)
        self.keywords_info.setMaximumHeight(400)
        self.keywords_info.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.keywords_info.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {t.get('input_bg_color', '#FFFFFF')};
                color: {t.get('fg_color', '#212529')};
                border: none;
                font-size: 13px;
                padding: 8px;
            }}
            QTextBrowser QScrollBar:vertical {{
                width: 6px;
                background: transparent;
            }}
            QTextBrowser QScrollBar::handle:vertical {{
                background: {t.get('text_secondary', '#888')};
                border-radius: 3px;
                min-height: 20px;
            }}
            QTextBrowser QScrollBar::add-line:vertical {{
                height: 0px;
            }}
            QTextBrowser QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        keywords_layout.addWidget(self.keywords_info)
        
        detail_layout.addWidget(keywords_group, 1)
        
        main_layout.addLayout(detail_layout)
        
        # ====== 趋势区域 ======
        self._trend_group = QGroupBox("写作趋势")
        self._trend_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: {radius};
                padding: 24px 16px 12px 16px;
                font-weight: 600;
                font-family: {t.get('font_family', "'Segoe UI', 'Microsoft YaHei UI', sans-serif")};
                font-size: 13px;
            }}
            QGroupBox::title {{
                subcontrol-origin: padding;
                left: 16px;
                top: 6px;
                padding: 0 6px;
                color: {fg};
            }}
        """)
        trend_layout = QVBoxLayout(self._trend_group)

        # 趋势图工具栏
        trend_toolbar = QHBoxLayout()
        trend_toolbar.setContentsMargins(0, 0, 0, 4)
        trend_toolbar.setSpacing(4)

        interval_label = QLabel("统计间隔:")
        interval_label.setStyleSheet(
            f"color: {t.get('text_secondary', '#6C757D')}; font-size: 11px; border: none;"
        )
        trend_toolbar.addWidget(interval_label)

        self._trend_interval = QComboBox()
        self._trend_interval.addItems(["今日逐时", "近7天", "近30天", "近90天", "全部"])
        self._trend_interval.setCurrentIndex(0)
        self._trend_interval.setFixedHeight(24)
        self._trend_interval.setStyleSheet(f"""
            QComboBox {{
                background-color: {t.get('input_bg_color', '#FFFFFF')};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 11px;
                min-width: 72px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 16px;
                border-left: 1px solid {border};
            }}
            QComboBox QAbstractItemView {{
                background-color: {t.get('card_bg', '#FFFFFF')};
                color: {fg};
                selection-background-color: {t.get('accent_color', '#0078D4')}40;
                border: 1px solid {border};
            }}
        """)
        self._trend_interval.currentIndexChanged.connect(self._on_trend_config_changed)
        trend_toolbar.addWidget(self._trend_interval)

        unit_label = QLabel("纵轴单位:")
        unit_label.setStyleSheet(
            f"color: {t.get('text_secondary', '#6C757D')}; font-size: 11px; border: none;"
        )
        trend_toolbar.addWidget(unit_label)

        self._trend_unit = QComboBox()
        self._trend_unit.addItems(["字", "千字", "万字"])
        self._trend_unit.setCurrentIndex(0)
        self._trend_unit.setFixedHeight(24)
        self._trend_unit.setStyleSheet(self._trend_interval.styleSheet())
        self._trend_unit.currentIndexChanged.connect(self._on_trend_config_changed)
        trend_toolbar.addWidget(self._trend_unit)

        trend_toolbar.addStretch()
        trend_layout.addLayout(trend_toolbar)

        self.trend_chart = TrendChart()
        trend_layout.addWidget(self.trend_chart, 1)
        
        main_layout.addWidget(self._trend_group, 1)
        
        logger.debug("[WritingDashboard] UI构建完成")
    
    def set_novel_dir(self, novel_dir: str):
        """设置小说目录"""
        if os.path.exists(novel_dir):
            self.novel_dir = novel_dir
            
            # 初始化缓存
            try:
                from core.chapter_index_cache import ChapterIndexCache
                self._chapter_cache = ChapterIndexCache(novel_dir)
                
                from core.frequency_data_cache import FrequencyDataCache
                self._freq_cache = FrequencyDataCache(novel_dir)
            except Exception as e:
                logger.error(f"[WritingDashboard] 初始化缓存失败: {e}")
            
            logger.info(f"[WritingDashboard] 设置目录: {novel_dir}")
    
    def get_chapter_cache(self):
        """获取章节缓存实例（供外部复用）"""
        return getattr(self, '_chapter_cache', None)
    
    def get_freq_cache(self):
        """获取词频缓存实例（供外部复用）"""
        return getattr(self, '_freq_cache', None)
    
    def _on_trend_config_changed(self):
        """趋势图配置变更时刷新"""
        self._update_trend_chart()

    def _get_trend_data_by_interval(self) -> List[Tuple[str, int]]:
        """根据选中的统计间隔获取趋势数据"""
        interval_text = self._trend_interval.currentText()
        if not self._chapter_cache:
            return []

        now = datetime.now()
        data_points = []

        if interval_text == "今日逐时":
            today_str = now.strftime("%Y-%m-%d")
            data = self._chapter_cache.get_recently_modified(hours=24)
            for h in range(24):
                key = f"{h:02d}:00"
                count = sum(
                    ch.get('word_count', 0) for ch in data
                    if ch.get('modified_at', '').startswith(today_str)
                    and ch.get('modified_at', '')[11:13] == f"{h:02d}"
                )
                data_points.append((key, count))
        elif interval_text == "近7天":
            hours = 24 * 7
            data = self._chapter_cache.get_recently_modified(hours=hours)
            for i in range(6, -1, -1):
                day = now - timedelta(days=i)
                key = day.strftime("%m-%d")
                count = sum(
                    ch.get('word_count', 0) for ch in data
                    if ch.get('modified_at', '').startswith(day.strftime("%Y-%m-%d"))
                )
                data_points.append((key, count))
        elif interval_text == "近30天":
            hours = 24 * 30
            data = self._chapter_cache.get_recently_modified(hours=hours)
            for i in range(29, -1, -1):
                day = now - timedelta(days=i)
                key = day.strftime("%m-%d")
                count = sum(
                    ch.get('word_count', 0) for ch in data
                    if ch.get('modified_at', '').startswith(day.strftime("%Y-%m-%d"))
                )
                data_points.append((key, count))
        elif interval_text == "近90天":
            hours = 24 * 90
            data = self._chapter_cache.get_recently_modified(hours=hours)
            for i in range(89, -1, -1):
                day = now - timedelta(days=i)
                key = day.strftime("%m-%d")
                count = sum(
                    ch.get('word_count', 0) for ch in data
                    if ch.get('modified_at', '').startswith(day.strftime("%Y-%m-%d"))
                )
                data_points.append((key, count))
        else:  # 全部
            all_chapters = []
            for vol in self._chapter_cache.get_volumes():
                vol_name = vol['name']
                chapters = self._chapter_cache.get_chapters(vol_name)
                for ch in chapters:
                    all_chapters.append(ch)
            if not all_chapters:
                return []
            sorted_chapters = sorted(all_chapters, key=lambda x: x.get('mtime', ''))
            dates = set()
            for ch in sorted_chapters:
                d = ch.get('mtime', '')[:10]
                if d:
                    dates.add(d)
            dates = sorted(list(dates))
            for d in dates:
                count = sum(
                    ch.get('word_count', 0) for ch in sorted_chapters
                    if ch.get('mtime', '').startswith(d)
                )
                data_points.append((d[-5:], count))

        return data_points

    def refresh_data(self):
        """刷新所有数据"""
        if not self.novel_dir or not os.path.exists(self.novel_dir):
            return
        
        logger.info("[WritingDashboard] 开始刷新数据...")
        
        try:
            # 1. 更新章节索引缓存
            if self._chapter_cache:
                chapter_stats = self._chapter_cache.refresh(count_words=True)
            else:
                chapter_stats = {}
            
            # 2. 更新词频缓存
            freq_stats = {}
            if self._freq_cache:
                freq_stats = self._freq_cache.get_stats()
            
            # 3. 计算总体统计
            total_words = chapter_stats.get('total_words', 0)
            total_chapters = chapter_stats.get('total_chapters', 0)
            total_volumes = chapter_stats.get('total_volumes', 0)
            
            # 4. 计算日均字数（基于最近修改的文件）
            daily_avg = self._calculate_daily_average()
            
            # 5. 更新UI
            self._update_stat_cards(total_words, total_chapters, total_volumes, daily_avg)
            self._update_volumes_info()
            self._update_keywords_info(freq_stats)
            self._update_trend_chart()
            self._update_daily_checkin()
            
            # 6. 更新时间戳
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 发出信号
            self._stats_data = {
                **chapter_stats,
                **freq_stats,
                'daily_avg': daily_avg,
                'refresh_time': now_str
            }
            self.data_refreshed.emit(self._stats_data)
            
            logger.info("[WritingDashboard] 数据刷新完成")
            
        except Exception as e:
            logger.error(f"[WritingDashboard] 刷新失败: {e}", exc_info=True)
    
    def _calculate_daily_average(self) -> int:
        """计算近7天日均字数"""
        if not self._chapter_cache:
            return 0
        
        recent = self._chapter_cache.get_recently_modified(hours=24 * 7)
        if not recent:
            return 0
        
        total = sum(item['word_count'] for item in recent)
        return int(total / 7)  # 日均
    
    def _calculate_today_words(self) -> Tuple[bool, int]:
        """计算今日已写字数

        Returns:
            (has_new_chapter, total_words) — 今日是否有写作活动，今日总字数
        """
        if not self._chapter_cache:
            return False, 0
        today_str = datetime.now().strftime("%Y-%m-%d")
        total = 0
        has_new = False
        for vol in self._chapter_cache.get_volumes():
            vol_name = vol['name']
            chapters = self._chapter_cache.get_chapters(vol_name)
            for ch_data in chapters:
                ch_mtime = ch_data.get('mtime', '')
                if ch_mtime.startswith(today_str):
                    total += ch_data.get('word_count', 0)
                    has_new = True
        return has_new, total

    def _update_daily_checkin(self):
        """更新每日打卡进度"""
        from ..core.theme_manager import theme_manager
        t = theme_manager.get_current_theme()
        accent = t.get('accent_color', '#0078D4')
        border = t.get('border_color', '#DEE2E6')

        has_new, today_words = self._calculate_today_words()
        daily_target = ConfigManager.get_int('Stats', 'daily_target_words', fallback=2000)
        progress = min(100, int(today_words / daily_target * 100)) if daily_target > 0 else 0

        self._today_progress.setValue(progress)

        if not has_new:
            self._today_label.setText("今日未检测到写作活动")
            self._today_progress.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {border};
                    border: none;
                    border-radius: 9px;
                }}
                QProgressBar::chunk {{
                    background-color: {accent};
                    border-radius: 9px;
                }}
            """)
        elif today_words >= daily_target:
            excess = today_words - daily_target
            steps = excess // 100
            ratio = min(1.0, steps / 10)
            green = QColor('#28A745')
            red = QColor('#DC3545')
            bar_color = QColor(
                int(green.red() + (red.red() - green.red()) * ratio),
                int(green.green() + (red.green() - green.green()) * ratio),
                int(green.blue() + (red.blue() - green.blue()) * ratio),
            )
            self._today_progress.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {border};
                    border: none;
                    border-radius: 9px;
                }}
                QProgressBar::chunk {{
                    background-color: {bar_color.name()};
                    border-radius: 9px;
                }}
            """)
            self._today_label.setText(
                f"{today_words:,} / {daily_target:,} 字（超预期 +{excess:,}）"
            )
        else:
            self._today_progress.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {border};
                    border: none;
                    border-radius: 9px;
                }}
                QProgressBar::chunk {{
                    background-color: {accent};
                    border-radius: 9px;
                }}
            """)
            self._today_label.setText(f"{today_words:,} / {daily_target:,} 字")

    def _on_change_daily_target(self):
        """弹出对话框修改每日目标字数"""
        from PyQt5.QtWidgets import QInputDialog
        current = ConfigManager.get_int('Stats', 'daily_target_words', fallback=2000)
        val, ok = QInputDialog.getInt(
            self, "修改每日目标", "每日目标字数:",
            value=current, min=100, max=100000, step=500
        )
        if ok and val > 0:
            ConfigManager.set('Stats', 'daily_target_words', str(val))
            self._update_daily_checkin()

    def _update_stat_cards(self, words, chapters, volumes, daily_avg):
        """更新统计卡片"""
        self.total_words_card.update_value(
            f"{words:,}",
            f"约 {words // 10000} 万字" if words >= 10000 else ""
        )
        self.total_chapters_card.update_value(str(chapters))
        self.total_volumes_card.update_value(str(volumes))
        self.daily_avg_card.update_value(f"{daily_avg:,}")
    
    @staticmethod
    def _clean_volume_name(raw_name):
        """过滤卷名中的方括号标识，移除括号内容中的数字后缀"""
        import re
        match = re.match(r'^(\d+)\[(.+?)\]$', raw_name)
        if match:
            prefix = match.group(1)
            inner = match.group(2)
            inner_clean = re.sub(r'_\d+$', '', inner)
            return f"{prefix}[{inner_clean}]"
        match = re.match(r'^(.+?)\[(.+?)\]$', raw_name)
        if match:
            prefix = match.group(1)
            inner = match.group(2)
            inner_clean = re.sub(r'_\d+$', '', inner)
            return f"{prefix}[{inner_clean}]"
        return raw_name

    def _update_volumes_info(self):
        """更新各卷详细信息"""
        if not self._chapter_cache:
            return
        
        from ..core.theme_manager import theme_manager
        t = theme_manager.get_current_theme()
        fg = t.get('fg_color', '#212529')
        accent = t.get('accent_color', '#0078D4')
        border = t.get('border_color', '#DEE2E6')

        volumes = self._chapter_cache.get_volumes()
        
        html = f"<div style='width:100%;overflow-x:auto;'>"
        html += f"<table style='width:100%;table-layout:fixed;border-collapse:collapse;font-size:13px;color:{fg};'>"
        html += f"<colgroup>"
        html += f"<col style='width:38%;'>"
        html += f"<col style='width:16%;'>"
        html += f"<col style='width:22%;'>"
        html += f"<col style='width:24%;'>"
        html += f"</colgroup>"
        html += f"<tr style='font-weight:bold;color:{fg};'>"
        html += "<th style='padding:6px 8px;text-align:left;'>卷名</th>"
        html += "<th style='padding:6px 8px;text-align:center;'>章节数</th>"
        html += "<th style='padding:6px 8px;text-align:right;'>总字数</th>"
        html += "<th style='padding:6px 8px;text-align:center;'>进度</th></tr>"
        
        for vol in volumes:
            raw_name = vol['name']
            name = self._clean_volume_name(raw_name)
            ch_count = vol['chapters']
            word_count = vol['total_words']
            
            target = ConfigManager.get_int('Stats', 'volume_target_words', fallback=100000)
            progress = min(100, int(word_count / target * 100)) if target > 0 else 0
            
            bar_color = accent if progress >= 80 else '#ffaa00' if progress >= 50 else accent
            pct_color = '#ffffff' if progress >= 80 else '#333333'
            
            html += f"<tr style='border-bottom:1px solid {border};'>"
            html += f"<td style='padding:5px 8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;' title='{raw_name}'>{name}</td>"
            html += f"<td style='padding:5px 8px;text-align:center;'>{ch_count}</td>"
            html += f"<td style='padding:5px 8px;text-align:right;'>{word_count:,}</td>"
            html += f"<td style='padding:5px 8px;text-align:center;white-space:nowrap;position:relative;'>"
            html += f"<div style='background:{border};border-radius:4px;height:14px;width:70px;display:inline-block;vertical-align:middle;position:relative;overflow:visible;'>"
            html += f"<div style='background:{bar_color};height:100%;width:{progress}%;"
            html += f"border-radius:4px;transition:width 0.3s;min-width:0;'></div>"
            html += f"<span style='position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-weight:bold;color:{pct_color};font-size:11px;line-height:14px;text-shadow:0 0 2px rgba(0,0,0,0.3);'>{progress}%</span>"
            html += f"</div></td>"
            html += "</tr>"
        
        html += "</table></div>"
        self.volumes_info.setHtml(html)
    
    def _update_keywords_info(self, freq_stats: Dict):
        """更新关键词覆盖信息"""
        from ..core.theme_manager import theme_manager
        t = theme_manager.get_current_theme()
        fg = t.get('fg_color', '#212529')
        accent = t.get('accent_color', '#0078D4')
        warn = t.get('warning_color', '#FF8C00')
        success = t.get('success_color', '#28A745')

        unique_words = freq_stats.get('unique_words', 0)
        matched = freq_stats.get('matched_keywords', 0)
        stale = freq_stats.get('stale_candidates', 0)
        
        coverage = (matched / unique_words * 100) if unique_words > 0 else 0
        
        html = f"<p style='margin:5px 0;color:{fg};'>"
        html += f"总词条: <b style='color:{fg};'>{unique_words}</b><br>"
        html += f"已匹配: <b style='color:{success};'>{matched}</b> "
        html += f"({coverage:.1f}%)<br>"
        html += f"待处理称谓: <b style='color:{warn};'>{stale}</b>"
        html += "</p>"
        
        self.keywords_info.setHtml(html)
    
    def _update_trend_chart(self):
        """更新写作趋势图"""
        data_points = self._get_trend_data_by_interval()
        unit = self._trend_unit.currentText()
        self.trend_chart.set_data(data_points, unit=unit)

        interval_text = self._trend_interval.currentText()
        self._trend_group.setTitle(f"写作趋势（{interval_text}）")
    
    def _export_report(self):
        """导出统计报告"""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        
        if not self._stats_data:
            QMessageBox.warning(self, "提示", "暂无数据可导出，请先刷新")
            return
        
        default_path = os.path.join(
            self.novel_dir or ".", 
            f"writing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出写作报告", default_path, "Text Files (*.txt)"
        )
        
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("=" * 60 + "\n")
                    f.write("NovelHelper 写作数据报告\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(f"生成时间: {self._stats_data.get('refresh_time', '')}\n\n")
                    
                    f.write("-" * 40 + "\n")
                    f.write("【总体统计】\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"总字数: {self._stats_data.get('total_words', 0):,}\n")
                    f.write(f"总章节数: {self._stats_data.get('total_chapters', 0)}\n")
                    f.write(f"总卷数: {self._stats_data.get('total_volumes', 0)}\n")
                    f.write(f"日均字数: {self._stats_data.get('daily_avg', 0):,}\n\n")
                    
                    f.write("-" * 40 + "\n")
                    f.write("【各卷详情】\n")
                    f.write("-" * 40 + "\n")
                    
                    if self._chapter_cache:
                        for vol in self._chapter_cache.get_volumes():
                            f.write(f"\n{vol['name']}:\n")
                            f.write(f"  章节数: {vol['chapters']}\n")
                            f.write(f"  总字数: {vol['total_words']:,}\n")
                    
                    f.write("\n" + "=" * 60 + "\n")
                    f.write("报告结束\n")
                
                QMessageBox.information(
                    self, "成功", f"报告已导出到:\n{filepath}"
                )
                logger.info(f"[WritingDashboard] 报告已导出: {filepath}")
                
            except Exception as e:
                QMessageBox.critical(self, language_manager.tr("error"), f"{language_manager.tr('export_failed')}: {e}")
                logger.error(f"[WritingDashboard] 导出报告失败: {e}")


class TrendChart(QWidget):
    """简单的趋势图组件（纯PyQt5实现），支持鼠标悬停显示数据"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data_points: List[Tuple[str, int]] = []
        self._hovered_index = -1
        self._hit_rects = []
        self.setMinimumHeight(250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: transparent;")
    
    def set_data(self, data_points: List[Tuple[str, int]], unit: str = "字"):
        """设置数据点和单位"""
        self._data_points = data_points
        self._unit = unit
        self._hovered_index = -1
        self._hit_rects = []
        self._label_indices = self._compute_label_indices(data_points)
        self.update()
    
    def _compute_label_indices(self, data_points):
        """根据数据点数量计算需要显示的标签索引（密度优化）"""
        n = len(data_points)
        if n <= 7:
            return list(range(n))
        elif n <= 30:
            count = 10
        elif n <= 90:
            count = 15
        else:
            return list(range(n))
        step = max(1, (n - 1) // (count - 1))
        indices = set()
        for i in range(0, n, step):
            indices.add(i)
        if n - 1 not in indices:
            indices.add(n - 1)
        return sorted(indices)
    
    def mouseMoveEvent(self, event):
        self._hovered_index = -1
        for i, rect in enumerate(self._hit_rects):
            if rect.contains(event.pos()):
                self._hovered_index = i
                break
        self.update()
        super().mouseMoveEvent(event)
    
    def leaveEvent(self, event):
        self._hovered_index = -1
        self.update()
        super().leaveEvent(event)
    
    def _format_val(self, val: int) -> str:
        """按当前单位格式化数值"""
        u = getattr(self, '_unit', '字')
        if u == "千字":
            return f"{val/1000:.1f}k"
        elif u == "万字":
            return f"{val/10000:.2f}万"
        return f"{val:,}"

    def _format_tooltip(self, val: int) -> str:
        """按当前单位格式化悬浮提示"""
        u = getattr(self, '_unit', '字')
        if u == "千字":
            return f"{val/1000:.1f} 千字"
        elif u == "万字":
            return f"{val/10000:.2f} 万字"
        return f"{val:,} 字"

    def paintEvent(self, event):
        """绘制趋势图"""
        from ..core.theme_manager import theme_manager
        t = theme_manager.get_current_theme()
        accent = t.get('accent_color', '#0078D4')
        fg = t.get('fg_color', '#212529')
        border = t.get('border_color', '#DEE2E6')
        text_secondary = t.get('text_secondary', '#6C757D')

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        if not self._data_points or len(self._data_points) < 2:
            painter.setPen(QColor(text_secondary))
            painter.drawText(w//2 - 50, h//2, "暂无足够数据")
            painter.end()
            return
        
        margin_left = 50
        margin_right = 20
        margin_top = 20
        margin_bottom = 30
        
        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom
        
        max_val = max(val for _, val in self._data_points) or 1
        min_val = 0
        val_range = max_val - min_val if max_val != min_val else 1

        # 智能Y轴刻度
        step = self._nice_step(max_val)
        ticks = list(range(0, max_val + step, step))
        if ticks[-1] < max_val:
            ticks.append(max_val)
        
        tick_len = 6
        painter.setPen(QPen(QColor(border), 1, Qt.DotLine))
        for val in ticks:
            ratio = val / max_val
            y = int(margin_top + chart_h * (1 - ratio))
            painter.drawLine(margin_left, y, w - margin_right, y)
            painter.setPen(QPen(QColor(text_secondary), 1))
            painter.drawLine(margin_left - tick_len, y, margin_left, y)
            painter.setPen(QPen(QColor(border), 1, Qt.DotLine))
        
        painter.setPen(QColor(text_secondary))
        painter.setFont(QFont('Consolas', 9))
        for val in ticks:
            ratio = val / max_val
            y = int(margin_top + chart_h * (1 - ratio))
            painter.drawText(5, y + 4, self._format_val(val))
        
        points = []
        n = len(self._data_points)
        step_x = chart_w / (n - 1) if n > 1 else chart_w
        
        for i, (label, value) in enumerate(self._data_points):
            x = margin_left + i * step_x
            y = margin_top + chart_h - (value - min_val) / val_range * chart_h
            points.append((x, y, label, value))

        # 构建点击热区
        self._hit_rects.clear()
        for i, (x, y, _, val) in enumerate(points):
            self._hit_rects.append(QRect(int(x) - 16, margin_top, 32, chart_h))
        
        # 面积填充
        path = QPainterPath()
        path.moveTo(points[0][0], margin_top + chart_h)
        for x, y, _, _ in points:
            path.lineTo(x, y)
        path.lineTo(points[-1][0], margin_top + chart_h)
        path.closeSubpath()
        painter.fillPath(path, QBrush(QColor(accent + '20')))
        
        # 折线
        pen = QPen(QColor(accent), 3)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        for i in range(len(points) - 1):
            x1, y1, _, _ = points[i]
            x2, y2, _, _ = points[i + 1]
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        
        # X轴标签（密度优化：超30点仅显示采样标签）
        painter.setPen(QColor(text_secondary))
        painter.setFont(QFont('Microsoft YaHei', 9))
        for i, (x, y, label, value) in enumerate(points):
            if i == self._hovered_index:
                continue
            if i not in self._label_indices:
                continue
            painter.drawText(int(x) - 15, h - 8, label)
        
        # 悬浮交叉线
        if self._hovered_index >= 0 and self._hovered_index < len(points):
            hx, hy, _, _ = points[self._hovered_index]
            painter.setPen(QPen(QColor(accent + '60'), 1, Qt.DashLine))
            painter.drawLine(int(hx), margin_top, int(hx), margin_top + chart_h)
            painter.drawLine(margin_left, int(hy), margin_left + chart_w, int(hy))
        
        # 数据点
        for i, (x, y, label, value) in enumerate(points):
            is_hovered = i == self._hovered_index
            r = 5 if is_hovered else 4
            painter.setPen(QPen(QColor(accent).lighter(180), 2))
            if is_hovered:
                painter.setBrush(QBrush(QColor(accent).lighter(130)))
            else:
                painter.setBrush(QBrush(QColor(accent)))
            painter.drawEllipse(int(x) - r, int(y) - r, r * 2, r * 2)
        
        # 悬浮数据标签
        if self._hovered_index >= 0 and self._hovered_index < len(self._data_points):
            label, value = self._data_points[self._hovered_index]
            x, y = points[self._hovered_index][0], points[self._hovered_index][1]
            tw = min(130, len(f"{label}{self._format_tooltip(value)}") * 9)
            th = 36
            tx = int(x - tw / 2)
            ty = int(y - th - 8)
            if tx < 4:
                tx = 4
            if tx + tw > w - 4:
                tx = w - 4 - tw
            if ty < 4:
                ty = int(y + 8)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(48, 48, 48, 230))
            painter.drawRoundedRect(tx, ty, tw, th, 6, 6)
            painter.setPen(QColor('#FFFFFF'))
            painter.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
            painter.drawText(tx, ty, tw, th // 2, Qt.AlignCenter, label)
            painter.setFont(QFont('Consolas', 9))
            painter.drawText(tx, ty + th // 2, tw, th // 2, Qt.AlignCenter, self._format_tooltip(value))
        
        painter.end()

    @staticmethod
    def _nice_step(max_val):
        if max_val <= 5:
            return 1
        elif max_val <= 20:
            return 5
        elif max_val <= 100:
            return 10
        elif max_val <= 500:
            return 50
        elif max_val <= 2000:
            return 200
        elif max_val <= 10000:
            return 1000
        elif max_val <= 50000:
            return 5000
        else:
            return max(1, max_val // 6)
