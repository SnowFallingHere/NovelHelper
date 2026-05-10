# NovelHelper — 小说写作辅助工具

> 一款基于 PyQt5 + qfluentwidgets 的**小说创作全流程管理工具**，提供章节管理、关键词图谱、实时监控、词频分析、统计仪表板等功能。

---

## 功能概览

| 模块 | 说明 |
|------|------|
| **初始化与创建章节** | 新建小说项目、批量创建章节模板、卷管理 |
| **卷与章合并** | 多卷统计、自动重命名文件夹、合并导出 |
| **监控管理** | 文件系统实时监控、新章节检测、日志追踪 |
| **关键词管理** | 人物/地点/物品/伏笔等关键词管理，含 **6 种视图模式** |
| **统计与分析** | 写作数据仪表板、趋势图表、时间线导航 |
| **参数配置** | UI 颜色/字号/主题、网络图配置、词频参数、格式自定义 |
| **使用说明** | 内置帮助浏览器 |

### 关键词管理的 6 种视图

- **列表视图** — 标签化关键词列表
- **卡片视图** — 角色卡 / 地点卡 / 物品卡 / 技能卡（HTML 渲染）
- **神经网络图** — 力导向关系图（SciFiNodeItem 节点 + SciFiEdge 边）
- **频度仪表盘** — 词频热力图、临时称谓检测、替换建议
- **势力卡片** — 组织结构浏览与编辑
- **家族树** — 血缘关系树形图（QGraphicsView）

---

## 快速开始

### 环境要求

- Python 3.10+
- Windows 10/11（推荐，支持亚克力窗口效果）
- 依赖：`PyQt5`, `qfluentwidgets`, `qframelesswindow`, `jieba`, `cn2an`

### 安装依赖

```bash
pip install PyQt5 qfluentwidgets qframelesswindow jieba cn2an
```

### 启动程序

```bash
cd novelhelper
python NovelHelper.py
```

或打包为 exe：

```bash
pyinstaller NovelHelper.spec
```

---

## 使用流程

### 第一步：初始化小说项目

1. 打开程序，进入 **「初始化与创建章节」** 标签页
2. 点击 **「初始化小说目录」** 按钮，选择一个空目录作为项目根目录
3. 程序会自动创建以下目录结构：

```
你的小说目录/
├── all/                  # 所有章节的汇总目录（扁平存放）
├── novel/
│   └── 小说名/           # 按卷组织的章节目录
│       ├── 1[第一卷]/
│       │   ├── 1第一章_标题.txt
│       │   ├── 2第二章_标题.txt
│       │   └── ...
│       ├── 2[第二卷]/
│       └── ...
├── log/                  # 运行日志
├── .novel_structure/     # 配置数据目录（关键词、词频、缓存等）
│   ├── entities.json
│   ├── relationships.json
│   ├── factions.json
│   ├── .frequency.json
│   └── ...
└── NovelHelper.ini       # 全局配置文件
```

4. 在 **小说信息** 区域填写：
   - **标签**：输入后按回车添加（如：玄幻、修仙、热血）
   - **简介**：输入小说简介（自动保存）

### 第二步：创建章节

1. 在 **「初始化与创建章节」** 标签页中：
   - 填写 **卷名**（如：第一卷）
   - 填写 **章节名**（如：第一章 陨落的天才）
   - 可选填写 **内容预览**
2. 点击 **「创建章节」** 按钮
3. 或使用 **批量创建** 功能一次性生成多个空章节文件

### 第三步：设置监控（可选但推荐）

1. 进入 **「监控管理」** 标签页
2. 确保 **小说目录** 已正确设置（在参数配置中设置）
3. 点击 **「启动监控」**
4. 监控功能会：
   - 定期扫描章节目录，检测新增/修改的文件
   - 自动发现新卷文件夹并提示处理
   - 实时显示日志信息
   - 支持章节预览

### 第四步：管理关键词

1. 进入 **「关键词管理」** 标签页
2. 点击 **「刷新关键词」** 扫描章节内容
3. 使用工具栏切换 6 种视图模式：
   - 列表 → 卡片 → 频度 → 神经网络图 → 势力 → 家族树
4. 在 **神经网络图** 中：
   - **拖拽节点** 移动位置
   - **拖拽节点右下角 + 号** 连接两个节点（选择关系类型）
   - **双击节点** 查看详情
   - **右键节点/边** 编辑或删除
   - **滚轮缩放** / **拖拽空白处平移**
5. 关键词类型支持：
   - `character`（人物）、`location`（地点）、`item`（物品）
   - `skill`（技能）、`foreshadowing`（伏笔）
   - `adventure`（事件）、`faction`（组织）、`time_point`（时间点）

### 第五步：查看统计数据

1. 进入 **「统计与分析」** 标签页
2. 查看：
   - 总字数、总章节数、总卷数、日均字数
   - 各卷进度条
   - 写作趋势折线图
   - 章节时间线导航
3. 可导出完整报告

### 第六步：合并导出（可选）

1. 进入 **「卷与章合并」** 标签页
2. 选择要处理的卷
3. 选择运行模式：
   - **仅统计**：只收集数据，不重命名
   - **统计并重命名**：按规则重命名卷文件夹
4. 点击执行，完成后可合并所有章节为单个文件

---

## 参数配置指南

进入 **「参数配置」** 标签页，修改后点击 **「保存并应用」** 生效。

### UI 配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `base_font_size` | 基础字号 | 14 |
| `theme` | 主题 (fluent/matrix) | fluent |
| `enable_animations` | 开启动效 | 1 |
| `enable_acrylic` | 亚克力效果 | 1 |
| `bg_color` | 背景色 | #F8F9FA |
| `accent_color` | 强调色 | #0078D4 |

### 网络图配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `node_limit` | 最大节点数 | 200 |
| `node_min_size` / `node_max_size` | 节点大小范围 | 60 ~ 160 |
| `enable_glow` | 发光效果 | 1 |
| `enable_size_sort` | 按连接数排序大小 | 1 |
| `layout_ideal_length` | 力导向布局理想边长 | 200 |

### 监控配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `check_interval` | 检查间隔（秒） | 15 |
| `novel_dir` | 小说目录路径 | （必填） |
| `min_word_count` | 最小有效字数 | 20 |

### 格式配置（高级）

支持自定义章节/卷文件名格式，占位符包括：

| 占位符 | 示例输出 | 说明 |
|--------|----------|------|
| `{cn.low.Chapter}` | 第一百五十三章 | 中文小写 |
| `{cn.up.Chapter}` | 第壹佰伍拾叁章 | 中文大写 |
| `{cn.num.Chapter}` | 第153章 | 数字中文 |
| `{en.Chapter}` | Chapter153 | 英文 |
| `{title}` | _标题名 | 章节标题 |
| `{types:markdown}` | .md | 文件后缀 |

示例：`{cn.low.Chapter}{title}{types:markdown}` → `1第一章_标题.md`

### 语言切换

在参数配置底部选择语言（`zh_CN` / `en_US` / `ja_JP`），保存后生效。部分翻译可能需要重启程序完全生效。

---

## 目录结构说明

```
novelhelper/
├── NovelHelper.py              # 程序入口
├── main_window.py              # 主窗口（AcrylicWindow 无边框亚克力）
├── NovelHelper.ini             # 配置文件（运行时自动生成）
│
├── core/                       # 核心基础设施层（单例管理器）
│   ├── config_manager.py       # ConfigManager — INI 配置读写
│   ├── theme_manager.py        # ThemeManager — 主题管理（支持热加载 JSON）
│   ├── language_manager.py     # LanguageManager — i18n 多语言
│   ├── file_manager.py         # FileManager + SafeFileOperation — 文件操作
│   ├── font_manager.py         # FontManager — 字体回退链
│   ├── animation_manager.py    # 动画效果管理
│   ├── log_manager.py          # 日志轮转管理
│   ├── chapter_index_cache.py  # 章节索引缓存
│   ├── frequency_data_cache.py # 词频数据缓存
│   └── graph_layout_cache.py   # 图布局缓存
│
├── models/                     # 数据模型层
│   ├── keyword_manager.py      # keyword_manager — 关键词 CRUD + 词频扫描
│   ├── novel_model.py          # Book / Chapter 数据模型
│   └── summary_generator.py    # 摘要生成
│
├── services/                   # 业务服务层
│   ├── chapter_service.py      # 章节管理服务
│   ├── export_service.py       # 多格式导出服务
│   └── monitor_service.py      # 文件监控服务
│
├── controllers/                # 控制器层
│   └── monitor_controller.py   # MonitorThread / MonitorController
│
├── tabs/                       # 视图层（7 个标签页，继承 BaseTab）
│   ├── base_tab.py             # BaseTab 基类（延迟初始化机制）
│   ├── create_tab.py           # 初始化与创建章节
│   ├── summary_tab.py          # 卷与章合并
│   ├── monitor_tab.py          # 监控管理
│   ├── keyword_tab.py          # 关键词管理（最大最复杂，~2500 行）
│   ├── stats_tab.py            # 统计与分析
│   ├── config_tab.py           # 参数配置
│   └── help_tab.py             # 使用说明
│
├── ui/                         # UI 组件层
│   ├── network_graph.py        # ★ 神经网络图核心（~3300 行）
│   ├── chapter_creator.py      # 章节创建器
│   ├── faction_editor.py       # 势力编辑器弹窗
│   ├── faction_list_view.py    # 势力列表
│   ├── faction_detail_view.py  # 势力详情
│   ├── family_tree_view.py     # 家族树图形视图
│   ├── style_theme.py          # 全局样式表生成
│   ├── theme.py                # 主题常量
│   └── widget_factory.py       # 控件工厂函数
│
├── widgets/                    # 独立 Widget
│   ├── writing_assistant.py    # 写作助理浮窗（番茄钟+字数目标）
│   ├── writing_dashboard.py    # 写作数据仪表板 + 趋势图
│   └── timeline_view.py        # 大纲时间线视图
│
├── workers/                    # 后台工作线程（QThread）
│   ├── base_worker.py          # BaseWorker 基类
│   ├── file_scanner_worker.py  # 文件扫描线程
│   ├── frequency_worker.py     # 词频分析线程
│   ├── layout_worker.py        # 图布局计算线程
│   ├── multi_thread_integration.py  # 多线程集成
│   └── task_scheduler.py       # 任务调度器
│
├── translations/               # i18n 翻译文件
│   ├── zh_CN.json
│   ├── en_US.json
│   └── ja_JP.json
│
├── themes/                     # 主题定义文件（JSON）
│   ├── fluent.json             # Fluent 浅色主题
│   └── matrix.json             # Matrix 黑客主题
│
├── data/                       # 数据资源
│   └── stopwords.json           # 停用词表
│
└── log/                        # 运行日志（自动生成）
```

---

## 架构设计要点

### 延迟初始化机制

所有标签页继承 `BaseTab`，采用**延迟初始化**策略：
- 启动时仅创建第一个标签页（CreateTab）
- 其余标签页通过 `_lazy_init_tabs()` 队列逐个延迟创建（50ms 间隔）
- 用户首次切换到某标签页时才触发 `initialize()` → `_build_ui()` → `_load_data()`
- 大幅减少冷启动时间

### 信号广播机制

`ConfigTab` 通过信号将配置变更广播到主窗口和其他标签页：

```
ConfigTab.config_applied
    → MainWindow._on_config_applied()
        → CreateTab._load_data()
        → KeywordTab.update_config()
        → StatsTab.reload_data()
        → SummaryTab._load_data()
        → MonitorTab.load_data()
        → apply_global_stylesheet()  // 全局样式刷新
```

### 单例管理模式

核心模块全部采用单例/模块级实例：

| 单例变量 | 类型 | 用途 |
|----------|------|------|
| `ConfigManager` | 类方法单例 | INI 配置读写（带线程锁和缓存） |
| `theme_manager` | `__new__` 单例 | 主题颜色/值读取 |
| `language_manager` | 模块级实例 | 多语言翻译 |
| `font_manager` | 模块级实例 | 字体回退链 |
| `keyword_manager` | 模块级实例 | 关键词数据管理 |
| `file_manager` | 模块级实例 | 文件操作封装 |

### 安全文件操作

所有危险操作（删除/重命名/写入）均通过 `SafeFileOperation` 包装：
- 操作前自动备份到 `.nh_backups/` 目录
- 备份文件带时间戳命名
- 支持过期清理（默认保留 30 天）

---

## 常见问题

### Q: 启动后界面空白？
A: 检查是否正确安装了 `qfluentwidgets` 和 `qframelesswindow`。查看 `log/` 目录下的日志文件获取详细错误。

### Q: 监控检测不到新章节？
A: 确认 `NovelHelper.ini` 中 `[Monitor]` 的 `novel_dir` 路径正确指向你的小说项目目录。

### Q: 关键词扫描结果为空？
A: 确保章节文件中有实际内容（非空文件），且满足 `min_word_length` 和 `min_occurrences` 阈值。

### Q: 如何添加新的主题？
A: 在 `themes/` 目录下新建 `.json` 文件，参照 `fluent.json` 的格式定义颜色值。程序启动时会自动发现。

### Q: 如何打包为独立 exe？
A: 项目已包含 `NovelHelper.spec`，运行 `pyinstaller NovelHelper.spec` 即可。注意确保所有依赖都在 `hiddenimports` 中。

---

## 技术栈

| 技术 | 版本/说明 |
|------|-----------|
| Python | 3.10+ |
| PyQt5 | GUI 框架 |
| qfluentwidgets | Fluent Design 组件库 |
| qframelesswindow | 无边框亚克力窗口 |
| jieba | 中文分词（词频扫描） |
| cn2an | 中文数字转换（章节命名） |
| configparser | INI 配置解析（标准库） |
| logging | 日志系统（标准库） |

---

## 许可证

本项目仅供个人学习和研究使用。
