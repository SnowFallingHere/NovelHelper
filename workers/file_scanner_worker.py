"""
文件扫描工作线程
在后台执行章节索引构建、文件发现等任务
"""

import os
import re
from datetime import datetime

from .base_worker import BaseWorker, CancellationException


class FileScannerWorker(BaseWorker):
    """文件扫描工作器"""
    
    def __init__(self, base_dir=None):
        super().__init__()
        self.task_name = "文件扫描"
        self.base_dir = base_dir
    
    def execute(self):
        """扫描目录结构，构建章节索引"""
        if not self.base_dir or not os.path.exists(self.base_dir):
            return {'volumes': [], 'chapters': [], 'total': 0}
        
        volumes = []
        total_chapters = 0
        
        # 扫描卷目录
        entries = sorted(os.listdir(self.base_dir))
        
        for i, entry in enumerate(entries):
            self.check_cancelled()
            
            entry_path = os.path.join(self.base_dir, entry)
            
            if not os.path.isdir(entry_path):
                continue
            
            progress = int((i / len(entries)) * 100)
            self.emit_progress(progress, f"扫描目录: {entry}")
            
            # 检查是否是卷目录（包含 .txt 文件）
            txt_files = [f for f in os.listdir(entry_path) if f.endswith('.txt')]
            
            if txt_files:
                volume_data = {
                    'name': entry,
                    'path': entry_path,
                    'chapters': []
                }
                
                # 扫描章节文件
                for j, txt_file in enumerate(sorted(txt_files)):
                    chapter_path = os.path.join(entry_path, txt_file)
                    chapter_info = self._parse_chapter(chapter_path, txt_file)
                    volume_data['chapters'].append(chapter_info)
                    total_chapters += 1
                
                volumes.append(volume_data)
        
        self.check_cancelled()
        self.emit_progress(100, f"扫描完成: {total_chapters} 个章节")
        
        return {
            'volumes': volumes,
            'chapters': total_chapters,
            'scan_time': datetime.now().isoformat(),
            'base_dir': self.base_dir
        }
    
    def _parse_chapter(self, filepath, filename):
        """解析单个章节文件"""
        info = {
            'filename': filename,
            'filepath': filepath,
            'title': self._extract_title(filename),
            'size': 0,
            'modified': None
        }
        
        try:
            stat = os.stat(filepath)
            info['size'] = stat.st_size
            info['modified'] = datetime.fromtimestamp(
                stat.st_mtime
            ).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass
        
        return info
    
    def _extract_title(self, filename):
        """从文件名提取标题"""
        name = os.path.splitext(filename)[0]
        # 移除序号前缀 (如 "001_" 或 "第1章_")
        title = re.sub(r'^[0-9]+[_\-]', '', name)
        title = re.sub(r'^第[一二三四五六七八九十百千万\d]+章[_\s]?', '', title)
        return title or name


class ChapterIndexBuilder(FileScannerWorker):
    """
    章节索引构建器
    增量更新章节索引，支持缓存
    """
    
    def __init__(self, base_dir, existing_index=None):
        super().__init__(base_dir=base_dir)
        self.task_name = "章节索引构建"
        self.existing_index = existing_index or {}
    
    def execute(self):
        """增量构建章节索引"""
        result = super().execute()
        
        # 合并已有数据
        if self.existing_index.get('volumes'):
            # 标记删除的卷/章节
            old_volumes = {v['name']: v for v in self.existing_index['volumes']}
            new_volumes = {v['name']: v for v in result['volumes']}
            
            for vol_name in old_volumes:
                if vol_name not in new_volumes:
                    old_volumes[vol_name]['status'] = 'deleted'
                    result['volumes'].append(old_volumes[vol_name])
            
            # 更新修改的章节
            for volume in result['volumes']:
                if volume['name'] in old_volumes:
                    old_vol = old_volumes[volume['name']]
                    old_chapters = {
                        c['filename']: c 
                        for c in old_vol.get('chapters', [])
                    }
                    
                    for chapter in volume['chapters']:
                        if chapter['filename'] in old_chapters:
                            old_ch = old_chapters[chapter['filename']]
                            if chapter['modified'] != old_ch.get('modified'):
                                chapter['status'] = 'modified'
                            else:
                                chapter['status'] = 'unchanged'
                        else:
                            chapter['status'] = 'new'
        
        result['incremental'] = True
        
        return result


class ContentAnalyzer(BaseWorker):
    """
    内容分析工作器
    分析文本内容：字数统计、段落分析等
    """
    
    def __init__(self, file_paths):
        super().__init__()
        self.task_name = "内容分析"
        self.file_paths = file_paths
    
    def execute(self):
        """分析所有文件的内容统计"""
        results = {}
        total_files = len(self.file_paths)
        total_words = 0
        total_chars = 0
        
        for i, filepath in enumerate(self.file_paths):
            self.check_cancelled()
            
            progress = int((i / total_files) * 100)
            self.emit_progress(
                progress, 
                f"分析: {os.path.basename(filepath)}"
            )
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                chars = len(content)
                words = len(content.replace('\n', '').replace(' ', ''))
                lines = content.count('\n') + 1
                paragraphs = len([p for p in content.split('\n\n') if p.strip()])
                
                # 对话比例估算（简单按引号）
                dialogue_chars = len(re.findall(r'["「].*?["」]', content))
                dialogue_ratio = dialogue_chars / max(chars, 1) * 100
                
                results[filepath] = {
                    'chars': chars,
                    'words': words,
                    'lines': lines,
                    'paragraphs': paragraphs,
                    'dialogue_ratio': round(dialogue_ratio, 1),
                    'avg_paragraph_length': round(
                        words / max(paragraphs, 1), 1
                    )
                }
                
                total_words += words
                total_chars += chars
                
            except Exception as e:
                self.status.emit(f"分析失败: {os.path.basename(filepath)} - {str(e)}")
        
        self.check_cancelled()
        self.emit_progress(100, "内容分析完成")
        
        return {
            'files': results,
            'summary': {
                'total_files': total_files,
                'total_words': total_words,
                'total_chars': total_chars,
                'avg_words_per_file': round(
                    total_words / max(total_files, 1), 0
                )
            }
        }
