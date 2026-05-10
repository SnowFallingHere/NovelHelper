"""
初始化与创建章节标签页
提供小说初始化和章节创建/管理功能
"""

import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QGroupBox, QFormLayout, QSpinBox,
    QMessageBox, QFileDialog, QProgressBar, QApplication,
    QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal

from .base_tab import BaseTab
from ..core.config_manager import ConfigManager
from ..core.language_manager import language_manager
from ..core.file_manager import get_novel_dir, get_base_dir, check_novel_initialized

import logging
logger = logging.getLogger(__name__)


class CreateTab(BaseTab):
    """初始化与创建章节标签页"""
    
    # 信号定义
    chapter_created = pyqtSignal(str)  # 章节创建成功时发出
    novel_initialized = pyqtSignal()   # 小说初始化完成
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_name = "初始化与创建章节"
        
        # 服务层引用（延迟导入避免循环依赖）
        self._chapter_service = None
        self.tags = []
        
        logger.info(f"[{self.tab_name}] 创建实例")
    
    def _build_ui(self):
        """构建UI界面"""
        from ..ui.widget_factory import (create_button, create_input,
                                         create_label, create_group_box)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        main_layout = QVBoxLayout(scroll_content)
        main_layout.setContentsMargins(20, 12, 20, 12)
        main_layout.setSpacing(16)

        LABEL_W = 90

        self._row_labels = []
        def _add_row(parent_layout, label_text, widget, label_align=None):
            wrapper = QWidget()
            row = QHBoxLayout(wrapper)
            row.setContentsMargins(0, 6, 0, 6)
            row.setSpacing(10)
            lbl = create_label(label_text, bold=True)
            self._row_labels.append(lbl)
            lbl.setFixedWidth(LABEL_W)
            lbl.setMinimumHeight(32)
            align = label_align if label_align is not None else (Qt.AlignRight | Qt.AlignVCenter)
            lbl.setAlignment(align)
            row.addWidget(lbl)
            row.addWidget(widget, 1)
            parent_layout.addWidget(wrapper)

        # ====== 小说信息 ======
        self._info_group = create_group_box(language_manager.tr("novel_info"))
        info_vbox = QVBoxLayout(self._info_group)
        info_vbox.setSpacing(10)

        novel_name = ConfigManager.get('Novel', 'title', fallback='')
        self.novel_title_label = create_label(
            novel_name if novel_name else "未命名小说",
            bold=True, font_size=16
        )
        info_vbox.addWidget(self.novel_title_label)

        self._tag_label = create_label("自定义标签：", bold=True)
        info_vbox.addWidget(self._tag_label)

        self.tag_container = QWidget()
        self.tag_layout = QVBoxLayout(self.tag_container)
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_layout.setSpacing(4)
        info_vbox.addWidget(self.tag_container)

        self.tag_input = QLineEdit()
        self.tag_input.setMinimumHeight(36)
        self.tag_input.setPlaceholderText("输入标签后按回车添加...")
        self.tag_input.returnPressed.connect(self._add_tag)
        info_vbox.addWidget(self.tag_input)

        self._desc_label = create_label("简介：", bold=True)
        info_vbox.addWidget(self._desc_label)

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("输入小说简介、背景设定等信息...")
        self.description_edit.setMinimumHeight(120)
        self.description_edit.textChanged.connect(self._save_novel_info)
        info_vbox.addWidget(self.description_edit)

        main_layout.addWidget(self._info_group)

        # ====== 章节创建 ======
        self.chapter_group = create_group_box(language_manager.tr("chapter_creation"))
        chapter_vbox = QVBoxLayout(self.chapter_group)
        chapter_vbox.setSpacing(10)

        self.volume_name_edit = create_input("如：第一卷", min_height=44)
        _add_row(chapter_vbox, "卷名：", self.volume_name_edit)

        self.chapter_name_edit = create_input("如：第一章 陨落的天才", min_height=44)
        _add_row(chapter_vbox, "章节：", self.chapter_name_edit)

        self.chapter_content_edit = QTextEdit()
        self.chapter_content_edit.setMinimumHeight(120)
        self.chapter_content_edit.setMaximumHeight(200)
        self.chapter_content_edit.setPlaceholderText(
            "在此输入章节开头内容（可选，用于预览）..."
        )
        _add_row(chapter_vbox, "内容预览：", self.chapter_content_edit,
                 label_align=Qt.AlignRight | Qt.AlignTop)

        btn_wrapper = QWidget()
        btn_wrapper.setMinimumHeight(56)
        btn_row = QHBoxLayout(btn_wrapper)
        btn_row.setContentsMargins(LABEL_W + 10, 6, 0, 6)
        btn_row.setSpacing(12)

        self.create_chapter_btn = create_button(
            language_manager.tr("create_chapter_btn"),
            kind='primary', min_height=42, min_width=150,
            on_click=self._on_create_chapter
        )
        btn_row.addWidget(self.create_chapter_btn)

        self.merge_volumes_btn = create_button(
            language_manager.tr("merge_volumes_btn"),
            kind='secondary', min_height=42, min_width=150,
            on_click=self._on_merge_volumes
        )
        btn_row.addWidget(self.merge_volumes_btn)
        btn_row.addStretch()
        chapter_vbox.addWidget(btn_wrapper)

        main_layout.addWidget(self.chapter_group)

        # ====== 快速操作 ======
        self.quick_group = create_group_box(language_manager.tr("quick_operations"))
        quick_vbox = QVBoxLayout(self.quick_group)
        quick_vbox.setSpacing(10)

        quick_btn_row = QHBoxLayout()
        quick_btn_row.setSpacing(12)

        self.init_novel_btn = create_button(
            language_manager.tr("init_novel_btn"),
            kind='primary', min_height=42, min_width=150,
            on_click=self._on_init_novel
        )
        quick_btn_row.addWidget(self.init_novel_btn)

        self.scan_chapters_btn = create_button(
            "扫描章节",
            kind='secondary', min_height=42, min_width=150,
            on_click=self._on_scan_chapters
        )
        quick_btn_row.addWidget(self.scan_chapters_btn)
        quick_btn_row.addStretch()
        quick_vbox.addLayout(quick_btn_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(28)
        self.progress_bar.setVisible(False)
        quick_vbox.addWidget(self.progress_bar)

        self._op_log_label = create_label("操作日志:", bold=True)
        quick_vbox.addWidget(self._op_log_label)
        self.log_output = QTextEdit()
        self.log_output.setMinimumHeight(120)
        self.log_output.setMaximumHeight(300)
        self.log_output.setReadOnly(True)
        quick_vbox.addWidget(self.log_output, 1)

        main_layout.addWidget(self.quick_group, 1)
        main_layout.addStretch()

        scroll.setWidget(scroll_content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        logger.debug(f"[{self.tab_name}] UI构建完成")
    
    def retranslate_ui(self):
        lm = language_manager.tr
        if hasattr(self, '_info_group'):
            self._info_group.setTitle(lm("novel_info"))
        if hasattr(self, 'chapter_group') and self.chapter_group is not None:
            self.chapter_group.setTitle(lm("chapter_creation"))
        if hasattr(self, 'quick_group') and self.quick_group is not None:
            self.quick_group.setTitle(lm("quick_operations"))
        if hasattr(self, 'create_chapter_btn'):
            self.create_chapter_btn.setText(lm("create_chapter_btn"))
        if hasattr(self, 'merge_volumes_btn'):
            self.merge_volumes_btn.setText(lm("merge_volumes_btn"))
        if hasattr(self, 'init_novel_btn'):
            self.init_novel_btn.setText(lm("init_novel_btn"))
        if hasattr(self, 'scan_chapters_btn'):
            self.scan_chapters_btn.setText("扫描章节")
    
    def _load_data(self):
        """加载已有数据"""
        try:
            novel_dir = get_novel_dir()
            dir_name = os.path.basename(os.path.normpath(novel_dir)) if novel_dir else ''
            stored_title = ConfigManager.get('Novel', 'title', fallback='')

            if dir_name and dir_name != stored_title:
                ConfigManager.set('Novel', 'title', dir_name)
                novel_name = dir_name
            else:
                novel_name = stored_title if stored_title else "未命名小说"

            self.novel_title_label.setText(novel_name)

            self.tags = self._load_tags_from_cache()
            self._refresh_tag_ui()

            description = ConfigManager.get('Novel', 'description', fallback='')
            self.description_edit.setPlainText(description)

            if novel_dir and os.path.exists(novel_dir):
                chapter_count = sum(
                    len([f for f in files if f.endswith('.txt')])
                    for _, _, files in os.walk(novel_dir)
                )
                self._log(f"当前目录: {novel_dir}")
                self._log(f"已发现 {chapter_count} 个章节文件")

        except Exception as e:
            logger.error(f"加载数据失败: {str(e)}", exc_info=True)
            self._log(f"加载数据出错: {str(e)}")

        self._apply_startup_visibility()
    
    def _apply_startup_visibility(self):
        """根据初始化状态控制UI区域的显示/隐藏"""
        initialized = check_novel_initialized()
        has_chapter_group = hasattr(self, 'chapter_group') and self.chapter_group is not None
        has_quick_group = hasattr(self, 'quick_group') and self.quick_group is not None

        if initialized:
            if has_chapter_group:
                self.chapter_group.setVisible(False)
            if has_quick_group:
                self.quick_group.setVisible(False)
        else:
            if has_chapter_group:
                self.chapter_group.setVisible(True)
            if has_quick_group:
                self.quick_group.setVisible(True)
    
    def _log(self, message: str):
        """添加日志到日志区域"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_output.append(log_entry)
        
        # 自动滚动到底部
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    # ====== 事件处理方法 ======
    
    def _on_create_chapter(self):
        """创建新章节"""
        raw_volume = self.volume_name_edit.text().strip()
        chapter_name = self.chapter_name_edit.text().strip()
        content = self.chapter_content_edit.toPlainText().strip()

        if not raw_volume or not chapter_name:
            QMessageBox.warning(
                self, "提示",
                "请填写卷名和章节名！"
            )
            return

        try:
            novel_dir = get_novel_dir()
            if not novel_dir:
                QMessageBox.critical(
                    self, "错误",
                    "未设置小说目录！请先初始化小说。"
                )
                return

            # 从用户输入中提取纯标题（去除"第X卷"前缀）
            import re
            title_only = re.sub(r'^第[一二三四五六七八九十百千\d]+卷[\s_]*', '', raw_volume).strip()
            if not title_only:
                title_only = raw_volume

            # 获取卷编号和格式化的目录名
            volume_number = self._get_next_volume_number(novel_dir)
            format_config = ConfigManager.get('Format', 'volume_folder_format',
                                               fallback='{cn.low.Volume}{title}')
            formatted_name = self._format_volume_name(title_only, volume_number, format_config)
            volume_dir = os.path.join(novel_dir, formatted_name)

            # 创建卷目录
            is_new_volume = not os.path.exists(volume_dir)
            if is_new_volume:
                os.makedirs(volume_dir)
                self._log(f"创建卷目录: {formatted_name}")

            # 创建章节文件
            safe_name = self._sanitize_filename(chapter_name)
            chapter_path = os.path.join(volume_dir, f"{safe_name}.txt")

            with open(chapter_path, 'w', encoding='utf-8') as f:
                if content:
                    f.write(content)

            self._log(f"创建章节: {formatted_name} / {chapter_name}")
            self.chapter_created.emit(chapter_path)

            # 更新 get_Volume_update.json
            self._update_volume_json(novel_dir, formatted_name, volume_dir, is_new_volume)

            # 清空输入框
            self.chapter_name_edit.clear()
            self.chapter_content_edit.clear()

            QMessageBox.information(
                self, "成功",
                f"章节已创建:\n{chapter_path}"
            )

        except Exception as e:
            logger.error(f"创建章节失败: {str(e)}", exc_info=True)
            self._log(f"创建章节失败: {str(e)}")
            QMessageBox.critical(
                self, "错误",
                f"创建章节失败: {str(e)}"
            )
    
    def _on_merge_volumes(self):
        """合并卷并导出到 output/ 目录"""
        from PyQt5.QtWidgets import QInputDialog, QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QDialogButtonBox
        
        # 自定义对话框：文件名输入 + 卷分割勾选
        dlg = QDialog(self)
        dlg.setWindowTitle("合并导出")
        dlg.resize(400, 140)
        layout = QVBoxLayout(dlg)
        
        name_layout = QHBoxLayout()
        name_label = QLabel("导出文件名:")
        name_edit = QLineEdit("合并后的卷")
        name_layout.addWidget(name_label)
        name_layout.addWidget(name_edit)
        layout.addLayout(name_layout)
        
        split_cb = QCheckBox("采用卷分割提取")
        split_cb.setChecked(False)
        layout.addWidget(split_cb)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        layout.addWidget(btn_box)
        
        if dlg.exec_() != QDialog.Accepted:
            return
        
        raw_name = name_edit.text().strip()
        if not raw_name:
            return
        
        safe_name = raw_name
        for ch in '<>:"/\\|?*':
            safe_name = safe_name.replace(ch, '')
        if not safe_name:
            safe_name = "merged_volume"
        
        split_enabled = split_cb.isChecked()
        target_filename = safe_name + ".txt"
        novel_dir = get_novel_dir()
        
        # 确保 output/ 目录存在
        output_dir = os.path.join(novel_dir, 'output')
        all_volume_dir = os.path.join(output_dir, 'all_volume')
        volume_divide_dir = os.path.join(output_dir, 'volume_divide')
        os.makedirs(all_volume_dir, exist_ok=True)
        os.makedirs(volume_divide_dir, exist_ok=True)
        
        target_path = os.path.join(all_volume_dir, target_filename)
        
        reply = QMessageBox.question(
            self, "确认导出",
            f"确定要将所有章节合并导出到\n{target_path}\n\n"
            "原始章节文件将保持不变。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            import re
            
            # 收集所有卷目录，按编号前缀排序
            volume_dirs = []
            for d in os.listdir(novel_dir):
                full_path = os.path.join(novel_dir, d)
                if os.path.isdir(full_path):
                    m = re.match(r'^(\d+)', d)
                    if m:
                        volume_dirs.append((int(m.group(1)), full_path, d))
            volume_dirs.sort(key=lambda x: x[0])
            
            total_chapters = 0
            all_source_paths = []
            
            from ..services.chapter_service import ChapterService
            service = ChapterService()
            
            # 收集章节
            for _, vol_path, vol_name in volume_dirs:
                chapter_files = []
                for f in os.listdir(vol_path):
                    if f.endswith('.txt') and f != 'get_Volume_update.json':
                        m = re.match(r'^(\d+)', f)
                        num = int(m.group(1)) if m else 0
                        chapter_files.append((num, f))
                chapter_files.sort(key=lambda x: x[0])
                
                vol_source_paths = []
                for _, filename in chapter_files:
                    src_path = os.path.join(vol_path, filename)
                    vol_source_paths.append(src_path)
                    all_source_paths.append(src_path)
                    total_chapters += 1
                
                # 勾选了才逐卷分割导出
                if split_enabled and vol_source_paths:
                    vol_out_path = os.path.join(volume_divide_dir, f"{vol_name}.txt")
                    service.merge_chapters(vol_source_paths, vol_out_path)
                    self._log(f"  卷分割: {vol_name} -> output/volume_divide/")
            
            # 全量合并导出到 all_volume/
            success = service.merge_chapters(all_source_paths, target_path)
            
            if success:
                msg = f"成功合并 {total_chapters} 个章节\n"
                msg += f"全部合并 → output/all_volume/{target_filename}"
                if split_enabled:
                    msg += "\n逐卷分割 → output/volume_divide/"
                msg += "\n\n原始章节文件已保留。"
                
                self._log(f"合并导出完成: {total_chapters} 个章节 -> {target_path}")
                QMessageBox.information(self, "完成", msg)
            else:
                self._log("合并导出失败：没有找到可合并的章节")
                QMessageBox.warning(self, "提示", "没有找到可合并的章节内容")
                
        except Exception as e:
            logger.error(f"合并导出失败: {str(e)}", exc_info=True)
            self._log(f"合并导出失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"合并导出失败: {str(e)}")
    
    def _on_init_novel(self):
        """初始化小说项目"""
        from PyQt5.QtWidgets import QFileDialog
        
        dir_path = QFileDialog.getExistingDirectory(
            self, 
            "选择小说根目录",
            get_base_dir()
        )
        
        if not dir_path:
            return
        
        reply = QMessageBox.question(
            self, "确认初始化",
            f"将在以下目录初始化小说项目:\n{dir_path}\n\n"
            "是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 5)
            self.progress_bar.setValue(0)
            QApplication.processEvents()
            
            # 步骤1: 创建配置目录
            self._log("创建配置目录...")
            self._create_project_structure(dir_path)
            self.progress_bar.setValue(1)
            QApplication.processEvents()
            
            # 步骤2: 创建8个JSON模板文件
            self._log("创建JSON模板文件...")
            self._create_json_templates(dir_path)
            self.progress_bar.setValue(2)
            QApplication.processEvents()
            
            # 步骤3: 创建首卷及10个章节
            self._log("创建首卷章节...")
            self._create_initial_volume(dir_path)
            self.progress_bar.setValue(3)
            QApplication.processEvents()
            
            # 步骤4: 扫描现有章节
            self._log("扫描现有章节...")
            self._scan_existing_chapters(dir_path)
            self.progress_bar.setValue(4)
            QApplication.processEvents()
            
            # 步骤5: 重启可见性
            self._apply_startup_visibility()
            self.progress_bar.setValue(5)
            QApplication.processEvents()
            
            self.progress_bar.setVisible(False)
            
            novel_name = os.path.basename(os.path.normpath(dir_path))
            ConfigManager.set('Novel', 'title', novel_name)
            self.novel_title_label.setText(novel_name)
            
            self._log("小说项目初始化完成！")
            self.novel_initialized.emit()
            
            QMessageBox.information(
                self, "成功",
                f"小说项目已初始化:\n{dir_path}"
            )
            
        except Exception as e:
            logger.error(f"初始化失败: {str(e)}", exc_info=True)
            self._log(f"初始化失败: {str(e)}")
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "错误", f"初始化失败: {str(e)}")
    
    def _on_scan_chapters(self):
        """扫描章节"""
        novel_dir = get_novel_dir()
        if not novel_dir:
            QMessageBox.warning(self, language_manager.tr("prompt"), language_manager.tr("please_init_or_select_novel_dir"))
            return
        
        self._log(f"开始扫描: {novel_dir}")
        
        total_files = 0
        total_chars = 0
        volumes = {}
        
        for root, dirs, files in os.walk(novel_dir):
            txt_files = [f for f in files if f.endswith('.txt')]
            
            if txt_files:
                vol_name = os.path.basename(root)
                volumes[vol_name] = len(txt_files)
                
                for txt_file in txt_files:
                    filepath = os.path.join(root, txt_file)
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            chars = len(content)
                            total_files += 1
                            total_chars += chars
                            
                    except Exception as e:
                        self._log(f"  读取失败: {txt_file} - {e}")
        
        self._log(f"扫描结果:")
        self._log(f"  总计: {total_files} 个章节, {total_chars:,} 字")
        
        for vol_name, count in sorted(volumes.items()):
            self._log(f"  {vol_name}: {count} 章")
        
        QMessageBox.information(
            self, "扫描完成",
            f"扫描完成:\n\n"
            f"总章节数: {total_files}\n"
            f"总字数: {total_chars:,}\n"
            f"卷数: {len(volumes)}"
        )
    
    # ====== 辅助方法 ======
    
    def _int_to_chinese(self, num: int, variant: str = 'lower') -> str:
        """将阿拉伯数字转为中文数字
        Args:
            num: 数字（1~9999）
            variant: 'upper'=壹贰叁, 'lower'=一二三, 'num'=123
        Returns:
            str: 中文数字
        """
        if variant == 'num':
            return str(num)
        if num < 1 or num > 9999:
            return str(num)

        upper_chars = '零壹贰叁肆伍陆柒捌玖'
        lower_chars = '零一二三四五六七八九'
        chars = upper_chars if variant == 'upper' else lower_chars

        units = ['', '十', '百', '千']
        big_units = ['', '万', '亿']

        def _convert(n: int) -> str:
            if n == 0:
                return '零'
            result = ''
            for i in range(4):
                digit = n % 10
                if digit == 0:
                    if result and result[0] != '零':
                        result = '零' + result
                else:
                    unit = units[i] if i > 0 else ''
                    result = chars[digit] + unit + result
                n //= 10
                if n == 0:
                    break
            return result

        result = ''
        unit_idx = 0
        while num > 0:
            part = num % 10000
            if part != 0:
                part_str = _convert(part)
                if unit_idx > 0:
                    part_str += big_units[unit_idx]
                result = part_str + result
            elif result and not result.startswith('零'):
                result = '零' + result
            num //= 10000
            unit_idx += 1

        return result if result else '零'

    def _format_volume_name(self, title: str, volume_number: int, format_config: str = None) -> str:
        """根据格式模板生成卷目录名
        Args:
            title: 卷标题（如"芜湖"）
            volume_number: 卷编号（从1开始）
            format_config: 格式模板，从配置读取
        Returns:
            str: 格式化后的目录名
        """
        if not format_config:
            format_config = ConfigManager.get('Format', 'volume_folder_format',
                                               fallback='{cn.low.Volume}{title}')

        from datetime import datetime

        cn_upper = self._int_to_chinese(volume_number, 'upper')
        cn_lower = self._int_to_chinese(volume_number, 'lower')

        result = format_config
        result = result.replace('{num}', str(volume_number))
        result = result.replace('{cn.up.Volume}', f'第{cn_upper}卷')
        result = result.replace('{cn.low.Volume}', f'第{cn_lower}卷')
        result = result.replace('{cn.num.Volume}', f'第{volume_number}卷')
        result = result.replace('{en.Volume}', f'Volume{volume_number}')
        result = result.replace('{ip.Volume}', f'{cn_lower}卷')
        result = result.replace('{title}', title)

        display_off = '{display:off}' in result
        result = result.replace('{display:on}', '')
        result = result.replace('{display:off}', '')

        base = f"{volume_number}{result}"

        if display_off:
            return base
        else:
            timestamp = int(datetime.now().timestamp())
            return f"{base}[new_{timestamp}]"

    def _get_next_volume_number(self, novel_dir: str) -> int:
        """扫描小说目录，获取下一个卷编号
        Args:
            novel_dir: 小说根目录
        Returns:
            int: 下一个可用编号
        """
        import re
        if not novel_dir or not os.path.isdir(novel_dir):
            return 1

        max_num = 0
        for d in os.listdir(novel_dir):
            full_path = os.path.join(novel_dir, d)
            if not os.path.isdir(full_path):
                continue
            m = re.match(r'^(\d+)', d)
            if m:
                num = int(m.group(1))
                if num > max_num:
                    max_num = num

        return max_num + 1

    def _update_volume_json(self, novel_dir: str, formatted_name: str, volume_dir: str, is_new_volume: bool):
        """创建或更新卷内的 get_Volume_update.json
        Args:
            novel_dir: 小说根目录
            formatted_name: 格式化后的卷目录名
            volume_dir: 卷目录完整路径
            is_new_volume: 是否为新创建的卷
        """
        from datetime import datetime
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 如果是新卷，将其他所有卷的 is_old 设为 true
        if is_new_volume:
            import re
            for d in os.listdir(novel_dir):
                other_dir = os.path.join(novel_dir, d)
                if not os.path.isdir(other_dir) or other_dir == volume_dir:
                    continue
                other_json = os.path.join(other_dir, 'get_Volume_update.json')
                if os.path.exists(other_json):
                    try:
                        with open(other_json, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        data['is_old'] = True
                        with open(other_json, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass

        # 构建/更新本卷的 JSON
        vol_json_path = os.path.join(volume_dir, 'get_Volume_update.json')
        if os.path.exists(vol_json_path):
            try:
                with open(vol_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = {}
        else:
            data = {}

        # 统计卷内章节
        chapter_files = [f for f in os.listdir(volume_dir)
                         if f.endswith('.txt') and f != 'get_Volume_update.json']
        chapter_count = len(chapter_files)

        # 最近修改的章节（只保留最后10条，防止膨胀）
        recent = []
        from datetime import datetime, timedelta
        three_days_ago = datetime.now() - timedelta(days=3)

        for cf in chapter_files:
            cf_path = os.path.join(volume_dir, cf)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(cf_path))
                if mtime > three_days_ago:
                    with open(cf_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    paragraphs = text.split('\n')
                    recent.append({
                        'chapter': cf.replace('.txt', ''),
                        'timestamp': mtime.strftime('%Y-%m-%d %H:%M:%S'),
                        'modified_paragraph': min(3, len(paragraphs)),
                        'preview': paragraphs[0][:100] if paragraphs else ''
                    })
            except Exception:
                pass

        # 只保留最近3天内的记录
        recent = recent[:50]

        data['volume_name'] = formatted_name
        data['is_old'] = False if is_new_volume else data.get('is_old', False)
        data['created_at'] = data.get('created_at', now_str)
        data['chapter_count'] = chapter_count
        data['latest_update'] = now_str
        data['recent_modifications'] = recent

        try:
            with open(vol_json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"写入 get_Volume_update.json 失败: {e}")

    def _sanitize_filename(self, name: str) -> str:
        """
        清理文件名，移除非法字符
        
        Args:
            name: 原始名称
            
        Returns:
            str: 安全的文件名
        """
        # 移除 Windows 文件名非法字符
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            name = name.replace(char, '')
        
        # 替换空格为下划线
        name = name.replace(' ', '_')
        
        # 限制长度
        if len(name) > 100:
            name = name[:100]
        
        return name or 'untitled'
    
    def _create_project_structure(self, base_dir: str):
        """创建项目目录结构"""
        config_dir = os.path.join(base_dir, '.novel_structure')
        os.makedirs(config_dir, exist_ok=True)
        self._log(f"  创建配置目录: .novel_structure/")
        
        output_dir = os.path.join(base_dir, 'output')
        os.makedirs(os.path.join(output_dir, 'volume_divide'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'all_volume'), exist_ok=True)
        self._log(f"  创建输出目录: output/volume_divide/")
        self._log(f"  创建输出目录: output/all_volume/")
    
    def _create_json_templates(self, base_dir: str):
        """在 .novel_structure/ 下创建8个JSON模板文件"""
        config_dir = os.path.join(base_dir, '.novel_structure')
        os.makedirs(config_dir, exist_ok=True)
        
        templates = {
            'entities.json': [
                {"name": "示例人物", "type": "character", "description": "这是一个示例人物", "personality": "勇敢、正直", "relationships": [{"target": "示例势力", "type": "belongs_to", "description": "成员"}]},
                {"name": "示例技能", "type": "skill", "description": "这是一个示例技能"},
                {"name": "示例地点", "type": "location", "description": "这是一个示例地点", "region": "东部大陆"},
                {"name": "示例物品", "type": "item", "description": "这是一个示例物品"}
            ],
            'factions.json': [
                {"name": "示例势力", "type": "faction", "description": "这是一个势力描述", "leader": "族长名字", "members": ["示例人物"], "headquarters": "示例地点"}
            ],
            'relationships.json': [
                {"name": "示例关系", "type": "relationship", "description": "这是一个关系描述", "source": "示例人物", "target": "示例势力", "relation_type": "belongs_to"}
            ],
            'workspace.json': {
                "notes": [],
                "foreshadowing": [],
                "adventure": [],
                "custom": [],
                "time_point": [],
                "timeline": []
            },
            'user_stopwords.json': {
                "stopwords": [],
                "regex_patterns": []
            },
            '.novel-enhancer.json': {
                "enabled": True,
                "auto_suggest": True,
                "suggestion_count": 3,
                "min_confidence": 0.5
            },
            '.frequency.json': {
                "frequencies": {},
                "is_replace": {},
                "last_scan": ""
            },
            '.chapter_index_cache.json': {
                "version": "1.0",
                "last_update": "",
                "novel_tags": ["奇怪", "神人"],
                "volumes": {},
                "stats": {
                    "total_volumes": 0,
                    "total_chapters": 0,
                    "total_words": 0,
                    "scan_time": 0
                }
            }
        }
        
        for filename, content in templates.items():
            filepath = os.path.join(config_dir, filename)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
                self._log(f"  创建: {filename}")
            except Exception as e:
                self._log(f"  创建 {filename} 失败: {e}")
    
    def _create_initial_volume(self, base_dir: str):
        """创建首卷及10个空白章节"""
        volume_number = self._get_next_volume_number(base_dir)
        format_config = ConfigManager.get('Format', 'volume_folder_format',
                                           fallback='{cn.low.Volume}{title}')
        formatted_name = self._format_volume_name('', volume_number, format_config)
        volume_dir = os.path.join(base_dir, formatted_name)
        os.makedirs(volume_dir, exist_ok=True)
        self._log(f"  创建首卷: {formatted_name}")
        
        # 创建10个章节（1第一章 ~ 10第十章）
        chapter_names = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
        for i, ch_name in enumerate(chapter_names, start=1):
            chapter_file = f"{i}第{ch_name}章.txt"
            chapter_path = os.path.join(volume_dir, chapter_file)
            with open(chapter_path, 'w', encoding='utf-8') as f:
                f.write("")
            self._log(f"  创建章节: {chapter_file}")
        
        # 创建 get_Volume_update.json
        self._update_volume_json(base_dir, formatted_name, volume_dir, True)
    
    def _scan_existing_chapters(self, base_dir: str):
        """扫描并记录现有章节"""
        count = 0
        for root, dirs, files in os.walk(base_dir):
            for filename in files:
                if filename.endswith('.txt'):
                    count += 1
        
        if count > 0:
            self._log(f"  发现 {count} 个现有章节")

    def _get_cache_tags_path(self, novel_dir: str = None) -> str:
        """获取 .chapter_index_cache.json 中 novel_tags 的完整路径"""
        if novel_dir is None:
            novel_dir = get_novel_dir()
        if not novel_dir:
            return ''
        return os.path.join(novel_dir, '.novel_structure', '.chapter_index_cache.json')

    def _load_tags_from_cache(self) -> list:
        """从 .chapter_index_cache.json 的 novel_tags 读取标签"""
        cache_path = self._get_cache_tags_path()
        if not cache_path or not os.path.exists(cache_path):
            return []
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            tags = data.get('novel_tags', [])
            return tags if isinstance(tags, list) else []
        except Exception:
            return []

    def _save_tags_to_cache(self, tags: list):
        """将标签保存到 .chapter_index_cache.json 的 novel_tags"""
        cache_path = self._get_cache_tags_path()
        if not cache_path:
            return
        try:
            if os.path.exists(cache_path):
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
            data['novel_tags'] = tags
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._log(f"  保存标签失败: {e}")

    def _refresh_tag_ui(self):
        """刷新标签UI显示"""
        while self.tag_layout.count():
            item = self.tag_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.tags:
            self.tag_layout.addWidget(QLabel("  (暂无标签)"))
            return

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        for tag in self.tags:
            chip = QPushButton(f"✕ {tag}")
            chip.setStyleSheet(f"""
                QPushButton {{
                    background-color: #0078D4; color: white;
                    border: none; border-radius: 10px;
                    padding: 4px 10px; font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: #d32f2f;
                }}
            """)
            chip.setCursor(Qt.PointingHandCursor)
            chip.setMaximumHeight(24)
            chip.clicked.connect(lambda checked, t=tag: self._remove_tag(t))
            row_layout.addWidget(chip)

        row_layout.addStretch()
        self.tag_layout.addWidget(row_widget)

    def _add_tag(self):
        """添加标签"""
        tag_text = self.tag_input.text().strip()
        if not tag_text:
            return

        if tag_text not in self.tags:
            self.tags.append(tag_text)
            self._save_tags_to_cache(self.tags)
            self._refresh_tag_ui()
            self._log(f"添加标签: {tag_text}")

        self.tag_input.clear()

    def _remove_tag(self, tag):
        """移除标签"""
        if tag in self.tags:
            self.tags.remove(tag)
            self._save_tags_to_cache(self.tags)
            self._refresh_tag_ui()
            self._log(f"移除标签: {tag}")

    def _save_novel_info(self):
        """自动保存简介信息"""
        description = self.description_edit.toPlainText()
        ConfigManager.set('Novel', 'description', description)
