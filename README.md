# NovelHelper 小说助手

***

## English

### Overview
A lightweight novel writing assistant that runs in background. Monitors your writing folder and automatically handles volume management, chapter export, and placeholder generation.

### Features
- Flexible directory selection (any folder works)
- Auto volume management with word count tags
- Auto chapter placeholder generation
- Auto export with customizable format
- Multi-language support (EN/CN/JP)
- Real-time monitoring

### Quick Start
1. Run `NovelHelper.exe`
2. Go to "Parameter Configuration" → Select novel directory
3. Click "Start Monitor"

### Folder Structure
```
your_folder/
├─ 1[new_0]/     # Volume 1 (10 empty chapters)
└─ NovelHelper.ini
```

### Requirements
- Windows 64-bit (EXE)
- Python 3.7+ / PyQt5 / cn2an (Python version)

### Run
```bash
./dist/NovelHelper.exe   # EXE
python NovelHelper.py     # Python
```

### Warning
1. Backup data before use
2. Don't delete files while monitoring
3. Ensure write permissions

***

## 中文

### 简介
轻量级小说写作辅助工具，后台运行。监控写作文件夹，自动处理卷管理、章节导出和占位符生成。

### 功能
- 灵活目录选择（任意文件夹）
- 自动卷管理（字数标签）
- 自动章节占位符生成
- 自动导出（可自定义格式）
- 多语言支持（中/英/日）
- 实时监控

### 快速开始
1. 运行 `NovelHelper.exe`
2. 进入「参数配置」→ 选择小说目录
3. 点击「启动监控」

### 目录结构
```
你的文件夹/
├─ 1[new_0]/     # 第一卷（含10个空章节）
└─ NovelHelper.ini
```

### 系统要求
- Windows 64位（EXE版）
- Python 3.7+ / PyQt5 / cn2an（Python版）

### 运行
```bash
./dist/NovelHelper.exe   # EXE版
python NovelHelper.py     # Python版
```

### 注意事项
1. 使用前备份数据
2. 监控期间不要删除文件
3. 确保有写入权限

***

**License: MIT**
