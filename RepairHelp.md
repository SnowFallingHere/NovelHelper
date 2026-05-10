# NovelHelper 架构手册与开发指南

> 本文档面向开发者，说明项目架构、扩展方法及常见问题的排查思路。

---

## 一、架构总览

### 1.1 分层架构

```
┌─────────────────────────────────────────────┐
│              main_window.py                  │  ← 主窗口 (AcrylicWindow)
│  ┌─── QTabWidget (7个标签页, 延迟初始化) ──┐  │
│  │  tabs/  (视图层, 继承 BaseTab)           │  │
│  │   ├── create_tab / summary_tab          │  │
│  │   ├── monitor_tab / keyword_tab         │  │
│  │   ├── stats_tab / config_tab / help_tab │  │
│  └──────────────┬──────────────────────────┘  │
│                 │ 信号/回调                    │
│  ┌──────────────▼──────────────────────────┐  │
│  │  ui/      (UI组件层)                     │  │
│  │   network_graph / faction_editor        │  │
│  │   family_tree_view / chapter_creator    │  │
│  │   widget_factory / style_theme          │  │
│  ├─────────────────────────────────────────┤  │
│  │  widgets/  (独立Widget)                 │  │
│  │   writing_assistant / writing_dashboard │  │
│  │   timeline_view                         │  │
│  ├─────────────────────────────────────────┤  │
│  │  services/ (业务服务层)                 │  │
│  │   chapter_service / export_service      │  │
│  │   monitor_service                       │  │
│  ├─────────────────────────────────────────┤  │
│  │  controllers/ (控制器层)                │  │
│  │   monitor_controller                    │  │
│  ├─────────────────────────────────────────┤  │
│  │  models/   (数据模型层)                 │  │
│  │   keyword_manager / novel_model         │  │
│  │   summary_generator                     │  │
│  ├─────────────────────────────────────────┤  │
│  │  workers/  (后台线程, QThread)          │  │
│  │   base_worker → frequency_worker        │  │
│  │   file_scanner_worker / layout_worker   │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  ┌─────────────────────────────────────────┐  │
│  │  core/     (基础设施单例层)              │  │
│  │   ConfigManager / ThemeManager          │  │
│  │   LanguageManager / FileManager         │  │
│  │   FontManager / AnimationManager        │  │
│  │   log_manager / *Cache                  │  │
│  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### 1.2 数据流

```
用户操作 → Tab UI → ConfigManager(读/写INI)
                ↓
         keyword_manager(读写JSON到.novel_structure/)
                ↓
         file_manager(文件系统操作 + SafeFileOperation备份)
                ↓
         workers/BaseWorker(QThread后台任务)
                ↓
         信号(progress/result/error) → UI更新
```

### 1.3 配置数据流向

```
NovelHelper.ini (主配置)
    ↓ ConfigManager.get/set()
    ├── [UI]       → 界面尺寸、颜色、字体、主题名
    ├── [Monitor]  → 监控目录、间隔、超时
    ├── [Graph]    → 节点大小范围、布局参数
    ├── [Theme]    → 图谱背景色、网格色
    ├── [Frequency]→ 词频参数（最小词长、出现次数）
    ├── [Format]   → 自定义章节/卷命名格式
    ├── [Language] → 当前语言
    ├── [Stats]    → 写作目标字数
    └── [Novel]     → 小说标题、标签、简介

.novel_structure/ (运行时数据，在小说项目目录下)
    ├── .novel-enhancer.json  → 关键词+关系数据
    ├── entities.json         → 实体数据
    ├── relationships.json    → 关系数据
    ├── factions.json         → 势力数据
    ├── workspace.json        → 工作区数据
    ├── .frequency.json       → 词频统计结果
    ├── user_stopwords.json   → 用户停用词
    └── *.layout_cache.json   → 图布局缓存
```

---

## 二、添加新功能

### 2.1 添加新标签页

**步骤：**

**1）创建新文件 `tabs/my_new_tab.py`**

```python
from .base_tab import BaseTab
from ..core.config_manager import ConfigManager
from ..core.language_manager import language_manager
import logging

logger = logging.getLogger(__name__)

class MyNewTab(BaseTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_name = "我的新功能"
        logger.info(f"[{self.tab_name}] 创建实例")

    def _build_ui(self):
        from ..ui.widget_factory import create_button, create_label, create_group_box
        from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

        layout = QVBoxLayout(self)
        group = create_group_box(language_manager.tr("my_feature_title"))
        vbox = QVBoxLayout(group)

        self._label = create_label("Hello World!")
        vbox.addWidget(self._label)

        self._btn = create_button(
            language_manager.tr("do_something"),
            kind='primary',
            on_click=self._on_action
        )
        vbox.addWidget(self._btn)

        layout.addWidget(group)

    def _load_data(self):
        pass

    def _on_action(self):
        pass

    def retranslate_ui(self):
        if hasattr(self, '_label'):
            self._label.setText(language_manager.tr("hello_text"))
        if hasattr(self, '_btn'):
            self._btn.setText(language_manager.tr("do_something"))
```

**2）在 `main_window.py` 中注册**

```python
# ① 导入
from novelhelper.tabs.my_new_tab import MyNewTab

# ② 在 _lazy_init_queues 的 init_queue 中添加
init_queue = ['summary', 'monitor', 'keyword', 'stats', 'my_new', 'config', 'help']

# ③ 在 _create_tab_by_name 的 method_map 中添加
method_map = {
    # ...existing...
    'my_new': self.my_new_tab,
}

# ④ 添加创建方法
def my_new_tab(self):
    tab = MyNewTab(self)
    self._tab_instances['my_new'] = tab
    self.tabs.addTab(tab, language_manager.tr("my_feature"))

# ⑤ 在 _get_tab_name_by_index 中更新索引映射
names = {0: 'create', 1: 'summary', ..., 6: 'help'}
# 注意：新增标签会改变后续索引

# ⑥ 在 update_ui_language 的 tab_titles 中添加
tab_titles = {
    # ...existing...
    # 需要按新的索引位置插入
}
```

**3）添加翻译键**

在 `core/language_manager.py` 的 `DEFAULT_TRANSLATIONS` 三种语言中分别添加：
```python
'my_feature': '我的新功能',        # zh_CN
'my_feature': 'My New Feature',     # en_US
'my_feature': '新機能',             # ja_JP
```

或在 `translations/*.json` 文件中添加。

> **⚠️ 注意事项**：
> - 标签页索引 (`_get_tab_name_by_index`) 必须与 `addTab` 顺序严格一致
> - 新标签页建议放在 `init_queue` 尾部（config/help 之前），避免改变已有索引
> - 如果需要在启动时立即显示（非延迟初始化），参考 `create_tab()` 的处理方式

### 2.2 添加新的后台任务

```python
from workers.base_worker import BaseWorker

class MyWorker(BaseWorker):
    def __init__(self, param1, param2):
        super().__init__()
        self.task_name = "我的任务"
        self.param1 = param1
        self.param2 = param2

    def execute(self):
        total = 100
        for i in range(total):
            self.check_cancelled()  # 检查是否被取消
            self.emit_progress(int((i+1)/total*100), f"处理中 {i+1}/{total}")
            self.msleep(10)  # 让出CPU
        return {"result": "done"}

# 使用
worker = MyWorker("a", "b")
worker.finished.connect(lambda: print("完成"))
worker.error.connect(lambda e: print(f"错误: {e}"))
worker.start()
```

### 2.3 添加新的配置项

**1）设置默认值** — 在 `core/config_manager.py` 的 `DEFAULT_CONFIG` 中添加：

```python
'MySection': {
    'new_param': 'default_value',
    'another_param': '42',
}
```

**2）读取配置** — 在 Tab 或其他模块中：

```python
value = ConfigManager.get('MySection', 'new_param', fallback='fallback')
int_val = ConfigManager.get_int('MySection', 'another_param', fallback=0)
```

**3）写入配置**：

```python
ConfigManager.set('MySection', 'new_param', 'new_value')
```

> **⚠️ 注意**：`ConfigManager.set()` 会立即写入 INI 文件并标记缓存脏。批量修改时注意性能。

### 2.4 添加新的关键词类型

**1）在 `models/keyword_manager.py` 中注册类型：**

```python
KEYWORD_TYPES = {
    # ...existing types...
    'my_new_type': {'color': '#FF00FF', 'label': '新类型'},
}
```

**2）在 `ui/network_graph.py` 中添加节点形状和颜色映射：**

```python
NODE_LABELS = {
    # ...existing...
    'my_new_type': '新类型',
}

# 在 SciFiNodeItem.paint() 中添加绘制分支
def _draw_my_type(self, painter, rect):
    # 自定义绘制逻辑
    pass
```

**3）在 `tabs/keyword_tab.py` 的过滤器中添加对应选项。**

---

## 三、UI 主题开发

### 3.1 主题文件结构

主题定义在 `themes/*.json` 中，程序启动时自动发现：

```json
{
  "name": "my_theme",
  "display_name": "My Custom Theme",
  "bg_color": "#F8F9FA",
  "fg_color": "#212529",
  "accent_color": "#0078D4",
  "border_color": "#DEE2E6",
  "error_color": "#D13438",
  "warn_color": "#FF8C00",
  "btn_bg_color": "#0078D4",
  "btn_hover_color": "#106EBE",
  "input_bg_color": "#FFFFFF",
  "card_bg": "#FFFFFF",
  "card_border": "#DEE2E6",
  "graph_bg": "#F8F9FA",
  "graph_grid": "#E9ECEF",
  "font_family": "'Segoe UI', 'Microsoft YaHei', sans-serif"
}
```

将 JSON 文件放入 `themes/` 目录即可热加载，无需修改代码。

### 3.2 主题切换的影响链

```
用户选择新主题 → ConfigManager.set('UI', 'theme', 'xxx')
    → MainWindow._on_config_applied()
        → theme_manager.set_theme('xxx')        // 切换主题管理器
        → load_config_values()                   // 重载所有配置值
        → apply_global_stylesheet()              // ★ 重新应用全局CSS
        → 各 Tab.refresh() / reload_data()       // 刷新各标签页
```

**关键函数** `apply_global_stylesheet()` 定义在 `ui/style_theme.py`，它会：
- 根据 `theme_manager` 当前值生成完整 CSS
- 应用到 `QApplication.instance()`
- 影响所有 `QGroupBox`, `QPushButton`, `QLineEdit`, `QScrollArea` 等控件

### 3.3 修改全局样式时的常见问题

#### 问题：自定义样式被全局样式覆盖

**原因**：`apply_global_stylesheet()` 会重新设置 `QApplication` 的样式表，可能覆盖控件级 `setStyleSheet()`。

**解决**：
- 使用更具体的选择器（带 `objectName`）
- 在 `_on_config_applied` 回调中重新应用自定义样式
- 使用 `theme_manager.get(key)` 动态获取颜色值而非硬编码

```python
self.my_widget.setObjectName('mySpecialWidget')
self.my_widget.setStyleSheet("""
    #mySpecialWidget {
        background-color: %s;
    }
""" % theme_manager.get('accent_color'))
```

#### 问题：暗色主题下文字不可见

**原因**：硬编码了深色文字在深色背景上。

**解决**：使用 `theme_manager` 获取颜色，或使用 `_is_dark()` 辅助函数判断：

```python
from core.theme_manager import theme_manager

def _is_dark():
    bg = theme_manager.get('bg_color', '#F8F9FA')
    r, g, b = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
    return (r*0.299 + g*0.587 + b*0.114) < 128

fg = '#FFFFFF' if _is_dark() else '#212529'
```

#### 问题：网络图背景与主题不同步

**原因**：图谱背景有独立配置项 `graph_bg_follow_theme`。

**解决**：在 `_on_config_applied` 中检查该标志：

```python
follow = ConfigManager.get('Theme', 'graph_bg_follow_theme', fallback='1') == '1'
if follow:
    bg = theme_manager.get('graph_bg', '#F8F9FA')
else:
    bg = ConfigManager.get('Theme', 'graph_bg_color', fallback='#F8F9FA')
view.update_graph_background(bg_color=bg)
```

### 3.4 网络图（network_graph.py）开发注意事项

这是项目中最复杂（~3300 行）的 UI 文件，修改时需特别注意：

| 注意点 | 说明 |
|--------|------|
| **SciFiNodeItem 是 QGraphicsItem** | 不是 QWidget，使用 `paint()` 自绘，不用 stylesheet |
| **坐标系统是场景坐标** | `pos()` 返回场景坐标，不是屏幕坐标 |
| **辉光效果用 QPixmap 缓存** | 修改节点外观后调用 `invalidate_glow_cache()` |
| **连线模式状态机** | `_connect_mode` + `_drag_line` + `_drag_start` 组成拖拽连线 FSM |
| **边路径计算** | `_compute_path()` 计算到节点边界（boundingRect）停止，不是中心到中心 |
| **暗色背景影响箭头颜色** | `SciFiEdge._is_dark_background` 是类变量，切换主题时必须更新 |

**添加新的节点类型的流程：**

1. `NODE_LABELS` 字典添加映射
2. `SciFiNodeItem.paint()` 的 `node_type` 分支添加绘制逻辑
3. `KeywordTab` 过滤器添加复选框
4. `LegendOverlay.refresh()` 添加图例项
5. 如需特殊形状，重写 `shape()` 和 `boundingRect()`

---

## 四、常见开发问题排查

### 4.1 启动崩溃

**排查步骤：**

1. 查看 `log/NovelHelper_YYYYMMDD.log` 最后几行
2. 常见原因：
   - **缺少依赖** → `ImportError` / `ModuleNotFoundError`
   - **配置文件损坏** → `configparser.Error` → 删除 `NovelHelper.ini` 重启
   - **QApplication 未创建前使用了 Qt 组件** → 检查模块级导入

**关键**：`NovelHelper.py` 的 `main()` 函数外层有 try/except，崩溃信息会记录到日志。

### 4.2 标签页初始化失败

**现象**：切换到某标签页时空白或报错

**排查：**
```python
# BaseTab.initialize() 内部有 try/except
# 错误会记录到日志但不会传播
# 查看 log 中 "[标签页名] 初始化失败" 信息
```

**常见原因：**
- `_build_ui()` 中引用了不存在的翻译键 → `language_manager.tr()` 返回 key 本身（不会崩溃但显示异常）
- `_load_data()` 中文件路径不存在 → 检查 `get_novel_dir()` 返回值
- 循环导入 → `tabs/` 与 `ui/` 之间互相导入时使用延迟导入（函数内 `from ... import`）

### 4.3 配置保存后不生效

**检查清单：**
1. `ConfigTab.save_and_apply_config()` 是否发射了 `config_applied` 信号？
2. `MainWindow._on_config_applied()` 是否正确连接？
3. 目标 Tab 是否实现了对应的刷新方法？

**信号连接链路：**
```
ConfigTab.config_applied → MainWindow._on_config_applied
    → self._tab_instances['xxx'].reload_data()  // 必须存在此方法
```

### 4.4 词频扫描慢或无结果

**参数调优：**
- `min_word_length=2` — 过滤单字
- `min_occurrences=3` — 最少出现 3 次
- `filter_stopwords=1` — 启用停用词过滤（推荐开启）

**如果 jieba 未安装**，`keyword_manager.py` 中有容错处理：
```python
try:
    import jieba
except ImportError:
    jieba = None  # 词频扫描将跳过分词
```

### 4.5 监控线程问题

**现象**：监控无法启动或自动停止

**排查：**
1. 检查 `novel_dir` 是否已设置且目录存在
2. 检查 `heartbeat_timeout`（默认 120 秒），超过无活动则认为异常
3. 监控线程在 `MonitorTab.cleanup()` 中停止，退出程序时确保调用
4. 日志中搜索 `[Monitor]` 关键字查看详细状态

### 4.6 图布局错乱

**原因及修复：**
- 节点位置缓存损坏 → 点击「重置布局」按钮清除缓存
- `node_cache_*` 配置项过多导致 INI 文件膨胀 → 这些是自动生成的，可安全删除
- 力导向参数不合理 → 调整 `layout_ideal_length`(默认200) 和 `repulsion_strength`(默认50000)

### 4.7 多语言翻译缺失

**现象**：界面显示英文 key 而非翻译文本

**排查：**
1. 检查 `language_manager.DEFAULT_TRANSLATIONS` 中是否有对应 key
2. 检查 `translations/xx_XX.json` 文件是否包含该 key
3. 调用 `language_manager.validate_translations()` 打印缺失列表

**添加翻译的正确方式：**
- 界面文本：优先加到 `translations/*.json`（支持热加载）
- 核心文本：加到 `DEFAULT_TRANSLATIONS`（代码内嵌兜底）
- 两处都添加可保证完整性

### 4.8 内存占用过高

**常见原因及优化方向：**

| 原因 | 优化方案 |
|------|----------|
| 神经图节点过多 | 降低 `node_limit`（默认 200） |
| 词频数据量大 | FrequencyDataCache 有自动清理机制 |
| HTML 卡片渲染多 | KeywordTab 的卡片视图使用虚拟化/分页 |
| 日志文件过大 | `log_manager` 支持按大小/时间轮转 |

### 4.9 PyInstaller 打包问题

**常见缺失模块：**

在 `.spec` 文件的 `hiddenimports` 中确保包含：
```
hidden_modules = [
    'jieba',
    'cn2an',
    'qfluentwidgets',
    'qframelesswindow',
    'novelhelper.core.config_manager',
    'novelhelper.core.theme_manager',
    'novelhelper.core.language_manager',
    'novelhelper.core.file_manager',
    # ... 所有 novelhelper 子模块
]
```

**数据文件打包：**
- `themes/*.json` → 必须打入包内
- `translations/*.json` → 必须
- `res/stopwords.json` → 必须
- `data/faction_templates.json` → 必须

---

## 五、编码规范

### 5.1 导入规范

```python
# ✅ 正确：延迟导入避免循环依赖
def _build_ui(self):
    from ..ui.widget_factory import create_button
    ...

# ❌ 错误：文件顶部循环导入
from ..ui.network_graph import NetworkGraphView  # 如果 network_graph 也导入了 tabs/*
```

### 5.2 翻译规范

```python
# ✅ 正确：所有用户可见文本走翻译
label = QLabel(language_manager.tr("save_and_exit_btn"))

# ❌ 错误：硬编码中文
label = QLabel("保存并退出")
```

### 5.3 配置读取规范

```python
# ✅ 正确：带 fallback
value = ConfigManager.get('Section', 'key', fallback='default')

# ❌ 错误：不带 fallback（KeyError 崩溃）
value = ConfigManager.get('Section', 'key')
```

### 5.4 文件操作规范

```python
# ✅ 正确：使用 SafeFileOperation
success, err = SafeFileOperation.safe_write(path, content)

# ❌ 错误：直接 open（无备份）
with open(path, 'w') as f:
    f.write(content)
```

### 5.5 日志规范

```python
# 模块级别 logger
logger = logging.getLogger(__name__)

# 关键操作必须记日志
logger.info(f"[{self.tab_name}] 操作描述")
logger.warning(f"[{self.tab_name}] 警告信息")
logger.error(f"[{self.tab_name}] 错误信息", exc_info=True)  # 异常时带上堆栈
```

---

## 六、关键文件修改风险矩阵

| 文件 | 修改风险 | 影响范围 | 备注 |
|------|----------|----------|------|
| `main_window.py` | **高** | 全局 | 标签页注册/信号连接/窗口生命周期 |
| `core/config_manager.py` | **高** | 全局 | 所有配置读取依赖此类 |
| `core/language_manager.py` | **中** | 全部 UI | 翻译键变更需同步 3 个语言 + JSON |
| `core/theme_manager.py` | **中** | 全部 UI | 颜色值变更影响全局渲染 |
| `core/file_manager.py` | **高** | 数据层 | 文件路径/格式变更影响全部 IO |
| `tabs/base_tab.py` | **高** | 全部标签页 | 基类变更影响所有子类 |
| `tabs/keyword_tab.py` | **中** | 关键词功能 | 最大最复杂的标签页 (~2500 行) |
| `tabs/config_tab.py` | **中** | 配置功能 | 信号发射遗漏会导致配置不生效 |
| `ui/network_graph.py` | **高** | 关键词图谱 | 最复杂 UI 文件 (~3300 行)，自绘图形 |
| `ui/style_theme.py` | **中** | 全局外观 | CSS 生成逻辑变更影响所有控件 |
| `workers/base_worker.py` | **低** | 后台任务 | 基类变更影响所有 Worker 子类 |
| `models/keyword_manager.py` | **中** | 关键词数据 | JSON 结构变更需考虑向后兼容 |

---

## 七、调试技巧

### 7.1 启用调试日志

```python
# NovelHelper.py 的 init_logging() 中调整级别
logging.basicConfig(level=logging.DEBUG, ...)  # 从 INFO 改为 DEBUG
```

### 7.2 查看标签页状态

```python
# 在任何地方打印标签页状态
for name, tab in main_window._tab_instances.items():
    print(f"{name}: initialized={tab.is_initialized}, status={tab.get_status()}")
```

### 7.3 检查配置实际值

```python
# 直接读取 INI 文件原始内容
config = ConfigManager.load_config()
import configparser
config.write(sys.stdout)  # 打印全部配置到控制台
```

### 7.4 Qt 对象inspect

```python
# 打印 Widget 树
def dump_widget(widget, indent=0):
    print("  " * indent + f"{widget.__class__.__name__} [{widget.objectName()}]")
    for child in widget.children():
        if isinstance(child, QWidget):
            dump_widget(child, indent + 1)

dump_widget(main_window)
```
