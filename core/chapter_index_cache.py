"""
章节索引缓存系统
提供高效的章节文件索引、统计信息缓存和增量更新功能

功能：
- 章节列表缓存（避免重复扫描目录）
- 字数统计缓存（避免重复读取文件）
- 增量更新（只重新计算变化的章节）
- 自动过期机制（基于文件修改时间）
- 持久化存储（保存到JSON文件）

使用示例：
    cache = ChapterIndexCache(novel_dir='./my_novel')
    
    # 获取所有卷
    volumes = cache.get_volumes()
    
    # 获取某个卷的章节数据
    chapters = cache.get_chapters('第一卷')
    
    # 强制刷新缓存
    cache.refresh()
    
    # 清理缓存
    cache.clear()
"""

import os
import json
import hashlib
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class ChapterIndexCache:
    """
    章节索引缓存类
    
    缓存结构：
    {
        'version': str,                    # 缓存版本号
        'last_update': str,                # 最后更新时间
        'volumes': {                       # 卷数据
            volume_name: {
                'path': str,               # 卷路径
                'chapters': {              # 章节索引
                    chapter_name: {
                        'path': str,       # 文件路径
                        'size': int,        # 文件大小（字节）
                        'mtime': float,     # 最后修改时间戳
                        'word_count': int,  # 中文字数（可选）
                        'hash': str         # 内容哈希（用于变化检测）
                    }
                },
                'total_chapters': int,      # 总章节数
                'total_words': int,        # 总字数
                'last_mtime': float        # 卷的最后修改时间
            }
        },
        'stats': {                         # 全局统计
            'total_volumes': int,
            'total_chapters': int,
            'total_words': int,
            'scan_time': float             # 扫描耗时（秒）
        }
    }
    """
    
    CACHE_VERSION = "1.0"
    CACHE_FILENAME = ".chapter_index_cache.json"
    CONFIG_DIR_NAME = ".novel_structure"
    
    def __init__(self, base_dir: str):
        """
        初始化章节索引缓存
        
        Args:
            base_dir: 小说根目录
        """
        self.base_dir = Path(base_dir)
        self.config_dir = self.base_dir / self.CONFIG_DIR_NAME
        
        if not self.base_dir.exists():
            raise FileNotFoundError(f"目录不存在: {base_dir}")
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.config_dir / self.CACHE_FILENAME
        self._cache_data: Dict[str, Any] = {}
        self._dirty = False  # 是否有未保存的修改
        
        logger.debug(f"[ChapterIndexCache] 初始化: {base_dir}")
        
        # 尝试加载已有缓存
        if self.cache_file.exists():
            self._load_cache()
    
    def _load_cache(self) -> bool:
        """从文件加载缓存"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 版本检查
            if data.get('version') != self.CACHE_VERSION:
                logger.warning(
                    f"[ChapterIndexCache] 缓存版本不匹配，将重建缓存 "
                    f"(期望: {self.CACHE_VERSION}, 实际: {data.get('version')})"
                )
                return False
            
            self._cache_data = data
            logger.info(f"[ChapterIndexCache] 已加载缓存 (共{len(data.get('volumes', {}))}个卷)")
            return True
            
        except Exception as e:
            logger.error(f"[ChapterIndexCache] 加载缓存失败: {e}")
            return False
    
    def _save_cache(self) -> bool:
        """保存缓存到文件"""
        if not self._dirty:
            return True
        
        try:
            self._cache_data['last_update'] = datetime.now().isoformat()
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache_data, f, ensure_ascii=False, indent=2)
            
            self._dirty = False
            logger.debug(f"[ChapterIndexCache] 缓存已保存")
            return True
            
        except Exception as e:
            logger.error(f"[ChapterIndexCache] 保存缓存失败: {e}")
            return False
    
    def get_volumes(self) -> List[Dict[str, Any]]:
        """
        获取所有卷的列表
        
        Returns:
            List[Dict]: [
                {
                    'name': str,      # 卷名
                    'path': str,       # 路径
                    'chapters': int,   # 章节数
                    'total_words': int # 总字数
                },
                ...
            ]
        """
        volumes = []
        
        for vol_name, vol_data in self._cache_data.get('volumes', {}).items():
            chapters = vol_data.get('chapters', {})
            total_words = sum(ch.get('word_count', 0) for ch in chapters.values())
            
            volumes.append({
                'name': vol_name,
                'path': vol_data.get('path', ''),
                'chapters': len(chapters),
                'total_words': total_words
            })
        
        # 按名称排序
        volumes.sort(key=lambda x: x['name'])
        
        return volumes
    
    def get_chapters(self, volume_name: str) -> List[Dict[str, Any]]:
        """
        获取指定卷的所有章节
        
        Args:
            volume_name: 卷名
            
        Returns:
            List[Dict]: [
                {
                    'name': str,       # 章节名
                    'path': str,        # 文件路径
                    'word_count': int,  # 字数
                    'size': int,        # 文件大小
                    'mtime': str        # 修改时间
                },
                ...
            ]
        """
        vol_data = self._cache_data.get('volumes', {}).get(volume_name)
        if not vol_data:
            return []
        
        chapters = []
        for ch_name, ch_data in vol_data.get('chapters', {}).items():
            mtime = ch_data.get('mtime', 0)
            mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S') if mtime else ''
            
            chapters.append({
                'name': ch_name.replace('.txt', ''),
                'path': ch_data.get('path', ''),
                'word_count': ch_data.get('word_count', 0),
                'size': ch_data.get('size', 0),
                'mtime': mtime_str
            })
        
        # 按名称排序
        chapters.sort(key=lambda x: x['name'])
        
        return chapters
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取全局统计信息
        
        Returns:
            Dict: 统计数据字典
        """
        return self._cache_data.get('stats', {
            'total_volumes': 0,
            'total_chapters': 0,
            'total_words': 0
        })
    
    def refresh(self, force: bool = False, count_words: bool = True) -> Dict[str, Any]:
        """
        刷新/重建缓存
        
        Args:
            force: 是否强制完全重建（忽略现有缓存）
            count_words: 是否统计字数（较耗时）
            
        Returns:
            Dict: 统计信息
        """
        start_time = datetime.now()
        logger.info(f"[ChapterIndexCache] 开始刷新缓存 (force={force})")
        
        if force or not self._cache_data:
            # 完全重建
            self._cache_data = {
                'version': self.CACHE_VERSION,
                'last_update': '',
                'volumes': {},
                'stats': {}
            }
        
        # 扫描所有卷目录
        total_volumes = 0
        total_chapters = 0
        total_words = 0
        found_volumes = set()
        
        for item in self.base_dir.iterdir():
            if not item.is_dir():
                continue
            
            # 跳过隐藏目录和非卷目录
            if item.name.startswith('.') or not re.match(r'^\d+', item.name):
                continue
            
            vol_path = item
            vol_name = item.name
            found_volumes.add(vol_name)
            txt_files = list(vol_path.glob('*.txt'))
            
            if not txt_files:
                continue
            
            # 检查是否需要更新该卷
            vol_mtime = max(f.stat().st_mtime for f in txt_files)
            cached_vol = self._cache_data.get('volumes', {}).get(vol_name)
            
            should_update = (
                force or 
                not cached_vol or 
                cached_vol.get('last_mtime', 0) < vol_mtime
            )
            
            if should_update:
                # 更新该卷的数据
                vol_data = self._scan_volume(vol_path, vol_name, txt_files, count_words)
                self._cache_data.setdefault('volumes', {})[vol_name] = vol_data
                
                total_chapters += vol_data['total_chapters']
                total_words += vol_data['total_words']
            else:
                # 使用缓存的统计数据
                total_chapters += cached_vol.get('total_chapters', 0)
                total_words += cached_vol.get('total_words', 0)
            
            total_volumes += 1
        
        # 移除已不存在于磁盘的旧卷缓存
        stale_volumes = set(self._cache_data.get('volumes', {}).keys()) - found_volumes
        for stale_vol in stale_volumes:
            logger.info(f"[ChapterIndexCache] 移除已不存在的卷缓存: {stale_vol}")
            del self._cache_data['volumes'][stale_vol]
        
        # 更新全局统计
        scan_duration = (datetime.now() - start_time).total_seconds()
        self._cache_data['stats'] = {
            'total_volumes': total_volumes,
            'total_chapters': total_chapters,
            'total_words': total_words,
            'scan_time': scan_duration
        }
        
        self._dirty = True
        self._save_cache()
        
        logger.info(
            f"[ChapterIndexCache] 刷新完成！"
            f" 共{total_volumes}卷, {total_chapters}章, {total_words}字"
            f" (耗时: {scan_duration:.2f}秒)"
        )
        
        return self._cache_data['stats']
    
    def _scan_volume(
        self, 
        vol_path: Path, 
        vol_name: str, 
        txt_files: List[Path],
        count_words: bool
    ) -> Dict[str, Any]:
        """
        扫描单个卷的章节
        
        Args:
            vol_path: 卷路径
            vol_name: 卷名
            txt_files: 章节文件列表
            count_words: 是否统计字数
            
        Returns:
            Dict: 卷数据
        """
        chapters = {}
        total_words = 0
        
        for txt_file in sorted(txt_files):
            stat = txt_file.stat()
            chapter_name = txt_file.stem
            
            # 计算字数（如果需要）
            word_count = 0
            if count_words:
                try:
                    content = txt_file.read_text(encoding='utf-8')
                    # 统计中文字符数
                    word_count = sum(1 for c in content if '\u4e00' <= c <= '\u9fff')
                except Exception:
                    pass
            
            chapters[chapter_name] = {
                'path': str(txt_file),
                'size': stat.st_size,
                'mtime': stat.st_mtime,
                'word_count': word_count,
                'hash': ''  # 可选：添加内容哈希
            }
            
            total_words += word_count
        
        # 计算卷的最后修改时间
        last_mtime = max(
            (ch.get('mtime', 0) for ch in chapters.values()),
            default=0
        )
        
        return {
            'path': str(vol_path),
            'chapters': chapters,
            'total_chapters': len(chapters),
            'total_words': total_words,
            'last_mtime': last_mtime
        }
    
    def invalidate_volume(self, volume_name: str):
        """
        使指定卷的缓存失效
        
        Args:
            volume_name: 卷名
        """
        if volume_name in self._cache_data.get('volumes', {}):
            del self._cache_data['volumes'][volume_name]
            self._dirty = True
            logger.debug(f"[ChapterIndexCache] 已失效卷: {volume_name}")
    
    def invalidate_all(self):
        """使所有缓存失效"""
        self._cache_data = {
            'version': self.CACHE_VERSION,
            'last_update': '',
            'volumes': {},
            'stats': {}
        }
        self._dirty = True
        logger.debug("[ChapterIndexCache] 所有缓存已失效")
    
    def clear(self):
        """清除缓存文件"""
        if self.cache_file.exists():
            self.cache_file.unlink()
            logger.info("[ChapterIndexCache] 缓存文件已删除")
        
        self._cache_data = {}
        self._dirty = False
    
    def get_recently_modified(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        获取最近修改的章节
        
        Args:
            hours: 最近多少小时内的修改
            
        Returns:
            List[Dict]: 修改的章节列表
        """
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_timestamp = cutoff_time.timestamp()
        
        recent_chapters = []
        
        for vol_name, vol_data in self._cache_data.get('volumes', {}).items():
            for ch_name, ch_data in vol_data.get('chapters', {}).items():
                if ch_data.get('mtime', 0) >= cutoff_timestamp:
                    recent_chapters.append({
                        'volume': vol_name,
                        'chapter': ch_name,
                        'path': ch_data.get('path', ''),
                        'word_count': ch_data.get('word_count', 0),
                        'modified_at': datetime.fromtimestamp(
                            ch_data['mtime']
                        ).strftime('%Y-%m-%d %H:%M')
                    })
        
        # 按修改时间倒序排列
        recent_chapters.sort(key=lambda x: x['modified_at'], reverse=True)
        
        return recent_chapters
