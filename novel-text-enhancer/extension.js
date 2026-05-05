const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

let decorationCollection;
let activeEditor;

const KEYWORD_TYPES = {
    foreshadowing: { color: '#ff6b6b', label: '伏笔' },
    character: { color: '#4ecdc4', label: '人物' },
    skill: { color: '#ffe66d', label: '技能' },
    location: { color: '#95e1d3', label: '地点' },
    item: { color: '#dda0dd', label: '物品' },
    relationship: { color: '#87ceeb', label: '关系' },
    custom: { color: '#c0c0c0', label: '自定义' }
};

function loadKeywords() {
    const config = vscode.workspace.getConfiguration('novelTextEnhancer');
    const keywords = config.get('keywords', []);
    
    let result = [...keywords];
    
    if (vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0) {
        const rootPath = vscode.workspace.workspaceFolders[0].uri.fsPath;
        const userKeywordsPath = path.join(rootPath, '.novel-enhancer.json');
        
        if (fs.existsSync(userKeywordsPath)) {
            try {
                const userData = JSON.parse(fs.readFileSync(userKeywordsPath, 'utf-8'));
                if (Array.isArray(userData.keywords)) {
                    result = [...result, ...userData.keywords];
                }
            } catch (e) {
                vscode.window.showWarningMessage(`加载自定义关键词失败: ${e.message}`);
            }
        }
    }
    
    return result;
}

function createDecoration(keyword) {
    const typeInfo = KEYWORD_TYPES[keyword.type] || KEYWORD_TYPES.custom;
    const color = keyword.color || typeInfo.color;
    
    return vscode.window.createTextEditorDecorationType({
        overviewRulerColor: color,
        overviewRulerLane: vscode.OverviewRulerLane.Right,
        backgroundColor: `${color}40`,
        borderRadius: '3px',
        textDecoration: `none; border-bottom: 2px dotted ${color};`,
        tooltip: `${typeInfo.label}: ${keyword.name}\n\n${keyword.description || '无描述'}`
    });
}

function updateDecorations() {
    if (!activeEditor) return;
    
    const config = vscode.workspace.getConfiguration('novelTextEnhancer');
    if (!config.get('enableHighlighting', true)) {
        activeEditor.setDecorations(decorationCollection, []);
        return;
    }
    
    const filePath = activeEditor.document.fileName;
    const fileName = path.basename(filePath);
    const filePatterns = config.get('filePatterns', ['*.txt', '*.md']);
    
    const matches = filePatterns.some(pattern => {
        if (pattern.startsWith('*.')) {
            return fileName.endsWith(pattern.slice(1));
        }
        return filePath.includes(pattern);
    });
    
    if (!matches) {
        activeEditor.setDecorations(decorationCollection, []);
        return;
    }
    
    const keywords = loadKeywords();
    const text = activeEditor.document.getText();
    const decorations = [];
    
    keywords.forEach(keyword => {
        if (!keyword.name) return;
        
        const regex = new RegExp(keyword.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
        let match;
        
        while ((match = regex.exec(text)) !== null) {
            const startPos = activeEditor.document.positionAt(match.index);
            const endPos = activeEditor.document.positionAt(match.index + match[0].length);
            
            if (!isOverlapping(decorations, startPos, endPos)) {
                decorations.push({
                    range: new vscode.Range(startPos, endPos),
                    decoration: createDecoration(keyword),
                    keyword: keyword
                });
            }
        }
    });
    
    const decorationRanges = decorations.map(d => ({
        range: d.range,
        decoration: d.decoration
    }));
    
    decorationCollection.clear();
    decorationCollection.set(decorationRanges);
}

function isOverlapping(existing, start, end) {
    return existing.some(d =>
        (start.isAfter(d.range.start) && start.isBefore(d.range.end)) ||
        (end.isAfter(d.range.start) && end.isBefore(d.range.end)) ||
        (start.isBefore(d.range.start) && end.isAfter(d.range.end))
    );
}

class HoverProvider {
    provideHover(document, position, token) {
        const config = vscode.workspace.getConfiguration('novelTextEnhancer');
        if (!config.get('enableHover', true)) {
            return null;
        }
        
        const keywords = loadKeywords();
        const wordRange = document.getWordRangeAtPosition(position);
        if (!wordRange) return null;
        
        const selectedText = document.getText(wordRange);
        
        for (const keyword of keywords) {
            if (keyword.name === selectedText ||
                keyword.name.toLowerCase() === selectedText.toLowerCase()) {
                
                const typeInfo = KEYWORD_TYPES[keyword.type] || KEYWORD_TYPES.custom;
                
                const lines = [
                    `**${typeInfo.label}: ${keyword.name}**`,
                    '',
                    keyword.description || '_暂无描述_'
                ];
                
                if (keyword.related && keyword.related.length > 0) {
                    lines.push('', '**相关联:**');
                    keyword.related.forEach(r => {
                        lines.push(`- ${r}`);
                    });
                }
                
                if (keyword.notes) {
                    lines.push('', '**笔记:**', keyword.notes);
                }
                
                return new vscode.Hover({
                    language: 'markdown',
                    value: lines.join('\n')
                }, wordRange);
            }
        }
        
        return null;
    }
}

function createCharacterPanel(context) {
    const panel = vscode.window.createWebviewPanel(
        'novelTextEnhancer.characterPanel',
        '人物卡',
        vscode.ViewColumn.Beside,
        {
            enableScripts: true,
            localResourceRoots: [vscode.Uri.file(context.extensionPath)]
        }
    );
    
    panel.webview.html = getCharacterPanelHtml();
    
    panel.webview.onDidReceiveMessage(message => {
        switch (message.command) {
            case 'addKeyword':
                vscode.commands.executeCommand('novelTextEnhancer.createConfig');
                break;
            case 'refreshKeywords':
                refreshKeywords(panel);
                break;
        }
    }, undefined, context.subscriptions);
    
    return panel;
}

function refreshKeywords(panel) {
    const keywords = loadKeywords();
    panel.webview.postMessage({ command: 'updateKeywords', keywords: keywords });
}

function getCharacterPanelHtml() {
    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>人物卡</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            padding: 20px;
            background-color: var(--vscode-editor-background);
            color: var(--vscode-editor-foreground);
        }
        h1 {
            color: var(--vscode-editor-foreground);
            border-bottom: 2px solid var(--vscode-editorWidget-border);
            padding-bottom: 10px;
        }
        .keyword-card {
            border: 1px solid var(--vscode-editorWidget-border);
            border-radius: 8px;
            padding: 16px;
            margin: 12px 0;
            background-color: var(--vscode-editorWidget-background);
        }
        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
        }
        .card-title {
            font-size: 18px;
            font-weight: bold;
        }
        .card-type {
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 12px;
            color: white;
        }
        .card-description {
            margin-bottom: 12px;
            line-height: 1.6;
        }
        .card-related {
            font-size: 13px;
            color: var(--vscode-descriptionForeground);
        }
        .card-related span {
            display: inline-block;
            background-color: var(--vscode-editor-selectionBackground);
            padding: 2px 8px;
            border-radius: 4px;
            margin: 2px 4px 2px 0;
        }
        .section-title {
            font-size: 16px;
            font-weight: bold;
            margin: 24px 0 12px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--vscode-editorWidget-border);
        }
        .btn {
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 8px;
        }
        .btn:hover {
            background-color: var(--vscode-button-hoverBackground);
        }
        .toolbar {
            margin-bottom: 16px;
        }
    </style>
</head>
<body>
    <h1>📚 小说要素管理器</h1>
    <div class="toolbar">
        <button class="btn" onclick="refreshKeywords()">🔄 刷新</button>
        <button class="btn" onclick="openConfig()">⚙️ 配置</button>
    </div>
    <div id="content"></div>
    <script>
        const vscode = acquireVsCodeApi();
        
        function refreshKeywords() {
            vscode.postMessage({ command: 'refreshKeywords' });
        }
        
        function openConfig() {
            vscode.postMessage({ command: 'addKeyword' });
        }
        
        function renderKeywords(keywords) {
            const content = document.getElementById('content');
            content.innerHTML = '';
            
            const grouped = {};
            keywords.forEach(k => {
                const type = k.type || 'custom';
                if (!grouped[type]) grouped[type] = [];
                grouped[type].push(k);
            });
            
            const typeNames = {
                foreshadowing: '🎯 伏笔',
                character: '👤 人物',
                skill: '⚡ 技能',
                location: '📍 地点',
                item: '🎁 物品',
                relationship: '💫 关系',
                custom: '✨ 自定义'
            };
            
            const typeColors = {
                foreshadowing: '#ff6b6b',
                character: '#4ecdc4',
                skill: '#ffe66d',
                location: '#95e1d3',
                item: '#dda0dd',
                relationship: '#87ceeb',
                custom: '#c0c0c0'
            };
            
            Object.keys(grouped).forEach(type => {
                const section = document.createElement('div');
                section.innerHTML = '<div class="section-title">' + (typeNames[type] || type) + ' (' + grouped[type].length + ')</div>';
                
                grouped[type].forEach(k => {
                    const card = document.createElement('div');
                    card.className = 'keyword-card';
                    let html = '<div class="card-header">';
                    html += '<div class="card-title">' + (k.name || '未命名') + '</div>';
                    html += '<div class="card-type" style="background-color: ' + (typeColors[type] || typeColors.custom) + '">' + (typeNames[type] || type) + '</div>';
                    html += '</div>';
                    
                    if (k.description) {
                        html += '<div class="card-description">' + k.description + '</div>';
                    }
                    
                    if (k.related && k.related.length > 0) {
                        html += '<div class="card-related">相关：';
                        k.related.forEach(r => {
                            html += '<span>' + r + '</span>';
                        });
                        html += '</div>';
                    }
                    
                    card.innerHTML = html;
                    section.appendChild(card);
                });
                
                content.appendChild(section);
            });
            
            if (keywords.length === 0) {
                content.innerHTML = '<p>暂无关键词，请先创建配置文件。</p>';
            }
        }
        
        window.addEventListener('message', event => {
            const message = event.data;
            if (message.command === 'updateKeywords') {
                renderKeywords(message.keywords || []);
            }
        });
        
        refreshKeywords();
    </script>
</body>
</html>`;
}

function activate(context) {
    decorationCollection = vscode.window.createDecorationCollection();
    
    vscode.window.onDidChangeActiveTextEditor(editor => {
        activeEditor = editor;
        if (editor) {
            updateDecorations();
        }
    }, null, context.subscriptions);
    
    vscode.workspace.onDidChangeTextDocument(event => {
        if (activeEditor && event.document === activeEditor.document) {
            updateDecorations();
        }
    }, null, context.subscriptions);
    
    vscode.workspace.onDidChangeConfiguration(() => {
        updateDecorations();
    }, null, context.subscriptions);
    
    vscode.workspace.onDidCreateFiles(() => {
        updateDecorations();
    }, null, context.subscriptions);
    
    vscode.workspace.onDidChangeFiles(() => {
        updateDecorations();
    }, null, context.subscriptions);
    
    vscode.languages.registerHoverProvider(
        [{ language: 'plaintext' }, { language: 'markdown' }],
        new HoverProvider()
    );
    
    if (vscode.window.activeTextEditor) {
        activeEditor = vscode.window.activeTextEditor;
        updateDecorations();
    }
    
    vscode.commands.registerCommand('novelTextEnhancer.test', () => {
        vscode.window.showInformationMessage('插件正常工作!');
    });
    
    vscode.commands.registerCommand('novelTextEnhancer.reloadKeywords', () => {
        updateDecorations();
        vscode.window.showInformationMessage('关键词已重新加载');
    });
    
    vscode.commands.registerCommand('novelTextEnhancer.openConfig', () => {
        vscode.commands.executeCommand('workbench.action.openSettings', 'novelTextEnhancer');
    });
    
    vscode.commands.registerCommand('novelTextEnhancer.createConfig', () => {
        if (!vscode.workspace.workspaceFolders || vscode.workspace.workspaceFolders.length === 0) {
            vscode.window.showErrorMessage('请先打开一个文件夹');
            return;
        }
        const rootPath = vscode.workspace.workspaceFolders[0].uri.fsPath;
        const configPath = path.join(rootPath, '.novel-enhancer.json');
        const template = {
            keywords: [
                {
                    name: "柳祖",
                    type: "character",
                    description: "邪门的神秘祖师",
                    related: ["伏笔-柳祖", "邪门"]
                },
                {
                    name: "筑基",
                    type: "skill",
                    description: "修行第一个境界",
                    related: ["炼气", "金丹"]
                },
                {
                    name: "伏笔-程溪",
                    type: "foreshadowing",
                    description: "程溪相关伏笔线索",
                    related: []
                }
            ]
        };
        fs.writeFileSync(configPath, JSON.stringify(template, null, 2), 'utf-8');
        vscode.window.showInformationMessage(`配置文件已创建: ${configPath}`);
        vscode.window.showTextDocument(vscode.Uri.file(configPath));
    });
    
    let characterPanel;
    vscode.commands.registerCommand('novelTextEnhancer.showCharacterPanel', () => {
        if (!characterPanel) {
            characterPanel = createCharacterPanel(context);
            characterPanel.onDidDispose(() => {
                characterPanel = null;
            });
        } else {
            characterPanel.reveal(vscode.ViewColumn.Beside);
        }
        refreshKeywords(characterPanel);
    });
}

function deactivate() {}

module.exports = { activate, deactivate };
