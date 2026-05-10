"""
监控服务
提供文件系统监控、自动处理新章节等功能
"""

import os
import time
import threading
import logging
from pathlib import Path
from typing import List, Dict, Callable, Optional

logger = logging.getLogger(__name__)


class MonitorService:
    """
    文件监控服务
    
    功能：
    - 监控指定目录的文件变化
    - 自动检测新章节
    - 支持回调通知
    - 线程安全
    
    使用示例：
        service = MonitorService()
        
        # 设置监控目录和回调
        service.watch_directory('./my_novel')
        service.on_new_chapter_found(lambda path: print(f"新章节: {path}"))
        
        # 启动监控
        service.start()
        
        # ... 做其他事情 ...
        
        # 停止监控
        service.stop()
    """
    
    def __init__(self, scan_interval: float = 2.0):
        """
        初始化监控服务
        
        Args:
            scan_interval: 扫描间隔（秒），默认2秒
        """
        self._scan_interval = scan_interval
        self._watch_dir = None
        self._is_running = False
        self._thread = None
        self._stop_event = threading.Event()
        
        # 回调函数列表
        self._callbacks = {
            'new_chapter': [],      # 新章节发现时调用
            'chapter_modified': [],  # 章节修改时调用
            'chapter_deleted': [],   # 章节删除时调用
            'error': []              # 出错时调用
        }
        
        # 已知文件状态 {path: mtime}
        self._known_files: Dict[str, float] = {}
        
        # 新发现的章节队列
        self._new_chapters: List[str] = []
        
        # 锁，保证线程安全
        self._lock = threading.Lock()
    
    @property
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._is_running
    
    @property
    def watch_directory(self) -> Optional[str]:
        """获取当前监控的目录"""
        return self._watch_dir
    
    def watch_directory(self, directory: str):
        """
        设置要监控的目录
        
        Args:
            directory: 目录路径
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"目录不存在: {directory}")
        
        self._watch_dir = directory
        logger.info(f"[Monitor] 设置监控目录: {directory}")
        
        # 预扫描已知文件
        self._scan_known_files()
    
    def on_new_chapter_found(self, callback: Callable[[str], None]):
        """
        注册新章节发现回调
        
        Args:
            callback: 回调函数，接收文件路径参数
                def my_callback(file_path: str):
                    print(f"新章节: {file_path}")
        """
        self._callbacks['new_chapter'].append(callback)
    
    def on_chapter_modified(self, callback: Callable[[str], None]):
        """注册章节修改回调"""
        self._callbacks['chapter_modified'].append(callback)
    
    def on_chapter_deleted(self, callback: Callable[[str], None]):
        """注册章节删除回调"""
        self._callbacks['chapter_deleted'].append(callback)
    
    def on_error(self, callback: Callable[[str], None]):
        """注册错误回调"""
        self._callbacks['error'].append(callback)
    
    def start(self):
        """
        启动监控服务
        在后台线程中运行
        """
        if self._is_running:
            logger.warning("[Monitor] 已经在运行中")
            return
        
        if not self._watch_dir:
            raise RuntimeError("未设置监控目录，请先调用 watch_directory()")
        
        self._is_running = True
        self._stop_event.clear()
        
        # 创建并启动监控线程
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="FileMonitorThread"
        )
        self._thread.start()
        
        logger.info(f"[Monitor] 监控已启动 (间隔: {self._scan_interval}s)")
    
    def stop(self):
        """停止监控服务"""
        if not self._is_running:
            return
        
        self._is_running = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        logger.info("[Monitor] 监控已停止")
    
    def get_new_chapters(self) -> List[str]:
        """
        获取自上次调用后新增的章节
        
        Returns:
            List[str]: 新章节路径列表
        """
        with self._lock:
            chapters = list(self._new_chapters)
            self._new_chapters.clear()
            return chapters
    
    def clear_new_chapters(self):
        """清空新章节队列"""
        with self._lock:
            self._new_chapters.clear()
    
    def scan_once(self) -> List[str]:
        """
        执行一次扫描，返回变化的文件
        
        Returns:
            List[str]: 变化的文件列表
        """
        if not self._watch_dir:
            return []
        
        changes = []
        current_files = {}
        
        try:
            # 扫描所有 .txt 文件
            for root, dirs, files in os.walk(self._watch_dir):
                for filename in files:
                    if not filename.endswith('.txt'):
                        continue
                    
                    filepath = os.path.join(root, filename)
                    stat = os.stat(filepath)
                    mtime = stat.st_mtime
                    
                    current_files[filepath] = mtime
                    
                    # 检查是否是新文件或已修改
                    if filepath not in self._known_files:
                        changes.append(filepath)
                        self._notify_callbacks('new_chapter', filepath)
                        
                        with self._lock:
                            self._new_chapters.append(filepath)
                            
                    elif abs(mtime - self._known_files[filepath]) > 1:
                        # 文件被修改（允许1秒误差）
                        changes.append(filepath)
                        self._notify_callbacks('chapter_modified', filepath)
            
            # 检查删除的文件
            for known_path in list(self._known_files.keys()):
                if known_path not in current_files:
                    changes.append(known_path)
                    self._notify_callbacks('chapter_deleted', known_path)
            
            # 更新已知文件
            self._known_files = current_files
            
        except Exception as e:
            logger.error(f"[Monitor] 扫描出错: {str(e)}", exc_info=True)
            self._notify_callbacks('error', str(e))
        
        return changes
    
    def _monitor_loop(self):
        """监控循环（在后台线程运行）"""
        logger.debug(f"[Monitor] 后台线程启动")
        
        while not self._stop_event.is_set():
            try:
                self.scan_once()
                
            except Exception as e:
                logger.error(f"[Monitor] 循环出错: {str(e)}", exc_info=True)
            
            # 等待下次扫描
            self._stop_event.wait(timeout=self._scan_interval)
        
        logger.debug(f"[Monitor] 后台线程退出")
    
    def _scan_known_files(self):
        """预扫描已知文件"""
        if not self._watch_dir:
            return
        
        for root, dirs, files in os.walk(self._watch_dir):
            for filename in files:
                if filename.endswith('.txt'):
                    filepath = os.path.join(root, filename)
                    try:
                        stat = os.stat(filepath)
                        self._known_files[filepath] = stat.m_time
                    except Exception as e:
                        logger.warning(f"[Monitor] 无法访问文件: {filepath} - {e}")
        
        logger.info(f"[Monitor] 预扫描完成，发现 {len(self._known_files)} 个文件")
    
    def _notify_callbacks(self, event_type: str, data: str):
        """
        通知注册的回调函数
        
        Args:
            event_type: 事件类型 ('new_chapter', 'chapter_modified' 等)
            data: 事件数据（通常是文件路径）
        """
        callbacks = self._callbacks.get(event_type, [])
        
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"[Monitor] 回调执行失败 ({event_type}): {str(e)}", exc_info=True)
    
    def cleanup(self):
        """清理资源"""
        self.stop()
        self._callbacks.clear()
        self._known_files.clear()
        self._new_chapters.clear()
        logger.debug("[Monitor] 资源已清理")


class AutoProcessor(MonitorService):
    """
    自动处理器
    继承 MonitorService，添加自动处理新章节的功能
    """
    
    def __init__(self, scan_interval: float = 5.0):
        super().__init__(scan_interval)
        
        # 处理规则
        self._auto_process_enabled = False
        self._process_rules = []
    
    def enable_auto_process(self, enabled: bool = True):
        """启用/禁用自动处理"""
        self._auto_process_enabled = enabled
        logger.info(f"[AutoProcessor] 自动处理: {'启用' if enabled else '禁用'}")
    
    def add_rule(self, rule: Callable[[str], bool]):
        """
        添加处理规则
        
        Args:
            rule: 处理函数，接收文件路径，返回是否成功处理
                def my_rule(path: str) -> bool:
                    # 处理逻辑...
                    return True
        """
        self._process_rules.append(rule)
    
    def _on_new_file_detected(self, file_path: str):
        """新文件检测到时的处理"""
        if not self._auto_process_enabled:
            return
        
        logger.info(f"[AutoProcessor] 处理新文件: {file_path}")
        
        for rule in self._process_rules:
            try:
                success = rule(file_path)
                if success:
                    logger.info(f"[AutoProcessor] 规则处理成功: {file_path}")
                    
            except Exception as e:
                logger.error(f"[AutoProcessor] 规则执行失败: {str(e)}", exc_info=True)
