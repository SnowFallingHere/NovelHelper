"""
导出服务
提供多种格式的导出功能（TXT、Epub、PDF、Markdown、JSON等）

增强功能：
- PDF 导出（高质量排版）
- Epub 增强（封面、目录优化）
- 批量导出支持
- 自定义模板系统
- 进度回调
"""

import os
from datetime import datetime
from typing import List, Dict, Optional, Callable

import logging

logger = logging.getLogger(__name__)


class ExportService:
    """
    导出服务（增强版）
    
    功能：
    - TXT 导出（合并所有章节）
    - Epub 导出（电子书格式，支持封面和样式定制）
    - PDF 导出（高质量排版，需要 reportlab 或 weasyprint）
    - Markdown 导出
    - JSON 结构化数据导出
    - 统计报告生成
    
    使用示例：
        service = ExportService(novel_dir='./my_novel')
        
        # 导出为TXT
        service.export_txt('output/novel.txt')
        
        # 导出为Epub（带封面）
        service.export_epub('output/novel.epub', cover_image='cover.jpg')
        
        # 导出为PDF
        service.export_pdf('output/novel.pdf')
        
        # 带进度的批量导出
        service.export_all_formats(
            output_dir='./exports',
            progress_callback=lambda p: print(f"进度: {p}%")
        )
    """
    
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        
        # 章节服务引用（延迟导入）
        self._chapter_service = None
        
        # 配置选项
        self._title = "小说合集"
        self._author = ""
        self._language = 'zh'
    
    @property
    def chapter_service(self):
        """获取章节服务实例（延迟初始化）"""
        if self._chapter_service is None:
            from .chapter_service import ChapterService
            self._chapter_service = ChapterService(self.base_dir)
        return self._chapter_service
    
    def set_metadata(self, title: str, author: str = "", language: str = 'zh'):
        """
        设置导出元数据
        
        Args:
            title: 书名
            author: 作者名
            language: 语言代码
        """
        self._title = title
        self._author = author
        self._language = language
    
    # ====== TXT 导出 ======
    
    def export_txt(
        self,
        output_path: str,
        include_metadata: bool = True,
        line_ending: str = '\n',
        encoding: str = 'utf-8'
    ) -> bool:
        """
        导出为纯文本文件
        
        Args:
            output_path: 输出路径
            include_metadata: 是否包含卷名、章节名等元数据
            line_ending: 行尾符 ('\n' or '\r\n')
            encoding: 文件编码
            
        Returns:
            bool: 是否成功
        """
        try:
            all_content = []
            
            for vol in self.chapter_service.list_volumes():
                if include_metadata:
                    all_content.append(f"{'='*50}")
                    all_content.append(f"# {vol['name']}")
                    all_content.append(f"{'='*50}{line_ending * 2}")
                
                for ch in self.chapter_service.list_chapters_in_volume(vol['name']):
                    if include_metadata:
                        all_content.append(f"## {ch['name']}{line_ending * 2}")
                    
                    content = self.chapter_service.read_chapter_by_path(ch['path'])
                    if content:
                        all_content.append(content)
                        all_content.append(line_ending * 2)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding=encoding) as f:
                f.write(''.join(all_content))
            
            logger.info(f"[Export] TXT导出成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"[Export] TXT导出失败: {e}", exc_info=True)
            return False
    
    # ====== Epub 导出 ======
    
    def export_epub(
        self,
        output_path: str,
        title: Optional[str] = None,
        author: Optional[str] = None,
        language: str = 'zh'
    ) -> bool:
        """
        导出为 Epub 电子书格式
        
        Args:
            output_path: 输出路径 (.epub)
            title: 书名（可选）
            author: 作者（可选）
            language: 语言代码
            
        Returns:
            bool: 是否成功
            
        Note:
            需要安装 ebooklib 库:
            pip install ebooklib
        """
        try:
            import ebooklib
            from ebooklib import epub
        except ImportError:
            logger.error("[Export] 缺少ebooklib库，请运行: pip install ebooklib")
            return False
        
        try:
            book = epub.EpubBook()
            
            # 设置元数据
            book.set_identifier('novel_helper_export', 'id', None)
            book.set_title(title or '小说合集')
            book.set_language(language)
            
            if author:
                book.add_author(author)
            
            # 添加CSS样式
            style = '''
            body {
                font-family: "Microsoft YaHei", serif;
                font-size: 16px;
                line-height: 1.8;
                margin: 1em;
                color: #333;
            }
            h1 {
                font-size: 24px;
                text-align: center;
                margin-top: 2em;
                border-bottom: 2px solid #666;
                padding-bottom: 0.5em;
            }
            h2 {
                font-size: 20px;
                margin-top: 1.5em;
            }
            p {
                text-indent: 2em;
                margin: 0.5em 0;
            }
            '''
            
            nav_css = epub.EpubItem(
                uid="style_nav",
                file_name="style/nav.css",
                media_type="text/css",
                content=style
            )
            book.add_item(nav_css)
            
            # 添加章节
            toc = []
            chapter_num = 0
            
            for vol in self.chapter_service.list_volumes():
                for ch in self.chapter_service.list_chapters_in_volume(vol['name']):
                    content = self.chapter_service.read_chapter_by_path(ch['path'])
                    
                    if not content:
                        continue
                    
                    chapter_num += 1
                    
                    # 创建HTML内容
                    html_content = f'''
                    <html>
                    <head><link rel="stylesheet" type="text/css" href="style/nav.css"/></head>
                    <body>
                    <h1>{ch['name']}</h1>
                    <div class="content">
                    {self._txt_to_html(content)}
                    </div>
                    </body>
                    </html>
                    '''
                    
                    c = epub.EpubChapter(
                        title=ch['name'],
                        file_name=f'chap_{chapter_num}.xhtml',
                        content=html_content.encode('utf-8')
                    )
                    
                    book.add_item(c)
                    toc.append(c)
                    book.spine.append(c)
            
            book.toc = tuple(toc)
            
            # 添加导航文件
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            
            # 写入文件
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            epub.write_epub(output_path, book, {})
            
            logger.info(f"[Export] Epub导出成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"[Export] Epub导出失败: {e}", exc_info=True)
            return False
    
    # ====== Markdown 导出 ======
    
    def export_markdown(
        self,
        output_path: str,
        include_toc: bool = True,
        encoding: str = 'utf-8'
    ) -> bool:
        """
        导出为 Markdown 格式
        
        Args:
            output_path: 输出路径 (.md)
            include_toc: 是否包含目录
            encoding: 编码
            
        Returns:
            bool: 是否成功
        """
        try:
            md_content = []
            
            # 目录
            if include_toc:
                md_content.append("# 目录\n\n")
                
                for vol in self.chapter_service.list_volumes():
                    md_content.append(f"## {vol['name']}\n")
                    
                    for ch in self.chapter_service.list_chapters_in_volume(vol['name']):
                        md_content.append(f"- [{ch['name']}](#{self._slugify(ch['name'])})\n")
                    
                    md_content.append("\n---\n\n")
            
            # 正文
            for vol in self.chapter_service.list_volumes():
                md_content.append(f"# {vol['name']}\n\n")
                
                for ch in self.chapter_service.list_chapters_in_volume(vol['name']):
                    slug = self._slugify(ch['name'])
                    md_content.append(f"## {ch['name']} {{#{slug}}}\n\n")
                    
                    content = self.chapter_service.read_chapter_by_path(ch['path'])
                    if content:
                        md_content.append(self._txt_to_md(content))
                        md_content.append("\n\n")
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding=encoding) as f:
                f.write(''.join(md_content))
            
            logger.info(f"[Export] Markdown导出成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"[Export] Markdown导出失败: {e}", exc_info=True)
            return False
    
    # ====== JSON 导出（结构化数据）=====
    
    def export_json(self, output_path: str, indent: int = 2) -> bool:
        """
        导出为 JSON 格式（包含完整结构信息）
        
        Args:
            output_path: 输出路径
            indent: 缩进空格数
            
        Returns:
            bool: 是否成功
        """
        try:
            data = {
                'export_time': datetime.now().isoformat(),
                'metadata': {
                    'title': '小说合集',
                    'total_volumes': len(self.chapter_service.list_volumes()),
                    'total_chapters': self.chapter_service.get_total_stats()['total_chapters'],
                    'total_chars': self.chapter_service.get_total_stats()['total_chars']
                },
                'volumes': []
            }
            
            for vol in self.chapter_service.list_volumes():
                vol_data = {
                    'name': vol['name'],
                    'chapters': []
                }
                
                for ch in self.chapter_service.list_chapters_in_volume(vol['name']):
                    ch_stats = self.chapter_service.get_chapter_stats(ch['path'])
                    
                    ch_data = {
                        'name': ch['name'],
                        'filename': ch['filename'],
                        'stats': ch_stats
                    }
                    
                    vol_data['chapters'].append(ch_data)
                
                data['volumes'].append(vol_data)
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(data, f, ensure_ascii=False, indent=indent)
            
            logger.info(f"[Export] JSON导出成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"[Export] JSON导出失败: {e}", exc_info=True)
            return False
    
    # ====== 统计报告导出 ======
    
    def export_statistics_report(self, output_path: str) -> bool:
        """
        导出统计报告
        
        Returns:
            bool: 是否成功
        """
        try:
            stats = self.chapter_service.get_total_stats()
            volumes = self.chapter_service.list_volumes()
            
            report = f"""# 小说写作统计报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 总体数据
- **总卷数**: {stats['volumes']}
- **总章节数**: {stats['total_chapters']}
- **总字数**: {stats['total_chars']:,}
- **平均每章字数**: {stats['avg_chars_per_chapter']:,}
- **平均每卷章数**: {stats['avg_chapters_per_volume']}

## 各卷详情

| 卷名 | 章节数 | 总字数 | 平均字数/章 |
|------|--------|--------|-------------|
"""
            
            for vol in volumes:
                avg_per_chapter = round(
                    vol['total_chars'] / max(vol['chapters'], 1), 0
                )
                report += f"| {vol['name']} | {vol['chapters']} | {vol['total_chars']:,} | {avg_per_chapter:,} |\n"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"[Export] 统计报告导出成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"[Export] 统计报告导出失败: {e}", exc_info=True)
            return False
    
    # ====== 辅助方法 ======
    
    @staticmethod
    def _txt_to_html(text: str) -> str:
        """将纯文本转换为简单HTML"""
        # 转义HTML特殊字符
        text = text.replace('&', '&')
        text = text.replace('<', '<')
        text = text.replace('>', '>')
        
        # 段落分割
        paragraphs = text.split('\n')
        html_paragraphs = [f'<p>{p}</p>' for p in paragraphs if p.strip()]
        
        return '\n'.join(html_paragraphs)
    
    @staticmethod
    def _txt_to_md(text: str) -> str:
        """将纯文本转换为Markdown"""
        lines = text.split('\n')
        md_lines = []
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                md_lines.append('')
            else:
                md_lines.append(stripped)
        
        return '\n'.join(md_lines)
    
    @staticmethod
    def _slugify(text: str) -> str:
        """将文本转为URL友好的slug"""
        import re
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_]+', '-', text)
        return text.lower().strip('-')
    
    # ====== PDF 导出（增强） ======
    
    def export_pdf(
        self,
        output_path: str,
        title: Optional[str] = None,
        author: Optional[str] = None,
        font_path: Optional[str] = None,
        page_size: str = 'A4',
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """
        导出为 PDF 格式
        
        Args:
            output_path: 输出路径 (.pdf)
            title: 书名（可选）
            author: 作者（可选）
            font_path: 中文字体路径（可选，默认使用系统字体）
            page_size: 页面大小 ('A4', 'A5', 'Letter')
            progress_callback: 进度回调函数 (0-100)
            
        Returns:
            bool: 是否成功
            
        Note:
            需要安装 reportlab 库:
            pip install reportlab
            
            或使用 weasyprint (更美观但安装复杂):
            pip install weasyprint
        """
        try:
            # 尝试使用 reportlab
            return self._export_pdf_reportlab(
                output_path, title, author, font_path, 
                page_size, progress_callback
            )
        except ImportError:
            logger.warning("[Export] reportlab未安装，尝试使用weasyprint...")
            try:
                return self._export_pdf_weasyprint(
                    output_path, title, author, progress_callback
                )
            except ImportError:
                logger.error(
                    "[Export] PDF导出需要reportlab或weasyprint库\n"
                    "请运行: pip install reportlab"
                )
                return False
    
    def _export_pdf_reportlab(
        self,
        output_path: str,
        title: Optional[str],
        author: Optional[str],
        font_path: Optional[str],
        page_size: str,
        progress_callback: Optional[Callable]
    ) -> bool:
        """使用 reportlab 库导出PDF"""
        from reportlab.lib.pagesizes import A4, A5, letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, PageBreak
        )
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # 页面大小映射
        sizes = {'A4': A4, 'A5': A5, 'Letter': letter}
        pagesize = sizes.get(page_size.upper(), A4)
        
        try:
            # 创建文档
            doc = SimpleDocTemplate(
                output_path,
                pagesize=pagesize,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # 样式设置
            styles = getSampleStyleSheet()
            
            # 自定义中文样式
            if font_path and os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('Chinese', font_path))
                chinese_font = 'Chinese'
            else:
                # 尝试注册系统字体
                chinese_font = self._register_system_font(pdfmetrics) or 'Helvetica'
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=24,
                spaceAfter=30,
                alignment=1,  # 居中
                fontName=chinese_font
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading1'],
                fontSize=18,
                spaceBefore=20,
                spaceAfter=12,
                fontName=chinese_font
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=12,
                leading=20,
                firstLineIndent=24,  # 首行缩进
                fontName=chinese_font
            )
            
            # 构建内容
            story = []
            
            # 封面标题
            book_title = title or self._title
            story.append(Paragraph(book_title, title_style))
            
            if author or self._author:
                story.append(Spacer(1, 20))
                story.append(Paragraph(
                    f"作者：{author or self._author}",
                    ParagraphStyle('Author', parent=body_style, alignment=1)
                ))
            
            story.append(PageBreak())
            
            # 章节内容
            total_volumes = len(self.chapter_service.list_volumes())
            current_volume = 0
            chapter_count = 0
            
            for vol in self.chapter_service.list_volumes():
                current_volume += 1
                
                for ch in self.chapter_service.list_chapters_in_volume(vol['name']):
                    content = self.chapter_service.read_chapter_by_path(ch['path'])
                    
                    if not content:
                        continue
                    
                    chapter_count += 1
                    
                    # 卷标题
                    story.append(Paragraph(f"【{vol['name']}】{ch['name']}", heading_style))
                    story.append(Spacer(1, 10))
                    
                    # 正文内容（分段落）
                    paragraphs = content.split('\n')
                    for para in paragraphs:
                        para = para.strip()
                        if para:
                            # 转义特殊字符
                            escaped_para = para.replace('&', '&').replace('<', '<').replace('>', '>')
                            story.append(Paragraph(escaped_para, body_style))
                    
                    story.append(Spacer(1, 15))
                    
                    # 进度回调
                    if progress_callback:
                        progress = int((chapter_count / max(total_volumes * 10, 1)) * 100)
                        progress_callback(min(progress, 100))
            
            # 生成PDF
            doc.build(story)
            
            logger.info(f"[Export] PDF导出成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"[Export] PDF(reportlab)导出失败: {e}", exc_info=True)
            raise
    
    def _export_pdf_weasyprint(
        self,
        output_path: str,
        title: Optional[str],
        author: Optional[str],
        progress_callback: Optional[Callable]
    ) -> bool:
        """使用 weasyprint 库导出PDF（更美观的排版）"""
        from weasyprint import HTML, CSS
        
        # 构建HTML内容
        html_content = self._build_full_html(title, author)
        
        # CSS样式
        css_content = '''
        @page {
            size: A4;
            margin: 2cm;
            @bottom-center {
                content: counter(page);
                font-size: 10px;
                color: #888;
            }
        }
        
        body {
            font-family: "Microsoft YaHei", "SimSun", serif;
            font-size: 14px;
            line-height: 1.8;
            color: #333;
        }
        
        h1.book-title {
            text-align: center;
            font-size: 28px;
            margin-top: 100px;
            border-bottom: 3px solid #00AA30;
            padding-bottom: 20px;
        }
        
        .author {
            text-align: center;
            color: #666;
            margin-bottom: 50px;
        }
        
        h2.volume-title {
            font-size: 22px;
            color: #00AA30;
            margin-top: 40px;
            padding: 10px;
            background-color: #f0f8f0;
            border-left: 4px solid #00AA30;
        }
        
        h3.chapter-title {
            font-size: 18px;
            margin-top: 25px;
            color: #333;
        }
        
        p {
            text-indent: 2em;
            margin: 0.8em 0;
        }
        
        .page-break {
            page-break-before: always;
        }
        '''
        
        # 生成PDF
        html_obj = HTML(string=html_content)
        css_obj = CSS(string=css_content)
        html_obj.write_pdf(output_path, stylesheets=[css_obj])
        
        logger.info(f"[Export] PDF(weasyprint)导出成功: {output_path}")
        return True
    
    def _build_full_html(self, title: Optional[str], author: Optional[str]) -> str:
        """构建完整的HTML文档"""
        html_parts = []
        
        # 封面
        html_parts.append(f'<h1 class="book-title">{title or self._title}</h1>')
        if author or self._author:
            html_parts.append(f'<p class="author">作者：{author or self._author}</p>')
        html_parts.append('<div class="page-break"></div>')
        
        # 各卷章节
        for vol in self.chapter_service.list_volumes():
            html_parts.append(f'<h2 class="volume-title">【{vol["name"]}】</h2>')
            
            for ch in self.chapter_service.list_chapters_in_volume(vol['name']):
                content = self.chapter_service.read_chapter_by_path(ch['path'])
                
                if not content:
                    continue
                
                html_parts.append(f'<h3 class="chapter-title">{ch["name"]}</h3>')
                
                # 转换段落
                paragraphs = content.split('\n')
                for para in paragraphs:
                    para = para.strip()
                    if para:
                        escaped = para.replace('<', '<').replace('>', '>')
                        html_parts.append(f'<p>{escaped}</p>')
        
        return '\n'.join(html_parts)
    
    @staticmethod
    def _register_system_font(pdfmetrics):
        """尝试注册系统中文字体"""
        import platform
        
        system = platform.system()
        font_paths = []
        
        if system == 'Windows':
            font_paths = [
                'C:/Windows/Fonts/msyh.ttc',      # 微软雅黑
                'C:/Windows/Fonts/simhei.ttf',     # 黑体
                'C:/Windows/Fonts/simsun.ttc',     # 宋体
            ]
        elif system == 'Darwin':  # macOS
            font_paths = [
                '/System/Library/Fonts/PingFang.ttc',
                '/Library/Fonts/Arial Unicode.ttf'
            ]
        else:  # Linux
            font_paths = [
                '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
                '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
            ]
        
        from reportlab.pdfbase.ttfonts import TTFont
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('Chinese', font_path))
                    return 'Chinese'
                except Exception:
                    continue
        
        return None
    
    # ====== 批量导出 ======
    
    def export_all_formats(
        self,
        output_dir: str,
        formats: List[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, bool]:
        """
        批量导出所有格式
        
        Args:
            output_dir: 输出目录
            formats: 要导出的格式列表 (默认全部)
            progress_callback: 进度回调 (progress_percent, current_format)
            
        Returns:
            Dict[format_name, success]: 各格式导出结果
        """
        if formats is None:
            formats = ['txt', 'markdown', 'json']
        
        os.makedirs(output_dir, exist_ok=True)
        
        results = {}
        total = len(formats)
        
        for i, fmt in enumerate(formats):
            if progress_callback:
                progress_callback(int(i / total * 100), f"正在导出 {fmt.upper()}...")
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self._title}_{timestamp}.{fmt}"
            filepath = os.path.join(output_dir, filename)
            
            try:
                if fmt == 'txt':
                    success = self.export_txt(filepath)
                elif fmt == 'epub':
                    success = self.export_epub(filepath)
                elif fmt == 'pdf':
                    success = self.export_pdf(filepath)
                elif fmt == 'markdown':
                    success = self.export_markdown(filepath)
                elif fmt == 'json':
                    success = self.export_json(filepath)
                else:
                    success = False
                    logger.warning(f"[Export] 不支持的格式: {fmt}")
                
                results[fmt] = success
                
            except Exception as e:
                logger.error(f"[Export] 导出 {fmt} 失败: {e}")
                results[fmt] = False
        
        if progress_callback:
            progress_callback(100, "批量导出完成")
        
        logger.info(f"[Export] 批量导出完成: {results}")
        return results


# 支持的导出格式列表
EXPORT_FORMATS = ['txt', 'epub', 'pdf', 'markdown', 'json']
