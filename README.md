# NovelHelper&写作辅助

A novel writing assistant designed for IDE-based workflows.

***

# English Version

## Overview

NovelHelper is a lightweight tool that runs in the background while you write novels in your preferred text editor. It monitors your writing folder and automatically handles volume management, chapter export, and placeholder generation.

**Note:** This program does not provide text editing capabilities.

## Features

### Automatic Volume Management

When you complete a volume, NovelHelper automatically:

- Creates new volume folders
- Marks old volumes with word count tags
- Pre-generates placeholder chapters in the new volume

### Automatic Export

- Merges all chapters into a single text file
- Organizes content by volume with word count statistics
- Supports optional folder renaming (adds `[old_XXXX]` or `[new_XXXX]` tags)

### Automatic Placeholder Generation

- Detects when your latest chapter has substantial content
- Automatically adds 2 leading placeholder chapters
- Triggers export when chapter count reaches multiples of 2

## Directory Structure

```
NovelStorage/
├─ novel/
│  ├─ your_novel/
│  │  ├─ 1[Volume 1]/
│  │  │  ├─ 1第...txt
│  │  │  └─ ...
│  │  ├─ 2[Volume 2]/
│  │  │  └─ ...
│  │  └─ NovelHelper.py
│  └─ ...
└─ all/               # Template library
```

## Usage

### First Time Setup

Click "Create Runtime Environment" to initialize:

- Creates necessary folders
- Generates chapter templates in `/all`
- Sets up initial volume structure

### During Writing

Just write in your text editor. NovelHelper will:

- Monitor folder changes every 15 seconds
- Auto-add placeholder chapters when you reach 20+ words in latest chapter
- Auto-trigger export at chapter 2, 4, 6, 8, etc.

### Manual Operations

- Add new volume: Click "Add New Volume" in Monitor tab
- Run export manually: Use Summary Merge tool
- Create templates: Use Chapter Template tool

## Folder Naming

- Volumes: `数字[卷名]` (e.g., `1[第一卷]`, `2[第二卷]`)
- Chapters: `数字第...txt` (e.g., `1第...txt`)

## Configuration

Edit `NovelHelper.ini` to adjust:

- Monitor interval
- Trigger word count threshold
- Leading chapter count
- UI appearance

### Language

Built-in languages: English, 简体中文, 日本語

Add custom languages by editing the ini file.

## Requirements

- Python 3.7+
- PyQt5
- cn2an

```bash
pip install PyQt5 cn2an
```

## Running

```bash
python NovelHelper.py
```

## Warning

1. Backup your data before use
2. Do not delete files while monitor is running
3. Export function modifies folder names
4. Ensure write permissions for all folders

## Technical Details

- GUI: PyQt5
- Threading: QThread for background monitoring
- Config: Python ConfigParser
- Number conversion: cn2an

## License

MIT

***

# 中文版

## 简介

NovelHelper 是一款轻量级工具，在你使用偏好的文本编辑器写小说时在后台运行。它监控你的写作文件夹，自动处理卷管理、章节导出和占位符生成。

**注意：** 本程序不提供文本编辑功能。

## 功能

### 自动卷管理

当你完成一卷时，NovelHelper 自动：

- 创建新卷文件夹
- 用字数标签标记旧卷
- 在新卷中预生成占位符章节

### 自动导出

- 将所有章节合并为单个文本文件
- 按卷组织内容并统计字数
- 支持可选的文件夹重命名（添加 `[old_XXXX]` 或 `[new_XXXX]` 标签）

### 自动占位符生成

- 检测最新章节是否有实质内容
- 自动添加2个领先占位符章节
- 当章节数达到2的倍数时触发导出

## 目录结构

```
NovelStorage/
├─ novel/
│  ├─ 你的小说/
│  │  ├─ 1[第一卷]/
│  │  │  ├─ 1第...txt
│  │  │  └─ ...
│  │  ├─ 2[第二卷]/
│  │  │  └─ ...
│  │  └─ NovelHelper.py
│  └─ ...
└─ all/               # 模板库
```

## 使用方法

### 首次设置

点击「创建运行环境」初始化：

- 创建必要文件夹
- 在 `/all` 生成章节模板
- 设置初始卷结构

### 写作时

只需在文本编辑器中写作，NovelHelper 会：

- 每15秒监控文件夹变化
- 当最新章节达到20+字时自动添加占位符章节
- 在第2、4、6、8...章时自动触发导出

### 手动操作

- 添加新卷：点击监控面板的「增加新卷」
- 手动导出：使用 Summary 合并工具
- 创建模板：使用章节模板工具

## 文件夹命名

- 卷：`数字[卷名]`（如 `1[第一卷]`、`2[第二卷]`）
- 章节：`数字第...txt`（如 `1第...txt`）

## 配置

编辑 `NovelHelper.ini` 调整：

- 监控间隔
- 触发字数阈值
- 领先章节数
- 界面外观

### 语言

内置语言：English, 简体中文, 日本語

通过编辑 ini 文件添加自定义语言。

## 系统要求

- Python 3.7+
- PyQt5
- cn2an

```bash
pip install PyQt5 cn2an
```

## 运行

```bash
python NovelHelper.py
```

## 注意事项

1. 使用前备份数据
2. 监控运行期间不要删除文件
3. 导出功能会修改文件夹名
4. 确保所有文件夹有写入权限

## 技术细节

- 界面：PyQt5
- 多线程：QThread 后台监控
- 配置：Python ConfigParser
- 数字转换：cn2an

## 许可证

MIT
