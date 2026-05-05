# Novel Text Enhancer - 小说文本增强插件

## 功能特性

- ✅ **关键词高亮** - 支持 6 种类型：伏笔、人物、技能、地点、物品、关系
- ✅ **悬浮提示** - 鼠标悬停显示关键词描述、关联内容、笔记
- ✅ **用户配置** - 支持 settings.json 和项目级 `.novel-enhancer.json`
- ✅ **伏笔关联** - 关键词之间可建立关联关系

## 安装方式

1. 打开 Trae/VS Code
2. 按 `Ctrl+Shift+P` 输入 `Extensions: Install from VISX`
3. 选择 `extension.js` 所在文件夹

或直接复制到 `~/.vscode/extensions/novel-text-enhancer/`

## 配置方式

### 方式一：VS Code 设置

```json
{
  "novelTextEnhancer.keywords": [
    {
      "name": "柳祖",
      "type": "character",
      "color": "#4ecdc4",
      "description": "邪门的神秘祖师",
      "related": ["伏笔-柳祖", "邪门"]
    },
    {
      "name": "筑基",
      "type": "skill",
      "color": "#ffe66d",
      "description": "修行第一个境界"
    },
    {
      "name": "伏笔-程溪",
      "type": "foreshadowing",
      "color": "#ff6b6b",
      "description": "程溪相关伏笔线索"
    }
  ]
}
```

### 方式二：项目级配置

在小说文件夹根目录创建 `.novel-enhancer.json`：

```json
{
  "keywords": [
    {
      "name": "柳契生",
      "type": "character",
      "description": "主角",
      "related": ["邪门", "筑基"]
    },
    {
      "name": "正阳之气",
      "type": "skill",
      "description": "主角的本命之气"
    }
  ]
}
```

## 关键词类型

| 类型 | 颜色 | 说明 |
|------|------|------|
| foreshadowing | 🔴 红色 | 伏笔线索 |
| character | 🔵 青色 | 人物角色 |
| skill | 🟡 黄色 | 技能功法 |
| location | 🟢 绿色 | 地点场所 |
| item | 🟣 紫色 | 物品道具 |
| relationship | 🔷 蓝色 | 人物关系 |
| custom | ⚪ 灰色 | 自定义类型 |

## 使用方法

1. **打开小说文件夹** - 插件会在 `.txt` 和 `.md` 文件中生效
2. **悬停查看** - 鼠标移到高亮文字上显示详细信息
3. **刷新配置** - `Ctrl+Shift+P` 输入 `NovelTextEnhancer: Reload Keywords`

## 快捷命令

- `Ctrl+Shift+P` → `NovelTextEnhancer: Reload Keywords` - 重新加载关键词
- `Ctrl+Shift+P` → `NovelTextEnhancer: Open Settings` - 打开设置
- `Ctrl+Shift+P` → `NovelTextEnhancer: Create Config` - 创建示例配置文件