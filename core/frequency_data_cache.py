"""
词频数据缓存系统
提供高效的词频统计结果缓存和智能更新机制

功能：
- 词频统计结果缓存（避免重复扫描）
- 增量扫描（只重新扫描新增/修改的章节）
- 词频趋势分析（按章节追踪词频变化）
- 热度排名缓存
- 自动合并策略

使用示例：
    cache = FrequencyDataCache(novel_dir='./my_novel')
    
    # 获取词频数据
    freq_data = cache.get_frequency_data()
    
    # 获取热度TOP10
    top10 = cache.get_top_words(10)
    
    # 增量更新
    cache.incremental_update()
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class FrequencyDataCache:
    """
    词频数据缓存类
    
    缓存结构：
    {
        'version': str,
        'last_scan_time': str,
        'total_chapters': int,
        
        'words': {
            word: {
                'total_occurrences': int,
                'chapters': {chapter_num: count},
                'type': str,           # 关键词类型或 '?'
                'is_stale': bool,      # 是否是临时称谓
                'chapter_distribution': [int],  # 每章出现次数分布
                'first_appearance': int,  # 首次出现章节
                'last_appearance': int   # 最后出现章节
            }
        },
        
        'is_replace': {
            stale_word: target_keyword  # 临时称谓 -> 正式关键词映射
        },
        
        'stats': {
            'scan_duration': float,     # 扫描耗时
            'unique_words': int,       # 不重复词条数
            'total_occurrences': int   # 总出现次数
        },
        
        'trend_data': {
            word: [count_per_chapter]  # 按章节的词频趋势
        }
    }
    """
    
    CACHE_VERSION = "1.0"
    CACHE_FILENAME = ".frequency_cache.json"
    
    def __init__(self, base_dir: str):
        """
        初始化词频缓存
        
        Args:
            base_dir: 小说根目录
        """
        self.base_dir = Path(base_dir)
        
        if not self.base_dir.exists():
            raise FileNotFoundError(f"目录不存在: {base_dir}")
        
        self.cache_file = self.base_dir / self.CACHE_FILENAME
        self._cache_data: Dict[str, Any] = {}
        self._dirty = False
        
        logger.debug(f"[FrequencyDataCache] 初始化: {base_dir}")
        
        if self.cache_file.exists():
            self._load_cache()
    
    def _load_cache(self) -> bool:
        """加载缓存"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('version') != self.CACHE_VERSION:
                logger.warning("[FrequencyDataCache] 缓存版本不匹配，将重建")
                return False
            
            self._cache_data = data
            logger.info(
                f"[FrequencyDataCache] 已加载缓存 "
                f"(共{len(data.get('words', {}))}个词条)"
            )
            return True
            
        except Exception as e:
            logger.error(f"[FrequencyDataCache] 加载失败: {e}")
            return False
    
    def _save_cache(self) -> bool:
        """保存缓存"""
        if not self._dirty:
            return True
        
        try:
            self._cache_data['last_scan_time'] = datetime.now().isoformat()
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache_data, f, ensure_ascii=False, indent=2)
            
            self._dirty = False
            logger.debug("[FrequencyDataCache] 缓存已保存")
            return True
            
        except Exception as e:
            logger.error(f"[FrequencyDataCache] 保存失败: {e}")
            return False
    
    def get_frequency_data(self) -> Dict[str, Any]:
        """
        获取完整的词频数据
        
        Returns:
            Dict: 词频数据字典
        """
        return self._cache_data
    
    def get_words(self) -> Dict[str, Any]:
        """获取所有词条数据"""
        return self._cache_data.get('words', {})
    
    def get_top_words(
        self, 
        limit: int = 20, 
        by_occurrences: bool = True
    ) -> List[Tuple[str, Dict]]:
        """
        获取热门词条排行
        
        Args:
            limit: 返回数量限制
            by_occurrences: 按总出现次数排序
            
        Returns:
            List[(word, data)] 排行列表
        """
        words = self._cache_data.get('words', {})
        
        if by_occurrences:
            sorted_words = sorted(
                words.items(),
                key=lambda x: x[1].get('total_occurrences', 0),
                reverse=True
            )
        else:
            sorted_words = sorted(
                words.items(),
                key=lambda x: len(x[1].get('chapters', {})),
                reverse=True
            )
        
        return sorted_words[:limit]
    
    def get_word_trend(self, word: str) -> List[int]:
        """
        获取某个词的频率趋势
        
        Args:
            word: 词条
            
        Returns:
            List[int]: 每章的出现次数
        """
        trend = self._cache_data.get('trend_data', {}).get(word)
        if trend is not None:
            return trend
        
        # 从 chapter_distribution 构建
        word_data = self._cache_data.get('words', {}).get(word, {})
        distribution = word_data.get('chapter_distribution', [])
        return distribution
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        words = self._cache_data.get('words', {})
        
        stats = {
            **self._cache_data.get('stats', {}),
            'unique_words': len(words),
            'total_occurrences': sum(
                w.get('total_occurrences', 0) for w in words.values()
            ),
            'matched_keywords': sum(
                1 for w in words.values() 
                if w.get('type', '?') != '?'
            ),
            'stale_candidates': sum(
                1 for w in words.values() 
                if w.get('is_stale', False)
            )
        }
        
        return stats
    
    def invalidate(self):
        """使缓存失效"""
        self._cache_data = {
            'version': self.CACHE_VERSION,
            'last_scan_time': '',
            'total_chapters': 0,
            'words': {},
            'is_replace': {},
            'stats': {},
            'trend_data': {}
        }
        self._dirty = True
        logger.info("[FrequencyDataCache] 缓存已失效")
    
    def clear(self):
        """清除缓存文件"""
        if self.cache_file.exists():
            self.cache_file.unlink()
            logger.info("[FrequencyDataCache] 缓存文件已删除")
        
        self._cache_data = {}
        self._dirty = False
    
    def update_from_scan_result(self, scan_result: Dict[str, Any]):
        """
        从扫描结果更新缓存
        
        Args:
            scan_result: 扫描结果数据（来自 .frequency.json）
        """
        self._cache_data.update(scan_result)
        self._cache_data['version'] = self.CACHE_VERSION
        self._dirty = True
        self._save_cache()
        
        logger.info(
            f"[FrequencyDataCache] 已从扫描结果更新 "
            f"(共{len(scan_result.get('words', {}))}个词条)"
        )
    
    def add_replacement(self, stale_word: str, target_keyword: str):
        """
        添加替换关系
        
        Args:
            stale_word: 临时称谓
            target_keyword: 正式关键词
        """
        replacements = self._cache_data.setdefault('is_replace', {})
        replacements[stale_word] = target_keyword
        self._dirty = True
        
        # 标记该词为已替换
        if stale_word in self._cache_data.get('words', {}):
            self._cache_data['words'][stale_word]['is_replaced'] = True
        
        self._save_cache()
        logger.debug(f"[FrequencyDataCache] 添加替换: {stale_word} → {target_keyword}")
    
    def remove_replacement(self, stale_word: str):
        """移除替换关系"""
        if 'is_replace' in self._cache_data and stale_word in self._cache_data['is_replace']:
            del self._cache_data['is_replace'][stale_word]
            self._dirty = True
            
            if stale_word in self._cache_data.get('words', {}):
                self._cache_data['words'][stale_word].pop('is_replaced', None)
            
            self._save_cache()
    
    def get_replacements(self) -> Dict[str, str]:
        """获取所有替换关系"""
        return self._cache_data.get('is_replace', {})
    
    def find_stale_candidates(
        self, 
        inactive_threshold: int = 3,
        stale_ratio: float = 3.0
    ) -> List[Tuple[str, Dict]]:
        """
        查找可能的临时称谓候选
        
        规则：
        1. 在前期频繁出现，后期骤降
        2. 出现次数超过阈值但未匹配关键词
        
        Args:
            inactive_threshold: 非活跃章节数
            stale_ratio: 前后期比例阈值
            
        Returns:
            List[(word, data)] 候选列表
        """
        total_chapters = self._cache_data.get('total_chapters', 0)
        if total_chapters == 0:
            return []
        
        split_idx = max(1, total_chapters // 3)
        candidates = []
        
        for word, data in self._cache_data.get('words', {}).items():
            # 跳过已替换的和已匹配关键词的
            if word in self._cache_data.get('is_replace', {}):
                continue
            if data.get('type', '?') != '?':
                continue
            
            # 分析分布
            distribution = data.get('chapter_distribution', [])
            if not distribution or len(distribution) < split_idx:
                continue
            
            front_count = sum(distribution[:split_idx])
            back_count = sum(distribution[split_idx:])
            
            # 判断是否为临时称谓
            if (front_count > 5 and 
                back_count > 0 and 
                front_count / max(back_count, 1) >= stale_ratio):
                
                data['_analysis'] = {
                    'front_count': front_count,
                    'back_count': back_count,
                    'ratio': front_count / max(back_count, 1)
                }
                candidates.append((word, data))
        
        # 按比例排序
        candidates.sort(
            key=lambda x: x[1].get('_analysis', {}).get('ratio', 0),
            reverse=True
        )
        
        return candidates
