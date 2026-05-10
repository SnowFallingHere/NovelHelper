"""
统一的工作线程基类
所有后台任务都继承此类，确保：
- 线程安全
- 可取消
- 进度报告
- 错误处理
"""

from PyQt5.QtCore import QThread, pyqtSignal, QObject
import time
import logging

logger = logging.getLogger(__name__)


class BaseWorker(QThread):
    """
    工作线程基类
    
    信号:
        - started: 任务开始
        - progress(int): 进度更新 (0-100)
        - status(str): 状态文本更新
        - finished: 任务成功完成
        - result(any): 返回结果数据
        - error(str): 发生错误
        - cancelled: 任务被取消
    """
    
    # 定义信号
    started = pyqtSignal()
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal()
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    cancelled = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._is_cancelled = False
        self._is_running = False
        self._task_name = "未知任务"
    
    @property
    def task_name(self):
        return self._task_name
    
    @task_name.setter
    def task_name(self, name):
        self._task_name = name
    
    def run(self):
        """主执行方法（子类不应重写此方法）"""
        self._is_running = True
        self._is_cancelled = False
        
        logger.info(f"[{self._task_name}] 开始执行")
        self.started.emit()
        
        try:
            # 调用子类实现的 execute 方法
            data = self.execute()
            
            if not self._is_cancelled:
                logger.info(f"[{self._task_name}] 执行完成")
                self.result.emit(data)
                self.finished.emit()
        except Exception as e:
            logger.error(f"[{self._task_name}] 执行出错: {str(e)}", exc_info=True)
            self.error.emit(str(e))
        finally:
            self._is_running = False
    
    def execute(self):
        """
        子类必须实现此方法
        返回: 结果数据
        """
        raise NotImplementedError("子类必须实现 execute() 方法")
    
    def cancel(self):
        """取消任务"""
        self._is_cancelled = True
        logger.info(f"[{self._task_name}] 收到取消请求")
    
    @property
    def is_cancelled(self):
        return self._is_cancelled
    
    @property
    def is_running(self):
        return self._is_running
    
    def check_cancelled(self):
        """检查是否被取消，用于在长时间循环中检查点"""
        if self._is_cancelled:
            self.cancelled.emit()
            raise CancellationException("任务被用户取消")
    
    def emit_progress(self, value, status_text=None):
        """发送进度更新"""
        self.progress.emit(value)
        if status_text:
            self.status.emit(status_text)
        
        # 让出CPU，保持UI响应
        self.msleep(1)


class CancellationException(Exception):
    """任务取消异常"""
    pass


class WorkerManager(QObject):
    """
    工作线程管理器
    统一管理所有后台任务的生命周期
    """
    
    task_started = pyqtSignal(str)  # 任务名称
    task_finished = pyqtSignal(str, object)  # 任务名称, 结果
    task_error = pyqtSignal(str, str)  # 任务名称, 错误信息
    global_progress = pyqtSignal(int)  # 全局进度 (0-100)
    global_status = pyqtSignal(str)  # 全局状态文本
    
    def __init__(self):
        super().__init__()
        self._workers = {}  # {worker_id: worker}
        self._current_worker_id = None
    
    def start_worker(self, worker_id, worker):
        """
        启动一个工作线程
        
        Args:
            worker_id: 工作线程唯一标识
            worker: BaseWorker 实例
        """
        # 如果有正在运行的任务，先停止
        if self._current_worker_id and self._current_worker_id in self._workers:
            old_worker = self._workers[self._current_worker_id]
            if old_worker.isRunning():
                old_worker.cancel()
                old_worker.wait(3000)  # 等待最多3秒
        
        # 连接信号
        worker.started.connect(lambda: self._on_worker_started(worker_id))
        worker.finished.connect(lambda: self._on_worker_finished(worker_id))
        worker.result.connect(lambda data: self._on_worker_result(worker_id, data))
        worker.error.connect(lambda err: self._on_worker_error(worker_id, err))
        worker.progress.connect(self.global_progress.emit)
        worker.status.connect(self.global_status.emit)
        
        # 存储并启动
        self._workers[worker_id] = worker
        self._current_worker_id = worker_id
        worker.start()
        
        logger.info(f"启动后台任务: {worker_id}")
    
    def cancel_worker(self, worker_id=None):
        """取消指定或当前任务"""
        target_id = worker_id or self._current_worker_id
        if target_id and target_id in self._workers:
            worker = self._workers[target_id]
            if worker.isRunning():
                worker.cancel()
                logger.info(f"取消后台任务: {target_id}")
    
    def _on_worker_started(self, worker_id):
        self.task_started.emit(worker_id)
    
    def _on_worker_finished(self, worker_id):
        if worker_id == self._current_worker_id:
            self._current_worker_id = None
        logger.info(f"后台任务完成: {worker_id}")
    
    def _on_worker_result(self, worker_id, data):
        self.task_finished.emit(worker_id, data)
    
    def _on_worker_error(self, worker_id, error_msg):
        self.task_error.emit(worker_id, error_msg)
        logger.error(f"后台任务错误 [{worker_id}]: {error_msg}")
    
    def cleanup(self):
        """清理所有工作线程"""
        for worker_id, worker in self._workers.items():
            if worker.isRunning():
                worker.cancel()
                worker.wait(2000)
        self._workers.clear()


# 全局单例实例
_global_worker_manager = None

def get_worker_manager():
    """获取全局工作管理器实例"""
    global _global_worker_manager
    if _global_worker_manager is None:
        _global_worker_manager = WorkerManager()
    return _global_worker_manager
