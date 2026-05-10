"""
多线程架构使用示例
展示如何将现有代码迁移到默认多线程模式
"""

from PyQt5.QtCore import (
    Qt
)
from PyQt5.QtWidgets import QProgressDialog, QApplication
from workers import (
    FrequencyWorker,
    LayoutWorker, 
    FileScannerWorker,
    TaskScheduler,
    get_async_helper
)
import logging

logger = logging.getLogger(__name__)


class MultiThreadedNovelHelperMixin:
    """
    多线程小说助手混入类
    提供便捷的方法来执行耗时操作
    """
    
    def __init__(self):
        # 初始化任务调度器
        self._task_scheduler = TaskScheduler(max_concurrent=3)
        
        # 异步助手
        self._async_helper = get_async_helper()
    
    # ============================================================
    # 词频分析（异步）
    # ============================================================
    
    def run_frequency_analysis_async(self, novel_dir=None, callback=None):
        """
        异步运行词频分析
        
        使用方法:
            self.run_frequency_analysis_async(
                novel_dir=get_novel_dir(),
                callback=self._on_frequency_complete
            )
        """
        worker = FrequencyWorker(novel_dir=novel_dir)
        
        # 创建进度对话框
        progress = QProgressDialog("正在分析词频...", "取消", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(500)  # 超过500ms才显示
        progress.show()
        
        # 连接信号
        worker.progress.connect(progress.setValue)
        worker.status.connect(lambda text: progress.setLabelText(text))
        worker.finished.connect(lambda: progress.close())
        worker.error.connect(lambda err: (progress.close(), logger.error(err)))
        worker.cancelled.connect(progress.close)
        
        # 取消按钮连接
        progress.canceled.connect(worker.cancel)
        
        # 完成回调
        if callback:
            worker.result.connect(callback)
        
        # 启动任务
        task_id = self._task_scheduler.submit_task(worker)
        
        logger.info(f"词频分析已启动（异步）: {task_id}")
        return task_id
    
    # ============================================================
    # 图谱布局计算（异步）
    # ============================================================
    
    def build_graph_async(self, keywords, freq_data=None):
        """
        异步构建网络图（带布局动画）
        
        使用方法:
            result = self.build_graph_async(keywords, freq_data)
        """
        if not keywords:
            return
        
        # 准备节点数据
        nodes_data = {}
        for kw in keywords:
            name = kw.get('name', '?')
            t = kw.get('type', 'custom')
            
            # 读取缓存位置或生成随机位置
            saved_pos = self.network_graph_view.load_node_positions()
            if name in saved_pos:
                x, y = saved_pos[name]
            else:
                import random
                x = random.uniform(-300, 300)
                y = random.uniform(-300, 300)
            
            nodes_data[name] = {
                'x': x,
                'y': y,
                'size': 80,  # 将由 _effective_size 计算
                'type': t
            }
        
        # 准备边数据
        edges_data = []
        for kw in keywords:
            name = kw.get('name')
            if not name:
                continue
            for rel in kw.get('relationships', []):
                target = rel.get('target')
                if target in nodes_data:
                    edges_data.append((name, target, rel.get('type', 'related_to')))
        
        # 创建布局工作器（使用动画版本）
        from workers.layout_worker import AnimatedLayoutWorker
        
        worker = AnimatedLayoutWorker(
            nodes=nodes_data,
            edges=edges_data,
            iterations=150
        )
        
        # 显示进度对话框
        progress = QProgressDialog(
            "正在构建网络图...",
            "取消",
            0, 
            100, 
            self
        )
        progress.setWindowTitle("神经网络图")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        # 连接信号 - 支持实时预览
        worker.progress.connect(progress.setValue)
        worker.status.connect(lambda text: progress.setLabelText(text))
        
        @worker.result.connect
        def on_layout_update(data):
            """接收布局中间结果/最终结果"""
            if data.get('type') == 'animation_frame':
                # 更新节点位置（动画效果）
                positions = data['positions']
                for name, pos in positions.items():
                    if name in self.network_graph_view.node_items:
                        item = self.network_graph_view.node_items[name]['item']
                        item.setPos(pos['x'], pos['y'])
                
                # 强制刷新显示
                self.network_graph_view.scene.update()
                QApplication.processEvents()
                
            elif data.get('type') == 'final':
                # 最终结果，保存位置
                positions = data['positions']
                for name, pos in positions.items():
                    if name in self.network_graph_view.node_items:
                        item = self.network_graph_view.node_items[name]['item']
                        item.setPos(pos['x'], pos['y'])
                
                self.network_graph_view.save_node_positions()
                self.network_graph_view._center_graph()
        
        worker.finished.connect(progress.close)
        worker.error.connect(lambda err: (progress.close(), logger.error(f"布局错误: {err}")))
        worker.cancelled.connect(progress.close)
        progress.canceled.connect(worker.cancel)
        
        # 先构建基础图形（无布局）
        self.network_graph_view.build_graph(keywords, freq_data, skip_layout=True)
        
        # 启动后台布局计算
        task_id = self._task_scheduler.submit_immediate(worker)
        
        logger.info(f"图谱布局计算已启动（异步）: {task_id}")
        return task_id
    
    # ============================================================
    # 文件扫描（异步）
    # ============================================================
    
    def scan_chapters_async(self, base_dir, callback=None):
        """
        异步扫描章节目录
        
        Returns:
            str: 任务ID
        """
        worker = FileScannerWorker(base_dir=base_dir)
        
        if callback:
            worker.result.connect(callback)
        
        task_id = self._task_scheduler.submit_task(
            worker, 
            priority=TaskScheduler.PRIORITY_HIGH  # 文件扫描优先级高
        )
        
        logger.info(f"章节扫描已启动（异步）: {task_id}")
        return task_id
    
    # ============================================================
    # 内容分析（异步）
    # ============================================================
    
    def analyze_content_async(self, file_paths, callback=None):
        """
        异步分析内容统计
        
        返回:
            字数、对话比例、段落长度等统计数据
        """
        from workers.file_scanner_worker import ContentAnalyzer
        
        worker = ContentAnalyzer(file_paths)
        
        if callback:
            worker.result.connect(callback)
        
        task_id = self._task_scheduler.submit_task(worker)
        
        logger.info(f"内容分析已启动（异步）: {task_id}")
        return task_id


# ============================================================
# 使用示例
# ============================================================

class ExampleUsage:
    """展示如何在代码中使用多线程功能"""
    
    def __init__(self):
        # 假设这是 NovelHelper 的 __init__
        super().__init__()
        
        # 混入多线程支持
        MultiThreadedNovelHelperMixin.__init__(self)
    
    def on_click_refresh_keywords(self):
        """刷新关键词时使用异步词频分析"""
        from core.file_manager import get_novel_dir, get_novel_config_dir
        
        novel_dir = get_novel_dir()
        
        # 显示加载提示
        self.status_bar.showMessage("正在分析词频...")
        
        # 异步执行
        self.run_frequency_analysis_async(
            novel_dir=novel_dir,
            callback=self._on_frequency_analysis_complete
        )
    
    def _on_frequency_analysis_complete(self, result):
        """词频分析完成回调（主线程中执行）"""
        words_data = result.get('words', {})
        
        # 更新UI（安全，因为在主线程）
        self.keyword_list_text.clear()
        
        for word, info in sorted(words_data.items(), 
                                  key=lambda x: x[1].get('total_occurrences', 0), 
                                  reverse=True)[:100]:
            count = info.get('total_occurrences', 0)
            line = f"【{word}】 出现 {count} 次\n"
            self.keyword_list_text.append(line)
        
        # 保存结果
        freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
        with open(freq_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        self.status_bar.showMessage(f"词频分析完成: {len(words_data)} 个关键词")
        logger.info(f"词频分析完成，发现 {len(words_data)} 个关键词")
    
    def on_show_neural_graph(self):
        """显示神经图时使用异步布局"""
        keywords = keyword_manager.load_keywords()
        
        if not keywords:
            return
        
        # 加载已有频率数据
        freq_file = os.path.join(get_novel_config_dir(), ".frequency.json")
        freq_data = None
        if os.path.exists(freq_file):
            with open(freq_file, 'r', encoding='utf-8') as f:
                freq_data = json.load(f)
        
        # 异步构建图谱
        self.build_graph_async(keywords, freq_data)


# ============================================================
# 全局配置：启用默认多线程模式
# ============================================================

ENABLE_MULTI_THREADING_BY_DEFAULT = True

def is_multi_threading_enabled():
    """检查是否启用了默认多线程模式"""
    return ENABLE_MULTI_THREADING_BY_DEFAULT
