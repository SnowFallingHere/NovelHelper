"""
使用说明标签页
提供完整的使用手册和帮助文档
"""

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextBrowser

from .base_tab import BaseTab
from ..core.config_manager import ConfigManager
from ..core.language_manager import language_manager

logger = logging.getLogger(__name__)


class HelpTab(BaseTab):
    """使用说明标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_name = "使用说明"
        
        # 配置属性
        self.base_font_size = int(ConfigManager.get('UI', 'base_font_size', fallback='18'))
        self.base_title_size = int(ConfigManager.get('UI', 'base_title_size', fallback='22'))
        
        logger.info(f"[{self.tab_name}] 创建实例")
    
    def _build_ui(self):
        """构建UI界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 10)
        
        # ====== 帮助文本浏览器 ======
        self.help_text = QTextBrowser()
        self.help_text.setOpenExternalLinks(True)
        self._render_help_html()
        main_layout.addWidget(self.help_text)
        
        logger.debug(f"[{self.tab_name}] UI构建完成")

    def retranslate_ui(self):
        self._render_help_html()
    
    def _load_data(self):
        """加载数据"""
        pass
    
    def _s(self, base, scale=1.0):
        """
        缩放字体大小
        
        Args:
            base: 基础大小
            scale: 缩放因子
            
        Returns:
            int: 缩放后的字体大小
        """
        return int(base * scale)
    
    def _render_help_html(self):
        """渲染帮助HTML内容"""
        if not hasattr(self, 'help_text'):
            return

        from ..core.theme_manager import theme_manager
        t = theme_manager.get_current_theme()
        bg = t.get('bg_color', '#F8F9FA')
        fg = t.get('fg_color', '#212529')
        accent = t.get('accent_color', '#0078D4')
        border = t.get('border_color', '#DEE2E6')
        font = t.get('font_family', "'Segoe UI', 'Microsoft YaHei', sans-serif")
        card = t.get('card_bg', '#FFFFFF')

        fs = self._s(self.base_font_size)
        fs_h2 = self._s(self.base_title_size)
        fs_h3 = self._s(self.base_font_size, 0.9)
        fs_h4 = self._s(self.base_font_size, 0.85)

        html_content = f"""
        <style>
        body {{ background:{bg}; color:{fg}; font-family:{font}; padding:1em 1.5em; line-height:1.7; font-size:{fs}px; }}
        h2 {{ color:{accent}; border-bottom:2px solid {border}; padding-bottom:6px; margin-top:0; font-size:{fs_h2}px; }}
        h3 {{ color:{accent}; margin-top:1.5em; font-size:{fs_h3}px; }}
        h4 {{ color:{fg}; font-size:{fs_h4}px; }}
        hr {{ border:0; border-top:1px solid {border}; }}
        code {{ background:{accent}15; color:{accent}; padding:1px 5px; border-radius:3px; font-family:Consolas; font-size:{int(fs*0.9)}px; }}
        blockquote {{ border-left:3px solid {accent}; margin:0.5em 0; padding:0.3em 1em; background:{accent}08; }}
        ul {{ padding-left:1.5em; }}
        li {{ margin:0.3em 0; }}
        .tag {{ display:inline-block; background:{accent}20; color:{accent}; padding:0 6px; border-radius:3px; font-size:{int(fs*0.85)}px; }}
        </style>
        
        <h2>{language_manager.tr('app_title')} — 完整使用手册</h2>
        
        <h3>一、概览</h3>
        <p>本工具是专为网络小说作者设计的写作辅助系统，集成了<strong>章节管理</strong>、<strong>剧情摘要</strong>、<strong>实时监控</strong>、<strong>关键词管理</strong>与<strong>关系图谱</strong>五大核心功能。</p>
        
        <hr>
        
        <h3>二、创建章节 <span class="tag">Create</span></h3>
        <p>用于创建新的卷和章节文件。程序启动时若检测到已初始化完成，将自动隐藏"章节创建"和"快速操作"区域。</p>
        <ul>
        <li><b>卷名</b>：输入卷的标题（如"芜湖"），程序根据配置的<strong>卷文件夹格式</strong>自动生成目录名</li>
        <li><b>章节名</b>：输入章节标题</li>
        <li><b>目录格式</b>：在参数配置中可自定义卷文件夹命名模板，支持：<br>
        <code>{{num}}</code>=数字 &nbsp; <code>{{cn.up.Volume}}</code>=第壹佰伍拾叁卷 &nbsp; <code>{{cn.low.Volume}}</code>=第一百五十三卷<br>
        <code>{{cn.num.Volume}}</code>=第153卷 &nbsp; <code>{{en.Volume}}</code>=Volume153 &nbsp; <code>{{ip.Volume}}</code>=一百五十三卷<br>
        <code>{{display:on}}</code>=显示格式描述（含new/old标记） &nbsp; <code>{{display:off}}</code>=隐藏格式描述<br>
        <code>{{title}}</code>=标题名</li>
        <li>示例：<code>{{cn.low.Volume}}{{title}}{{display:on}}</code> → <code>1第一卷_芜湖[new_35527]</code></li>
        <li>创建新章节时，自动更新 <code>get_Volume_update.json</code> 记录卷状态</li>
        </ul>
        
        <h4>初始化向导</h4>
        <ul>
        <li>首次使用时，系统将引导您初始化小说目录</li>
        <li>自动创建 <code>.novel_structure/</code> 目录并生成8个JSON模板文件（entities.json、factions.json、relationships.json、workspace.json、user_stopwords.json、.novel-enhancer.json、.frequency.json、.chapter_index_cache.json）</li>
        <li>自动创建第一卷目录和10个空白章节（1第一章.txt ~ 10第十章.txt）</li>
        <li>初始化完成后，章节创建和快速操作区域自动隐藏</li>
        </ul>
        
        <hr>
        
        <h3>三、Summary合并 <span class="tag">Merge</span></h3>
        <p>将小说目录下所有卷的章节文件合并为一个总览文件，方便通读与校对。</p>
        <ul>
        <li><b>排序规则</b>：卷按数字编号前缀升序排列，卷内章节也按数字编号升序排列</li>
        <li><b>覆盖范围</b>：合并所有卷下的所有章节文件（.txt）</li>
        <li>合并后的文件保存在小说目录下，文件名包含合并时间戳</li>
        <li>支持过滤空章节、自动跳过隐藏文件</li>
        </ul>
        
        <hr>
        
        <h3>四、监控管理 <span class="tag">Monitor</span></h3>
        <p>实时监控小说目录的变化，包括新增章节、文件修改等，并记录详细日志。监控是整个自动流程的核心引擎。</p>
        <ul>
        <li><b>启动监控</b>：开始监视选定目录</li>
        <li><b>停止监控</b>：暂停监视</li>
        <li><b>检查间隔</b>：每多少秒检测一次变化（可在参数配置中调整）</li>
        <li><b>心跳超时</b>：超过指定时间无响应则判定监控异常</li>
        <li><b>日志区</b>：按时间倒序显示所有监控事件，<span style='color:#00FF41'>成功信息为绿色</span>，<span style='color:#FFAA00'>警告为黄色</span>，<span style='color:#FF3333'>错误为红色</span></li>
        </ul>

        <h4>自动增章机制</h4>
        <ul>
        <li>每检测周期检查所有卷的最新章节</li>
        <li>如果最新章节内容<strong>超过配置的最少字数</strong>（默认20个中文字符），且不是默认模板内容：</li>
        <ul>
        <li>自动在该卷末尾新增配置数量（默认2章）的空章节供继续写作</li>
        <li>每到2的倍数章节触发Summary日志记录</li>
        </ul>
        </ul>

        <h4>自动增卷与旧卷处理</h4>
        <ul>
        <li>当用户手动创建新卷文件夹（纯数字文件夹，如 <code>2</code>、<code>3</code>）后，监控自动检测并执行完整流程：</li>
        <ol>
        <li><b>清理旧卷</b>：扫描上一卷，删除所有无内容的空章节</li>
        <li><b>承接章节</b>：找到上一卷最后一个有内容的章节号，在新卷中从该号+1开始创建规定数量的空章节</li>
        <li><b>统计字数</b>：计算旧卷总字数</li>
        <li><b>标记旧卷</b>：上一卷重命名为 <code>1[old_98765]</code></li>
        <li><b>标记新卷</b>：新卷重命名为 <code>2[new_12345]</code></li>
        <li><b>自动Summary</b>：自动运行一次Summary合并（模式2：统计并重命名），生成卷合并文件</li>
        </ol>
        <li>之后监控继续跟踪新卷，重复自动增章流程</li>
        </ul>
        
        <hr>
        
        <h3>五、写作趋势 <span class="tag">Trend</span></h3>
        <p>实时追踪写作进度和字数变化趋势。</p>
        <ul>
        <li><b>今日逐时</b>：按小时统计当日各时段的字数增量，精确到24小时</li>
        <li><b>近7/30/90天</b>：按天统计连续天数内的字数变化趋势</li>
        <li><b>坐标密度优化</b>：超过30天时X轴标签自动降采样（30天→10个标签，90天→15个标签），折线数据保持不变</li>
        <li><b>悬浮交叉线</b>：鼠标悬停在数据点上时，显示虚线的横纵交叉参考线</li>
        <li><b>自动刷新</b>：监控页检测到新章节时，自动刷新统计数据</li>
        </ul>
        
        <h3>六、参数配置 <span class="tag">Config</span></h3>
        <p>集中管理程序的各项参数。</p>
        <ul>
        <li><b>UI尺寸</b>：基础字号、标题字号、日志字号、网络图字号、关键词字号、关键词标题字号、人物卡字号、人物卡标题字号</li>
        <li><b>窗口尺寸</b>：初始宽度/高度</li>
        <li><b>色彩方案</b>：背景色、前景色、边框色、错误色、警告色等</li>
        <li><b>监控配置</b>：检查间隔、预读取章节数、最单词数、小说目录路径、心跳超时</li>
        <li><b>图谱配置</b>：布局理想长度、节点上限、自动保存布局</li>
        <li><b>词频配置</b>：最小词长、最小出现次数、非活跃章节数、自动扫描</li>
        <li><b>卷文件夹格式</b>：自定义新卷的目录命名模板，支持多种编号格式和显示模式</li>
        <li><b>主题</b>：图谱背景色、网格色、连线宽度</li>
        <li>修改后点击「保存并应用」生效，所有标签页自动刷新；点击「恢复默认」还原为Matrix风格配色</li>
        <li>切换小说目录时，所有标签页自动刷新数据，无需重启程序</li>
        </ul>
        
        <hr>
        
        <h3>七、关键词管理 <span class="tag">Keywords</span></h3>
        <p>结构化地管理小说中的核心元素：人物、技能、物品、地点、伏笔、势力关系等。</p>
        
        <h4>7.1 关键词列表视图</h4>
        <ul>
        <li>以列表形式展示所有关键词，显示名称、类型和简介</li>
        <li><b>类型筛选</b>：支持按类型筛选（全部/人物/技法/地点/物品/伏笔/事件/势力/时间点/关系/自定义）</li>
        <li>不同类型以不同颜色高亮：<span style='color:#00ff88'>人物</span>、<span style='color:#ff4466'>技能</span>、<span style='color:#00ccff'>地点</span>、<span style='color:#ffcc00'>物品</span>、<span style='color:#ff8c42'>伏笔</span>、<span style='color:#cc66ff'>关系</span> 等</li>
        <li>格式：<code>[名称][类型] - 简介</code></li>
        <li>支持自定义字号、颜色、字体（在参数配置中调整）</li>
        <li><b>编辑描述</b>：在人物卡详情页点击"编辑描述"可修改关键词描述，使用简单的输入框 + 确定按钮</li>
        </ul>

        <h4>7.2 人物卡视图 <span class="tag">Card</span></h4>
        <ul>
        <li>点击人物列表中的姓名，进入该人物的专属详情页（人物卡）</li>
        <li>人物卡展示：人物描述、关联技能、关联物品、关联地点、关联关系、关联伏笔</li>
        <li>支持双向关联：在人物卡中点击关联项可跳转到对应的人物卡</li>
        <li>底部显示"被以下人物提及"的反向引用列表</li>
        </ul>

        <h4>7.3 神经网络视图 <span class="tag">Graph</span></h4>
        <ul>
        <li>以力导向图方式展示所有关键词之间的关系网络</li>
        <li><b>节点类型</b>：不同颜色圆角矩形代表不同类型的关键词</li>
        <li><b>关系线</b>：
            <span style='color:#00ff88'>━━ 实线</span> 表示密切关系（友谊/恋情/敌对），
            <span style='color:#00ff88'>- - 虚线</span> 表示间接关系（掌握/传授/背负），
            <span style='color:#00ff88'>· · 点线</span> 表示暗示/推测关系，
            <span style='color:#00ff88'>-· -· 点划线</span> 表示空间关系（位于/连接/包含）</li>
        <li><b>交互操作</b>：
            <ul>
            <li>滚轮缩放图谱</li>
            <li>拖拽空白区域平移视图</li>
            <li>点击节点高亮该节点及其关联线</li>
            <li>双击节点跳转到对应的人物卡</li>
            <li>右键节点可查看详细菜单</li>
            </ul>
        </li>
        <li><b>节点导航</b>：右上角面板可通过复选框筛选显示/隐藏特定类型的节点</li>
        <li><b>图例</b>：左上角显示节点类型和关系线类型的颜色对照表</li>
        <li><b>布局控制</b>：支持保存/重置布局、导出为PNG、隔离显示选中节点</li>
        </ul>

        <h4>7.4 词频统计视图 <span class="tag">Frequency</span></h4>
        <ul>
        <li>自动统计关键词在章节文本中出现的频率</li>
        <li>支持设置最小词长、最小出现次数以过滤低价值数据</li>
        <li>可设定非活跃章节数，自动标记长期未出现的关键词</li>
        <li>词频数据用于辅助分析角色出场率、主题词热度变化等</li>
        </ul>
        
        <hr>
        
        <h3>八、快捷键与操作提示</h3>
        <ul>
        <li><b>保存并退出</b>：任意页面底部红色按钮，安全终止所有进程后关闭程序</li>
        <li><b>标签页切换</b>：点击顶部标签栏可在各功能模块间切换</li>
        <li>图谱区域支持鼠标右键菜单查看更多操作</li>
        </ul>
        
        <hr>
        
        <h3>九、数据文件说明</h3>
        <ul>
        <li><b>配置文件</b>：<code>NovelHelper.ini</code> — 存储所有UI配置、监控参数、图谱布局设置</li>
        <li><b>关键词文件</b>：<code>keywords.json</code> — 存储关键词及其关系和属性数据</li>
        <li><b>图谱布局文件</b>：<code>graph_layout.json</code> — 存储节点的手动布局位置</li>
        <li>建议定期备份上述文件以防数据丢失</li>
        </ul>
        
        <hr>
        
        <p style='text-align:center; color:#556655; font-size:{int(fs*0.85)}px;'>
        {language_manager.tr('app_title')} — 祝您写作顺利
        </p>
        """
        
        self.help_text.setHtml(html_content)
    
    def refresh_help(self):
        """刷新帮助内容（当语言或配置改变时调用）"""
        self._render_help_html()
