import os
import re
import logging

logger = logging.getLogger(__name__)


class ChapterCreator:
    def __init__(self, novel_dir_getter=None, lang_getter=None):
        self._novel_dir_getter = novel_dir_getter
        self._lang_getter = lang_getter
        self.results = []
    
    def _get_novel_dir(self):
        if self._novel_dir_getter:
            return self._novel_dir_getter()
        return ""
    
    def _get_lang(self):
        if self._lang_getter:
            return self._lang_getter()
        return "cn"
    
    def validate_suffix(self, suffix):
        return re.sub(r'[^\w\u4e00-\u9fff\-]', '', suffix) or "name"
    
    def create_chapters(self, output, prefix, suffix, count, start_num, name_list=None):
        self.results = []
        
        if not os.path.isdir(output):
            self.results.append(f"[ERR] 目录不存在: {output}")
            return self.results
        
        try:
            test_path = os.path.join(output, '.write_test')
            with open(test_path, 'w') as f:
                f.write('')
            os.remove(test_path)
        except (IOError, OSError) as e:
            self.results.append(f"[ERR] 目录不可写: {output} ({e})")
            return self.results
        
        suffix = self.validate_suffix(suffix)
        created = 0
        
        for i in range(count):
            num = start_num + i
            name = name_list[i] if name_list and i < len(name_list) else suffix
            
            filename = f"{num}{prefix}{name}.txt"
            filepath = os.path.join(output, filename)
            
            try:
                if not os.path.exists(filepath):
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write("")
                    created += 1
                    self.results.append(f"[OK] {filename}")
                else:
                    self.results.append(f"[SKIP] {filename} (已存在)")
            except (IOError, OSError) as e:
                self.results.append(f"[ERR] {filename}: {e}")
        
        self.results.append(f"完成: 创建 {created} 个文件")
        return self.results
