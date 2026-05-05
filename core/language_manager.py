import os
import json
import logging
from .config_manager import ConfigManager

logger = logging.getLogger(__name__)

class LanguageManager:
    DEFAULT_TRANSLATIONS = {
        'zh_CN': {
            'app_title': '小说助手',
            'monitor_started': '监控已启动',
            'monitor_stopped': '监控已停止',
            'new_chapter_detected': '检测到新章节',
            'chapter_updated': '章节已更新',
            'new_folder_detected': '发现新文件夹',
            'new_chapters_added': '新增章节',
            'empty_chapters_deleted': '删除无内容章节',
            'old_volume_marked': '自动标记旧卷',
            'new_volume_marked': '自动标记新卷',
            'summary_triggered': '触发Summary',
            'waiting_for_write': '等待写入',
            'active': '活跃',
            'new': '新增',
            'volume_word_count': '本卷字数',
            'chapter_1': '第一章',
            'add_new_volume_btn': '增加新卷',
            'execute_summary': '执行 Summary',
            'parameter_config': '参数配置',
            'summary_merge_tool': 'Summary 合并工具',
            'create_chapters': '创建章节',
            'monitor_management': '监控管理',
            'user_guide': '使用说明',
            'keyword_manager': '关键词管理',
            'keyword_page_title': '=== 关键词管理系统 ===',
            'keyword_tab_title': '关键词管理',
            'refresh_btn': '刷新关键词',
            'add_btn': '添加关键词',
            'delete_btn': '删除关键词',
            'edit_btn': '编辑关键词',
            'keyword_name_label': '关键词名:',
            'keyword_type_label': '类型:',
            'keyword_desc_label': '描述:',
            'keyword_color_label': '颜色:',
            'keyword_related_label': '相关关键词 (逗号分隔):',
            'keyword_type_foreshadowing': '伏笔',
            'keyword_type_character': '人物',
            'keyword_type_skill': '技能',
            'keyword_type_location': '地点',
            'keyword_type_item': '物品',
            'keyword_type_relationship': '关系',
            'keyword_type_custom': '自定义',
            'view_all_keywords': '全部关键词',
            'view_by_type': '按类型查看',
            'keyword_list_title': '关键词列表',
            'keyword_count': '关键词数量: {0}',
            'create_sample_config': '创建示例配置',
            'sample_config_created': '示例配置已创建: {0}',
            'create_runtime_env': '⚙ 创建运行环境',
            'exit_program': '⏻ 退出程序',
            'chapter_template_tool': '=== 章节模板创建工具 ===',
            'enter_start_chapter': '输入起始章节号',
            'enter_end_chapter': '输入结束章节号',
            'enter_file_suffix': '输入文件名后缀',
            'start_chapter_label': '起始章节',
            'end_chapter_label': '结束章节',
            'file_suffix_label': '文件后缀:',
            'start_creation': '开始创建',
            'select_directory': '选择目录',
            'save_directory_label': '保存目录:',
            'creation_result': '创建结果',
            'run_mode': '运行模式',
            'stats_only': '1. 仅统计并收集（不重命名文件夹）',
            'stats_and_rename': '2. 统计并重命名文件夹（默认）',
            'progress': '进度',
            'execution_result': '执行结果',
            'param_config_page': '=== 参数配置 ===',
            'ui_size_config': 'UI 尺寸配置',
            'base_font_size': '基础字号',
            'title_font_size': '标题字号',
            'log_font_size': '日志字号',
            'initial_width': '初始宽度',
            'initial_height': '初始高度',
            'min_width': '最小宽度',
            'min_height': '最小高度',
            'ui_color_config': 'UI 颜色配置',
            'bg_color': '背景颜色',
            'fg_color': '字体颜色',
            'border_color': '边框颜色',
            'error_color': '错误颜色',
            'btn_bg': '按钮背景',
            'btn_hover': '按钮悬停',
            'input_bg': '输入框背景',
            'monitor_config': '监控配置',
            'monitor_interval': '监控间隔',
            'pregenerate_chapters': '预生成章节数',
            'trigger_word_count': '触发字数',
            'adaptive_config': '自适应配置',
            'area_scale': '面积缩放倍数',
            'height_scale': '高度缩放倍数',
            'font_increment': '字号增加量',
            'format_config': '格式配置',
            'export_filename_format': '文件名格式',
            'export_volume_format': '卷标题格式',
            'export_chapter_format': '章节标题格式',
            'format_help_filename': '格式：{num}=数字、{cn.up.Chapter}=第壹佰伍拾叁章、{cn.low.Chapter}=第一百五十三章、{cn.num.Chapter}=第153章、{en.Chapter}=Chapter153、{jp.Chapter}=第一百五十三章、{title}=标题名、{types:xxx}=后缀 | 示例：{cn.low.Chapter}{title}{types:markdown} → 1第一章_title.md',
            'format_help_volume': '格式：{cn.up.Volume}=第壹佰伍拾叁卷、{cn.low.Volume}=第一百五十三卷、{cn.num.Volume}=第153卷、{en.Volume}=Volume153、{jp.Volume}=第一百五十三巻、{name}=卷名、{word_count}=字数 | _在语言格式和{name}之间时自动转为·',
            'format_help_chapter': '格式：{cn.up.Chapter}=第壹佰伍拾叁章、{cn.low.Chapter}=第一百五十三章、{cn.num.Chapter}=第153章、{en.Chapter}=Chapter153、{jp.Chapter}=第一百五十三章、{name}=后缀 | _在语言格式和{name}之间时自动转为·',
            'preview_color': '预览颜色',
            'preview_font_size': '预览字号',
            'language_config': '语言配置',
            'select_language': '选择语言',
            'tip_change_language': '提示：切换语言后点击「保存并应用」生效',
            'save_and_apply': '保存并应用',
            'save_config': '保存配置',
            'reload': '重新加载',
            'user_guide_page': '=== 使用说明 ===',
            'monitor_system': '=== 监控管理系统 ===',
            'status_stopped': '状态: 已停止',
            'status_running': '状态: 运行中',
            'log_filter': '日志筛选',
            'folder_status': '文件夹状态',
            'recent_operations': '最近操作',
            'add_new_volume': '📖 增加新卷',
            'start_monitor': '启动监控',
            'stop_monitor': '停止监控',
            'confirm': '确认',
            'cancel': '取消',
            'confirm_exit': '确认退出',
            'exit_confirm_msg': '确定要退出程序吗？\n所有线程将会安全停止。',
            'env_not_initialized': '环境未初始化',
            'env_init_tip': '请先点击「创建运行环境」按钮！',
            'success': '成功',
            'error': '错误',
            'warning': '警告',
            'config_saved_restart': '配置已保存！\n重启程序后生效。',
            'config_saved_applied': '配置已保存并应用！',
            'config_reloaded': '配置已重新加载！',
            'save_config_failed': '保存配置失败',
            'save_apply_failed': '保存并应用失败',
            'reload_failed': '重新加载配置失败',
            'confirm_creation': '确认创建',
            'creating_runtime_env': '即将创建运行环境：',
            'create_folders': '1. 在当前目录创建 /all, /novel, /log 文件夹',
            'generate_templates': '2. 在 /all 生成章节模板',
            'create_title_folder': '3. 在 /novel 创建 title 文件夹',
            'copy_first_10': '4. 复制前10章到 /novel/title/1',
            'continue_question': '是否继续？',
            'new_volume_created': '已创建新卷',
            'add_volume_failed': '增加新卷失败',
            'monitor_auto_process': '监控正在运行，将自动处理新卷。',
            'start_monitor_process': '请启动监控来处理新卷。',
            'dir_not_exist': '目录不存在',
            'dir_not_exist_question': '目录不存在：{0}\n是否创建？',
            'create_question': '是否创建？',
            'create_dir_failed': '创建目录失败',
            'dir_not_writable': '目录不可写',
            'start_must_gt_zero': '起始章节必须大于0',
            'end_must_gt_zero': '结束章节必须大于0',
            'start_lt_end': '起始章节不能大于结束章节',
            'enter_valid_int': '请输入有效的正整数',
            'skipped_existing': '跳过已存在的',
            'files_unit': '个文件',
            'created_successfully': '成功创建',
            'clear_file_failed': '清空文件失败',
            'read_failed': '读取失败',
            'completed_cjk': '完成！CJK字符',
            'non_whitespace': '非空白字符',
            'filter_all': '全部',
            'filter_recent_15': '最近15条',
            'filter_recent_30': '最近30条',
            'filter_recent_50': '最近50条',
            'start_new_program': '启动新程序',
            'start_program_now_question': '是否立即启动新程序？',
            'create_env_failed': '创建运行环境失败',
            'start_program_failed': '启动新程序失败',
            'no_volume_folders': '没有找到卷文件夹！',
            'folder_exists': '文件夹 {0} 已存在！',
            'generating_chapters': '正在生成 {0} 章模板...',
            'novel_dir': '小说目录:',
            'select': '选择...',
            'select_novel_directory': '选择小说目录',
            'initialize_directory': '初始化目录',
            'initialize_directory_msg': '目录为空或没有找到卷文件夹，是否自动初始化？\n\n将创建：\n  - 1[new_0]/ 目录（第一卷）\n  - 10个无内容章节\n\n继续吗？',
            'check_directory_failed': '检查目录失败',
            'initialize_complete': '目录初始化完成！',
            'initialize_failed': '初始化目录失败',
            'monitor_check_error': '监控检查异常',
            'monitor_fatal_error': '监控线程致命错误',
            'init_folders_failed': '初始化文件夹失败',
            'new_folder_state': '发现新文件夹状态',
            'monitor_error': '监控线程错误',
            'prev_volume_not_found': '未找到上一卷',
            'delete_empty_chapter_failed': '删除无内容章节失败',
            'cannot_determine_start_chapter': '无法确定开始章节',
            'create_chapter_failed': '创建章节失败',
            'mark_old_volume_failed': '自动标记旧卷失败',
            'mark_new_volume_failed': '自动标记新卷失败',
            'process_new_volume_failed': '处理新卷文件夹失败',
            'summary_execute_failed': 'Summary执行失败',
            'novel_dir_label': '小说目录',
            'language_settings': '语言设置',
            'language': '语言',
            'save_and_apply': '保存并应用',
            'reload_config': '重载配置',
            'help_content': """【一、灵活的目录选择
====================
★ 程序可以放在任意位置，无需固定目录结构
★ 通过GUI选择任意文件夹作为小说目录
★ 自动初始化会在选定目录创建必要结构

【二、首次设置步骤
==================
1. 启动程序
2. 进入「参数配置」标签页
3. 点击「小说目录」旁边的「选择...」按钮
4. 选择你要存放小说的文件夹
5. 如果文件夹为空，程序会询问是否自动初始化
6. 选择「是」将自动创建：
   - 1[new_0]/ 目录（第一卷，含10个空章节）

【三、功能说明
=============
1. 创建章节
   - 用于在小说目录中创建章节模板文件
   - 起始和结束章节必须是正整数
   - 文件后缀默认为 "name"
   - 如果文件已存在会自动跳过

2. Summary合并
   - 统计所有卷目录
   - 合并章节为一个完整文件
   - 可选择是否重命名文件夹（加上字数后缀）
   - 可自定义导出格式（见参数配置）

3. 监控管理
   - 自动监控小说文件夹
   - 检测到最新章节被编写后自动新增2章
   - 每到2的倍数章节自动触发Summary
   - 日志可筛选查看数量

4. 自动卷管理
   - 创建新卷文件夹（点击「增加新卷」）
   - 用字数标签标记旧卷 [old_XXXX]
   - 用字数标签标记新卷 [new_XXXX]

【四、目录结构
=============
程序可以适应任意目录结构。自动初始化后会创建：

  your_folder/
  ├─ 1[new_0]/         ← 第一卷（含10个空章节）
  └─ NovelHelper.ini    ← 配置文件

【五、文件夹命名规则
====================
卷文件夹：数字[卷名]
  例如：1[第一卷]、2[第二卷]、1[new_0]、2[old_12345]

章节文件：数字第...txt
  例如：1第一章_name.txt、2第二章_.txt

【六、注意事项与风险
====================
⚠️  重要警告！

1. 文件备份
   - 使用前务必备份重要数据！
   - 误操作可能导致文件被覆盖

2. 不要随意删除文件
   - 监控运行时不要随意删除章节文件
   - 删除可能导致监控异常
   - 如需删除请先停止监控

3. 权限问题
   - 确保有文件夹和文件有读写权限
   - 选择具有适当权限的目录

4. Summary功能
   - 会生成合并后的文本文件
   - 重命名模式会修改文件夹名
   - 使用前确认备份！

5. 监控功能
   - 监控每15秒检查一次（可配置）
   - 自动新增领先2章（可配置）
   - 默认内容字数超过20字触发（可配置）

【七、多语言支持
===============
内置语言：简体中文、English、日本語

在「参数配置」标签页切换语言，然后保存并重启生效。
""",
        },
        'en_US': {
            'app_title': 'Novel Helper',
            'monitor_started': 'Monitor Started',
            'monitor_stopped': 'Monitor Stopped',
            'new_chapter_detected': 'New Chapter Detected',
            'chapter_updated': 'Chapter Updated',
            'new_folder_detected': 'New Folder Detected',
            'new_chapters_added': 'New Chapters Added',
            'empty_chapters_deleted': 'Empty Chapters Deleted',
            'old_volume_marked': 'Old Volume Marked',
            'new_volume_marked': 'New Volume Marked',
            'summary_triggered': 'Summary Triggered',
            'waiting_for_write': 'Waiting for Write',
            'active': 'Active',
            'new': 'New',
            'volume_word_count': 'Volume Word Count',
            'chapter_1': 'Chapter 1',
            'add_new_volume_btn': 'Add New Volume',
            'execute_summary': 'Execute Summary',
            'parameter_config': 'Parameter Configuration',
            'summary_merge_tool': 'Summary Merge Tool',
            'create_chapters': 'Create Chapters',
            'monitor_management': 'Monitor Management',
            'user_guide': 'User Guide',
            'keyword_manager': 'Keyword Manager',
            'keyword_page_title': '=== Keyword Management System ===',
            'keyword_tab_title': 'Keyword Manager',
            'refresh_btn': 'Refresh Keywords',
            'add_btn': 'Add Keyword',
            'delete_btn': 'Delete Keyword',
            'edit_btn': 'Edit Keyword',
            'keyword_name_label': 'Keyword Name:',
            'keyword_type_label': 'Type:',
            'keyword_desc_label': 'Description:',
            'keyword_color_label': 'Color:',
            'keyword_related_label': 'Related Keywords (comma sep):',
            'keyword_type_foreshadowing': 'Foreshadowing',
            'keyword_type_character': 'Character',
            'keyword_type_skill': 'Skill',
            'keyword_type_location': 'Location',
            'keyword_type_item': 'Item',
            'keyword_type_relationship': 'Relationship',
            'keyword_type_custom': 'Custom',
            'view_all_keywords': 'All Keywords',
            'view_by_type': 'View By Type',
            'keyword_list_title': 'Keyword List',
            'keyword_count': 'Keyword Count: {0}',
            'create_sample_config': 'Create Sample Config',
            'sample_config_created': 'Sample config created: {0}',
            'create_runtime_env': '⚙ Create Runtime Environment',
            'exit_program': '⏻ Exit Program',
            'chapter_template_tool': '=== Chapter Template Creation Tool ===',
            'enter_start_chapter': 'Enter Start Chapter',
            'enter_end_chapter': 'Enter End Chapter',
            'enter_file_suffix': 'Enter File Name Suffix',
            'start_chapter_label': 'Start Chapter',
            'end_chapter_label': 'End Chapter',
            'file_suffix_label': 'File Suffix:',
            'start_creation': 'Start Creation',
            'select_directory': 'Select Directory',
            'save_directory_label': 'Save Directory:',
            'creation_result': 'Creation Result',
            'run_mode': 'Run Mode',
            'stats_only': '1. Statistics Only (No Rename)',
            'stats_and_rename': '2. Statistics And Rename',
            'progress': 'Progress',
            'execution_result': 'Execution Result',
            'param_config_page': '=== Parameter Configuration ===',
            'ui_size_config': 'UI Size Configuration',
            'base_font_size': 'Base Font Size',
            'title_font_size': 'Title Font Size',
            'log_font_size': 'Log Font Size',
            'initial_width': 'Initial Width',
            'initial_height': 'Initial Height',
            'min_width': 'Minimum Width',
            'min_height': 'Minimum Height',
            'ui_color_config': 'UI Color Configuration',
            'bg_color': 'Background Color',
            'fg_color': 'Font Color',
            'border_color': 'Border Color',
            'error_color': 'Error Color',
            'btn_bg': 'Button Background',
            'btn_hover': 'Button Hover',
            'input_bg': 'Input Background',
            'monitor_config': 'Monitor Configuration',
            'monitor_interval': 'Monitor Interval',
            'pregenerate_chapters': 'Pre-generate Chapters',
            'trigger_word_count': 'Trigger Word Count',
            'adaptive_config': 'Adaptive Configuration',
            'area_scale': 'Area Scale Factor',
            'height_scale': 'Height Scale Factor',
            'font_increment': 'Font Size Increment',
            'format_config': 'Format Configuration',
            'export_filename_format': 'Filename Format',
            'export_volume_format': 'Volume Title Format',
            'export_chapter_format': 'Chapter Title Format',
            'format_help_filename': 'Format: {num}=num, {cn.up.Chapter}=第壹佰伍拾叁章, {cn.low.Chapter}=第一百五十三章, {cn.num.Chapter}=第153章, {en.Chapter}=Chapter153, {jp.Chapter}=第一百五十三章, {title}=title, {types:xxx}=extension | Example: {cn.low.Chapter}{title}{types:markdown} → 1第一章_title.md',
            'format_help_volume': 'Format: {cn.up.Volume}=第壹佰伍拾叁卷, {cn.low.Volume}=第一百五十三卷, {cn.num.Volume}=第153卷, {en.Volume}=Volume153, {jp.Volume}=第一百五十三巻, {name}=name, {word_count}=count | _ between lang format and {name} auto to ·',
            'format_help_chapter': 'Format: {cn.up.Chapter}=第壹佰伍拾叁章, {cn.low.Chapter}=第一百五十三章, {cn.num.Chapter}=第153章, {en.Chapter}=Chapter153, {jp.Chapter}=第一百五十三章, {name}=suffix | _ between lang format and {name} auto to ·',
            'preview_color': 'Preview Color',
            'preview_font_size': 'Preview Font Size',
            'language_config': 'Language Configuration',
            'select_language': 'Select Language',
            'tip_change_language': 'Tip: Click Save & Apply after changing language',
            'save_and_apply': 'Save & Apply',
            'save_config': 'Save Configuration',
            'reload': 'Reload',
            'user_guide_page': '=== User Guide ===',
            'monitor_system': '=== Monitor Management System ===',
            'status_stopped': 'Status: Stopped',
            'status_running': 'Status: Running',
            'log_filter': 'Log Filter',
            'folder_status': 'Folder Status',
            'recent_operations': 'Recent Operations',
            'add_new_volume': '📖 Add New Volume',
            'start_monitor': 'Start Monitor',
            'stop_monitor': 'Stop Monitor',
            'confirm': 'Confirm',
            'cancel': 'Cancel',
            'confirm_exit': 'Confirm Exit',
            'exit_confirm_msg': 'Are you sure to exit? All threads will stop safely.',
            'env_not_initialized': 'Environment Not Initialized',
            'env_init_tip': 'Please click Create Runtime Environment first!',
            'success': 'Success',
            'error': 'Error',
            'warning': 'Warning',
            'config_saved_restart': 'Configuration saved! Restart to take effect.',
            'config_saved_applied': 'Configuration saved and applied!',
            'config_reloaded': 'Configuration reloaded!',
            'save_config_failed': 'Save configuration failed',
            'save_apply_failed': 'Save and apply failed',
            'reload_failed': 'Reload configuration failed',
            'confirm_creation': 'Confirm Creation',
            'creating_runtime_env': 'Creating runtime environment:',
            'create_folders': '1. Create /all, /novel, /log folders in current directory',
            'generate_templates': '2. Generate chapter templates in /all',
            'create_title_folder': '3. Create title folder in /novel',
            'copy_first_10': '4. Copy first 10 chapters to /novel/title/1',
            'continue_question': 'Continue?',
            'new_volume_created': 'New volume created',
            'add_volume_failed': 'Add new volume failed',
            'monitor_auto_process': 'Monitor is running, will process automatically.',
            'start_monitor_process': 'Please start monitor to process new volume.',
            'dir_not_exist': 'Directory does not exist',
            'dir_not_exist_question': 'Directory does not exist: {0}\nCreate it?',
            'create_question': 'Create?',
            'create_dir_failed': 'Create directory failed',
            'dir_not_writable': 'Directory not writable',
            'start_must_gt_zero': 'Start chapter must be greater than 0',
            'end_must_gt_zero': 'End chapter must be greater than 0',
            'start_lt_end': 'Start cannot be greater than end',
            'enter_valid_int': 'Please enter a valid positive integer',
            'skipped_existing': 'Skipped existing',
            'files_unit': 'files',
            'created_successfully': 'Successfully created',
            'clear_file_failed': 'Clear file failed',
            'read_failed': 'Read failed',
            'completed_cjk': 'Completed! CJK characters',
            'non_whitespace': 'Non-whitespace characters',
            'filter_all': 'All',
            'filter_recent_15': 'Recent 15',
            'filter_recent_30': 'Recent 30',
            'filter_recent_50': 'Recent 50',
            'start_new_program': 'Start New Program',
            'start_program_now_question': 'Start the new program now?',
            'create_env_failed': 'Failed to create runtime environment',
            'start_program_failed': 'Failed to start new program',
            'no_volume_folders': 'No volume folders found!',
            'folder_exists': 'Folder {0} already exists!',
            'generating_chapters': 'Generating {0} chapter templates...',
            'novel_dir': 'Novel Directory:',
            'select': 'Select...',
            'select_novel_directory': 'Select Novel Directory',
            'initialize_directory': 'Initialize Directory',
            'initialize_directory_msg': 'Directory is empty or no volume folders found. Auto-initialize?\n\nWill create:\n  - 1[new_0]/ (Volume 1)\n  - 10 empty chapters\n\nContinue?',
            'check_directory_failed': 'Check directory failed',
            'initialize_complete': 'Directory initialization complete!',
            'initialize_failed': 'Initialize directory failed',
            'monitor_check_error': 'Monitor check error',
            'monitor_fatal_error': 'Monitor thread fatal error',
            'init_folders_failed': 'Initialize folders failed',
            'new_folder_state': 'New folder state found',
            'monitor_error': 'Monitor thread error',
            'prev_volume_not_found': 'Previous volume not found',
            'delete_empty_chapter_failed': 'Delete empty chapter failed',
            'cannot_determine_start_chapter': 'Cannot determine start chapter',
            'create_chapter_failed': 'Create chapter failed',
            'mark_old_volume_failed': 'Mark old volume failed',
            'mark_new_volume_failed': 'Mark new volume failed',
            'process_new_volume_failed': 'Process new volume folder failed',
            'summary_execute_failed': 'Summary execution failed',
            'novel_dir_label': 'Novel Directory',
            'language_settings': 'Language Settings',
            'language': 'Language',
            'save_and_apply': 'Save & Apply',
            'reload_config': 'Reload Config',
            'help_content': """【一、Flexible Directory Selection
========================================
★ Program can be placed anywhere - no fixed directory structure required
★ Select any folder as your novel directory via GUI
★ Auto-initialization creates necessary structure in selected directory

【二、First Time Setup
=====================
1. Launch the program
2. Go to "Parameter Configuration" tab
3. Click "Select..." button next to "Novel Directory"
4. Choose your novel storage folder
5. If the folder is empty, click "Yes" to auto-initialize
6. Program will automatically create:
   - 1[new_0]/ (Volume 1 with 10 empty chapters)

【三、Function Description
==========================
1. Create Chapters
   - Used to create chapter template files in the novel directory
   - Start and end chapters must be positive integers
   - Default file suffix is "name"
   - Automatically skips existing files

2. Summary Merge
   - Statistics all volume directories
   - Merges chapters into a complete file
   - Can choose whether to rename folders (add word count suffix)
   - Customizable export format (see Parameter Configuration)

3. Monitor Management
   - Automatically monitors novel folders
   - Automatically adds 2 chapters when latest chapter is written
   - Auto-triggers Summary at every multiple of 2 chapter
   - Logs can be filtered by count

4. Auto Volume Management
   - Create new volume folders (click "Add New Volume")
   - Mark old volumes with word count tags [old_XXXX]
   - Mark new volumes with word count tags [new_XXXX]

【四、Directory Structure
========================
Program works with any directory. After auto-initialization:

  your_folder/
  ├─ 1[new_0]/         ← Volume 1 (with 10 empty chapters)
  └─ NovelHelper.ini    ← Configuration file

【五、Folder Naming Rules
==========================
Volume folders: number[volume name]
  Example: 1[Volume 1]、2[Volume 2]、1[new_0]、2[old_12345]

Chapter files: numberChapter...txt
  Example: 1Chapter_name.txt、2Chapter_.txt

【六、Notes and Risks
=====================
⚠️  Important Warning!

1. File Backup
   - Always backup important data before use!
   - Mistakes may overwrite files

2. Don't Delete Files Arbitrarily
   - Don't delete chapter files while monitor is running
   - Deletion may cause monitor anomalies
   - Stop monitor first if you need to delete

3. Permissions Issues
   - Ensure read/write permissions for folders and files
   - Choose a directory with proper permissions

4. Summary Function
   - Generates merged text file
   - Rename mode modifies folder names
   - Confirm backup before use!

5. Monitor Function
   - Monitor checks every 15 seconds (configurable)
   - Auto-adds 2 leading chapters (configurable)
   - Triggers when default content exceeds 20 words (configurable)

【七、Multi-Language Support
=============================
Built-in languages: English, 简体中文, 日本語

Switch language in "Parameter Configuration" tab, then save and restart.
""",
        },
        'ja_JP': {
            'app_title': '小説ヘルパー',
            'monitor_started': '監視開始',
            'monitor_stopped': '監視停止',
            'new_chapter_detected': '新規章検出',
            'chapter_updated': '章更新',
            'new_folder_detected': '新規フォルダ検出',
            'new_chapters_added': '新規章追加',
            'empty_chapters_deleted': '空章削除',
            'old_volume_marked': '旧巻マーク',
            'new_volume_marked': '新巻マーク',
            'summary_triggered': 'Summaryトリガー',
            'waiting_for_write': '書き込み待ち',
            'active': 'アクティブ',
            'new': '新規',
            'volume_word_count': '巻字数',
            'chapter_1': '第1章',
            'add_new_volume_btn': '新規巻追加',
            'execute_summary': 'Summary実行',
            'parameter_config': 'パラメータ設定',
            'summary_merge_tool': 'Summaryマージツール',
            'create_chapters': '章作成',
            'monitor_management': '監視管理',
            'user_guide': '使用説明',
            'keyword_manager': 'キーワード管理',
            'keyword_page_title': '=== キーワード管理システム ===',
            'keyword_tab_title': 'キーワード管理',
            'refresh_btn': 'キーワードを更新',
            'add_btn': 'キーワード追加',
            'delete_btn': 'キーワード削除',
            'edit_btn': 'キーワード編集',
            'keyword_name_label': 'キーワード名:',
            'keyword_type_label': 'タイプ:',
            'keyword_desc_label': '説明:',
            'keyword_color_label': '色:',
            'keyword_related_label': '関連キーワード（カンマ区切り）:',
            'keyword_type_foreshadowing': '伏線',
            'keyword_type_character': 'キャラクター',
            'keyword_type_skill': 'スキル',
            'keyword_type_location': '場所',
            'keyword_type_item': 'アイテム',
            'keyword_type_relationship': '関係',
            'keyword_type_custom': 'カスタム',
            'view_all_keywords': 'すべてのキーワード',
            'view_by_type': 'タイプで表示',
            'keyword_list_title': 'キーワードリスト',
            'keyword_count': 'キーワード数: {0}',
            'create_sample_config': 'サンプル設定作成',
            'sample_config_created': 'サンプル設定作成: {0}',
            'create_runtime_env': '⚙ 実行環境作成',
            'exit_program': '⏻ プログラム終了',
            'chapter_template_tool': '=== 章テンプレート作成ツール ===',
            'enter_start_chapter': '開始章を入力',
            'enter_end_chapter': '終了章を入力',
            'enter_file_suffix': 'ファイル名接尾辞を入力',
            'start_chapter_label': '開始章',
            'end_chapter_label': '終了章',
            'file_suffix_label': 'ファイル接尾辞:',
            'start_creation': '作成開始',
            'select_directory': 'ディレクトリを選択',
            'save_directory_label': '保存ディレクトリ:',
            'creation_result': '作成結果',
            'run_mode': '実行モード',
            'stats_only': '1. 統計のみ（フォルダ名変更なし）',
            'stats_and_rename': '2. 統計してフォルダ名変更',
            'progress': '進捗',
            'execution_result': '実行結果',
            'param_config_page': '=== パラメータ設定 ===',
            'ui_size_config': 'UIサイズ設定',
            'base_font_size': '基本フォントサイズ',
            'title_font_size': 'タイトルフォントサイズ',
            'log_font_size': 'ログフォントサイズ',
            'initial_width': '初期幅',
            'initial_height': '初期高さ',
            'min_width': '最小幅',
            'min_height': '最小高さ',
            'ui_color_config': 'UI色設定',
            'bg_color': '背景色',
            'fg_color': 'フォント色',
            'border_color': 'ボーダー色',
            'error_color': 'エラー色',
            'btn_bg': 'ボタンバックグラウンド',
            'btn_hover': 'ボタンホバー',
            'input_bg': '入力框バックグラウンド',
            'monitor_config': '監視設定',
            'monitor_interval': '監視間隔',
            'pregenerate_chapters': '予生成章数',
            'trigger_word_count': 'トリガー文字数',
            'adaptive_config': '適応設定',
            'area_scale': '面積倍率',
            'height_scale': '高さ倍率',
            'font_increment': 'フォントサイズ増分',
            'format_config': 'フォーマット設定',
            'export_filename_format': 'ファイル名形式',
            'export_volume_format': '巻タイトル形式',
            'export_chapter_format': '章タイトル形式',
            'format_help_filename': '形式：{num}=数字、{cn.up.Chapter}=第壹佰伍拾叁章、{cn.low.Chapter}=第一百五十三章、{cn.num.Chapter}=第153章、{en.Chapter}=Chapter153、{jp.Chapter}=第一百五十三章、{title}=タイトル名、{types:xxx}=拡張子 | 例：{cn.low.Chapter}{title}{types:markdown} → 1第一章_title.md',
            'format_help_volume': '形式：{cn.up.Volume}=第壹佰伍拾叁巻、{cn.low.Volume}=第一百五十三巻、{cn.num.Volume}=第153巻、{en.Volume}=Volume153、{jp.Volume}=第一百五十三巻、{name}=巻名、{word_count}=文字数 | _ は言語形式と{name}の間で自動的に·に変換',
            'format_help_chapter': '形式：{cn.up.Chapter}=第壹佰伍拾叁章、{cn.low.Chapter}=第一百五十三章、{cn.num.Chapter}=第153章、{en.Chapter}=Chapter153、{jp.Chapter}=第一百五十三章、{name}=接尾辞 | _ は言語形式と{name}の間で自動的に·に変換',
            'preview_color': 'プレビュー色',
            'preview_font_size': 'プレビューフォントサイズ',
            'language_config': '言語設定',
            'select_language': '言語を選択',
            'tip_change_language': 'ヒント：言語変更後は「保存して適用」をクリック',
            'save_and_apply': '保存して適用',
            'save_config': '設定を保存',
            'reload': '再読み込み',
            'user_guide_page': '=== 使用説明 ===',
            'monitor_system': '=== 監視管理システム ===',
            'status_stopped': '状態：停止',
            'status_running': '状態：実行中',
            'log_filter': 'ログフィルター',
            'folder_status': 'フォルダ状態',
            'recent_operations': '最近の操作',
            'add_new_volume': '📖 新規巻追加',
            'start_monitor': '監視開始',
            'stop_monitor': '監視停止',
            'confirm': '確認',
            'cancel': 'キャンセル',
            'confirm_exit': '終了確認',
            'exit_confirm_msg': '終了してもよろしいですか？全スレッドが安全に停止します。',
            'env_not_initialized': '環境未初期化',
            'env_init_tip': '「実行環境作成」ボタンをクリックしてください！',
            'success': '成功',
            'error': 'エラー',
            'warning': '警告',
            'config_saved_restart': '設定が保存されました！再起動後に有効になります。',
            'config_saved_applied': '設定が保存され適用されました！',
            'config_reloaded': '設定が再読み込みされました！',
            'save_config_failed': '設定の保存に失敗しました',
            'save_apply_failed': '保存と適用に失敗しました',
            'reload_failed': '再読み込みに失敗しました',
            'confirm_creation': '作成確認',
            'creating_runtime_env': '実行環境を作成中：',
            'create_folders': '1. 現在のディレクトリに /all, /novel, /log フォルダを作成',
            'generate_templates': '2. /all に章テンプレートを生成',
            'create_title_folder': '3. /novel に title フォルダを作成',
            'copy_first_10': '4. 最初の10章を /novel/title/1 にコピー',
            'continue_question': '続行しますか？',
            'new_volume_created': '新規巻を作成しました',
            'add_volume_failed': '新規巻の追加に失敗しました',
            'monitor_auto_process': '監視が実行中です。自動的に処理されます。',
            'start_monitor_process': '監視を開始して新規巻を処理してください。',
            'dir_not_exist': 'ディレクトリが存在しません',
            'dir_not_exist_question': 'ディレクトリが存在しません: {0}\n作成しますか？',
            'create_question': '作成しますか？',
            'create_dir_failed': 'ディレクトリの作成に失敗しました',
            'dir_not_writable': 'ディレクトリは書き込めません',
            'start_must_gt_zero': '開始章は0より大きくなければなりません',
            'end_must_gt_zero': '終了章は0より大きくなければなりません',
            'start_lt_end': '開始章は終了章より大きくできません',
            'enter_valid_int': '有効な正整数を入力してください',
            'skipped_existing': '既存をスキップ',
            'files_unit': 'ファイル',
            'created_successfully': '作成成功',
            'clear_file_failed': 'ファイルのクリアに失敗しました',
            'read_failed': '読み込みに失敗しました',
            'completed_cjk': '完成！CJK文字',
            'non_whitespace': '非空白文字',
            'filter_all': 'すべて',
            'filter_recent_15': '最近15件',
            'filter_recent_30': '最近30件',
            'filter_recent_50': '最近50件',
            'start_new_program': '新規プログラム起動',
            'start_program_now_question': '新規プログラムを起動しますか？',
            'create_env_failed': '実行環境作成に失敗しました',
            'start_program_failed': '新規プログラム起動に失敗しました',
            'no_volume_folders': '巻フォルダが見つかりません！',
            'folder_exists': 'フォルダ {0} が既に存在します！',
            'generating_chapters': '{0} 章テンプレートを生成中...',
            'novel_dir': '小説ディレクトリ:',
            'select': '選択...',
            'select_novel_directory': '小説ディレクトリを選択',
            'initialize_directory': 'ディレクトリを初期化',
            'initialize_directory_msg': 'ディレクトリが空か巻フォルダが見つかりません。自動的に初期化しますか？\n\n作成内容：\n  - 1[new_0]/（第一巻）\n  - 10個の空き章\n\n続行しますか？',
            'check_directory_failed': 'ディレクトリのチェックに失敗しました',
            'initialize_complete': 'ディレクトリの初期化が完了しました！',
            'initialize_failed': 'ディレクトリの初期化に失敗しました',
            'monitor_check_error': '監視チェック異常',
            'monitor_fatal_error': '監視スレッド致命的エラー',
            'init_folders_failed': 'フォルダ初期化失敗',
            'new_folder_state': '新しいフォルダ状態を発見',
            'monitor_error': '監視スレッドエラー',
            'prev_volume_not_found': '前の巻が見つかりません',
            'delete_empty_chapter_failed': '空章の削除に失敗',
            'cannot_determine_start_chapter': '開始章を特定できません',
            'create_chapter_failed': '章の作成に失敗',
            'mark_old_volume_failed': '旧巻マーク失敗',
            'mark_new_volume_failed': '新巻マーク失敗',
            'process_new_volume_failed': '新巻フォルダ処理失敗',
            'summary_execute_failed': 'サマリー実行失敗',
            'novel_dir_label': '小説ディレクトリ',
            'language_settings': '言語設定',
            'language': '言語',
            'save_and_apply': '保存して適用',
            'reload_config': '設定を再読み込み',
            'help_content': """一、柔軟なディレクトリ選択
==========================================
★ プログラムは任意の位置に配置可能 - 固定ディレクトリ構造不要
★ GUIを通じて任意フォルダを小説ディレクトリとして選択
★ 自動初期化を選択ディレクトリに作成

二、初めての設定手順
=====================
1. プログラムを起動
2.「パラメータ設定」タブを開く
3.「小説ディレクトリ」の横の「選択...」ボタンをクリック
4. 小説を保存するフォルダを選択
5. フォルダが空の場合、プログラムは自動初期化を尋ねます
6.「はい」を選択すると自動作成：
   - 1[new_0]/（第一巻、10個の空の章を含む）

三、機能説明
=============
1. 章作成
   - 小説ディレクトリに章テンプレートファイルを作成するために使用
   - 開始章と終了章は正の整数である必要があります
   - ファイル接尾辞のデフォルトは "name"
   - ファイルが既に存在する場合は自動的にスキップ

2. Summaryマージ
   - すべての巻ディレクトリを統計
   - 章を1つの完全なファイルにマージ
   - フォルダ名を変更するかどうかを選択可能（文字数接尾辞を追加）
   - カスタムエクスポート形式（パラメータ設定を参照）

3. 監視管理
   - 小説フォルダを自動監視
   - 最新の章が書かれたことを検出すると自動的に2章を追加
   - 2の倍数の章ごとに自動的にSummaryをトリガー
   - ログは件数でフィルタリング可能

4. 自動巻管理
   - 新規巻フォルダを作成（「新規巻追加」をクリック）
   - 旧巻を文字数タグでマーク [old_XXXX]
   - 新巻を文字数タグでマーク [new_XXXX]

四、ディレクトリ構造
====================
プログラムは任意ディレクトリ対応。自動初期化後：

  your_folder/
  ├─ 1[new_0]/         ← 第一巻（10個の空の章を含む）
  └─ NovelHelper.ini    ← 設定ファイル

五、フォルダ命名規則
====================
巻フォルダ：数字[巻名]
  例：1[第一巻]、2[第二巻]、1[new_0]、2[old_12345]

章ファイル：数字第...txt
  例：1第一章_name.txt、2第二章_.txt

六、注意事項とリスク
====================
⚠️  重要な警告！

1. ファイルバックアップ
   - 使用前に必ず重要なデータをバックアップしてください！
   - 誤操作によりファイルが上書きされる可能性があります

2. ファイルを勝手に削除しないでください
   - 監視実行中は章ファイルを勝手に削除しないでください
   - 削除により監視が異常になる可能性があります
   - 削除が必要な場合は先に監視を停止してください

3. 権限の問題
   - フォルダとファイルの読み書き権限があることを確認してください
   - 適切な権限を持つディレクトリを選択してください

4. Summary機能
   - マージされたテキストファイルを生成
   - 名前変更モードはフォルダ名を変更します
   - 使用前にバックアップを確認してください！

5. 監視機能
   - 監視は15秒ごとにチェック（設定可能）
   - 自動的に2章先まで追加（設定可能）
   - デフォルトの内容が20文字を超えるとトリガー（設定可能）

七、多言語サポート
==================
組み込み言語：English、简体中文、日本語

「パラメータ設定」タブで言語を切り替え、保存して再起動すると有効になります。
""",
        }
    }
    
    def __init__(self):
        self._current_lang = None
        self._translations = {}
        self._available_languages = []
        self._json_translations = {}
        self.load_translations_from_json()

    def load_translations_from_json(self):
        trans_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'translations')
        if not os.path.isdir(trans_dir):
            return
        for fname in os.listdir(trans_dir):
            if fname.endswith('.json'):
                lang = fname.replace('.json', '')
                fpath = os.path.join(trans_dir, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if lang in data:
                        self._json_translations[lang] = data[lang]
                    logger.info(f"加载翻译文件: {fname}")
                except Exception as e:
                    logger.warning(f"加载翻译文件失败 {fname}: {e}")

    @staticmethod
    def generate_ini_file():
        config_path = ConfigManager.get_config_file_path()
        if os.path.exists(config_path):
            return
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write('[UI]\n')
            f.write('base_font_size = 20\n')
            f.write('base_title_size = 32\n')
            f.write('initial_width = 1006\n')
            f.write('initial_height = 975\n')
            f.write('min_width = 800\n')
            f.write('min_height = 600\n')
            f.write('log_font_size = 16\n')
            f.write('bg_color = #0D0208\n')
            f.write('fg_color = #00FF41\n')
            f.write('border_color = #00FF41\n')
            f.write('accent_color = #00FF41\n')
            f.write('error_color = #FF4444\n')
            f.write('btn_bg_color = #001100\n')
            f.write('btn_hover_color = #003300\n')
            f.write('input_bg_color = #001100\n\n')
            f.write('[Monitor]\n')
            f.write('check_interval = 15\n')
            f.write('max_ahead_chapters = 2\n')
            f.write('min_word_count = 20\n')
            f.write('novel_dir = \n\n')
            f.write('[Adaptive]\n')
            f.write('area_scale_factor = 2\n')
            f.write('height_scale_factor = 1.2\n')
            f.write('font_increase = 4\n\n')
            f.write('[Environment]\n')
            f.write('init_chapter_count = 2000\n')
            f.write('init_copy_count = 10\n')
            f.write('pending_delete = 0\n\n')
            f.write('[Language]\n')
            f.write('current = zh_CN\n')
    
    def load_available_languages(self):
        self._available_languages = list(self.DEFAULT_TRANSLATIONS.keys())
        return self._available_languages
    
    def get_current_language(self):
        if self._current_lang is None:
            self._current_lang = ConfigManager.get('Language', 'current', fallback='zh_CN')
        return self._current_lang
    
    def set_current_language(self, lang_code):
        self._current_lang = lang_code
        ConfigManager.set('Language', 'current', lang_code)
        self._translations = {}
    
    def get_available_languages(self):
        if not self._available_languages:
            self.load_available_languages()
        return self._available_languages
    
    def get_translation(self, key):
        current_lang = self.get_current_language()
        if current_lang in self._json_translations:
            if key in self._json_translations[current_lang]:
                return self._json_translations[current_lang][key]
        if current_lang in self.DEFAULT_TRANSLATIONS:
            if key in self.DEFAULT_TRANSLATIONS[current_lang]:
                return self.DEFAULT_TRANSLATIONS[current_lang][key]
        config = ConfigManager.load_config()
        section = f'Language_{current_lang}'
        if config.has_section(section):
            if config.has_option(section, key):
                return config.get(section, key)
        logger.warning(f"翻译缺失: [{current_lang}] {key}")
        return key
    
    def validate_translations(self):
        all_keys = set()
        for lang, trans in self.DEFAULT_TRANSLATIONS.items():
            all_keys.update(trans.keys())
        
        missing = {}
        for lang in self.DEFAULT_TRANSLATIONS:
            lang_missing = []
            for key in all_keys:
                if key not in self.DEFAULT_TRANSLATIONS[lang]:
                    lang_missing.append(key)
            if lang_missing:
                missing[lang] = lang_missing
        
        if missing:
            for lang, keys in missing.items():
                logger.warning(f"语言 {lang} 缺失 {len(keys)} 个翻译: {', '.join(keys[:5])}{'...' if len(keys) > 5 else ''}")
        return missing
    
    def tr(self, key):
        return self.get_translation(key)


language_manager = LanguageManager()

language_manager = LanguageManager()
