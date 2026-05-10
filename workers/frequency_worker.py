"""
词频分析工作线程
在后台执行词频扫描，不阻塞主线程UI
"""

import os
import re
import json
from collections import Counter, defaultdict

from .base_worker import BaseWorker, CancellationException


class FrequencyWorker(BaseWorker):
    """词频扫描工作器"""
    
    def __init__(self, file_paths=None, novel_dir=None):
        super().__init__()
        self.task_name = "词频分析"
        
        if file_paths:
            self.file_paths = file_paths
        elif novel_dir:
            self.file_paths = self._scan_files(novel_dir)
        else:
            self.file_paths = []
    
    def _scan_files(self, directory):
        """递归扫描目录中的所有文本文件"""
        files = []
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                if filename.endswith('.txt'):
                    files.append(os.path.join(root, filename))
        return files
    
    def execute(self):
        """执行词频扫描"""
        if not self.file_paths:
            return {'words': {}, 'is_replace': {}, 'total_files': 0}
        
        total_files = len(self.file_paths)
        word_counts = Counter()
        cooccurrence = defaultdict(lambda: defaultdict(int))
        sentence_patterns = {}
        
        # 加载停用词表
        stopwords = self._load_stopwords()
        
        for i, filepath in enumerate(self.file_paths):
            self.check_cancelled()  # 检查是否取消
            
            progress = int((i / total_files) * 100)
            self.emit_progress(
                progress, 
                f"正在扫描: {os.path.basename(filepath)} ({i+1}/{total_files})"
            )
            
            # 读取文件内容
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 分句
                sentences = re.split(r'[。！？\n]', content)
                
                # 提取词汇
                words_in_file = set()
                for sentence in sentences:
                    if len(sentence) < 2:
                        continue
                    
                    # 简单分词（按标点和空格）
                    tokens = re.findall(r'[\u4e00-\u9fff]{2,}', sentence)
                    
                    for token in tokens:
                        if token not in stopwords and len(token) >= 2:
                            word_counts[token] += 1
                            words_in_file.add(token)
                            
                            # 记录共现关系
                            for other_token in tokens:
                                if other_token != token and other_token not in stopwords:
                                    cooccurrence[token][other_token] += 1
                
                # 记录每个文件中出现的词
                for word in words_in_file:
                    if word not in sentence_patterns:
                        sentence_patterns[word] = {
                            'files': [],
                            'first_occurrence': None,
                            'last_occurrence': None,
                            'total_occurrences': 0,
                            'file_occurrences': 0
                        }
                    sentence_patterns[word]['files'].append(filepath)
                    sentence_patterns[word]['file_occurrences'] += 1
                    
            except Exception as e:
                self.status.emit(f"读取文件出错: {filepath} - {str(e)}")
        
        self.check_cancelled()
        self.emit_progress(100, "正在整理结果...")
        
        # 整理结果
        result_words = {}
        for word, count in word_counts.most_common():
            if count >= 2:  # 至少出现2次
                info = sentence_patterns.get(word, {})
                result_words[word] = {
                    'total_occurrences': count,
                    'file_occurrences': info.get('file_occurrences', 0),
                    'files': info.get('files', [])[:10],  # 只保留前10个文件
                }
        
        return {
            'words': result_words,
            'is_replace': {},  # 同义词替换（可后续添加）
            'total_files': total_files,
            'total_unique_words': len(result_words)
        }
    
    def _load_stopwords(self):
        """加载停用词表"""
        try:
            import sys
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            stopword_path = os.path.join(base_dir, 'res', 'stopwords.json')
            
            if os.path.exists(stopword_path):
                with open(stopword_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('stopwords', []))
        except Exception as e:
            pass
        
        # 默认停用词
        default_stopwords = {
            '的', '了', '在', '是', '我', '有', '和', '就',
            '不', '人', '都', '一', '一个', '上', '也', '很', '到',
            '说', '要', '去', '你', '会', '着', '没有', '看', '好',
            '自己', '这', '他', '她', '它', '们', '那', '个', '但'
        }
        return default_stopwords


class IncrementalFrequencyWorker(FrequencyWorker):
    """
    增量词频工作器
    只扫描新增或修改的文件
    """
    
    def __init__(self, file_paths, existing_data=None):
        super().__init__(file_paths=file_paths)
        self.task_name = "增量词频分析"
        self.existing_data = existing_data or {}
    
    def execute(self):
        """增量更新词频数据"""
        if not self.file_paths:
            return self.existing_data
        
        # 合并已有数据
        merged_words = dict(self.existing_data.get('words', {}))
        total_files = len(self.file_paths)
        
        for i, filepath in enumerate(self.file_paths):
            self.check_cancelled()
            
            progress = int((i / total_files) * 100)
            self.emit_progress(progress, f"增量扫描: {os.path.basename(filepath)}")
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                sentences = re.split(r'[。！？\n]', content)
                
                for sentence in sentences:
                    tokens = re.findall(r'[\u4e00-\u9fff]{2,}', sentence)
                    for token in tokens:
                        if token not in merged_words:
                            merged_words[token] = {
                                'total_occurrences': 1,
                                'file_occurrences': 1,
                                'files': [filepath]
                            }
                        else:
                            merged_words[token]['total_occurrences'] += 1
                            if filepath not in merged_words[token]['files']:
                                merged_words[token]['files'].append(filepath)
                                merged_words[token]['file_occurrences'] += 1
                
            except Exception as e:
                self.status.emit(f"读取文件出错: {str(e)}")
        
        self.check_cancelled()
        self.emit_progress(100, "增量分析完成")
        
        return {
            'words': merged_words,
            'is_replace': self.existing_data.get('is_replace', {}),
            'total_files': total_files + self.existing_data.get('total_files', 0),
            'total_unique_words': len(merged_words),
            'incremental': True
        }
