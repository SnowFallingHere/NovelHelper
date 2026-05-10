# NovelHelper 代码参考手册

> 自动生成于 2026-05-09 | 项目根目录: `e:\.novel_saver\NovelStorage\novelhelper`

---

## 一、项目结构总览

```
novelhelper/
├── main_window.py          # 主窗口 (NovelHelper)
├── NovelHelper.py           # 应用入口
│
├── core/                    # 核心基础设施（单例管理器层）
│   ├── theme_manager.py     # ThemeManager - 主题管理单例
│   ├── language_manager.py  # LanguageManager - 多语言管理单例
│   ├── config_manager.py    # ConfigManager - 配置管理单例
│   ├── log_manager.py       # 日志管理
│   ├── font_manager.py       # 字体管理
│   ├── animation_manager.py  # 动画管理
│   ├── chapter_index_cache.py
│   ├── frequency_data_cache.py
│   ├── graph_layout_cache.py
│   └── file_manager.py
│
├── models/                  # 数据模型层
│   ├── keyword_manager.py   # keyword_manager单例 - 关键词数据管理
│   ├── novel_model.py       # Book / Chapter
│   └── summary_generator.py  # 摘要生成
│
├── services/                # 服务层（业务逻辑）
│   ├── chapter_service.py
│   ├── export_service.py
│   └── monitor_service.py
│
├── controllers/             # 控制器层
│   └── monitor_controller.py  # MonitorThread / MonitorController
│
├── tabs/                    # 标签页（视图层，7个标签页）
│   ├── base_tab.py           # BaseTab - 所有标签页基类
│   ├── create_tab.py         # CreateTab - "初始化与创建章节"
│   ├── summary_tab.py         # SummaryTab - "卷&章合并工具"
│   ├── monitor_tab.py         # MonitorTab - "监控管理"
│   ├── keyword_tab.py         # KeywordTab - "关键词管理" (最大最复杂)
│   ├── stats_tab.py           # StatsTab - "统计与分析"
│   ├── config_tab.py          # ConfigTab - "参数配置"
│   └── help_tab.py            # HelpTab - "使用说明"
│
├── ui/                      # UI组件层
│   ├── network_graph.py      # *** 神经图核心 (SciFiNodeItem, SciFiEdge, NetworkGraphView, LegendOverlay, NodeIndexOverlay) ***
│   ├── chapter_creator.py    # ChapterCreator
│   ├── faction_editor.py      # FactionEditorDialog - 势力编辑器
│   ├── faction_list_view.py   # FactionListView / FactionListItem
│   ├── faction_detail_view.py # FactionDetailView
│   ├── family_tree_view.py    # FamilyTreeView / FamilyTreeNode / FamilyTreeEdge
│   ├── style_theme.py         # 样式主题函数（全局样式表生成）
│   ├── theme.py               # 主题常量类 (Colors, Sizes, Fonts, Layout)
│   └── widget_factory.py       # 控件工厂函数
│
├── widgets/                 # 独立Widget组件
│   ├── writing_assistant.py  # WritingAssistant - 写作助理浮窗
│   ├── writing_dashboard.py  # WritingDashboard / StatCard / TrendChart
│   └── timeline_view.py       # TimelineView / TimelineNode / MiniTimelineWidget
│
├── workers/                 # 后台工作线程
│   ├── base_worker.py
│   ├── file_scanner_worker.py
│   ├── frequency_worker.py
│   ├── layout_worker.py
│   ├── multi_thread_integration.py
│   └── task_scheduler.py
│
├── utils/
│   └── writing_assistant.py   # WritingAssistant / WritingSession (数据层)
│
├── translations/             # 多语言翻译文件
│   ├── en.json
│   └── zh_CN.json
│
└── themes/                   # 主题配置文件
    ├── fluent.json
    └── matrix.json
```

---

## 二、main_window.py — 主窗口

**文件**: [main_window.py](file:///e:/.novel_saver/NovelStorage/novelhelper/main_window.py)

### 类: `NovelHelper` (继承 `AcrylicWindow`)

| 属性 | 类型 | 说明 |
|------|------|------|
| `self.settings` | QSettings | 配置持久化 |
| `self.titleBar` | FluentTitleBar | 标题栏 |
| `self.tabs` | QTabWidget | 标签页控件 |
| `self.base_font_size` | int | 基础字体大小 |
| `self.base_title_size` | int | 标题字体大小 |
| `self._save_exit_btn` | QPushButton | **"保存并退出"按钮** (底部) |
| `self._tab_instances` | dict | 标签页实例缓存 |
| `self._tabs_created` | set | 已创建的标签页名集合 |
| `self._init_queue` | list | 延迟初始化队列 |

### NovelHelper 关键方法

| 方法 | 说明 |
|------|------|
| `_build_content()` | 构建主界面布局（底部栏 + 标签页） |
| `create_tab()` → `_create_tab_by_name()` | 创建/懒加载标签页 |
| `_lazy_init_tabs()` → `_process_init_queue()` | 延迟初始化标签页队列 |
| `_on_tab_changed(index)` | 标签页切换事件 |
| `_save_and_exit()` | 保存并退出 |
| `update_ui_language()` | 刷新所有UI语言 |
| `apply_adaptive()` | 自适应窗口 |
| `closeEvent()` | 退出清理 |

### 标签页索引与中文名

| 索引 | 标识 | 中文标签 | Tab类 | 文件 |
|------|------|----------|-------|------|
| 0 | `create` | 初始化与创建章节 | `CreateTab` | [create_tab.py](file:///e:/.novel_saver/NovelStorage/novelhelper/tabs/create_tab.py) |
| 1 | `summary` | 卷&章合并工具 | `SummaryTab` | [summary_tab.py](file:///e:/.novel_saver/NovelStorage/novelhelper/tabs/summary_tab.py) |
| 2 | `monitor` | 监控管理 | `MonitorTab` | [monitor_tab.py](file:///e:/.novel_saver/NovelStorage/novelhelper/tabs/monitor_tab.py) |
| 3 | `keyword` | 关键词管理 | `KeywordTab` | [keyword_tab.py](file:///e:/.novel_saver/NovelStorage/novelhelper/tabs/keyword_tab.py) |
| 4 | `stats` | 统计与分析 | `StatsTab` | [stats_tab.py](file:///e:/.novel_saver/NovelStorage/novelhelper/tabs/stats_tab.py) |
| 5 | `config` | 参数配置 | `ConfigTab` | [config_tab.py](file:///e:/.novel_saver/NovelStorage/novelhelper/tabs/config_tab.py) |
| 6 | `help` | 使用说明 | `HelpTab` | [help_tab.py](file:///e:/.novel_saver/NovelStorage/novelhelper/tabs/help_tab.py) |

### 关键信号连接 (main_window 内)

| 信号 | → | 槽 |
|------|---|-----|
| `self.tabs.currentChanged` | → | `self._on_tab_changed` |
| `self._save_exit_btn.clicked` | → | `self._save_and_exit` |
| `tab.config_saved` | → | `self._on_config_saved` |
| `tab.config_applied` | → | `self._on_config_applied` |
| `tab.overlay_pos_changed` | → | `self._on_overlay_pos_changed` |
| `tab.legend_config_changed` | → | `self._on_legend_config_changed` |
| `tab.glow_config_changed` | → | `self._on_glow_config_changed` |
| `tab.size_sort_config_changed` | → | `self._on_size_sort_config_changed` |

---

## 三、tabs/ — 标签页

### 3.1 base_tab.py — 标签页基类

**文件**: [base_tab.py](file:///e:/.novel_saver/NovelStorage/novelhelper/tabs/base_tab.py)

#### 类: `BaseTab(QWidget)`

| 方法 | 说明 |
|------|------|
| `__init__(parent)` | 初始化，设置 `self._initialized = False` |
| `initialize()` | 初始化入口（调用 `_build_ui` + `_load_data`） |
| `is_initialized()` → bool | 是否已初始化 |
| `_build_ui()` | 子类重写：构建UI |
| `_load_data()` | 子类重写：加载数据 |
| `refresh(force=False)` | 刷新（默认调用 `_load_data`） |
| `cleanup()` | 清理资源 |
| `get_status()` → dict | 获取状态信息 |
| `on_show()` | 标签页显示时回调 |
| `on_hide()` | 标签页隐藏时回调 |

---

### 3.2 keyword_tab.py — 关键词管理（最大标签页）

**文件**: [keyword_tab.py](file:///e:/.novel_saver/NovelStorage/novelhelper/tabs/keyword_tab.py)

#### 类: `ViewMode` (枚举)

值: `LIST_VIEW`, `CARD_VIEW`, `FREQUENCY_VIEW`, `NEURAL_VIEW`

#### 类: `KeywordTab(BaseTab)` — 核心标签页

**关键字视图（6种）之间的切换由工具栏按钮控制。**

| 方法分类 | 方法名 | 说明 |
|----------|--------|------|
| **初始化** | `_load_config()` | 从ConfigManager加载配置 |
| | `_build_ui()` | 构建全部UI（工具栏+视图堆栈） |
| | `_load_data()` | 加载关键词数据 |
| **辅助** | `_s(size)` | 字号缩放 |
| | `_t(key, fallback)` | 多语言翻译 |
| | `_is_dark()` | 是否暗色主题 |
| | `_theme_colors()` | 获取主题色字典 |
| **视图切换** | `_switch_to_view(mode)` | 切换到指定视图 |
| | `_animate_view_fade()` | 视图切换动画 |
| **列表视图** | `render_list_view()` | **渲染列表视图（`[角色] 李玄明` 标签化格式）** |
| **卡片视图** | `render_card_view()` | 渲染卡片视图入口 |
| | `_render_character_list()` | 角色列表 |
| | `_render_character_card(name)` | 单个角色卡片HTML |
| | `_render_location_card(name)` | 地点卡片HTML |
| | `_render_timeline_point_card(name)` | 时间点卡片HTML |
| | `_render_item_card(name)` | 物品卡片HTML |
| | `_render_skill_card(name)` | 技能卡片HTML |
| **频度视图** | `render_frequency_view()` | 渲染频度仪表盘 |
| | `_freq_heat_color(factor)` | 热力图颜色 |
| | `_render_freq_overview(data)` | 频度概览 |
| | `_render_freq_replace(data)` | 替换建议 |
| | `_handle_freq_replace(word)` | 执行替换 |
| | `_handle_freq_unreplace(word)` | 撤销替换 |
| | 配置路径 | 所有 `.frequency.json` / `user_stopwords.json` 读写使用 `get_novel_config_dir()` |
| **神经图** | `render_neural_view()` | **渲染神经图（主入口）** |
| | `_render_neural_view_lazy()` | 延迟渲染神经图 |
| | `_get_graph_layout_path()` | 获取布局缓存路径 |
| | `_show_graph_loading_hint()` | 显示加载提示 |
| | `_build_graph_async()` | 异步构建图数据 |
| | `_save_graph_layout()` | 保存图布局 |
| | `_reset_graph_layout()` | 重置图布局 |
| | `_detect_isolated_nodes()` | 检测孤立节点 |
| | `_export_graph_png()` | 导出PNG |
| | `_on_filter_changed(type, state)` | 节点类型过滤器变化 |
| | `_on_graph_search()` | 搜索节点 |
| | `_on_graph_node_right_click(...)` | 节点右键菜单 |
| | `_on_graph_node_double_clicked(name)` | 节点双击 |
| | `_on_graph_edge_right_click(edge, pos)` | 边右键菜单 |
| | `_rename_graph_node(name)` | 重命名节点 |
| | `_change_node_type(name, type)` | 修改节点类型 |
| | `_delete_graph_node(name)` | 删除节点 |
| | `_invalidate_neural_cache()` | 失效神经图缓存 |
| **配置广播** | `update_config()` | 更新配置到图 |
| | `update_legend_config(visible, font, size)` | 更新图例配置 |
| | `update_connect_btn_config(size, color)` | **更新+号按钮配置** |
| | `update_node_visual_config(min, max, minB, maxB)` | 更新节点视觉配置 |
| | `update_glow_config(enabled)` | 更新辉光配置 |
| | `update_size_sort_config(enabled)` | 更新大小排序配置 |
| | `set_overlay_position(pos)` | 设置节点索引位置 |
| **势力编辑** | `_edit_faction_structure(name)` | 编辑势力 |
| | `_export_faction_structure(name)` | 导出势力 |
| | `_show_faction_list()` | 势力列表视图 |
| | `_show_faction_card(name)` | 势力卡片视图 |
| | `_render_faction_card_html(...)` | 势力卡片HTML |
| | `_set_faction_browser_html(html)` | 设置势力浏览器HTML |
| | `_set_faction_action_buttons_visible(v)` | 势力操作按钮可见性 |
| **家族树** | `_render_family_tree_view()` | 渲染家族树视图 |
| | `_populate_root_combo()` | 填充根节点下拉 |
| | `_on_family_root_changed(text)` | 根节点变化 |
| | `_refresh_family_tree()` | 刷新家族树 |
| | `_load_and_display_family_tree(root)` | 加载显示家族树 |
| | `_show_family_tree_placeholder(msg)` | 占位提示 |
| | `_on_family_node_clicked(name)` | 家族节点点击 |
| | `_export_family_tree_png()` | 导出家族树PNG |
| | `show_family_tree_for_character(name)` | 从角色跳转家族树 |
| | `_select_and_show_family_tree(name)` | 选择并展示家族树 |
| **其他** | `refresh_keywords()` | 刷新关键词 |
| | `_on_keyword_clicked(url)` | URL点击处理 |
| | `_start_frequency_scan()` | 开始频度扫描 |
| | `_sync_keyword_browser_font()` | 同步字体 |
| | `_sync_faction_card_font()` | 同步势力卡字体 |

---

### 3.3 create_tab.py

**文件**: [create_tab.py](file:///e:/.novel_saver/NovelStorage/novelhelper/tabs/create_tab.py)

#### 类: `CreateTab(BaseTab)` — "初始化与创建章节"

| 方法 | 说明 |
|------|------|
| `_build_ui()` | **构建标签系统 + 简介文本框 + 章节创建区域**（移除了旧的小说标题/作者/类型输入） |
| `_load_data()` | **加载标签、简介等数据** |
| `_log(message)` | 日志输出 |
| `_on_create_chapter()` | 创建章节 |
| `_on_merge_volumes()` | **合并导出到小说一级目录**（输入文件名 → 合并所有章节 → 输出到 novelDir/） |
| `_on_init_novel()` | **初始化新小说**（自动设置小说名为目录名） |
| `_on_scan_chapters()` | 扫描已有章节 |
| `_sanitize_filename(name)` | 文件名清理 |
| `_create_project_structure(dir)` | 创建项目目录结构 |
| `_init_config(dir)` | 初始化配置 |
| `_scan_existing_chapters(dir)` | 扫描已有章节 |
| `_add_tag()` | **回车添加标签，自动保存到 ConfigManager** |
| `_remove_tag(tag)` | **点击 ✕ 移除标签** |
| `_save_novel_info()` | **简介文本框 textChanged 自动保存** |
| `_refresh_tag_ui()` | **刷新标签 chips 显示** |

**UI 控件变更**: 旧 `novel_title_edit` / `author_edit` / `genre_combo` → `novel_title_label`(QLabel粗体) + `tag_container`(FlowLayout) + `tag_input`(QLineEdit) + `description_edit`(QTextEdit)

**ConfigManager 配置键**:
- `Novel.tags` — 标签列表（逗号分隔）
- `Novel.description` — 简介文本
- `Novel.title` — 小说名（目录名自动设置）

---

### 3.4 summary_tab.py

**文件**: [summary_tab.py](file:///e:/.novel_saver/NovelStorage/novelhelper/tabs/summary_tab.py)

#### 类: `SummaryTab(BaseTab)` — "卷&章合并工具"

| 方法 | 说明 |
|------|------|
| `_build_ui()` | 构建卷列表 + 进度条 + 结果框 |
| `_load_data()` | 加载卷列表 |
| `_refresh_volume_list()` | 刷新卷列表 |
| `_select_all_volumes()` | 全选 |
| `_deselect_all_volumes()` | 取消全选 |
| `_get_selected_volumes()` | 获取选中的卷 |
| `run_summary()` | 开始摘要任务 |
| `_run_next_volume_summary()` | 处理下一个卷 |
| `_on_single_summary_finished(result)` | 单卷完成 |
| `_on_all_summaries_finished()` | 全部完成 |
| `_on_summary_progress(value)` | 进度更新 |
| `_on_summary_message(msg)` | 消息更新 |
| `_on_summary_error(msg)` | 错误处理 |
| `refresh_data()` | 刷新数据 |

---

### 3.5 monitor_tab.py

**文件**: [monitor_tab.py](file:///e:/.novel_saver/NovelStorage/novelhelper/tabs/monitor_tab.py)

#### 类: `MonitorTab(BaseTab)` — "监控管理"

| 方法 | 说明 |
|------|------|
| `_build_ui()` | 构建监控界面 |
| `_load_data()` | 加载数据 |
| `start_monitor()` | 启动监控 |
| `stop_monitor()` | 停止监控 |
| `_on_monitor_update(states, msgs)` | 监控更新回调 |
| `_on_monitor_error(msg)` | 错误回调 |
| `filter_logs()` | 过滤日志 |
| `update_log_display()` | 更新日志显示 |
| `_show_chapter_preview()` | 章节预览 |
| `_auto_refresh_preview()` | 自动刷新预览 |
| `_on_preview_item_double_clicked(...)` | 预览双击 |
| `_on_auto_summary_request(dir)` | 自动摘要请求 |
| `_on_auto_summary_finished(result)` | 自动摘要完成 |
| `add_new_volume()` | 添加新卷 |
| `cleanup()` | 清理 |

---

### 3.6 stats_tab.py

**文件**: [stats_tab.py](file:///e:/.novel_saver/NovelStorage/novelhelper/tabs/stats_tab.py)

#### 类: `StatsTab(BaseTab)` — "统计与分析"

| 方法 | 说明 |
|------|------|
| `_build_ui()` | 构建统计仪表盘界面 |
| `_load_data()` | 加载数据 |
| `initialize()` | 初始化 |
| `_load_novel_data(dir)` | 加载小说数据 |
| `_load_timeline_from_cache(dir)` | 从缓存加载时间线 |
| `_refresh_all_data()` | 刷新全部数据 |
| `_export_full_report()` | 导出完整报告 |
| `_on_timeline_node_selected(path)` | 时间线节点选中 |
| `_on_timeline_node_clicked(data)` | 时间线节点点击 |
| `_on_timeline_node_double_clicked(path)` | 时间线节点双击 |
| `refresh(force)` | 刷新 |
| `update_config()` | 更新配置 |

---

### 3.7 config_tab.py

**文件**: [config_tab.py](file:///e:/.novel_saver/NovelStorage/novelhelper/tabs/config_tab.py)

#### 类: `ConfigTab(BaseTab)` — "参数配置"

| 方法 | 说明 |
|------|------|
| `_load_all_config_values()` | 加载所有配置值 |
| `_build_ui()` | 构建配置界面（最复杂，大量配置项） |
| `_load_data()` | 加载数据 |
| `_write_config_to_file()` | 写入配置文件 |
| `_select_config_dir()` | 选择配置目录 |
| `save_config()` | 保存配置 |
| `save_and_apply_config()` | 保存并应用配置 **(发射 config_saved + config_applied 信号)** |
| `reload_config()` | 重新加载配置 |
| `_reset_config_default()` | 重置为默认 |
| `update_format_preview()` | 更新格式预览 |
| `_update_format_preview_style()` | 格式预览样式 |
| `_update_format_help_style()` | 格式帮助样式 |
| `_on_overlay_pos_changed()` | 节点索引位置变化 → `overlay_pos_changed` |
| `_on_legend_config_changed()` | 图例配置变化 → `legend_config_changed` |
| `_on_node_visual_config_changed()` | 节点视觉配置变化 |
| `_on_connect_btn_config_changed()` | **连接按钮配置变化** |
| `_on_glow_config_changed(state)` | **辉光配置变化** → `glow_config_changed` |
| `_on_size_sort_config_changed(state)` | 大小排序变化 → `size_sort_config_changed` |
| `_on_brightness_sort_config_changed(state)` | 亮度排序变化 |
| `_show_rule_editor()` | 打开规则编辑器 |
| `_hide_rule_editor()` | 隐藏规则编辑器 |
| `_reset_rule_editor_inputs()` | 重置规则编辑输入 |
| `_on_rule_type_changed(index)` | 规则类型变化 |
| `_save_current_rule()` | 保存当前规则 |
| `_delete_selected_rule()` | 删除选中规则 |
| `_format_rule_display_text(rule)` | 格式化规则显示 |
| `_apply_rules_to_network_graph()` | 应用规则到神经图 |
| `load_custom_rules_from_config()` | 从配置加载自定义规则 |
| `get_current_custom_rules()` | 获取当前规则 |

**重要信号** (定义在 ConfigTab 上):
- `config_saved` — 配置已保存
- `config_applied` — 配置已应用
- `overlay_pos_changed` — 节点索引位置变化
- `legend_config_changed` — 图例配置变化
- `glow_config_changed` — 辉光配置变化
- `size_sort_config_changed` — 大小排序配置变化

---

### 3.8 help_tab.py

**文件**: [help_tab.py](file:///e:/.novel_saver/NovelStorage/novelhelper/tabs/help_tab.py)

#### 类: `HelpTab(BaseTab)` — "使用说明"

| 方法 | 说明 |
|------|------|
| `_build_ui()` | 构建帮助浏览器 |
| `_load_data()` | 加载 |
| `_s(base, scale)` | 字号缩放 |
| `_render_help_html()` | 渲染帮助HTML |
| `refresh_help()` | 刷新帮助 |

---

## 四、ui/ — UI组件

### 4.1 network_graph.py — 神经图（最核心UI文件）

**文件**: [network_graph.py](file:///e:/.novel_saver/NovelStorage/novelhelper/ui/network_graph.py) (~3300行)

---

#### 类: `SciFiNodeItem(QGraphicsItem)` — 节点图形项

**关键属性**:
| 属性 | 说明 |
|------|------|
| `node_name` | 节点名称 |
| `node_type` | 节点类型 (character/location/item/skill/time_point/adventure/faction) |
| `_btn_color` | **+号按钮颜色** (由 `update_connect_btn_config` 设置) |
| `_btn_r` | **+号按钮半径** |
| `_is_dragging` | 是否正在拖拽 |
| `_connect_mode` | **是否处于连线模式（拖+号）** |
| `_drag_line` | 拖拽时显示的临时虚线 QGraphicsPathItem |
| `_drag_start` | 拖拽起始位置 |
| `_selected` | 是否被选中 |
| `_connection_count` | 连接数 |
| `_glow_cache` | 辉光缓存 (QPixmap) |
| `_edge_refs` | 关联的边引用列表 |

**类方法（全局配置）**:
| 类方法 | 说明 |
|--------|------|
| `set_global_max_connections(max)` | 设置全局最大连接数 |
| `set_glow_enabled(bool)` | **设置辉光开关** |
| `set_size_sort_enabled(bool)` | 设置大小排序 |
| `set_brightness_sort_enabled(bool)` | 设置亮度排序 |
| `set_custom_rules(rules)` | 设置自定义规则 |
| `load_custom_rules(rules)` | 加载自定义规则 |
| `get_custom_rules()` | 获取自定义规则 |
| `evaluate_rule_for_node(conn_count)` | 评估规则 |
| `serialize_rules_to_config()` | 序列化规则 |
| `deserialize_rules_from_config(json)` | 反序列化规则 |
| `set_visual_config(min, max, minB, maxB)` | **设置节点视觉配置（大小/亮度范围）** |
| `invalidate_glow_cache()` | 失效辉光缓存 |

**实例方法**:
| 方法 | 说明 |
|------|------|
| `_calc_node_size()` | 计算节点大小 |
| `_effective_size()` | 有效渲染大小 |
| `update_connection_count()` | 更新连接数并重算大小 |
| `boundingRect()` | 边界矩形 |
| `shape()` | **碰撞检测形状（含+号区域）** |
| `paint(painter, option, widget)` | **核心绘制** |
| `_draw_circle(...)` | 圆形节点 |
| `_draw_hexagon(...)` | 六边形节点 |
| `_draw_diamond(...)` | 菱形节点 |
| `_draw_dashed_rect(...)` | 虚线矩形节点 |
| `_draw_adventure(...)` | 冒险节点 |
| `_draw_faction(...)` | 势力节点 |
| `_draw_time_point(...)` | 时间点节点 |
| `_draw_rounded_rect(...)` | 圆角矩形节点 |
| `_draw_glow_cached(...)` | **辉光缓存绘制** |
| `_draw_label(...)` | 标签绘制 |
| `_draw_name(...)` | 名称文字绘制 |
| `set_highlight_color(color)` | 设置高亮色 |
| `add_edge_ref(data)` | 添加边引用 |
| `remove_edge_ref(data)` | 移除边引用 |
| `itemChange(change, value)` | 位置变化事件 |
| `hoverEnterEvent(event)` | 鼠标悬停 |
| `hoverLeaveEvent(event)` | 鼠标离开 |
| `mouseDoubleClickEvent(event)` | 双击事件 |
| `mousePressEvent(event)` | **鼠标按下（含+号拖拽检测）** |
| `mouseMoveEvent(event)` | **鼠标移动（更新拖拽线+目标高亮）** |
| `mouseReleaseEvent(event)` | **鼠标释放（完成连线或移动）** |
| `_show_relation_menu(target)` | 显示关系选择菜单 |

---

#### 类: `SciFiEdge` — 边（连线）

**关键属性**:
| 属性 | 说明 |
|------|------|
| `edge_path` | 主路径 QGraphicsPathItem |
| `glow_path` | **辉光路径** QGraphicsPathItem（含发光效果） |
| `hit_area` | 点击检测区域（加粗透明线） |
| `_arrow_item` | 箭头 QGraphicsPolygonItem |
| `from_name` / `to_name` | 起点/终点节点名 |
| `rel_type` | 关系类型 |
| `_is_dark_background` | **类变量：是否暗色背景（影响辉光颜色）** |

**实例方法**:
| 方法 | 说明 |
|------|------|
| `__init__(scene, from, to, rel_type)` | 创建边 |
| `_create_arrow_item(color)` | 创建箭头 |
| `set_hovered(bool)` | 悬停高亮 |
| `_apply_dim()` | 应用暗淡 |
| `_apply_highlight()` | 应用高亮 |
| `_apply_style()` | 应用样式 |
| `set_force_highlight(on)` | 强制高亮 |
| `_compute_path()` | 计算路径（到节点边界停止） |
| `_update_path()` | 更新路径 |
| `set_visible(bool)` | 设置可见 |
| `update_positions()` | 更新位置 |
| `remove_from_scene()` | 从场景移除 |

**类方法**:
| 方法 | 说明 |
|------|------|
| `highlight_node_edges(name, items, edges)` | 高亮某节点的边 |
| `clear_highlight(edge_items)` | **清除所有边高亮** |

---

#### 类: `LegendOverlay(QWidget)` — 图例浮层

| 方法 | 说明 |
|------|------|
| `__init__(graph_view)` | 初始化 |
| `refresh(type_colors, groups)` | 刷新图例内容 |
| `apply_style(font_name, font_size)` | 应用字体样式 |

---

#### 类: `NodeIndexOverlay(QWidget)` — 节点索引侧栏

**关键属性**:
| 属性 | 说明 |
|------|------|
| `_toggle_btn` | 折叠/展开按钮 |
| `_list_container` | 列表容器 |
| `_start_list` / `_end_list` | 起点列表 / 终点列表 (QListWidget, 勾选模式) |
| `_btn_container` | 按钮容器 |
| `_collapsed` | 是否折叠 |
| `collapsed_width` / `expanded_width` | 36px / 280px |

| 方法 | 说明 |
|------|------|
| `__init__(graph_view, parent)` | 初始化侧栏 |
| `_apply_list_style()` | 应用列表样式 |
| `_toggle()` | 折叠/展开切换 |
| `refresh()` | 刷新节点列表 |
| `_get_selected(lst)` | 获取勾选的节点 |
| `_on_focus()` | "定位"按钮 |
| `_on_path()` | "路径"按钮 |
| `_on_clear()` | "清除"按钮 |

---

#### 类: `NetworkGraphView(QGraphicsView)` — 神经图视图（最核心）

**关键属性**:
| 属性 | 说明 |
|------|------|
| `node_items` | dict: `{name: {'item': SciFiNodeItem, 'type': str}}` |
| `edge_items` | list: `[SciFiEdge, ...]` |
| `_legend_overlay` | LegendOverlay 实例 |
| `_index_overlay` | NodeIndexOverlay 实例 |
| `_overlay_position` | 节点索引位置 ("left"/"right") |
| `_selected_node` | 当前选中的 SciFiNodeItem |
| `_focus_node` | 专注模式下的节点 |
| `_pinned_nodes` | 钉住的节点集合 |
| `_is_panning` | 是否正在平移拖拽 |
| `_pan_start` | 平移起始点 |
| `zoom` | 当前缩放级别 |
| `_bg_color` | **背景颜色** |
| `_grid_color` | 网格颜色 |
| `_bg_luminance` | 背景亮度（判断暗/亮主题） |
| `_node_filters` | 节点类型可见性字典 |
| `_edge_filters` | 边类型可见性字典 |
| `_on_double_click_node` | 双击回调 |
| `_on_node_right_click` | 节点右键回调 |
| `_on_edge_right_click` | 边右键回调 |

**背景相关**:
| 方法 | 说明 |
|------|------|
| `update_graph_background(bg_color, grid_color)` | **更新背景颜色和网格颜色** |
| `get_background_luminance()` → float | 获取背景亮度 |
| `get_background_color()` → QColor | 获取背景颜色 |
| `drawBackground(painter, rect)` | **绘制背景 + 网格** |
| `_show_background_context_menu(pos)` | 背景右键菜单（添加节点） |

**图管理**:
| 方法 | 说明 |
|------|------|
| `build_graph(keywords, freq_data)` | **构建完整图（主入口）** |
| `clear_graph()` | 清除图 |
| `add_node(name, type, ...)` | 添加节点 |
| `remove_node(name)` | 移除节点 |
| `remove_edge(edge)` | 移除边 |
| `add_edge_incremental(from, to, rel)` | 增量添加边 |
| `remove_edge_incremental(from, to, rel)` | 增量移除边 |
| `get_isolated_nodes()` | 获取孤立节点 |
| `_center_graph()` | 图中居中 |
| `_determine_and_add_edge(...)` | 判断并添加边 |

**拖拽连线（+号）**:
| 方法 | 说明 |
|------|------|
| `_start_connect_mode(from_name)` | 开始连接模式 |
| `_on_connect_target_selected(name)` | 连接目标选中 |
| `_cancel_connect_mode()` | 取消连接模式 |
| `_show_relation_select_menu(from, to)` | 显示关系选择菜单 |
| `highlight_drag_start(node)` | **拖拽开始高亮（起点节点高亮，其余变暗）** |
| `highlight_drag_nodes(start, target)` | **拖拽中高亮（起点+目标高亮，其余变暗）** |
| `clear_drag_highlight()` | 清除拖拽高亮 |
| `_flush_drag_edge_updates()` | 刷新拖拽边更新 |

**平移与缩放**:
| 方法 | 说明 |
|------|------|
| `mousePressEvent(event)` | **鼠标按下（选中节点 / 开始平移）** |
| `mouseMoveEvent(event)` | **鼠标移动（平移 translate）** |
| `mouseReleaseEvent(event)` | 鼠标释放（结束平移） |
| `mouseDoubleClickEvent(event)` | 双击 |
| `wheelEvent(event)` | **滚轮缩放** |
| `scrollContentsBy(dx, dy)` | 滚动内容 |

**节点选择与操作**:
| 方法 | 说明 |
|------|------|
| `_select_node(node_item)` | **选中节点（设置高亮+边高亮）** |
| `_on_node_right_click(name, screen, scene)` | 节点右键菜单 |
| `_on_edge_right_click(edge, screen)` | 边右键菜单 |
| `_change_node_type(name, type)` | 修改节点类型 |
| `_change_node_description(name)` | 修改节点描述 |
| `_delete_node(name)` | 删除节点 |
| `_change_edge_relation(from, old, new)` | 修改边关系 |
| `_change_edge_description(...)` | 修改边描述 |
| `_delete_edge_relation(...)` | 删除边关系 |

**专注模式与路径**:
| 方法 | 说明 |
|------|------|
| `focus_on_node(name)` | 聚焦节点（缩放+居中） |
| `enter_focus_mode(name)` | **进入专注模式** |
| `exit_focus_mode()` | **退出专注模式** |
| `toggle_pin_node(name)` | 切换节点钉住 |
| `_update_highlight()` | 更新高亮 |
| `find_shortest_path(a, b)` | 最短路径 |
| `highlight_path(path)` | 高亮路径 |
| `clear_path_highlight()` | 清除路径高亮 |

**过滤器**:
| 方法 | 说明 |
|------|------|
| `toggle_node_filter(type, visible)` | 切换节点类型过滤 |
| `toggle_edge_filter(rel, visible)` | 切换边类型过滤 |
| `set_filter_state(visible_dict)` | 设置过滤状态 |
| `set_edge_filter_state(visible_dict)` | 设置边过滤状态 |
| `apply_filter()` | 应用过滤 |

**布局持久化**:
| 方法 | 说明 |
|------|------|
| `save_node_positions()` | 保存节点位置 |
| `load_node_positions()` | 加载节点位置 |
| `save_layout(path)` | 保存布局到文件 |
| `load_layout(path)` | 从文件加载布局 |
| `export_to_png(path)` | 导出PNG |

**配置回调**:
| 方法 | 说明 |
|------|------|
| `set_graph_font_size(size)` | 设置字体大小 |
| `set_double_click_callback(cb)` | 设置双击回调 |
| `set_right_click_callback(cb)` | 设置右键回调 |
| `set_edge_right_click_callback(cb)` | 设置边右键回调 |
| `set_index_overlay(overlay)` | 设置节点索引 |
| `set_overlay_position(pos)` | 设置节点索引位置 |
| `update_legend_position()` | 更新图例位置 |
| `_pin_overlays()` | 固定浮层位置 |
| `update_legend_config(visible, font, size)` | 更新图例配置 |
| `update_connect_btn_config(size, color)` | **更新+号按钮大小和颜色** |
| `update_node_visual_config(min, max, minB, maxB)` | 更新节点视觉配置 |
| `update_glow_enabled(bool)` | **更新辉光开关** |
| `update_size_sort_enabled(bool)` | 更新大小排序 |
| `update_brightness_sort_enabled(bool)` | 更新亮度排序 |

---

### 4.2 chapter_creator.py

**文件**: [chapter_creator.py](file:///e:/.novel_saver/NovelStorage/novelhelper/ui/chapter_creator.py)

#### 类: `ChapterCreator`

| 方法 | 说明 |
|------|------|
| `__init__(novel_dir_getter, lang_getter)` | 初始化 |
| `_get_novel_dir()` | 获取小说目录 |
| `_get_lang()` | 获取语言 |
| `validate_suffix(suffix)` | 验证后缀 |
| `create_chapters(...)` | 创建章节 |

---

### 4.3 faction_editor.py

**文件**: [faction_editor.py](file:///e:/.novel_saver/NovelStorage/novelhelper/ui/faction_editor.py)

#### 类: `FactionEditorDialog(QDialog)` — 势力编辑器弹出窗口

**关键属性**: `_all_members_list`, `_queue_list`, `_center_scroll`, `_preview_browser`, `_stats_label`, `_save_btn`, `_cancel_btn`, `_reset_btn`, `_template_btn`, `_import_btn`, `_editing_queue`, `_member_cards`, `_gender_map`, `_max_sequence`

| 方法 | 说明 |
|------|------|
| `_init_ui()` | 构建三栏布局 |
| `_build_left_panel()` | 左侧：成员列表 |
| `_build_center_panel()` | 中间：队列+卡片 |
| `_build_right_panel()` | 右侧：预览+统计 |
| `_load_data(faction)` | 加载势力数据 |
| `_populate_member_list()` / `_populate_from_structure()` | 填充列表 |
| `_add_to_queue()` / `_add_selected_to_queue()` / `_add_all_to_queue()` | 添加到队列 |
| `_remove_from_queue()` / `_clear_queue()` | 从队列移除 |
| `_apply_queue_to_center()` | 应用到中间 |
| `_rebuild_center_cards()` / `_create_member_card()` | 重建卡片 |
| `_refresh_preview()` / `_build_preview_html()` | 刷新预览 |
| `_show_enlarged_preview()` | 放大预览 |
| `_update_stats()` | 更新统计 |
| `_validate_and_save()` | 验证并保存 |
| `_reset_to_original()` | 重置 |
| `_save_as_template()` / `_import_from_template()` | 模板操作 |

---

### 4.4 faction_list_view.py

**文件**: [faction_list_view.py](file:///e:/.novel_saver/NovelStorage/novelhelper/ui/faction_list_view.py)

#### 类: `FactionListItem` / `FactionListView`

| FactionListView 方法 | 说明 |
|------|------|
| `_load_data()` | 加载势力数据 |
| `_render_list_items()` | 渲染列表项 |
| `_show_empty_state()` / `_show_error_state()` | 空状态/错误状态 |
| `refresh()` | 刷新 |

---

### 4.5 faction_detail_view.py

**文件**: [faction_detail_view.py](file:///e:/.novel_saver/NovelStorage/novelhelper/ui/faction_detail_view.py)

#### 类: `FactionDetailView`

| 属性 | 说明 |
|------|------|
| `structure_browser` | 结构浏览器 QTextBrowser |
| `members_browser` | 成员浏览器 QTextBrowser |

| 方法 | 说明 |
|------|------|
| `_load_data()` | 加载势力详情 |
| `_html_style()` | HTML样式模板 |
| `_render_structure()` | 渲染结构 |
| `_render_members()` | 渲染成员 |
| `_on_structure_link_clicked()` / `_on_member_link_clicked()` | 链接点击 |
| `refresh()` | 刷新 |

---

### 4.6 family_tree_view.py

**文件**: [family_tree_view.py](file:///e:/.novel_saver/NovelStorage/novelhelper/ui/family_tree_view.py)

#### 类: `FamilyTreeNode`, `FamilyTreeEdge`, `LayoutDirection`, `FamilyTreeView(QGraphicsView)`

| FamilyTreeView 方法 | 说明 |
|------|------|
| `set_tree_data(data)` | 设置树数据 |
| `render_tree()` | 渲染树 |
| `_draw_layer_lines()` | 绘制层级线 |
| `_calculate_layout()` | 计算布局 |
| `_create_nodes_and_edges()` | 创建节点和边 |
| `wheelEvent()` | 滚轮缩放 |
| `export_to_png()` | 导出PNG |
| `reset_view()` | 重置视图 |

---

### 4.7 style_theme.py — 全局样式

**文件**: [style_theme.py](file:///e:/.novel_saver/NovelStorage/novelhelper/ui/style_theme.py)

#### 全局函数（非类）

| 函数 | 说明 |
|------|------|
| `_t(key, fallback='')` | 多语言翻译 |
| `_is_dark()` | 是否暗色主题 |
| `button_style(kind)` | **按钮样式 (primary/secondary/warn/accent)** |
| `input_style()` | 输入框样式 |
| `group_box_style()` | 分组框样式 |
| `scrollbar_style()` | 滚动条样式 |
| `checkbox_style()` | 复选框样式 |
| `combo_box_style()` | 下拉框样式 |
| `tab_style()` | 标签页样式 |
| `apply_global_stylesheet(app)` | 应用全局样式表 |

**模块级常量**: `BG_COLOR`, `FG_COLOR`, `ACCENT_COLOR`, `ACCENT_DIM`, `BORDER_COLOR`, `ERROR_COLOR`, `WARN_COLOR`, `CARD_BG`, `CARD_BORDER`, `NODE_COLORS`, `GRAPH_BG`, `GRAPH_GRID`, `GRAPH_ACCENT`, `MATRIX_GRADIENT`, `MATRIX_DIM`, `RELATION_COLORS`

---

### 4.8 theme.py — 主题常量

**文件**: [theme.py](file:///e:/.novel_saver/NovelStorage/novelhelper/ui/theme.py)

| 类 | 说明 |
|------|------|
| `Colors` | 颜色常量类（纯静态属性） |
| `Sizes` | 尺寸常量类 |
| `Fonts` | 字体类（含 `get_default_font()`, `get_fallback_fonts()`） |
| `Layout` | 布局常量类 |

---

### 4.9 widget_factory.py — 控件工厂

**文件**: [widget_factory.py](file:///e:/.novel_saver/NovelStorage/novelhelper/ui/widget_factory.py)

#### 全局函数（非类）

| 函数 | 说明 |
|------|------|
| `_is_fluent()` | 是否当前为 fluent 主题 |
| `create_button(text, color, on_click, min_height, min_width, kind)` | **创建按钮** (`kind`: primary/danger/warning/default) |
| `create_input(placeholder, min_height, read_only)` | 创建输入框 |
| `create_label(text, color, font_size, bold)` | 创建标签 |
| `create_group_box(title, color)` | 创建分组框 |
| `create_radio(text, color, checked)` | 创建单选按钮 |
| `create_spinbox(min_val, max_val, default, color)` | 创建数字输入框 |
| `create_combo(items, color)` | 创建下拉框 |
| `create_form_row(label_text, widget, label_color)` | 创建"标签+控件"一行 |

---

## 五、core/ — 核心基础设施

### 5.1 config_manager.py — 配置管理（单例）

**文件**: [config_manager.py](file:///e:/.novel_saver/NovelStorage/novelhelper/core/config_manager.py)

#### 类: `ConfigManager` — **全局单例**（`ConfigManager.`）

| 方法 | 说明 |
|------|------|
| `get(section, key, fallback=None)` | **读取字符串配置** |
| `get_int(section, key, fallback=0)` | 读取整数配置 |
| `get_float(section, key, fallback=0.0)` | 读取浮点数配置 |
| `set(section, key, value)` | **写入配置**（自动写INI文件） |
| `remove_option(section, key)` | 删除配置项 |
| `load_config()` | 加载配置（带缓存） |
| `create_default_config()` | 创建默认配置 |
| `get_config_file_path()` | 获取配置文件路径 |

**常用配置项**:
```
[UI] theme, base_font_size, kwlist_font_family, kwlist_font_color
[Graph] node_min_size, node_max_size, enable_glow, enable_size_sort
[Monitor] check_interval, novel_dir, heartbeat_timeout
[Environment] novel_dir, init_chapter_count
[Language] current
[Frequency] min_word_length, min_occurrences, auto_scan
```

---

### 5.2 theme_manager.py — 主题管理（单例）

**文件**: [theme_manager.py](file:///e:/.novel_saver/NovelStorage/novelhelper/core/theme_manager.py)

#### 类: `ThemeManager` — **全局单例**（`theme_manager.`）

| 方法 | 说明 |
|------|------|
| `get(key, fallback=None)` | **读取主题颜色/值**（最重要） |
| `set(key, value)` | 运行时设置主题值 |
| `qcolor(key, fallback)` | 获取 QColor 对象 |
| `set_theme(theme_name)` | **切换主题** |
| `get_current_theme()` → dict | 获取当前主题全部配置 |
| `theme_css()` → str | 生成内联CSS字符串 |
| `list_themes()` | 列出所有可用主题 |
| `reload_themes()` | 热重载主题 |

**常用主题 key**:
```
bg_color, fg_color, accent_color, border_color, error_color, warn_color
btn_bg_color, btn_hover_color, input_bg_color
card_bg, card_border, card_radius, button_radius, input_radius
graph_bg, graph_grid, graph_accent
node_colors, relation_colors, matrix_gradient, matrix_dim
font_family, base_font_size
```

---

### 5.3 language_manager.py — 多语言管理（单例）

**文件**: [language_manager.py](file:///e:/.novel_saver/NovelStorage/novelhelper/core/language_manager.py)

#### 类: `LanguageManager` — **全局单例**（`language_manager.`）

| 方法 | 说明 |
|------|------|
| `tr(key)` / `get_translation(key)` | **翻译键值**（最常用） |
| `set_current_language(lang_code)` | 切换语言 (zh_CN/en_US/ja_JP) |
| `get_current_language()` | 获取当前语言 |
| `get_available_languages()` | 获取可用语言列表 |
| `load_available_languages()` | 加载语言列表 |
| `validate_translations()` | 验证翻译完整性 |

**内置语言**: zh_CN / en_US / ja_JP

---

### 5.4 font_manager.py — 字体管理（单例）

**文件**: [font_manager.py](file:///e:/.novel_saver/NovelStorage/novelhelper/core/font_manager.py)

#### 类: `FontManager` — **全局实例**（`font_manager.`）

| 方法 | 说明 |
|------|------|
| `get_default_font(font_type, lang)` | 获取系统默认字体 (type: default/monospace) |
| `get_font_family(config_value, lang)` | 获取字体（带回退） |
| `get_os_name()` | 获取操作系统名 (windows/macos/linux) |
| `_is_font_available(font_name)` | 检查字体是否可用 |

---

### 5.5 其他 core 模块

| 文件 | 类/函数 | 说明 |
|------|---------|------|
| `log_manager.py` | 日志管理 | 日志记录 |
| `animation_manager.py` | 动画管理 | 过渡动画控制 |
| `chapter_index_cache.py` | ChapterIndexCache | **章节索引缓存（配置目录: `.novel_structure/`，含 stale 卷清理）** |
| `frequency_data_cache.py` | FrequencyDataCache | 词频数据缓存 |
| `graph_layout_cache.py` | GraphLayoutCache | 图布局缓存 |
| `file_manager.py` | 文件管理 | **新增 `NOVEL_CONFIG_DIR='.novel_structure'`, `get_novel_config_dir()`, `ensure_novel_config_dir()`, `migrate_old_config_files()`** |

---

## 六、models/ — 数据模型

### 6.1 keyword_manager.py — 关键词管理（模块级单例）

**文件**: [keyword_manager.py](file:///e:/.novel_saver/NovelStorage/novelhelper/models/keyword_manager.py)

**模块级实例**: `keyword_manager`

| 方法 | 说明 |
|------|------|
| `add_keyword(word, category, note)` | 添加关键词 |
| `remove_keyword(word)` | 删除关键词 |
| `get_keywords(category)` | 获取某分类关键词列表 |
| `get_all_keywords()` → dict | 获取所有关键词 `{category: [words]}` |
| `get_categories()` → list | 获取所有分类 |
| `save_keywords()` | 保存到文件 |
| `_load_from_file()` | 从文件加载 |
| `get_config_path()` | **获取 `.novel-enhancer.json` 路径（`.novel_structure/` 下）** |
| `scan_frequency()` | **词频扫描（`.frequency.json` 路径使用 `get_novel_config_dir()`）** |

**配置文件路径变更**: 所有 JSON 文件从 `novelDir/` 迁移到 `novelDir/.novel_structure/`，包括 `.novel-enhancer.json`, `.frequency.json`, `user_stopwords.json`, `entities.json`, `relationships.json`, `factions.json`, `workspace.json`

---

### 6.2 novel_model.py — 小说数据模型

**文件**: [novel_model.py](file:///e:/.novel_saver/NovelStorage/novelhelper/models/novel_model.py)

| 类 | 说明 |
|------|------|
| `Book` | 小说（含 chapters 列表） |
| `Chapter(QStandardItem)` | 章节（继承 QStandardItem） |

**Book 方法**: `add_chapter()`, `remove_chapter()`, `get_chapters()`, `get_chapter_count()`

**Chapter 方法**: `get_title()`, `set_title()`, `get_content()`, `set_content()`, `get_word_count()`

---

### 6.3 summary_generator.py

**文件**: [summary_generator.py](file:///e:/.novel_saver/NovelStorage/novelhelper/models/summary_generator.py)

摘要生成相关类（详见文件内）

---

## 七、workers/ — 后台工作线程

| 文件 | 类 | 说明 |
|------|-----|------|
| `base_worker.py` | BaseWorker | 工作线程基类 |
| `file_scanner_worker.py` | FileScannerWorker | 文件扫描线程 |
| `frequency_worker.py` | FrequencyWorker | 词频分析线程 |
| `layout_worker.py` | LayoutWorker | 图布局计算线程 |
| `multi_thread_integration.py` | MultiThreadIntegration | 多线程集成管理 |
| `task_scheduler.py` | TaskScheduler | 任务调度器 |

---

## 八、controllers/ — 控制器

### 8.1 monitor_controller.py — 监控控制器

**文件**: [monitor_controller.py](file:///e:/.novel_saver/NovelStorage/novelhelper/controllers/monitor_controller.py)

| 类 | 说明 |
|------|------|
| `MonitorThread(QThread)` | 后台监测线程 |
| `MonitorController` | 监控控制器 |

**MonitorThread 方法**: `run()`, `stop()`, `init_folders()`, `check_folders()`, `process_new_volume_folder()`, `_check_cycle()`

**MonitorController 方法**: `start()`, `stop()`, `is_running()`, `set_callbacks()`, `get_last_heartbeat()`

---

## 九、services/ — 业务服务层

| 文件 | 类/函数 | 说明 |
|------|---------|------|
| `chapter_service.py` | 章节服务 | 章节创建/管理 |
| `export_service.py` | ExportService | 导出服务 |
| `monitor_service.py` | MonitorService | 监控服务 |

---

## 十、widgets/ — 独立Widget组件

### 10.1 writing_assistant.py — 写作助理

**文件**: [widgets/writing_assistant.py](file:///e:/.novel_saver/NovelStorage/novelhelper/widgets/writing_assistant.py)

#### 类: `WritingAssistant(QWidget)`

| 属性 | 说明 |
|------|------|
| `_start_btn`, `_pause_btn`, `_reset_btn`, `_skip_btn` | 计时器按钮 |
| `_time_label` | 时间显示 |
| `_focus_check`, `_short_break_check`, `_long_break_check` | 模式复选框 |
| `_goal_spin` | 目标字数输入 |
| `_today_label` | 今日字数显示 |
| `_goal_progress` | 进度条 |
| `_stat_days_label`, `_stat_total_label`, `_stat_avg_label` | 统计标签 |
| `_timer` | QTimer |

| 信号 | 说明 |
|------|------|
| `timer_updated(remaining_seconds)` | 计时更新 |
| `timer_finished(is_focus_done)` | 计时完成 |
| `goal_progress_updated(current, target)` | 目标进度更新 |

| 方法 | 说明 |
|------|------|
| `_on_start()`, `_on_pause()`, `_on_reset()`, `_on_skip_break()` | 计时器操作 |
| `_on_timer_tick()`, `_timer_finished_handler()` | 计时器内部 |
| `_on_mode_changed()`, `_on_goal_changed()` | 配置变更 |
| `add_word_count(delta)` | **增加今日字数** |
| `set_word_count(count)` | 直接设置字数 |

---

### 10.2 writing_dashboard.py — 写作数据仪表板

**文件**: [widgets/writing_dashboard.py](file:///e:/.novel_saver/NovelStorage/novelhelper/widgets/writing_dashboard.py)

#### 类: `WritingDashboard(QWidget)`

| 属性 | 说明 |
|------|------|
| `total_words_card`, `total_chapters_card`, `total_volumes_card`, `daily_avg_card` | 统计卡片 |
| `volumes_info`, `keywords_info` | QTextBrowser 信息区 |
| `trend_chart` | TrendChart 趋势图 |
| `_chapter_cache`, `_freq_cache` | 缓存引用 |

| 信号 | 说明 |
|------|------|
| `data_refreshed(stats_dict)` | 数据刷新时 |

| 方法 | 说明 |
|------|------|
| `set_novel_dir(path)` | 设置小说目录 |
| `refresh_data()` | **刷新所有数据** |
| `get_chapter_cache()` | 获取章节缓存 |
| `get_freq_cache()` | 获取词频缓存 |
| `_export_report()` | 导出报告 |

#### 类: `StatCard(QFrame)` — 统计卡片

| 方法 | 说明 |
|------|------|
| `update_value(value, subtitle)` | 更新数值 |

#### 类: `TrendChart(QWidget)` — 趋势图

| 方法 | 说明 |
|------|------|
| `set_data(data_points)` | 设置数据 `[(label, value), ...]` |
| `paintEvent(event)` | 绘制图表 |

#### TrendChart 绘图细节

| 特性 | 说明 |
|------|------|
| `paintEvent` | 全自定义绘制，绘制流程：清空→网格线→Y轴刻度线(6px)→数据折线(3px, RoundJoin)→数据点(白色描边)→悬停高亮+Tooltip |
| Y轴刻度 | `_compute_ticks()` 计算，6px 短刻度线标记 |
| Tooltip | 显示日期+字数，边缘检测（左右侧均防截断） |

---

### 10.3 timeline_view.py — 大纲时间线

**文件**: [widgets/timeline_view.py](file:///e:/.novel_saver/NovelStorage/novelhelper/widgets/timeline_view.py)

#### 类: `TimelineView(QWidget)`

| 属性 | 说明 |
|------|------|
| `orientation_btn` | 方向切换按钮 |
| `zoom_in_btn`, `zoom_out_btn`, `zoom_reset_btn` | 缩放按钮 |
| `view` | QGraphicsView 图形视图 |
| `scene` | QGraphicsScene 场景 |

| 信号 | 说明 |
|------|------|
| `node_clicked(dict)` | 节点点击 |
| `node_double_clicked(str)` | 节点双击 |

| 方法 | 说明 |
|------|------|
| `set_data(data)` | 设置时间线数据 |
| `_render_timeline()` | 渲染时间线 |
| `_toggle_orientation()` | 切换方向 |
| `_set_zoom(factor)` | 设置缩放 |
| `load_from_chapter_cache(cache)` | 从章节缓存加载 |

#### 类: `MiniTimelineWidget(QFrame)` — 迷你时间线

| 信号 | 说明 |
|------|------|
| `node_selected(path)` | 节点选中 |

| 方法 | 说明 |
|------|------|
| `add_item(item)` | 添加条目 |
| `set_items(items)` | 设置所有条目 |

---

## 十一、utils/ — 工具函数

### 11.1 writing_assistant.py — 写作会话数据

**文件**: [utils/writing_assistant.py](file:///e:/.novel_saver/NovelStorage/novelhelper/utils/writing_assistant.py)

#### 类: `WritingSession` — 写作会话数据模型

| 属性 | 说明 |
|------|------|
| `start_time`, `end_time` | 开始/结束时间 |
| `word_count`, `target_words` | 字数/目标 |
| `note` | 备注 |

| 方法 | 说明 |
|------|------|
| `duration` (property) | 会话时长 |
| `duration_minutes` (property) | 分钟数 |
| `is_complete` (property) | 是否完成 |
| `target_achieved` (property) | 目标达成 |
| `to_dict()`, `from_dict()` | 序列化/反序列化 |

#### 类: `WritingAssistant` — 写作统计管理

| 方法 | 说明 |
|------|------|
| `start_session()`, `pause_session()`, `end_session()` | 会话管理 |
| `update_word_count(delta)` | 更新字数 |
| `get_today_sessions()`, `get_today_total_words()` | 今日统计 |
| `get_weekly_statistics()` | 本周统计 |
| `get_target_progress()` | 目标进度 |
| `export_statistics(path)` | 导出统计 |

---

## 附录：全局重要单例速查

| 变量名 | 类型 | 文件 | 说明 |
|--------|------|------|------|
| `config_manager` | ConfigManager | core/config_manager.py | 配置读写 |
| `theme_manager` | ThemeManager | core/theme_manager.py | 主题管理 |
| `language_manager` | LanguageManager | core/language_manager.py | 多语言翻译 |
| `font_manager` | FontManager | core/font_manager.py | 字体管理 |
| `keyword_manager` | keyword_manager单例 | models/keyword_manager.py | 关键词数据 |
| `signal_bus` | SignalBus | core/signal_bus.py | 信号总线 |

---

## 附录：神经图（network_graph.py）关键类变量速查

| 类 | 变量 | 类型 | 说明 |
|----|------|------|------|
| `SciFiNodeItem` | `_btn_color` | str | +号按钮颜色 |
| | `_btn_r` | float | +号按钮半径 |
| | `_is_dragging` | bool | 是否拖拽中 |
| | `_connect_mode` | bool | 是否连线模式 |
| | `_selected` | bool | 是否选中 |
| | `_glow_cache` | QPixmap | 辉光缓存 |
| `SciFiEdge` | `_is_dark_background` | bool | 是否暗色背景（类变量） |
| `NetworkGraphView` | `_bg_color` | str | 背景颜色 |
| | `zoom` | float | 当前缩放级别 |
| | `_selected_node` | SciFiNodeItem | 当前选中节点 |
| | `_focus_node` | SciFiNodeItem | 专注模式节点 |
| | `_legend_overlay` | LegendOverlay | 图例浮层 |
| | `_index_overlay` | NodeIndexOverlay | 节点索引侧栏 |

---

## 附录：关键词分类（keyword_tab.py）

| 分类标识 | 中文名 | 颜色说明 |
|----------|--------|----------|
| `character` | 人物 | `node_colors.character` |
| `location` | 地点 | `node_colors.location` |
| `item` | 物品 | `node_colors.item` |
| `skill` | 技能 | `node_colors.skill` |
| `foreshadowing` | 伏笔 | `node_colors.foreshadowing` |
| `adventure` | 事件 | `node_colors.adventure` |
| `faction` | 组织 | `node_colors.faction` |
| `time_point` | 时间点 | `node_colors.time_point` |

---

## 附录：视图模式枚举（keyword_tab.py）

```python
class ViewMode:
    LIST_VIEW       # 列表视图
    CARD_VIEW       # 人物卡视图
    FREQUENCY_VIEW  # 频度仪表盘
    NEURAL_VIEW     # 神经网络图
```
