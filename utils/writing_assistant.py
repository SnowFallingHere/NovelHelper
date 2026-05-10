"""
写作辅助工具
功能：
- 写作计时器
- 字数目标设定和提醒
- 写作记录和统计
- 专注模式
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, List, Dict

logger = logging.getLogger(__name__)


class WritingSession:
    """
    一次写作会话记录
    """
    def __init__(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        word_count: int = 0,
        target_words: int = 0,
        notes: str = ""
    ):
        self.start_time = start_time or datetime.now()
        self.end_time = end_time
        self.word_count = word_count
        self.target_words = target_words
        self.notes = notes
        self.id = self.start_time.strftime('%Y%m%d_%H%M%S')

    @property
    def duration(self) -> Optional[timedelta]:
        if self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def duration_minutes(self) -> int:
        if self.duration:
            return int(self.duration.total_seconds() // 60)
        return 0

    @property
    def is_complete(self) -> bool:
        return self.end_time is not None

    @property
    def target_achieved(self) -> bool:
        return self.target_words > 0 and self.word_count >= self.target_words

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'word_count': self.word_count,
            'target_words': self.target_words,
            'notes': self.notes
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'WritingSession':
        session = cls(
            start_time=datetime.fromisoformat(data['start_time']),
            word_count=data.get('word_count', 0),
            target_words=data.get('target_words', 0),
            notes=data.get('notes', '')
        )
        if data.get('end_time'):
            session.end_time = datetime.fromisoformat(data['end_time'])
        return session


class WritingAssistant:
    """
    写作辅助主类
    """

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        self._sessions = []
        self._current_session: Optional[WritingSession] = None
        self._data_file = os.path.join(data_dir, 'writing_records.json')
        self._config_file = os.path.join(data_dir, 'writing_config.json')
        
        # 配置
        self._config = {
            'daily_target_words': 2000,
            'focus_mode_duration': 25,  # 分钟
            'short_break': 5,
            'long_break': 15,
            'remind_interval': 60  # 秒
        }
        
        self._load()

    def _load(self):
        """加载数据"""
        # 加载会话记录
        if os.path.exists(self._data_file):
            try:
                with open(self._data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._sessions = [WritingSession.from_dict(s) for s in data.get('sessions', [])]
            except Exception as e:
                logger.error(f"加载写作记录失败: {e}")
        
        # 加载配置
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self._config.update(config)
            except Exception as e:
                logger.error(f"加载写作配置失败: {e}")

    def _save(self):
        """保存数据"""
        try:
            with open(self._data_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'sessions': [s.to_dict() for s in self._sessions]
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存写作记录失败: {e}")

        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存写作配置失败: {e}")

    # ====== 计时器功能 ======

    def start_session(self, target_words: int = None, notes: str = "") -> WritingSession:
        """
        开始一次写作会话
        
        Args:
            target_words: 本次会话目标字数
            notes: 备注
            
        Returns:
            WritingSession
        """
        if self._current_session and not self._current_session.is_complete:
            logger.warning("存在未完成的写作会话，已自动结束")
            self.end_session(self._current_session.word_count)
        
        target = target_words or self._config['daily_target_words']
        self._current_session = WritingSession(target_words=target, notes=notes)
        self._sessions.append(self._current_session)
        self._save()
        
        logger.info(f"写作会话开始: {self._current_session.id}")
        return self._current_session

    def pause_session(self):
        """暂停会话（当前只是标记，未完全实现）"""
        if self._current_session and not self._current_session.is_complete:
            logger.info("写作会话暂停")

    def update_word_count(self, word_count: int):
        """
        更新当前会话字数
        
        Args:
            word_count: 当前累计字数
        """
        if self._current_session:
            self._current_session.word_count = word_count
            self._save()

    def end_session(self, final_word_count: int = None) -> Optional[WritingSession]:
        """
        结束写作会话
        
        Args:
            final_word_count: 最终字数
            
        Returns:
            完成的会话
        """
        if not self._current_session or self._current_session.is_complete:
            logger.warning("没有活跃的写作会话")
            return None
        
        if final_word_count is not None:
            self._current_session.word_count = final_word_count
        
        self._current_session.end_time = datetime.now()
        self._save()
        
        logger.info(f"写作会话结束: {self._current_session.id}")
        session = self._current_session
        self._current_session = None
        return session

    @property
    def current_session(self) -> Optional[WritingSession]:
        return self._current_session

    @property
    def is_in_session(self) -> bool:
        return self._current_session is not None and not self._current_session.is_complete

    # ====== 统计功能 ======

    def get_sessions(self, 
                     start_date: datetime = None, 
                     end_date: datetime = None) -> List[WritingSession]:
        """
        获取指定时间范围内的写作会话
        
        Args:
            start_date: 起始日期
            end_date: 结束日期
            
        Returns:
            会话列表
        """
        sessions = self._sessions
        
        if start_date:
            sessions = [s for s in sessions if s.start_time >= start_date]
        
        if end_date:
            sessions = [s for s in sessions if s.start_time <= end_date]
        
        return sorted(sessions, key=lambda s: s.start_time, reverse=True)

    def get_today_sessions(self) -> List[WritingSession]:
        """获取今天的所有会话"""
        today = datetime.now().date()
        return [
            s for s in self._sessions 
            if s.start_time.date() == today
        ]

    def get_today_total_words(self) -> int:
        """获取今天累计字数"""
        return sum(s.word_count for s in self.get_today_sessions())

    def get_today_total_time(self) -> timedelta:
        """获取今天累计写作时长"""
        total = timedelta()
        for s in self.get_today_sessions():
            if s.duration:
                total += s.duration
        return total

    def get_target_progress(self) -> tuple:
        """
        获取今日目标进度
        
        Returns:
            (current_words, target_words, percentage)
        """
        current = self.get_today_total_words()
        target = self._config['daily_target_words']
        percentage = min(100, int((current / max(target, 1)) * 100))
        return current, target, percentage

    def get_weekly_statistics(self) -> Dict:
        """
        获取本周统计
        
        Returns:
            统计数据
        """
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        daily_words = {}
        for i in range(7):
            day = week_start + timedelta(days=i)
            daily_words[day.isoformat()] = 0
        
        for s in self._sessions:
            day = s.start_time.date().isoformat()
            if day in daily_words:
                daily_words[day] += s.word_count
        
        week_total = sum(daily_words.values())
        avg_per_day = int(week_total / 7) if week_total > 0 else 0
        
        return {
            'weekly_total': week_total,
            'daily_words': daily_words,
            'avg_per_day': avg_per_day,
            'days_completed_target': sum(
                1 for words in daily_words.values() 
                if words >= self._config['daily_target_words']
            )
        }

    # ====== 配置 ======

    @property
    def daily_target_words(self) -> int:
        return self._config.get('daily_target_words', 2000)

    @daily_target_words.setter
    def daily_target_words(self, value: int):
        self._config['daily_target_words'] = max(0, value)
        self._save()

    @property
    def focus_mode_duration(self) -> int:
        """专注模式时长（分钟）"""
        return self._config.get('focus_mode_duration', 25)

    @focus_mode_duration.setter
    def focus_mode_duration(self, value: int):
        self._config['focus_mode_duration'] = max(1, value)
        self._save()

    @property
    def remind_interval(self) -> int:
        """提醒间隔（秒）"""
        return self._config.get('remind_interval', 60)

    def clear_history(self):
        """清空所有历史记录"""
        self._sessions = []
        self._current_session = None
        self._save()
        logger.info("写作历史已清空")

    # ====== 导出 ======

    def export_statistics(self, output_path: str) -> bool:
        """
        导出统计报告
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            是否成功
        """
        try:
            weekly_stats = self.get_weekly_statistics()
            today_words, target, progress = self.get_target_progress()
            
            report = [
                "# 写作统计报告",
                f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"本周写作字数: {weekly_stats}",
                f"今日字数: {today_words} / 目标: {target} ({progress:.1f}%)",
            ]
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report))
            return True
        except Exception as e:
            print(f"导出统计报告失败: {e}")
            return False