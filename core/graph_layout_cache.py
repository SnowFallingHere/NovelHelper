"""
图谱布局缓存优化系统
提供高效的节点位置缓存、增量更新和智能布局恢复功能

功能：
- 节点位置持久化（保存/加载手动调整的布局）
- 增量更新（只重新计算新增/删除的节点）
- 布局快照（支持多版本布局）
- 布局验证和修复
- 自动备份机制

使用示例：
    cache = GraphLayoutCache()
    
    # 保存当前布局
    cache.save_layout(nodes, edges, 'manual_layout_v1')
    
    # 加载布局
    positions = cache.load_layout('manual_layout_v1')
    
    # 增量更新（添加新节点）
    new_positions = cache.incremental_update(
        existing_positions, 
        new_nodes, 
        removed_nodes
    )
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Set
from copy import deepcopy

logger = logging.getLogger(__name__)


class GraphLayoutCache:
    """
    图谱布局缓存类
    
    缓存结构（JSON格式）：
    {
        'version': str,
        'created_at': str,
        'last_modified': str,
        
        'layouts': {
            layout_name: {
                'timestamp': str,
                'node_positions': {
                    node_name: {'x': float, 'y': float}
                },
                'metadata': {
                    'total_nodes': int,
                    'total_edges': int,
                    'graph_hash': str  # 用于检测图结构变化
                }
            }
        },
        
        'active_layout': str,  # 当前使用的布局名
        
        'settings': {
            'auto_save': bool,
            'max_snapshots': int,
            'backup_interval': int
        }
    }
    """
    
    CACHE_VERSION = "2.0"
    DEFAULT_LAYOUT_NAME = "default"
    MAX_SNAPSHOTS = 5  # 最大快照数量
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        初始化图谱布局缓存
        
        Args:
            cache_dir: 缓存目录路径（默认使用项目根目录）
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # 默认使用项目根目录
            from core.file_manager import get_base_dir
            self.cache_dir = Path(get_base_dir())
        
        self.cache_file = self.cache_dir / "graph_layout_cache.json"
        self.backup_dir = self.cache_dir / "graph_layout_backups"
        
        self._cache_data: Dict[str, Any] = {}
        self._dirty = False
        
        logger.debug(f"[GraphLayoutCache] 初始化: {self.cache_dir}")
        
        if self.cache_file.exists():
            self._load_cache()
        
        # 确保备份目录存在
        self.backup_dir.mkdir(exist_ok=True)
    
    def _load_cache(self) -> bool:
        """加载缓存"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('version') != self.CACHE_VERSION:
                logger.warning("[GraphLayoutCache] 版本不兼容，将重建")
                return False
            
            self._cache_data = data
            layouts = data.get('layouts', {})
            active = data.get('active_layout', self.DEFAULT_LAYOUT_NAME)
            
            logger.info(
                f"[GraphLayoutCache] 已加载缓存 "
                f"(共{len(layouts)}个布局，活跃: {active})"
            )
            return True
            
        except Exception as e:
            logger.error(f"[GraphLayoutCache] 加载失败: {e}")
            return False
    
    def _save_cache(self) -> bool:
        """保存缓存"""
        if not self._dirty:
            return True
        
        try:
            self._cache_data['last_modified'] = datetime.now().isoformat()
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache_data, f, ensure_ascii=False, indent=2)
            
            self._dirty = False
            logger.debug("[GraphLayoutCache] 缓存已保存")
            return True
            
        except Exception as e:
            logger.error(f"[GraphLayoutCache] 保存失败: {e}")
            return False
    
    def save_layout(
        self,
        node_positions: Dict[str, Tuple[float, float]],
        layout_name: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        保存节点布局
        
        Args:
            node_positions: 节点位置字典 {node_name: (x, y)}
            layout_name: 布局名称（默认为 'default'）
            metadata: 额外的元数据
            
        Returns:
            bool: 是否成功
        """
        if not node_positions:
            logger.warning("[GraphLayoutCache] 空的节点位置数据")
            return False
        
        name = layout_name or self.DEFAULT_LAYOUT_NAME
        
        # 构建位置数据
        positions_data = {}
        for node_name, (x, y) in node_positions.items():
            positions_data[node_name] = {
                'x': round(x, 2),
                'y': round(y, 2)
            }
        
        # 计算图的哈希值（用于检测结构变化）
        graph_hash = self._compute_graph_hash(positions_data)
        
        # 创建布局记录
        layout_record = {
            'timestamp': datetime.now().isoformat(),
            'node_positions': positions_data,
            'metadata': {
                **(metadata or {}),
                'total_nodes': len(positions_data),
                'graph_hash': graph_hash
            }
        }
        
        # 更新缓存
        layouts = self._cache_data.setdefault('layouts', {})
        layouts[name] = layout_record
        self._cache_data['active_layout'] = name
        self._dirty = True
        
        # 自动备份
        settings = self._cache_data.get('settings', {})
        if settings.get('auto_save', True):
            self._create_backup(name)
        
        result = self._save_cache()
        
        if result:
            logger.info(
                f"[GraphLayoutCache] 已保存布局 '{name}' "
                f"({len(positions_data)}个节点)"
            )
        
        return result
    
    def load_layout(
        self, 
        layout_name: Optional[str] = None
    ) -> Optional[Dict[str, Tuple[float, float]]]:
        """
        加载节点布局
        
        Args:
            layout_name: 布局名称（默认使用活跃布局）
            
        Returns:
            Dict[(x, y)] 或 None
        """
        name = layout_name or self._cache_data.get('active_layout', self.DEFAULT_LAYOUT_NAME)
        
        layout = self._cache_data.get('layouts', {}).get(name)
        if not layout:
            logger.warning(f"[GraphLayoutCache] 未找到布局: {name}")
            return None
        
        positions = {}
        for node_name, pos in layout.get('node_positions', {}).items():
            positions[node_name] = (pos['x'], pos['y'])
        
        logger.info(
            f"[GraphLayoutCache] 已加载布局 '{name}' "
            f"({len(positions)}个节点)"
        )
        
        return positions
    
    def get_active_layout_name(self) -> str:
        """获取当前活跃布局名称"""
        return self._cache_data.get('active_layout', self.DEFAULT_LAYOUT_NAME)
    
    def list_layouts(self) -> List[Dict[str, Any]]:
        """
        列出所有已保存的布局
        
        Returns:
            List[Dict]: 布局信息列表
        """
        layouts_info = []
        
        for name, layout in self._cache_data.get('layouts', {}).items():
            meta = layout.get('metadata', {})
            layouts_info.append({
                'name': name,
                'timestamp': layout.get('timestamp', ''),
                'node_count': meta.get('total_nodes', 0),
                'is_active': name == self._cache_data.get('active_layout')
            })
        
        # 按时间倒序排列
        layouts_info.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return layouts_info
    
    def delete_layout(self, layout_name: str) -> bool:
        """
        删除指定布局
        
        Args:
            layout_name: 布局名称
            
        Returns:
            bool: 是否成功
        """
        if layout_name == self.DEFAULT_LAYOUT_NAME:
            logger.error("[GraphLayoutCache] 不能删除默认布局")
            return False
        
        if layout_name in self._cache_data.get('layouts', {}):
            del self._cache_data['layouts'][layout_name]
            self._dirty = True
            self._save_cache()
            logger.info(f"[GraphLayoutCache] 已删除布局: {layout_name}")
            return True
        
        return False
    
    def incremental_update(
        self,
        current_positions: Dict[str, Tuple[float, float]],
        added_nodes: Set[str],
        removed_nodes: Set[str],
        strategy: str = "spread"
    ) -> Dict[str, Tuple[float, float]]:
        """
        增量更新布局（只计算变化的部分）
        
        Args:
            current_positions: 当前所有节点的位置
            added_nodes: 新增的节点集合
            removed_nodes: 被移除的节点集合
            strategy: 新节点放置策略 ('spread', 'center', 'random')
            
        Returns:
            Dict[(x, y)] 更新后的位置
        """
        updated_positions = deepcopy(current_positions)
        
        # 移除被删除的节点
        for node in removed_nodes:
            if node in updated_positions:
                del updated_positions[node]
        
        # 为新增节点计算位置
        if added_nodes and updated_positions:
            # 计算现有节点的边界
            xs = [p[0] for p in updated_positions.values()]
            ys = [p[1] for p in updated_positions.values()]
            
            center_x = sum(xs) / len(xs)
            center_y = sum(ys) / len(ys)
            
            # 根据策略放置新节点
            import math
            radius = max(abs(max(xs) - min(xs)), abs(max(ys) - min(ys))) * 0.6
            
            for i, node in enumerate(added_nodes):
                if strategy == "spread":
                    # 均匀分布在边缘
                    angle = 2 * math.pi * i / len(added_nodes)
                    x = center_x + radius * math.cos(angle)
                    y = center_y + radius * math.sin(angle)
                    
                elif strategy == "center":
                    # 在中心附近随机偏移
                    offset = radius * 0.3
                    x = center_x + (i % 2 - 0.5) * offset
                    y = center_y + (i // 2 - 0.5) * offset
                    
                else:  # random
                    x = center_x + (i % 7 - 3) * radius * 0.4
                    y = center_y + (i // 7 - 1) * radius * 0.4
                
                updated_positions[node] = (round(x, 2), round(y, 2))
        
        elif added_nodes and not updated_positions:
            # 第一个节点放在原点
            for node in added_nodes:
                updated_positions[node] = (0.0, 0.0)
        
        logger.info(
            f"[GraphLayoutCache] 增量更新完成 "
            f"(+{len(added_nodes)}, -{len(removed_nodes)})"
        )
        
        return updated_positions
    
    def validate_layout(
        self, 
        layout_name: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        验证布局的有效性
        
        检查项：
        - 是否有重复位置
        - 是否有NaN或Inf坐标
        - 节点是否过于密集
        
        Args:
            layout_name: 布局名称
            
        Returns:
            (is_valid, issues) 是否有效及问题列表
        """
        positions = self.load_layout(layout_name)
        if not positions:
            return False, ["布局不存在"]
        
        issues = []
        seen_positions = set()
        
        for node_name, (x, y) in positions.items():
            # 检查无效坐标
            if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
                issues.append(f"节点 '{node_name}' 的坐标类型错误")
                continue
            
            if math.isnan(x) or math.isnan(y) or math.isinf(x) or math.isinf(y):
                issues.append(f"节点 '{node_name}' 的坐标包含 NaN 或 Inf")
                continue
            
            # 检查重复位置（允许一定误差）
            pos_key = (round(x, 1), round(y, 1))
            if pos_key in seen_positions:
                issues.append(f"节点 '{node_name}' 与其他节点位置过于接近")
            seen_positions.add(pos_key)
        
        is_valid = len(issues) == 0
        
        if not is_valid:
            logger.warning(f"[GraphLayoutCache] 布局验证发现 {len(issues)} 个问题")
        
        return is_valid, issues
    
    def repair_layout(
        self, 
        layout_name: Optional[str] = None
    ) -> bool:
        """
        尝试修复布局问题
        
        Args:
            layout_name: 布局名称
            
        Returns:
            bool: 是否成功修复
        """
        import math
        positions = self.load_layout(layout_name)
        if not positions:
            return False
        
        repaired = False
        fixed_positions = {}
        
        for node_name, (x, y) in positions.items():
            # 修复无效坐标
            if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
                fixed_positions[node_name] = (0.0, 0.0)
                repaired = True
                continue
            
            if math.isnan(x) or math.isnan(y):
                fixed_positions[node_name] = (0.0, 0.0)
                repaired = True
                continue
            
            if math.isinf(x):
                x = 10000.0 if x > 0 else -10000.0
                repaired = True
            if math.isinf(y):
                y = 10000.0 if y > 0 else -10000.0
                repaired = True
            
            fixed_positions[node_name] = (round(x, 2), round(y, 2))
        
        if repaired:
            # 保存修复后的布局
            name = layout_name or self.get_active_layout_name()
            self.save_layout(fixed_positions, f"{name}_repaired")
            logger.info(f"[GraphLayoutCache] 已修复布局并保存为 '{name}_repaired'")
        
        return repaired
    
    def _compute_graph_hash(self, positions: Dict) -> str:
        """计算图的哈希值（用于检测结构变化）"""
        # 使用节点名称排序后的字符串生成哈希
        nodes_str = '|'.join(sorted(positions.keys()))
        return hashlib.md5(nodes_str.encode()).hexdigest()[:16]
    
    def _create_backup(self, layout_name: str):
        """创建布局备份"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.backup_dir / f"{layout_name}_{timestamp}.json"
            
            layout = self._cache_data.get('layouts', {}).get(layout_name)
            if layout:
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(layout, f, ensure_ascii=False, indent=2)
                
                # 清理旧备份（保留最近N个）
                backups = sorted(
                    self.backup_dir.glob(f"{layout_name}_*.json"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True
                )
                
                for old_backup in backups[self.MAX_SNAPSHOTS:]:
                    old_backup.unlink()
                    logger.debug(f"[GraphLayoutCache] 已清理旧备份: {old_backup.name}")
                    
        except Exception as e:
            logger.error(f"[GraphLayoutCache] 备份失败: {e}")
    
    def clear_all(self):
        """清除所有缓存"""
        self._cache_data = {
            'version': self.CACHE_VERSION,
            'created_at': datetime.now().isoformat(),
            'layouts': {},
            'settings': {
                'auto_save': True,
                'max_snapshots': self.MAX_SNAPSHOTS
            }
        }
        self._dirty = True
        self._save_cache()
        logger.info("[GraphLayoutCache] 所有缓存已清除")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        layouts = self._cache_data.get('layouts', {})
        total_nodes = sum(
            len(l.get('node_positions', {})) 
            for l in layouts.values()
        )
        
        backup_count = len(list(self.backup_dir.glob('*.json'))) if self.backup_dir.exists() else 0
        
        return {
            'total_layouts': len(layouts),
            'total_nodes_cached': total_nodes,
            'active_layout': self._cache_data.get('active_layout'),
            'backup_count': backup_count,
            'cache_size_kb': round(
                self.cache_file.stat().st_size / 1024 
                if self.cache_file.exists() else 0, 
                2
            )
        }


# 导入math模块（在类定义后使用）
import math
