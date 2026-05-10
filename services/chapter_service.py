"""
章节管理服务
提供章节的创建、读取、更新、删除等操作
"""

import os
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import logging

logger = logging.getLogger(__name__)


class ChapterService:
    """
    章节管理服务
    
    功能：
    - CRUD 操作（创建/读取/更新/删除章节）
    - 章节索引构建和查询
    - 内容分析（字数统计等）
    - 批量操作
    
    使用示例：
        service = ChapterService(novel_dir='./my_novel')
        
        # 创建章节
        service.create_chapter('第一卷', '第一章', '内容...')
        
        # 读取章节
        content = service.read_chapter('第一卷', '第一章')
        
        # 获取所有章节列表
        chapters = service.list_all_chapters()
    """
    
    def __init__(self, base_dir: str):
        """
        初始化章节服务
        
        Args:
            base_dir: 小说根目录
        """
        self.base_dir = Path(base_dir)
        
        if not self.base_dir.exists():
            raise FileNotFoundError(f"目录不存在: {base_dir}")
        
        logger.debug(f"[ChapterService] 初始化: {base_dir}")
    
    # ====== 创建操作 ======
    
    def create_chapter(
        self,
        volume_name: str,
        chapter_name: str,
        content: str = "",
        overwrite: bool = False
    ) -> str:
        """
        创建新章节
        
        Args:
            volume_name: 卷名（如 "第一卷"）
            chapter_name: 章节名（如 "第一章 陨落的天才"）
            content: 章节内容（可选）
            overwrite: 是否覆盖已存在的文件
            
        Returns:
            str: 创建的文件路径
            
        Raises:
            FileExistsError: 文件已存在且 overwrite=False
            OSError: 创建失败
        """
        # 清理文件名
        safe_volume = self._sanitize_path(volume_name)
        safe_chapter = self._sanitize_filename(chapter_name)
        
        # 构建路径
        volume_dir = self.base_dir / safe_volume
        chapter_file = volume_dir / f"{safe_chapter}.txt"
        
        # 检查是否已存在
        if chapter_file.exists() and not overwrite:
            raise FileExistsError(f"章节已存在: {chapter_file}")
        
        # 创建卷目录
        volume_dir.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(chapter_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"[ChapterService] 创建章节: {chapter_file}")
        
        return str(chapter_file)
    
    def create_volume(self, volume_name: str) -> str:
        """
        创建新卷目录
        
        Args:
            volume_name: 卷名
            
        Returns:
            str: 卷目录路径
        """
        safe_name = self._sanitize_path(volume_name)
        volume_dir = self.base_dir / safe_name
        volume_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[ChapterService] 创建卷: {volume_dir}")
        
        return str(volume_dir)
    
    # ====== 读取操作 ======
    
    def read_chapter(
        self,
        volume_name: str,
        chapter_name: str,
        encoding: str = 'utf-8'
    ) -> Optional[str]:
        """
        读取章节内容
        
        Args:
            volume_name: 卷名
            chapter_name: 章节名
            encoding: 编码格式
            
        Returns:
            Optional[str]: 章节内容，如果不存在返回 None
        """
        path = self._get_chapter_path(volume_name, chapter_name)
        
        if not path or not os.path.exists(path):
            return None
        
        try:
            with open(path, 'r', encoding=encoding) as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"[ChapterService] 读取失败: {path} - {e}")
            return None
    
    def read_chapter_by_path(self, filepath: str, encoding: str = 'utf-8') -> Optional[str]:
        """通过文件路径读取章节"""
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return f.read()
        except Exception as e:
            logger.error(f"[ChapterService] 读取失败: {filepath} - {e}")
            return None
    
    # ====== 更新操作 ======
    
    def update_chapter(
        self,
        volume_name: str,
        chapter_name: str,
        new_content: str,
        append: bool = False
    ) -> bool:
        """
        更新章节内容
        
        Args:
            volume_name: 卷名
            chapter_name: 章节名
            new_content: 新内容
            append: 是否追加（默认为替换）
            
        Returns:
            bool: 是否成功
        """
        path = self._get_chapter_path(volume_name, chapter_name)
        
        if not path:
            return False
        
        try:
            mode = 'a' if append else 'w'
            with open(path, mode, encoding='utf-8') as f:
                if append and new_content and not new_content.endswith('\n'):
                    f.write('\n')
                f.write(new_content)
            
            logger.info(f"[ChapterService] 更新章节: {path} ({'追加' if append else '替换'})")
            return True
            
        except Exception as e:
            logger.error(f"[ChapterService] 更新失败: {path} - {e}")
            return False
    
    def rename_chapter(
        self,
        volume_name: str,
        old_name: str,
        new_name: str
    ) -> bool:
        """
        重命名章节
        
        Returns:
            bool: 是否成功
        """
        old_path = self._get_chapter_path(volume_name, old_name)
        new_path = self._get_chapter_path(volume_name, new_name)
        
        if not old_path or not os.path.exists(old_path):
            return False
        
        if os.path.exists(new_path):
            logger.error(f"[ChapterService] 目标文件已存在: {new_path}")
            return False
        
        try:
            os.rename(old_path, new_path)
            logger.info(f"[ChapterService] 重命名: {old_name} → {new_name}")
            return True
        except Exception as e:
            logger.error(f"[ChapterService] 重命名失败: {e}")
            return False
    
    def rename_volume(self, old_name: str, new_name: str) -> bool:
        """重命名卷"""
        old_dir = self.base_dir / self._sanitize_path(old_name)
        new_dir = self.base_dir / self._sanitize_path(new_name)
        
        if not old_dir.exists():
            return False
        
        if new_dir.exists():
            return False
        
        try:
            os.rename(old_dir, new_dir)
            logger.info(f"[ChapterService] 重命名卷: {old_name} → {new_name}")
            return True
        except Exception as e:
            logger.error(f"[ChapterService] 重命名卷失败: {e}")
            return False
    
    # ====== 删除操作 ======
    
    def delete_chapter(self, volume_name: str, chapter_name: str) -> bool:
        """删除章节"""
        path = self._get_chapter_path(volume_name, chapter_name)
        
        if not path or not os.path.exists(path):
            return False
        
        try:
            os.remove(path)
            logger.info(f"[ChapterService] 删除章节: {chapter_name}")
            return True
        except Exception as e:
            logger.error(f"[ChapterService] 删除失败: {e}")
            return False
    
    def delete_volume(self, volume_name: str, confirm: bool = False) -> bool:
        """
        删除整个卷及其所有章节
        
        Args:
            confirm: 必须为 True 才能执行删除
            
        Warning:
            此操作不可逆！
        """
        if not confirm:
            logger.warning("[ChapterService] 删除卷需要 confirm=True")
            return False
        
        vol_dir = self.base_dir / self._sanitize_path(volume_name)
        
        if not vol_dir.exists():
            return False
        
        try:
            import shutil
            shutil.rmtree(vol_dir)
            logger.warning(f"[ChapterService] 已删除卷: {volume_name}")
            return True
        except Exception as e:
            logger.error(f"[ChapterService] 删除卷失败: {e}")
            return False
    
    # ====== 查询操作 ======
    
    def list_volumes(self) -> List[Dict]:
        """
        列出所有卷及章节数量
        
        Returns:
            List[Dict]: [
                {
                    'name': str,      # 卷名
                    'path': str,       # 路径
                    'chapters': int,   # 章节数
                    'total_chars': int  # 总字数
                },
                ...
            ]
        """
        volumes = []
        
        for item in self.base_dir.iterdir():
            if not item.is_dir():
                continue
            
            # 跳过隐藏目录和非文本目录
            if item.name.startswith('.'):
                continue
            
            txt_files = list(item.glob('*.txt'))
            if not txt_files:
                continue
            
            total_chars = sum(
                f.stat().st_size 
                for f in txt_files 
                if f.is_file()
            )
            
            volumes.append({
                'name': item.name,
                'path': str(item),
                'chapters': len(txt_files),
                'total_chars': total_chars
            })
        
        # 按名称排序
        volumes.sort(key=lambda x: x['name'])
        
        return volumes
    
    def list_chapters_in_volume(self, volume_name: str) -> List[Dict]:
        """
        列出指定卷中的所有章节
        
        Returns:
            List[Dict]: [
                {
                    'name': str,           # 章节名
                    'filename': str,       # 文件名
                    'path': str,           # 完整路径
                    'size': int,           # 字节数
                    'modified': str,       # 修改时间
                    'chars': int          # 字符数
                },
                ...
            ]
        """
        vol_dir = self.base_dir / self._sanitize_path(volume_name)
        
        if not vol_dir.exists():
            return []
        
        chapters = []
        
        for f in sorted(vol_dir.glob('*.txt')):
            stat = f.stat()
            
            try:
                chars = len(f.read_text(encoding='utf-8'))
            except:
                chars = 0
            
            chapters.append({
                'name': f.stem,
                'filename': f.name,
                'path': str(f),
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(
                    stat.st_mtime
                ).strftime('%Y-%m-%d %H:%M'),
                'chars': chars
            })
        
        return chapters
    
    def list_all_chapters(self) -> List[Dict]:
        """
        列出所有章节（跨卷）
        
        Returns:
            List[Dict]: 包含 volume_name 的章节信息
        """
        all_chapters = []
        
        for vol in self.list_volumes():
            chapters = self.list_chapters_in_volume(vol['name'])
            for ch in chapters:
                ch['volume'] = vol['name']
                all_chapters.append(ch)
        
        return all_chapters
    
    def search_chapters(
        self,
        keyword: str,
        case_sensitive: bool = False
    ) -> List[Dict]:
        """
        搜索包含关键词的章节
        
        Args:
            keyword: 搜索关键词
            case_sensitive: 是否区分大小写
            
        Returns:
            List[Dict]: 匹配的章节列表
        """
        results = []
        
        flags = 0 if case_sensitive else re.IGNORECASE
        
        for chapter in self.list_all_chapters():
            content = self.read_chapter_by_path(chapter['path'])
            
            if content and re.search(keyword, content, flags):
                # 提取匹配行上下文
                lines = content.split('\n')
                matched_lines = [
                    (i+1, line.strip()) 
                    for i, line in enumerate(lines) 
                    if re.search(keyword, line, flags)
                ]
                
                chapter['matched_lines'] = matched_lines[:5]  # 只保留前5个匹配
                results.append(chapter)
        
        return results
    
    def get_chapter_stats(self, filepath: str) -> Dict:
        """
        获取章节统计信息
        
        Returns:
            Dict: 统计数据
                {
                    'chars': int,              # 总字符数
                    'words': int,              # 总词数
                    'lines': int,              # 行数
                    'paragraphs': int,         # 段落数
                    'dialogue_ratio': float,   # 对话比例 (0-100)
                    'avg_line_length': float   # 平均行长
                }
        """
        content = self.read_chapter_by_path(filepath)
        
        if not content:
            return {}
        
        lines = content.split('\n')
        paragraphs = [p for p in content.split('\n\n') if p.strip()]
        
        # 简单对话检测（引号内的内容）
        dialogue_chars = len(re.findall(r'["「].*?["」]', content))
        
        stats = {
            'chars': len(content),
            'words': len(content.replace('\n', '').replace(' ', '')),
            'lines': len(lines),
            'paragraphs': len(paragraphs),
            'dialogue_ratio': round(dialogue_chars / max(len(content), 1) * 100, 1),
            'avg_line_length': round(
                sum(len(line) for line in lines) / max(len(lines), 1), 
                1
            )
        }
        
        return stats
    
    # ====== 批量操作 ======
    
    def merge_chapters(
        self,
        source_paths: List[str],
        target_path: str,
        separator: str = "\n\n---\n\n"
    ) -> bool:
        """
        合并多个章节到一个文件
        
        Args:
            source_paths: 源文件路径列表
            target_path: 目标文件路径
            separator: 分隔符
            
        Returns:
            bool: 是否成功
        """
        contents = []
        
        for path in source_paths:
            content = self.read_chapter_by_path(path)
            if content is not None:
                contents.append(content)
        
        if not contents:
            return False
        
        try:
            combined = separator.join(contents)
            
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(combined)
            
            logger.info(f"[ChapterService] 合并 {len(source_paths)} 个章节到 {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"[ChapterService] 合并失败: {e}")
            return False
    
    def export_to_single_file(
        self,
        output_path: str,
        include_metadata: bool = True
    ) -> bool:
        """
        导出所有章节到单个文件
        
        Args:
            output_path: 输出文件路径
            include_metadata: 是否包含元数据（卷名、章节名等）
            
        Returns:
            bool: 是否成功
        """
        all_parts = []
        
        for vol in self.list_volumes():
            if include_metadata:
                all_parts.append(f"# {vol['name']}\n\n")
            
            for ch in self.list_chapters_in_volume(vol['name']):
                if include_metadata:
                    all_parts.append(f"## {ch['name']}\n\n")
                
                content = self.read_chapter_by_path(ch['path'])
                if content:
                    all_parts.append(content)
                    all_parts.append("\n\n")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(''.join(all_parts))
            
            logger.info(f"[ChapterService] 导出到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"[ChapterService] 导出失败: {e}")
            return False
    
    # ====== 辅助方法 ======
    
    def _get_chapter_path(self, volume_name: str, chapter_name: str) -> Optional[str]:
        """获取章节文件的完整路径"""
        safe_vol = self._sanitize_path(volume_name)
        safe_chap = self._sanitize_filename(chapter_name)
        
        path = self.base_dir / safe_vol / f"{safe_chap}.txt"
        
        if path.exists():
            return str(path)
        return None
    
    @staticmethod
    def _sanitize_path(name: str) -> str:
        """清理路径中的非法字符"""
        illegal = '<>:"/\\|?*'
        for char in illegal:
            name = name.replace(char, '')
        return name.strip() or 'untitled'
    
    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """清理文件名"""
        name = ChapterService._sanitize_path(name)
        name = name.replace(' ', '_')
        return name[:100] or 'untitled'
    
    def get_total_stats(self) -> Dict:
        """
        获取整体统计信息
        
        Returns:
            Dict: 整体统计数据
        """
        volumes = self.list_volumes()
        
        total_chapters = sum(v['chapters'] for v in volumes)
        total_chars = sum(v['total_chars'] for v in volumes)
        
        return {
            'volumes': len(volumes),
            'total_chapters': total_chapters,
            'total_chars': total_chars,
            'avg_chars_per_chapter': round(
                total_chars / max(total_chapters, 1), 0
            ),
            'avg_chapters_per_volume': round(
                total_chapters / max(len(volumes), 1), 0
            )
        }
