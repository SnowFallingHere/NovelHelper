import os
import json
import logging

logger = logging.getLogger(__name__)


class NovelModel:
    def __init__(self, novel_dir=""):
        self.novel_dir = novel_dir
        self.volumes = []
        self.chapters = {}
        self.keywords = []
        self._keyword_path = None
    
    def refresh(self):
        if not self.novel_dir or not os.path.exists(self.novel_dir):
            return
        
        self.volumes = []
        self.chapters = {}
        
        for vol in sorted(os.listdir(self.novel_dir)):
            vol_path = os.path.join(self.novel_dir, vol)
            if not os.path.isdir(vol_path):
                continue
            self.volumes.append({'name': vol, 'path': vol_path})
            self.chapters[vol] = []
            for fname in sorted(os.listdir(vol_path)):
                if fname.endswith('.txt') and not fname.startswith('.'):
                    self.chapters[vol].append({
                        'name': fname,
                        'path': os.path.join(vol_path, fname),
                        'size': os.path.getsize(os.path.join(vol_path, fname))
                    })
        
        self._load_keywords()
    
    def _load_keywords(self):
        if not self.novel_dir:
            return
        
        self._keyword_path = os.path.join(self.novel_dir, '.keywords.json')
        if os.path.exists(self._keyword_path):
            try:
                with open(self._keyword_path, 'r', encoding='utf-8') as f:
                    self.keywords = json.load(f)
            except Exception as e:
                logger.warning(f"加载关键词失败: {e}")
                self.keywords = []
        else:
            self.keywords = []
    
    def save_keywords(self, keywords=None):
        if keywords is not None:
            self.keywords = keywords
        if self._keyword_path:
            try:
                with open(self._keyword_path, 'w', encoding='utf-8') as f:
                    json.dump(self.keywords, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"保存关键词失败: {e}")
    
    def get_volume_count(self):
        return len(self.volumes)
    
    def get_chapter_count(self, volume=None):
        if volume:
            return len(self.chapters.get(volume, []))
        return sum(len(v) for v in self.chapters.values())
    
    def find_chapters_containing(self, keyword):
        results = []
        for vol, chapters in self.chapters.items():
            for ch in chapters:
                try:
                    with open(ch['path'], 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    if keyword in content:
                        results.append({
                            'dir': vol, 'file': ch['name'],
                            'path': ch['path'], 'count': content.count(keyword)
                        })
                except Exception:
                    pass
        return sorted(results, key=lambda x: x['count'], reverse=True)
