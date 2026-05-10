"""
任务调度器
统一管理所有后台任务，支持：
- 任务队列
- 优先级调度
- 并发控制
- 任务依赖
"""

from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import threading
from collections import deque
import logging

from .base_worker import BaseWorker, get_worker_manager

logger = logging.getLogger(__name__)


class TaskScheduler(QObject):
    """
    任务调度器
    
    功能：
    - 管理任务队列
    - 控制并发数量
    - 支持任务优先级
    - 任务状态跟踪
    """
    
    # 信号
    task_queued = pyqtSignal(str, str)  # task_id, description
    task_started = pyqtSignal(str)  # task_id
    task_completed = pyqtSignal(str, object)  # task_id, result
    task_failed = pyqtSignal(str, str)  # task_id, error
    queue_changed = pyqtSignal(int)  # queue_size
    all_tasks_finished = pyqtSignal()
    
    # 任务优先级
    PRIORITY_HIGH = 1
    PRIORITY_NORMAL = 2
    PRIORITY_LOW = 3
    
    def __init__(self, max_concurrent=2):
        super().__init__()
        
        self._max_concurrent = max_concurrent  # 最大并发数
        self._running_tasks = {}  # {task_id: worker}
        self._task_queue = deque()  # 待执行队列 [(priority, task_id, worker)]
        self._completed_tasks = []  # 已完成任务
        self._failed_tasks = []  # 失败任务
        
        self._worker_manager = get_worker_manager()
        self._lock = threading.Lock()
        self._task_counter = 0
        
        # 自动处理队列的定时器
        self._queue_timer = QTimer(self)
        self._queue_timer.timeout.connect(self._process_queue)
        self._queue_timer.start(100)  # 每100ms检查一次队列
    
    def submit_task(self, worker, priority=PRIORITY_NORMAL, task_id=None):
        """
        提交任务到队列
        
        Args:
            worker: BaseWorker 实例
            priority: 优先级 (PRIORITY_HIGH/NORMAL/LOW)
            task_id: 可选的任务ID（自动生成如果未提供）
        
        Returns:
            str: 任务ID
        """
        if task_id is None:
            self._task_counter += 1
            task_id = f"task_{self._task_counter}"
        
        with self._lock:
            # 按优先级插入队列
            entry = (priority, task_id, worker)
            
            # 找到合适的位置插入（按优先级排序）
            inserted = False
            for i, existing in enumerate(self._task_queue):
                if existing[0] > priority:
                    self._task_queue.insert(i, entry)
                    inserted = True
                    break
            
            if not inserted:
                self._task_queue.append(entry)
        
        logger.info(f"任务已入队: {task_id} (优先级: {priority}, 队列大小: {len(self._task_queue)})")
        
        self.task_queued.emit(task_id, worker.task_name)
        self.queue_changed.emit(len(self._task_queue))
        
        return task_id
    
    def submit_immediate(self, worker, task_id=None):
        """
        提交高优先级任务（立即执行，可能取消低优先级任务）
        """
        return self.submit_task(worker, self.PRIORITY_HIGH, task_id)
    
    def _process_queue(self):
        """处理任务队列"""
        with self._lock:
            # 检查是否有空位
            if len(self._running_tasks) >= self._max_concurrent:
                return
            
            # 从队列取任务
            if not self._task_queue:
                # 检查是否所有任务都完成了
                if not self._running_tasks and not self._task_queue:
                    self.all_tasks_finished.emit()
                return
            
            priority, task_id, worker = self._task_queue.popleft()
        
        # 启动任务
        logger.info(f"开始执行任务: {task_id}")
        
        with self._lock:
            self._running_tasks[task_id] = worker
        
        # 连接信号
        worker.finished.connect(lambda: self._on_task_completed(task_id))
        worker.result.connect(lambda data: self._on_task_result(task_id, data))
        worker.error.connect(lambda err: self._on_task_failed(task_id, err))
        
        self.task_started.emit(task_id)
        self.queue_changed.emit(len(self._task_queue))
        
        # 启动工作线程
        worker.start()
    
    def _on_task_completed(self, task_id):
        """任务完成回调"""
        with self._lock:
            if task_id in self._running_tasks:
                worker = self._running_tasks.pop(task_id)
                self._completed_tasks.append({
                    'id': task_id,
                    'worker': worker.task_name,
                    'status': 'success'
                })
        
        logger.info(f"任务完成: {task_id}")
    
    def _on_task_result(self, task_id, result):
        """任务结果回调"""
        self.task_completed.emit(task_id, result)
    
    def _on_task_failed(self, task_id, error):
        """任务失败回调"""
        with self._lock:
            if task_id in self._running_tasks:
                self._running_tasks.pop(task_id)
                self._failed_tasks.append({
                    'id': task_id,
                    'error': error
                })
        
        logger.error(f"任务失败: {task_id} - {error}")
        self.task_failed.emit(task_id, error)
    
    def cancel_task(self, task_id):
        """取消指定任务"""
        with self._lock:
            # 检查是否在运行中
            if task_id in self._running_tasks:
                worker = self._running_tasks[task_id]
                worker.cancel()
                return True
            
            # 检查是否在队列中
            for i, (priority, tid, worker) in enumerate(self._task_queue):
                if tid == task_id:
                    del self._task_queue[i]
                    self.queue_changed.emit(len(self._task_queue))
                    return True
        
        return False
    
    def cancel_all(self):
        """取消所有任务"""
        with self._lock:
            # 取消运行中的任务
            for task_id, worker in list(self._running_tasks.items()):
                worker.cancel()
            
            # 清空队列
            self._task_queue.clear()
            self.queue_changed.emit(0)
        
        logger.info("已取消所有任务")
    
    @property
    def queue_size(self):
        """待执行队列大小"""
        with self._lock:
            return len(self._task_queue)
    
    @property
    def running_count(self):
        """正在运行的任务数"""
        with self._lock:
            return len(self._running_tasks)
    
    @property
    def is_idle(self):
        """是否空闲（无运行和排队任务）"""
        return self.queue_size == 0 and self.running_count == 0
    
    def get_status(self):
        """获取调度器状态"""
        with self._lock:
            return {
                'queued': len(self._task_queue),
                'running': len(self._running_tasks),
                'completed': len(self._completed_tasks),
                'failed': len(self._failed_tasks),
                'max_concurrent': self._max_concurrent
            }
    
    def clear_history(self):
        """清除历史记录"""
        with self._lock:
            self._completed_tasks.clear()
            self._failed_tasks.clear()


class AsyncTaskHelper:
    """
    异步任务辅助类
    提供便捷的方法来创建和提交常见任务
    """
    
    def __init__(self):
        self.scheduler = TaskScheduler()
    
    def run_frequency_analysis(self, file_paths=None, novel_dir=None, callback=None):
        """
        运行词频分析（异步）
        
        Args:
            file_paths: 文件路径列表
            novel_dir: 小说目录（与file_paths二选一）
            callback: 完成回调 function(result)
        
        Returns:
            str: 任务ID
        """
        from .frequency_worker import FrequencyWorker
        
        worker = FrequencyWorker(
            file_paths=file_paths,
            novel_dir=novel_dir
        )
        
        task_id = self.scheduler.submit_task(worker)
        
        if callback:
            def on_result(data):
                callback(data)
            worker.result.connect(on_result)
        
        return task_id
    
    def run_layout_calculation(self, nodes, edges, iterations=150, callback=None):
        """
        运行布局计算（异步）
        
        Returns:
            str: 任务ID
        """
        from .layout_worker import LayoutWorker
        
        worker = LayoutWorker(nodes, edges, iterations)
        task_id = self.scheduler.submit_task(worker)
        
        if callback:
            worker.result.connect(callback)
        
        return task_id
    
    def run_file_scan(self, base_dir, callback=None):
        """
        运行文件扫描（异步）
        
        Returns:
            str: 任务ID
        """
        from .file_scanner_worker import FileScannerWorker
        
        worker = FileScannerWorker(base_dir=base_dir)
        task_id = self.scheduler.submit_task(worker)
        
        if callback:
            worker.result.connect(callback)
        
        return task_id
    
    def run_content_analysis(self, file_paths, callback=None):
        """
        运行内容分析（异步）
        
        Returns:
            str: 任务ID
        """
        from .file_scanner_worker import ContentAnalyzer
        
        worker = ContentAnalyzer(file_paths)
        task_id = self.scheduler.submit_task(worker)
        
        if callback:
            worker.result.connect(callback)
        
        return task_id


# 全局实例
_async_helper = None

def get_async_helper():
    """获取全局异步助手实例"""
    global _async_helper
    if _async_helper is None:
        _async_helper = AsyncTaskHelper()
    return _async_helper
