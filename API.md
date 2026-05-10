# NovelHelper API 文档

## 目录
1. [核心模块](#核心模块)
   - [ConfigManager](#configmanager)
   - [FileManager / file_manager](#filemanager--file_manager)
   - [SafeFileOperation](#safefileoperation)
   - [LanguageManager / language_manager](#languagemanager--language_manager)
   - [FontManager / font_manager](#fontmanager--font_manager)
   - [log_manager](#log_manager)
2. [模型层](#模型层)
   - [NovelModel](#novelmodel)
   - [KeywordManager](#keywordmanager)
3. [服务层](#服务层)
   - [ExportService](#exportservice)
4. [后台任务](#后台任务)
   - [BaseWorker](#baseworker)

---

## 核心模块

### ConfigManager
**模块**: `core.config_manager`

配置管理器，负责配置文件的加载、保存和缓存管理。

```python
from core import ConfigManager
```

#### 方法
- `ConfigManager.get_config_file_path()` → `str`
  获取配置文件完整路径

- `ConfigManager.load_config()` → `ConfigParser`
  加载配置（内部带缓存）

- `ConfigManager.get(section, key, fallback)` → `str`
  获取配置项
  - section: 配置节名
  - key: 配置键名
  - fallback: 默认值

- `ConfigManager.get_int(section, key, fallback)` → `int`
  获取整数配置项

- `ConfigManager.get_float(section, key, fallback)` → `float`
  获取浮点数配置项

- `ConfigManager.set(section, key, value)`
  设置配置项（自动保存到文件）

- `ConfigManager.create_default_config()`
  创建默认配置文件

- `ConfigManager.remove_option(section, key)`
  删除配置项

#### 配置节示例
```
[UI]
base_font_size = 18
kwlist_font_family = Microsoft YaHei

[Monitor]
check_interval = 15
novel_dir = D:/novels

[Graph]
auto_save_layout = 1
```

---

### FileManager / file_manager
**模块**: `core.file_manager`

文件和目录管理工具，提供小说文件操作功能。

```python
from core import file_manager, FileManager
```

#### 实例方法
- `file_manager.set_language(lang)`
  设置当前语言 (zh_CN / en_US / ja_JP)

- `file_manager.get_chapter_number(filename)` → `int` 或 `None`
  从文件名提取章节编号

- `file_manager.find_latest_chapter(folder_path)` → `(int, str)` 或 `None`
  获取最新章节编号和文件名

- `file_manager.generate_chapter_name(chapter_num, title="")` → `str`
  生成章节文件名

- `file_manager.format_volume_title_export(volume_num, volume_name, word_count)` → `str`
  格式化卷标题（用于导出）

- `file_manager.format_chapter_title_export(chapter_num, chapter_name)` → `str`
  格式化章节标题（用于导出）

- `file_manager.get_word_count(file_path)` → `(int, str)`
  获取字数，返回 (count, error)

- `file_manager.get_folder_number(folder_name)` → `int` 或 `None`
  从文件夹名提取卷号

- `file_manager.is_default_content(file_path)` → `bool`
  检查文件是否为默认占位内容

- `file_manager.ensure_ahead_chapters_internal(...)` → `int`
  确保有足够的预生成章节

#### 独立函数
- `get_base_dir()` → `str`
- `get_novel_dir()` → `str`
- `get_all_dir()` → `str`

---

### SafeFileOperation
**模块**: `core.file_manager`

安全文件操作包装器，提供自动备份和安全检查。

```python
from core import SafeFileOperation
```

#### 静态方法
- `SafeFileOperation.create_backup(file_path, backup_dir=None, auto_rename=True)` → `str` 或 `None`
  创建文件备份
  - file_path: 源文件路径
  - backup_dir: 备份目录，默认同目录下的 .nh_backups
  - auto_rename: 是否添加时间戳重命名
  - 返回: 备份文件路径

- `SafeFileOperation.safe_rename(old_path, new_path, backup=True)` → `(bool, str)`
  安全重命名（先备份再重命名）
  - 返回: (success, error_msg)

- `SafeFileOperation.safe_remove(file_path, backup=True, really_delete=False)` → `(bool, str)`
  安全删除
  - really_delete: False=移动到回收站；True=真正删除
  - 返回: (success, backup_path)

- `SafeFileOperation.safe_write(file_path, content, backup=True)` → `(bool, str)`
  安全写入文件
  - 返回: (success, error_msg)

- `SafeFileOperation.clean_old_backups(base_path, keep_days=30)` → `int`
  清理过期备份
  - 返回: 删除数量

---

### LanguageManager / language_manager
**模块**: `core.language_manager`

国际化翻译管理器。

```python
from core import language_manager, LanguageManager
```

#### 实例属性
- `language_manager.current_lang` → `str`
  当前语言

#### 方法
- `language_manager.set_language(lang)`
  切换语言 (zh_CN/en_US/ja_JP)

- `language_manager.tr(key, **kwargs)` → `str`
  获取翻译文本
  - 支持变量替换: `language_manager.tr('hello_user', name='World')`

- `language_manager.get_available_languages()` → `dict`
  获取可用语言列表 {lang_code: display_name}

---

### FontManager / font_manager
**模块**: `core.font_manager`

跨平台字体管理，自动回退到系统可用字体。

```python
from core import font_manager, FontManager
```

#### 方法
- `font_manager.get_os_name()` → `str`
  获取操作系统名 (windows/macos/linux)

- `font_manager.get_default_font(font_type='default', lang=None)` → `str`
  获取默认字体
  - font_type: 'default' 或 'monospace'

- `font_manager.get_font_family(config_value=None, lang=None)` → `str`
  获取可用字体（含回退链）
  - config_value: 用户在配置中指定的字体名

- `font_manager._is_font_available(font_name)` → `bool`
  检查字体是否可用（内部使用）

---

### log_manager
**模块**: `core.log_manager`

日志管理与轮转功能。

```python
from core import setup_logging, get_log_dir, clean_old_logs, get_log_size, archive_logs
```

#### 函数
- `setup_logging(...)`
  配置日志系统
  - log_name: 日志文件名前缀
  - max_bytes: 单个日志文件大小（字节）
  - backup_count: 保留文件数
  - log_level: 日志级别
  - use_timed_rotation: 是否按时间轮转 (True/False)
  - when: 时间轮转触发点 ('midnight', 'D', 'H', 等)
  - interval: 时间间隔
  - backup_days: 保留天数

- `get_log_dir()` → `str`
  获取日志目录路径

- `clean_old_logs(log_dir, keep_days=30)` → `int`
  清理过期日志

- `get_log_size()` → `int`
  获取日志目录总大小（字节）

- `archive_logs()` → `str`
  归档日志到 zip 文件，返回 zip 路径

---

## 模型层

### NovelModel
**模块**: `models.novel_model`

小说数据模型。

```python
from models import NovelModel
```

### KeywordManager
**模块**: `models.keyword_manager`

关键词管理器。

```python
from models import KeywordManager
```

---

## 服务层

### ExportService
**模块**: `services.export_service`

多格式导出服务。

```python
from services import ExportService
```

---

## 后台任务

### BaseWorker
**模块**: `workers.base_worker`

后台任务基类。

```python
from workers import BaseWorker
```

#### 信号
- `started` - 任务开始
- `progress(int)` - 进度更新
- `status(str)` - 状态更新
- `finished` - 任务完成
- `result(obj)` - 结果返回
- `error(str)` - 错误
- `cancelled` - 被取消

#### 子类需实现
- `execute()` - 执行实际任务逻辑

---

## UI 组件

### WritingAssistant
**模块**: `widgets.writing_assistant`

写作辅助控制面板（番茄钟、字数目标管理）

```python
from widgets.writing_assistant import WritingAssistant
```

#### 信号
- `timer_updated(int)` - 计时器每秒更新（剩余秒数
- `timer_finished(bool)` - 计时器完成（True=专注结束，False=休息结束
- `goal_progress_updated(int, int)` - 字数目标进度更新（当前，目标）

#### 公共方法
- `add_word_count(delta)` - 增加今日字数（传入增量
- `set_word_count(count)` - 直接设置今日字数

---

## 使用示例

### 快速开始
```python
from core import (
    ConfigManager,
    file_manager,
    language_manager,
    SafeFileOperation,
    setup_logging
)

# 1. 初始化日志
setup_logging(backup_count=10, backup_days=30)

# 2. 读取配置
novel_dir = ConfigManager.get('Monitor', 'novel_dir', fallback='')

# 3. 使用字体管理
font_name = font_manager.get_default_font()

# 4. 安全操作
success, backup = SafeFileOperation.safe_remove('old_file.txt')

# 5. 获取翻译
text = language_manager.tr('welcome')
```
