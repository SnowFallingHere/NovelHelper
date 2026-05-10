"""
力导向布局计算工作线程
在后台执行网络图的力导向布局算法，不阻塞主线程
"""

import math
import random
from .base_worker import BaseWorker, CancellationException


class LayoutWorker(BaseWorker):
    """力导向布局工作器"""
    
    def __init__(self, nodes, edges, iterations=150):
        super().__init__()
        self.task_name = "图谱布局计算"
        
        self.nodes = nodes  # {name: {'x': x, 'y': y, 'size': s}}
        self.edges = edges  # [(from_name, to_name, type)]
        self.iterations = iterations
        
        # 布局参数
        self.ideal_length = 200.0
        self.repulsion_strength = 50000.0
        self.attraction_strength = 0.01
        self.center_gravity = 0.005
        self.damping = 0.9
    
    def execute(self):
        """执行力导向布局计算"""
        if not self.nodes:
            return {}
        
        # 初始化位置（如果节点没有位置信息）
        positions = {}
        velocities = {}
        node_sizes = {}
        
        for name, data in self.nodes.items():
            if 'x' in data and 'y' in data:
                positions[name] = [float(data['x']), float(data['y'])]
            else:
                # 随机初始位置
                positions[name] = [
                    random.uniform(-300, 300),
                    random.uniform(-300, 300)
                ]
            
            velocities[name] = [0.0, 0.0]
            node_sizes[name] = data.get('size', 80)
        
        # 计算边列表
        edges_list = []
        for from_name, to_name, rel_type in self.edges:
            if from_name in positions and to_name in positions:
                edges_list.append((from_name, to_name))
        
        # 迭代计算
        batch_size = max(1, self.iterations // 15)  # 分成约15批报告进度
        
        for iteration in range(self.iterations):
            self.check_cancelled()
            
            # 报告进度
            if iteration % batch_size == 0 or iteration == self.iterations - 1:
                progress = int((iteration / self.iterations) * 100)
                self.emit_progress(
                    progress,
                    f"布局计算中... ({iteration + 1}/{self.iterations})"
                )
            
            # 计算力
            forces = {name: [0.0, 0.0] for name in positions}
            
            # 斥力（所有节点对之间）
            node_names = list(positions.keys())
            for i in range(len(node_names)):
                for j in range(i + 1, len(node_names)):
                    n1, n2 = node_names[i], node_names[j]
                    
                    x1, y1 = positions[n1]
                    x2, y2 = positions[n2]
                    
                    dx = x1 - x2
                    dy = y1 - y2
                    dist_sq = dx * dx + dy * dy
                    dist = max(math.sqrt(dist_sq), 1.0)
                    
                    # 考虑节点大小，避免重叠
                    min_dist = (node_sizes[n1] + node_sizes[n2]) * 0.6
                    if dist < min_dist:
                        overlap_force = (min_dist - dist) * 3.0
                        fx = overlap_force * dx / dist
                        fy = overlap_force * dy / dist
                        forces[n1][0] += fx
                        forces[n1][1] += fy
                        forces[n2][0] -= fx
                        forces[n2][1] -= fy
                    
                    # 库仑斥力
                    repulsion = self.repulsion_strength / dist_sq
                    fx = repulsion * dx / dist
                    fy = repulsion * dy / dist
                    forces[n1][0] += fx
                    forces[n1][1] += fy
                    forces[n2][0] -= fx
                    forces[n2][1] -= fy
            
            # 引力（连接的节点之间）
            for from_name, to_name in edges_list:
                if from_name not in positions or to_name not in positions:
                    continue
                
                x1, y1 = positions[from_name]
                x2, y2 = positions[to_name]
                
                dx = x2 - x1
                dy = y2 - y1
                dist = max(math.sqrt(dx * dx + dy * dy), 1.0)
                
                # 胡克引力
                attraction = self.attraction_strength * (dist - self.ideal_length)
                fx = attraction * dx / dist
                fy = attraction * dy / dist
                
                forces[from_name][0] += fx
                forces[from_name][1] += fy
                forces[to_name][0] -= fx
                forces[to_name][1] -= fy
            
            # 向心力（拉向中心）
            for name in positions:
                x, y = positions[name]
                forces[name][0] -= self.center_gravity * x
                forces[name][1] -= self.center_gravity * y
            
            # 应用力并更新位置
            max_force = 50.0
            for name in positions:
                fx, fy = forces[name]
                
                # 限制最大力
                force_mag = math.sqrt(fx * fx + fy * fy)
                if force_mag > max_force:
                    fx = fx / force_mag * max_force
                    fy = fy / force_mag * max_force
                
                # 更新速度（带阻尼）
                velocities[name][0] = (velocities[name][0] + fx) * self.damping
                velocities[name][1] = (velocities[name][1] + fy) * self.damping
                
                # 更新位置
                positions[name][0] += velocities[name][0]
                positions[name][1] += velocities[name][1]
            
            # 每隔一段时间发送中间结果（用于实时预览）
            if iteration % 10 == 0:
                intermediate_result = {
                    name: {'x': pos[0], 'y': pos[1]} 
                    for name, pos in positions.items()
                }
                self.result.emit({
                    'type': 'intermediate',
                    'positions': intermediate_result,
                    'iteration': iteration + 1,
                    'total_iterations': self.iterations
                })
        
        # 最终结果
        final_positions = {
            name: {'x': pos[0], 'y': pos[1]} 
            for name, pos in positions.items()
        }
        
        self.emit_progress(100, "布局计算完成")
        
        return {
            'type': 'final',
            'positions': final_positions,
            'iterations_completed': self.iterations
        }


class AnimatedLayoutWorker(LayoutWorker):
    """
    动画式布局工作器
    每次迭代后都发送更新，支持平滑动画效果
    """
    
    def __init__(self, nodes, edges, iterations=150, update_interval=5):
        super().__init__(nodes, edges, iterations)
        self.task_name = "动画布局计算"
        self.update_interval = update_interval  # 每 N 次迭代更新一次
    
    def execute(self):
        """执行带动画效果的布局"""
        if not self.nodes:
            return {}
        
        # 初始化
        positions = {}
        velocities = {}
        node_sizes = {}
        
        for name, data in self.nodes.items():
            if 'x' in data and 'y' in data:
                positions[name] = [float(data['x']), float(data['y'])]
            else:
                positions[name] = [
                    random.uniform(-300, 300),
                    random.uniform(-300, 300)
                ]
            velocities[name] = [0.0, 0.0]
            node_sizes[name] = data.get('size', 80)
        
        edges_list = [(f, t) for f, t, _ in self.edges 
                      if f in positions and t in positions]
        
        for iteration in range(self.iterations):
            self.check_cancelled()
            
            # 执行一次迭代
            positions, velocities = self._single_iteration(
                positions, velocities, edges_list, node_sizes
            )
            
            # 发送更新（用于动画）
            if iteration % self.update_interval == 0:
                progress = int((iteration / self.iterations) * 100)
                
                intermediate = {
                    name: {'x': pos[0], 'y': pos[1]} 
                    for name, pos in positions.items()
                }
                
                self.result.emit({
                    'type': 'animation_frame',
                    'positions': intermediate,
                    'progress': progress,
                    'iteration': iteration
                })
                
                self.emit_progress(progress, f"布局中 ({iteration + 1}/{self.iterations})")
                
                # 让出CPU时间，使动画更流畅
                self.msleep(20)
        
        # 最终结果
        final_positions = {
            name: {'x': pos[0], 'y': pos[1]} 
            for name, pos in positions.items()
        }
        
        self.emit_progress(100, "完成")
        
        return {
            'type': 'final',
            'positions': final_positions
        }
    
    def _single_iteration(self, positions, velocities, edges_list, node_sizes):
        """执行单次迭代"""
        forces = {name: [0.0, 0.0] for name in positions}
        
        # 斥力
        names = list(positions.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                n1, n2 = names[i], names[j]
                x1, y1 = positions[n1]
                x2, y2 = positions[n2]
                dx, dy = x1 - x2, y1 - y2
                dist_sq = dx * dx + dy * dy
                dist = max(math.sqrt(dist_sq), 1.0)
                
                min_dist = (node_sizes[n1] + node_sizes[n2]) * 0.6
                if dist < min_dist:
                    overlap = (min_dist - dist) * 3.0
                    fx, fy = overlap * dx / dist, overlap * dy / dist
                    forces[n1][0] += fx; forces[n1][1] += fy
                    forces[n2][0] -= fx; forces[n2][1] -= fy
                
                rep = self.repulsion_strength / dist_sq
                forces[n1][0] += rep * dx / dist
                forces[n1][1] += rep * dy / dist
                forces[n2][0] -= rep * dx / dist
                forces[n2][1] -= rep * dy / dist
        
        # 引力
        for f, t in edges_list:
            if f not in positions or t not in positions:
                continue
            x1, y1 = positions[f]
            x2, y2 = positions[t]
            dx, dy = x2 - x1, y2 - y1
            dist = max(math.sqrt(dx*dx + dy*dy), 1.0)
            attr = self.attraction_strength * (dist - self.ideal_length)
            forces[f][0] += attr * dx / dist
            forces[f][1] += attr * dy / dist
            forces[t][0] -= attr * dx / dist
            forces[t][1] -= attr * dy / dist
        
        # 向心力和阻尼
        for name in positions:
            x, y = positions[name]
            forces[name][0] -= self.center_gravity * x
            forces[name][1] -= self.center_gravity * y
            
            fx, fy = forces[name]
            mag = math.sqrt(fx*fx + fy*fy)
            if mag > 50:
                fx, fy = fx/mag*50, fy/mag*50
            
            velocities[name][0] = (velocities[name][0] + fx) * self.damping
            velocities[name][1] = (velocities[name][1] + fy) * self.damping
            positions[name][0] += velocities[name][0]
            positions[name][1] += velocities[name][1]
        
        return positions, velocities
