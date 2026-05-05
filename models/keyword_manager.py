import os
import json
import re
import logging
from collections import defaultdict
from core.config_manager import ConfigManager
from core.file_manager import file_manager, get_novel_dir
try:
    import jieba
except ImportError:
    jieba = None

logger = logging.getLogger(__name__)

class KeywordManager:
    """关键词管理器 - 负责加载、管理关键词高亮配置"""
    
    KEYWORD_TYPES = {
        'foreshadowing': {'color': '#ff6b6b', 'label': '伏笔'},
        'character': {'color': '#4ecdc4', 'label': '人物'},
        'skill': {'color': '#ffe66d', 'label': '技能'},
        'location': {'color': '#95e1d3', 'label': '地点'},
        'item': {'color': '#dda0dd', 'label': '物品'},
        'relationship': {'color': '#87ceeb', 'label': '关系'},
        'custom': {'color': '#c0c0c0', 'label': '自定义'}
    }
    
    @staticmethod
    def get_config_path():
        """获取关键词配置文件路径 - 在当前选定的小说目录"""
        novel_dir = get_novel_dir()
        return os.path.join(novel_dir, '.novel-enhancer.json')
    
    @staticmethod
    def load_keywords():
        """加载关键词配置"""
        config_path = KeywordManager.get_config_path()
        if not os.path.exists(config_path):
            return []
        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            keywords = data.get('keywords', [])
            for kw in keywords:
                if 'related' in kw and 'relationships' not in kw:
                    kw['relationships'] = [
                        {'target': target, 'type': 'related_to', 'description': ''}
                        for target in kw.pop('related')
                    ]
            return keywords
        except Exception as e:
            logger.error(f"加载关键词失败: {e}")
            return []
    
    @staticmethod
    def scan_novel_for_keyword(keyword_name):
        """扫描小说目录，找到关键词出现的章节"""
        novel_dir = get_novel_dir()
        if not os.path.exists(novel_dir):
            return []
        
        result = []
        try:
            # 遍历小说目录
            for root, dirs, files in os.walk(novel_dir):
                # 优先找符合卷名格式的目录
                for file in sorted(files):
                    if file.endswith('.txt') and not file.startswith('.'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if keyword_name in content:
                                    # 统计出现次数
                                    count = content.count(keyword_name)
                                    result.append({
                                        'file': file,
                                        'path': file_path,
                                        'count': count,
                                        'dir': os.path.basename(root),
                                        'chapter_num': file_manager.get_chapter_number(file)
                                    })
                        except Exception as e:
                            logger.debug(f"读取文件 {file_path} 失败: {e}")
                            continue
        except Exception as e:
            logger.error(f"扫描小说失败: {e}")
        return result
    
    _chapter_index_cache = None
    _chapter_index_mtime = None
    
    @staticmethod
    def _build_chapter_index():
        """构建倒排索引：关键词→章节列表，带缓存"""
        novel_dir = get_novel_dir()
        if not os.path.exists(novel_dir):
            return {}
        
        index = {}
        for vol in sorted(os.listdir(novel_dir)):
            vol_path = os.path.join(novel_dir, vol)
            if not os.path.isdir(vol_path):
                continue
            for fname in sorted(os.listdir(vol_path)):
                fpath = os.path.join(vol_path, fname)
                if not os.path.isfile(fpath) or not fname.endswith('.txt'):
                    continue
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    for kw in KeywordManager.load_keywords():
                        kw_name = kw.get('name')
                        if kw_name and kw_name in content:
                            if kw_name not in index:
                                index[kw_name] = []
                            index[kw_name].append({
                                'dir': vol, 'file': fname, 'path': fpath,
                                'count': content.count(kw_name)
                            })
                except Exception:
                    pass
        return index
    
    @staticmethod
    def scan_chapters_for_adventure(adventure_name, keywords):
        chapters = {}
        cache = KeywordManager._build_chapter_index()
        for kw in keywords:
            kw_name = kw.get('name')
            if not kw_name:
                continue
            kw_adventures = kw.get('adventures', [])
            if adventure_name in kw_adventures or adventure_name in kw_name:
                if kw_name in cache:
                    for r in cache[kw_name]:
                        chapter_key = f"{r['dir']}/{r['file']}"
                        if chapter_key not in chapters:
                            chapters[chapter_key] = {'file': r['file'], 'dir': r['dir'], 'path': r['path'], 'count': 0}
                        chapters[chapter_key]['count'] += r['count']
        return sorted(chapters.values(), key=lambda x: x['count'], reverse=True)
    
    @staticmethod
    def save_keywords(keywords):
        """保存关键词配置"""
        config_path = KeywordManager.get_config_path()
        try:
            import json
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({'keywords': keywords}, f, ensure_ascii=False, indent=2)
            logger.info(f"关键词已保存到 {config_path}")
            return True
        except Exception as e:
            logger.error(f"保存关键词失败: {e}")
            return False

    @staticmethod
    def add_relationship(from_name, to_name, rel_type, description):
        keywords = KeywordManager.load_keywords()
        from_kw = next((kw for kw in keywords if kw.get('name') == from_name), None)
        to_kw = next((kw for kw in keywords if kw.get('name') == to_name), None)
        if not from_kw:
            logger.error(f"未找到关键词: {from_name}")
            return False
        if not to_kw:
            logger.error(f"未找到关键词: {to_name}")
            return False
        if 'relationships' not in from_kw:
            from_kw['relationships'] = []
        for rel in from_kw['relationships']:
            if rel.get('target') == to_name:
                logger.info(f"关系已存在: {from_name} → {to_name}")
                return False
        from_kw['relationships'].append({
            'target': to_name,
            'type': rel_type,
            'description': description
        })
        return KeywordManager.save_keywords(keywords)
    
    @staticmethod
    def create_sample_config():
        """根据当前语言创建示例配置 - 中文萧炎、英文哈利波特、日语哆啦A梦"""
        current_lang = ConfigManager.get('Global', 'language', fallback='zh_CN')
        
        if current_lang == 'zh_CN':
            sample = {
                'keywords': [
                    {
                        'name': '萧炎',
                        'type': 'character',
                        'description': '主角，从天才沦为废柴，后逆袭成帝，号"炎帝"',
                        'personality': '坚毅、重情重义、隐忍、有恩报恩、有仇报仇',
                        'relationships': [
                            {'target': '萧薰儿', 'type': 'romance', 'description': '青梅竹马，终成眷属'},
                            {'target': '药老', 'type': 'mentorship', 'description': '师徒，授焚决、炼丹术'},
                            {'target': '美杜莎女王', 'type': 'romance', 'description': '伴侣，共育一子'},
                            {'target': '小医仙', 'type': 'friendship', 'description': '生死之交'},
                            {'target': '纳兰嫣然', 'type': 'hostility', 'description': '退婚之辱'},
                            {'target': '魂天帝', 'type': 'hostility', 'description': '最终宿敌'},
                            {'target': '魂族', 'type': 'hostility', 'description': '灭族之仇'},
                            {'target': '天府联盟', 'type': 'participates_in', 'description': '盟主'},
                            {'target': '玄重尺', 'type': 'owns', 'description': '早期武器，玄阶斗技载体'},
                            {'target': '焚决', 'type': 'masters', 'description': '主修功法，可吞噬异火进化'},
                            {'target': '佛怒火莲', 'type': 'masters', 'description': '自创斗技，融合多种异火'},
                            {'target': '纳戒', 'type': 'owns', 'description': '药老寄居之处'},
                            {'target': '迦南学院', 'type': 'travels_to', 'description': '两年修炼，获陨落心炎'},
                            {'target': '黑角域', 'type': 'travels_to', 'description': '历练、收服陨落心炎'},
                            {'target': '中州', 'type': 'travels_to', 'description': '后期主要舞台'},
                            {'target': '乌坦城退婚', 'type': 'participates_in', 'description': '故事起点'},
                            {'target': '双帝之战', 'type': 'participates_in', 'description': '最终决战'},
                            {'target': '三年之约', 'type': 'triggers', 'description': '约定之日'},
                            {'target': '魂族阴谋', 'type': 'carries', 'description': '背负对抗魂族的命运'},
                            {'target': '陀舍古帝传承', 'type': 'carries', 'description': '继承陀舍古帝衣钵'},
                            {'target': '萧战', 'type': 'family', 'description': '父亲'},
                            {'target': '彩鳞', 'type': 'romance', 'description': '美杜莎女王化名'},
                            {'target': '海波东', 'type': 'friendship', 'description': '忘年交'},
                            {'target': '紫妍', 'type': 'friendship', 'description': '认作妹妹'},
                            {'target': '古元', 'type': 'family', 'description': '岳父，萧薰儿之父'},
                            {'target': '丹塔', 'type': 'travels_to', 'description': '参加炼药师大会'},
                            {'target': '蛇人族圣城', 'type': 'travels_to', 'description': '收服美杜莎'},
                            {'target': '出云帝国', 'type': 'travels_to', 'description': '与小医仙同行'},
                        ]
                    },
                    {
                        'name': '萧薰儿',
                        'type': 'character',
                        'description': '女主角，古族大小姐，古帝血脉者，对萧炎一往情深',
                        'personality': '温柔、聪慧、内敛、对萧炎极尽包容',
                        'relationships': [
                            {'target': '萧炎', 'type': 'romance', 'description': '青梅竹马，古族回归后分离多年'},
                            {'target': '古族', 'type': 'family', 'description': '古族大小姐'},
                            {'target': '古元', 'type': 'family', 'description': '父亲'},
                            {'target': '金帝焚天炎', 'type': 'owns', 'description': '古族传承异火'},
                            {'target': '帝印决', 'type': 'masters', 'description': '古族镇族斗技'},
                            {'target': '古玉', 'type': 'owns', 'description': '古族世代守护'},
                            {'target': '迦南学院', 'type': 'travels_to', 'description': '与萧炎同窗'},
                            {'target': '古界', 'type': 'located_at', 'description': '古族隐居空间'},
                            {'target': '乌坦城', 'type': 'travels_to', 'description': '童年与萧炎共处'},
                            {'target': '魂族', 'type': 'hostility', 'description': '古族宿敌'},
                        ]
                    },
                    {
                        'name': '药老',
                        'type': 'character',
                        'description': '药尊者，九品炼药师，萧炎的老师，灵魂体',
                        'personality': '慈爱、护短、幽默、学识渊博',
                        'relationships': [
                            {'target': '萧炎', 'type': 'mentorship', 'description': '师徒，视如己出'},
                            {'target': '焚决', 'type': 'teaches', 'description': '传给萧炎'},
                            {'target': '骨灵冷火', 'type': 'owns', 'description': '自己收服的异火'},
                            {'target': '纳戒', 'type': 'located_at', 'description': '灵魂寄居之处'},
                            {'target': '韩枫', 'type': 'mentorship', 'description': '前弟子，后叛变'},
                            {'target': '魂族', 'type': 'hostility', 'description': '被魂殿囚禁多年'},
                            {'target': '天府联盟', 'type': 'participates_in', 'description': '荣誉盟主'},
                            {'target': '蛇人族圣城', 'type': 'travels_to', 'description': '随萧炎前往'},
                            {'target': '中州', 'type': 'travels_to', 'description': '被囚和重获自由之地'},
                        ]
                    },
                    {
                        'name': '美杜莎女王',
                        'type': 'character',
                        'description': '蛇人族女王，后与萧炎相识相爱，号"彩鳞"',
                        'personality': '高傲、冷艳、对萧炎深情、护短',
                        'relationships': [
                            {'target': '萧炎', 'type': 'romance', 'description': '伴侣，共育萧霖'},
                            {'target': '蛇人族', 'type': 'family', 'description': '女王'},
                            {'target': '蛇人族圣城', 'type': 'located_at', 'description': '领地'},
                            {'target': '迦南学院', 'type': 'travels_to', 'description': '随萧炎前往'},
                            {'target': '中州', 'type': 'travels_to', 'description': '后期定居'},
                            {'target': '彩鳞', 'type': 'related_to', 'description': '化名'},
                            {'target': '魂族', 'type': 'hostility', 'description': '对抗魂族'},
                        ]
                    },
                    {
                        'name': '彩鳞',
                        'type': 'character',
                        'description': '美杜莎女王的人类化名，萧炎之妻',
                        'personality': '冷艳深情',
                        'relationships': [
                            {'target': '萧炎', 'type': 'romance', 'description': '夫妻'},
                            {'target': '美杜莎女王', 'type': 'related_to', 'description': '同一人'},
                        ]
                    },
                    {
                        'name': '小医仙',
                        'type': 'character',
                        'description': '厄难毒体，萧炎的生死之交，毒宗宗主',
                        'personality': '善良、坚韧、为萧炎甘愿牺牲',
                        'relationships': [
                            {'target': '萧炎', 'type': 'friendship', 'description': '生死之交，暗恋萧炎'},
                            {'target': '出云帝国', 'type': 'located_at', 'description': '毒宗所在地'},
                            {'target': '中州', 'type': 'travels_to', 'description': '随萧炎前往'},
                            {'target': '魂族', 'type': 'hostility', 'description': '曾被魂族利用'},
                        ]
                    },
                    {
                        'name': '纳兰嫣然',
                        'type': 'character',
                        'description': '云岚宗宗主之徒，曾与萧炎有婚约，后退婚',
                        'personality': '高傲、骄傲、后对萧炎心生悔意',
                        'relationships': [
                            {'target': '萧炎', 'type': 'hostility', 'description': '退婚之耻'},
                            {'target': '云岚宗', 'type': 'family', 'description': '宗主之徒'},
                            {'target': '云韵', 'type': 'mentorship', 'description': '师傅'},
                            {'target': '加玛帝国', 'type': 'located_at', 'description': '所属帝国'},
                        ]
                    },
                    {
                        'name': '云韵',
                        'type': 'character',
                        'description': '云岚宗宗主，加玛帝国十大强者，与萧炎有情感纠葛',
                        'personality': '温柔、知性、重情义',
                        'relationships': [
                            {'target': '萧炎', 'type': 'romance', 'description': '曖昧情愫，有缘无分'},
                            {'target': '云岚宗', 'type': 'family', 'description': '前任宗主'},
                            {'target': '纳兰嫣然', 'type': 'mentorship', 'description': '徒弟'},
                            {'target': '加玛帝国', 'type': 'located_at', 'description': '宗门所在地'},
                            {'target': '中州', 'type': 'travels_to', 'description': '后来前往'},
                        ]
                    },
                    {
                        'name': '海波东',
                        'type': 'character',
                        'description': '加玛帝国十大强者，人称"冰皇"，萧炎忘年交',
                        'personality': '豪爽、重诺',
                        'relationships': [
                            {'target': '萧炎', 'type': 'friendship', 'description': '忘年交'},
                            {'target': '蛇人族圣城', 'type': 'travels_to', 'description': '曾与美杜莎大战'},
                            {'target': '加玛帝国', 'type': 'located_at', 'description': '所属帝国'},
                            {'target': '魂族', 'type': 'hostility', 'description': '对抗魂族'},
                        ]
                    },
                    {
                        'name': '萧战',
                        'type': 'character',
                        'description': '萧炎之父，萧家族长',
                        'relationships': [
                            {'target': '萧炎', 'type': 'family', 'description': '父子'},
                            {'target': '萧鼎', 'type': 'family', 'description': '长子'},
                            {'target': '萧厉', 'type': 'family', 'description': '次子'},
                            {'target': '乌坦城', 'type': 'located_at', 'description': '萧家驻地'},
                        ]
                    },
                    {
                        'name': '古元',
                        'type': 'character',
                        'description': '古族族长，九星斗圣，萧薰儿之父',
                        'relationships': [
                            {'target': '萧薰儿', 'type': 'family', 'description': '父女'},
                            {'target': '萧炎', 'type': 'family', 'description': '女婿'},
                            {'target': '古族', 'type': 'family', 'description': '族长'},
                            {'target': '魂天帝', 'type': 'hostility', 'description': '相互制衡'},
                        ]
                    },
                    {
                        'name': '魂天帝',
                        'type': 'character',
                        'description': '魂族族长，九星斗圣巅峰，最终反派',
                        'personality': '野心极大、心狠手辣、诡计多端',
                        'relationships': [
                            {'target': '萧炎', 'type': 'hostility', 'description': '最终对决'},
                            {'target': '古元', 'type': 'hostility', 'description': '宿敌'},
                            {'target': '魂族', 'type': 'family', 'description': '族长'},
                            {'target': '魂族阴谋', 'type': 'triggers', 'description': '幕后主使'},
                            {'target': '陀舍古帝传承', 'type': 'hostility', 'description': '争夺传承'},
                            {'target': '双帝之战', 'type': 'participates_in', 'description': '与萧炎最终决战'},
                        ]
                    },
                    {
                        'name': '紫妍',
                        'type': 'character',
                        'description': '太虚古龙族龙皇，化为人形，萧炎认作妹妹',
                        'personality': '天真、贪吃、战力极强',
                        'relationships': [
                            {'target': '萧炎', 'type': 'friendship', 'description': '认作大哥'},
                            {'target': '迦南学院', 'type': 'located_at', 'description': '长期居住在药材库'},
                            {'target': '中州', 'type': 'travels_to', 'description': '随萧炎闯荡'},
                            {'target': '魂族', 'type': 'hostility', 'description': '对抗魂族'},
                        ]
                    },
                    {
                        'name': '古族',
                        'type': 'faction',
                        'description': '远古八族之一，拥有古帝血脉，萧薰儿出身',
                        'relationships': [
                            {'target': '萧薰儿', 'type': 'contains', 'description': '大小姐'},
                            {'target': '古元', 'type': 'contains', 'description': '族长'},
                            {'target': '魂族', 'type': 'hostility', 'description': '世代宿敌'},
                            {'target': '天府联盟', 'type': 'friendship', 'description': '盟友'},
                            {'target': '古界', 'type': 'located_at', 'description': '族地'},
                        ]
                    },
                    {
                        'name': '魂族',
                        'type': 'faction',
                        'description': '远古八族之一，野心最大，妄图统治大陆',
                        'relationships': [
                            {'target': '魂天帝', 'type': 'contains', 'description': '族长'},
                            {'target': '萧炎', 'type': 'hostility', 'description': '追杀对象'},
                            {'target': '古族', 'type': 'hostility', 'description': '世代宿敌'},
                            {'target': '天府联盟', 'type': 'hostility', 'description': '对立方'},
                            {'target': '魂殿', 'type': 'contains', 'description': '下属组织'},
                            {'target': '魂界', 'type': 'located_at', 'description': '族地'},
                            {'target': '魂族阴谋', 'type': 'triggers', 'description': '幕后策划'},
                        ]
                    },
                    {
                        'name': '天府联盟',
                        'type': 'faction',
                        'description': '萧炎创立的联盟，联合各大势力对抗魂族',
                        'relationships': [
                            {'target': '萧炎', 'type': 'contains', 'description': '盟主'},
                            {'target': '药老', 'type': 'contains', 'description': '荣誉盟主'},
                            {'target': '魂族', 'type': 'hostility', 'description': '对抗对象'},
                            {'target': '古族', 'type': 'friendship', 'description': '盟友'},
                            {'target': '丹塔', 'type': 'friendship', 'description': '盟友'},
                            {'target': '中州', 'type': 'located_at', 'description': '总部所在地'},
                        ]
                    },
                    {
                        'name': '蛇人族',
                        'type': 'faction',
                        'description': '生活在塔戈尔大沙漠的种族，美杜莎女王统领',
                        'relationships': [
                            {'target': '美杜莎女王', 'type': 'contains', 'description': '女王'},
                            {'target': '蛇人族圣城', 'type': 'located_at', 'description': '族地'},
                            {'target': '萧炎', 'type': 'friendship', 'description': '盟友'},
                        ]
                    },
                    {
                        'name': '云岚宗',
                        'type': 'faction',
                        'description': '加玛帝国最強宗门，曾与萧炎结仇',
                        'relationships': [
                            {'target': '云韵', 'type': 'contains', 'description': '前任宗主'},
                            {'target': '纳兰嫣然', 'type': 'contains', 'description': '核心弟子'},
                            {'target': '加玛帝国', 'type': 'located_at', 'description': '宗门所在地'},
                            {'target': '萧炎', 'type': 'hostility', 'description': '宗门覆灭'},
                        ]
                    },
                    {
                        'name': '乌坦城',
                        'type': 'location',
                        'description': '萧炎出生的边陲小城，萧家位于此',
                        'region': '加玛帝国',
                        'relationships': [
                            {'target': '萧炎', 'type': 'contains', 'description': '出生地'},
                            {'target': '萧战', 'type': 'contains', 'description': '萧家驻地'},
                            {'target': '萧薰儿', 'type': 'contains', 'description': '寄居之地'},
                            {'target': '乌坦城退婚', 'type': 'contains', 'description': '退婚事件发生地'},
                            {'target': '加玛帝国', 'type': 'connects_to', 'description': '所属帝国'},
                        ]
                    },
                    {
                        'name': '迦南学院',
                        'type': 'location',
                        'description': '大陆知名的修炼学院，内院有天焚炼气塔',
                        'region': '黑角域边缘',
                        'relationships': [
                            {'target': '萧炎', 'type': 'contains', 'description': '在此修炼两年'},
                            {'target': '萧薰儿', 'type': 'contains', 'description': '同窗'},
                            {'target': '紫妍', 'type': 'contains', 'description': '内院药材库常客'},
                            {'target': '陨落心炎', 'type': 'contains', 'description': '天焚炼气塔核心'},
                            {'target': '黑角域', 'type': 'connects_to', 'description': '邻近区域'},
                        ]
                    },
                    {
                        'name': '黑角域',
                        'type': 'location',
                        'description': '法外之地，势力混杂，弱肉强食',
                        'region': '中州与边缘地带交界',
                        'relationships': [
                            {'target': '迦南学院', 'type': 'connects_to', 'description': '相邻'},
                            {'target': '萧炎', 'type': 'contains', 'description': '在此历练收服陨落心炎'},
                            {'target': '韩枫', 'type': 'contains', 'description': '黑角域强者'},
                            {'target': '中州', 'type': 'connects_to', 'description': '通往中州的必经之路'},
                        ]
                    },
                    {
                        'name': '中州',
                        'type': 'location',
                        'description': '斗气大陆中心地带，强者云集之处',
                        'region': '大陆中心',
                        'relationships': [
                            {'target': '天府联盟', 'type': 'contains', 'description': '联盟总部'},
                            {'target': '丹塔', 'type': 'contains', 'description': '位于中州'},
                            {'target': '古界', 'type': 'connects_to', 'description': '古族空间入口'},
                            {'target': '萧炎', 'type': 'contains', 'description': '后期主要活动区域'},
                            {'target': '魂殿', 'type': 'contains', 'description': '魂族据点'},
                        ]
                    },
                    {
                        'name': '蛇人族圣城',
                        'type': 'location',
                        'description': '蛇人族王城，位于塔戈尔大沙漠深处',
                        'region': '塔戈尔大沙漠',
                        'relationships': [
                            {'target': '美杜莎女王', 'type': 'contains', 'description': '王宫所在地'},
                            {'target': '蛇人族', 'type': 'contains', 'description': '种族聚居地'},
                            {'target': '萧炎', 'type': 'contains', 'description': '收服美杜莎之地'},
                        ]
                    },
                    {
                        'name': '出云帝国',
                        'type': 'location',
                        'description': '以毒闻名，小医仙创建毒宗之处',
                        'region': '大陆边缘',
                        'relationships': [
                            {'target': '小医仙', 'type': 'contains', 'description': '毒宗所在地'},
                            {'target': '萧炎', 'type': 'contains', 'description': '与小医仙同行历练'},
                        ]
                    },
                    {
                        'name': '古界',
                        'type': 'location',
                        'description': '古族隐居的独立空间，外人难入',
                        'region': '中州隐秘空间',
                        'relationships': [
                            {'target': '古族', 'type': 'contains', 'description': '族地'},
                            {'target': '古元', 'type': 'contains', 'description': '族长居所'},
                            {'target': '萧薰儿', 'type': 'contains', 'description': '古族回归后居所'},
                        ]
                    },
                    {
                        'name': '丹塔',
                        'type': 'location',
                        'description': '中州炼药师圣殿，举办炼药师大会',
                        'region': '中州',
                        'relationships': [
                            {'target': '天府联盟', 'type': 'friendship', 'description': '盟友'},
                            {'target': '萧炎', 'type': 'contains', 'description': '参加炼药师大会'},
                            {'target': '药老', 'type': 'contains', 'description': '曾为丹塔长老'},
                            {'target': '中州', 'type': 'located_at', 'description': '位于中州'},
                        ]
                    },
                    {
                        'name': '玄重尺',
                        'type': 'item',
                        'description': '萧炎早期武器，实为玄阶斗技载体',
                        'relationships': [
                            {'target': '萧炎', 'type': 'owns', 'description': '持有者'},
                            {'target': '纳戒', 'type': 'combines_with', 'description': '配套使用'},
                        ]
                    },
                    {
                        'name': '纳戒',
                        'type': 'item',
                        'description': '空间戒指，药老灵魂寄居其中',
                        'relationships': [
                            {'target': '萧炎', 'type': 'owns', 'description': '持有者'},
                            {'target': '药老', 'type': 'contains', 'description': '灵魂寄居'},
                        ]
                    },
                    {
                        'name': '古玉',
                        'type': 'item',
                        'description': '远古八族世代守护的钥匙，开启陀舍古帝洞府的关键',
                        'relationships': [
                            {'target': '古族', 'type': 'owns', 'description': '守护者'},
                            {'target': '萧薰儿', 'type': 'owns', 'description': '持有者'},
                            {'target': '陀舍古帝传承', 'type': 'hints_at', 'description': '开启传承的关键'},
                            {'target': '魂族', 'type': 'hostility', 'description': '争夺对象'},
                        ]
                    },
                    {
                        'name': '焚决',
                        'type': 'skill',
                        'description': '药老传承的功法，可通过吞噬异火不断进化',
                        'relationships': [
                            {'target': '药老', 'type': 'derives_from', 'description': '药老获得'},
                            {'target': '萧炎', 'type': 'masters', 'description': '主修功法'},
                            {'target': '异火', 'type': 'combines_with', 'description': '吞噬异火进化'},
                            {'target': '佛怒火莲', 'type': 'derives_from', 'description': '基于焚决创造'},
                        ]
                    },
                    {
                        'name': '佛怒火莲',
                        'type': 'skill',
                        'description': '萧炎自创斗技，融合多种异火威力极大',
                        'relationships': [
                            {'target': '萧炎', 'type': 'masters', 'description': '创造者'},
                            {'target': '焚决', 'type': 'derives_from', 'description': '基于焚决'},
                            {'target': '异火', 'type': 'combines_with', 'description': '需要多种异火融合'},
                        ]
                    },
                    {
                        'name': '帝印决',
                        'type': 'skill',
                        'description': '古族镇族斗技，共五印，威力随修炼程度递增',
                        'relationships': [
                            {'target': '古族', 'type': 'derives_from', 'description': '古族斗技'},
                            {'target': '萧炎', 'type': 'masters', 'description': '修炼者'},
                            {'target': '萧薰儿', 'type': 'masters', 'description': '古族血脉修炼'},
                        ]
                    },
                    {
                        'name': '金帝焚天炎',
                        'type': 'skill',
                        'description': '古族传承的异火，威力极强，排名极高',
                        'relationships': [
                            {'target': '萧薰儿', 'type': 'owns', 'description': '持有者'},
                            {'target': '古族', 'type': 'derives_from', 'description': '古族传承'},
                        ]
                    },
                    {
                        'name': '异火',
                        'type': 'item',
                        'description': '天地间诞生的火焰，极为稀有，焚决可吞噬进化',
                        'relationships': [
                            {'target': '萧炎', 'type': 'owns', 'description': '吞噬多种'},
                            {'target': '焚决', 'type': 'combines_with', 'description': '焚决的进化材料'},
                            {'target': '骨灵冷火', 'type': 'contains', 'description': '异火之一'},
                            {'target': '陨落心炎', 'type': 'contains', 'description': '异火之一'},
                        ]
                    },
                    {
                        'name': '骨灵冷火',
                        'type': 'item',
                        'description': '药老收服的异火，呈森白色',
                        'relationships': [
                            {'target': '药老', 'type': 'owns', 'description': '持有者'},
                            {'target': '异火', 'type': 'contains', 'description': '异火种类'},
                            {'target': '萧炎', 'type': 'uses', 'description': '药老赠予'},
                        ]
                    },
                    {
                        'name': '陨落心炎',
                        'type': 'item',
                        'description': '迦南学院天焚炼气塔核心的异火',
                        'relationships': [
                            {'target': '迦南学院', 'type': 'contains', 'description': '炼气塔核心'},
                            {'target': '萧炎', 'type': 'owns', 'description': '收服者'},
                            {'target': '异火', 'type': 'contains', 'description': '异火种类'},
                        ]
                    },
                    {
                        'name': '乌坦城退婚',
                        'type': 'adventure',
                        'description': '纳兰嫣然前来萧家退婚，萧炎受辱发誓三年后超越',
                        'relationships': [
                            {'target': '萧炎', 'type': 'participates_in', 'description': '当事人'},
                            {'target': '纳兰嫣然', 'type': 'triggers', 'description': '退婚发起者'},
                            {'target': '乌坦城', 'type': 'contains', 'description': '事发地点'},
                            {'target': '三年之约', 'type': 'triggers', 'description': '约定之始'},
                            {'target': '萧战', 'type': 'participates_in', 'description': '见证者'},
                        ]
                    },
                    {
                        'name': '双帝之战',
                        'type': 'adventure',
                        'description': '炎帝萧炎与魂天帝的最终决战，决定大陆命运',
                        'relationships': [
                            {'target': '萧炎', 'type': 'participates_in', 'description': '炎帝'},
                            {'target': '魂天帝', 'type': 'participates_in', 'description': '最终反派'},
                            {'target': '陀舍古帝传承', 'type': 'triggers', 'description': '争夺的根源'},
                            {'target': '魂族', 'type': 'participates_in', 'description': '魂族大军'},
                            {'target': '天府联盟', 'type': 'participates_in', 'description': '联军'},
                        ]
                    },
                    {
                        'name': '三年之约',
                        'type': 'time_point',
                        'description': '萧炎与纳兰嫣然的三年后决战之约，标志萧炎正式崛起',
                        'status': '已过',
                        'relationships': [
                            {'target': '萧炎', 'type': 'triggers', 'description': '约定一方'},
                            {'target': '纳兰嫣然', 'type': 'triggers', 'description': '约定另一方'},
                            {'target': '乌坦城退婚', 'type': 'triggers', 'description': '约定的起因'},
                            {'target': '云岚宗', 'type': 'contains', 'description': '决战地点'},
                        ]
                    },
                    {
                        'name': '魂族阴谋',
                        'type': 'foreshadowing',
                        'description': '魂族妄图收集古玉、夺取陀舍古帝传承，统治大陆',
                        'relationships': [
                            {'target': '魂族', 'type': 'triggers', 'description': '策划者'},
                            {'target': '魂天帝', 'type': 'triggers', 'description': '幕后主使'},
                            {'target': '陀舍古帝传承', 'type': 'hints_at', 'description': '阴谋目标'},
                            {'target': '萧炎', 'type': 'carries', 'description': '对抗者'},
                            {'target': '天府联盟', 'type': 'carries', 'description': '对抗者'},
                            {'target': '药老', 'type': 'carries', 'description': '受害者'},
                        ]
                    },
                    {
                        'name': '陀舍古帝传承',
                        'type': 'foreshadowing',
                        'description': '远古斗帝留下的传承，需古玉开启，萧炎最终继承',
                        'relationships': [
                            {'target': '萧炎', 'type': 'carries', 'description': '最终继承者'},
                            {'target': '魂天帝', 'type': 'hostility', 'description': '争夺者'},
                            {'target': '古玉', 'type': 'hints_at', 'description': '开启钥匙'},
                            {'target': '双帝之战', 'type': 'triggers', 'description': '争夺的根源'},
                        ]
                    },
                ]
            }
        elif current_lang == 'en_US':
            # 英文：哈利波特
            sample = {
                'keywords': [
                    {
                        'name': 'Harry Potter',
                        'type': 'character',
                        'description': 'The Boy Who Lived',
                        'relationships': [
                            {'target': 'Hermione Granger', 'type': 'related_to', 'description': ''},
                            {'target': 'Ron Weasley', 'type': 'related_to', 'description': ''},
                            {'target': 'Voldemort', 'type': 'related_to', 'description': ''}
                        ],
                        'personality': 'Brave, Loyal, Kind',
                        'skills': ['Expelliarmus', 'Patronus Charm'],
                        'items': ['Wand', 'Invisibility Cloak', 'Resurrection Stone'],
                        'adventures': [
                            'Philosopher\'s Stone',
                            'Chamber of Secrets',
                            'Prisoner of Azkaban',
                            'Goblet of Fire',
                            'Order of Phoenix',
                            'Half Blood Prince',
                            'Deathly Hallows'
                        ]
                    },
                    {
                        'name': 'Hermione Granger',
                        'type': 'character',
                        'description': "Harry's brilliant best friend",
                        'relationships': [
                            {'target': 'Harry Potter', 'type': 'related_to', 'description': ''},
                            {'target': 'Ron Weasley', 'type': 'related_to', 'description': ''}
                        ],
                        'personality': 'Intelligent, Diligent',
                        'skills': ['O.W.L.s', 'Wit'],
                        'items': ['Wand', 'Time Turner'],
                        'adventures': [
                            'All adventures with Harry'
                        ]
                    },
                    {
                        'name': 'Ron Weasley',
                        'type': 'character',
                        'description': "Harry's loyal best friend",
                        'relationships': [
                            {'target': 'Harry Potter', 'type': 'related_to', 'description': ''},
                            {'target': 'Hermione Granger', 'type': 'related_to', 'description': ''}
                        ],
                        'personality': 'Loyal, Humorous',
                        'skills': ['Wizard Chess'],
                        'items': ['Wand', 'Deluminator'],
                        'adventures': [
                            'All adventures with Harry'
                        ]
                    },
                    {
                        'name': 'Voldemort',
                        'type': 'character',
                        'description': 'The Dark Lord who tried to kill Harry',
                        'relationships': [
                            {'target': 'Harry Potter', 'type': 'related_to', 'description': ''}
                        ]
                    },
                    {
                        'name': 'Wand',
                        'type': 'item',
                        'description': "A wizard's most important tool",
                        'relationships': [
                            {'target': 'Harry Potter', 'type': 'related_to', 'description': ''},
                            {'target': 'Voldemort', 'type': 'related_to', 'description': ''}
                        ]
                    },
                    {
                        'name': 'Expelliarmus',
                        'type': 'skill',
                        'description': 'The disarming charm',
                        'relationships': []
                    },
                    {
                        'name': 'Foreshadowing-Horcruxes',
                        'type': 'foreshadowing',
                        'description': 'Mysterious objects that seem important',
                        'relationships': [
                            {'target': 'Voldemort', 'type': 'related_to', 'description': ''}
                        ]
                    }
                ]
            }
        elif current_lang == 'ja_JP':
            # 日文：哆啦A梦
            sample = {
                'keywords': [
                    {
                        'name': 'ドラえもん',
                        'type': 'character',
                        'description': '未来から来たネコ型ロボット',
                        'relationships': [
                            {'target': 'のび太', 'type': 'related_to', 'description': ''},
                            {'target': '四次元ポケット', 'type': 'related_to', 'description': ''},
                            {'target': '道具', 'type': 'related_to', 'description': ''}
                        ],
                        'personality': 'おっちょこちょいだがやさしい',
                        'skills': ['道具取り出し'],
                        'items': ['四次元ポケット', 'どこでもドア', 'タケコプター'],
                        'adventures': [
                            '未来から来る',
                            'のび太を助ける'
                        ]
                    },
                    {
                        'name': 'のび太',
                        'type': 'character',
                        'description': 'ドラえもんがサポートする主人公',
                        'relationships': [
                            {'target': 'ドラえもん', 'type': 'related_to', 'description': ''},
                            {'target': 'しずかちゃん', 'type': 'related_to', 'description': ''}
                        ],
                        'personality': 'のろまだが心は優しい',
                        'skills': ['射撃', '眠ること'],
                        'items': ['ドラえもんの道具'],
                        'adventures': [
                            '学校',
                            '空き地',
                            'いろいろな冒険'
                        ]
                    },
                    {
                        'name': 'しずかちゃん',
                        'type': 'character',
                        'description': 'のび太のクラスメイト',
                        'relationships': [
                            {'target': 'のび太', 'type': 'related_to', 'description': ''}
                        ]
                    },
                    {
                        'name': '四次元ポケット',
                        'type': 'item',
                        'description': '未来の道具が入った魔法のポケット',
                        'relationships': [
                            {'target': 'ドラえもん', 'type': 'related_to', 'description': ''},
                            {'target': '道具', 'type': 'related_to', 'description': ''}
                        ]
                    },
                    {
                        'name': 'どこでもドア',
                        'type': 'item',
                        'description': '行きたい場所に瞬間移動できる扉',
                        'relationships': [
                            {'target': '四次元ポケット', 'type': 'related_to', 'description': ''},
                            {'target': '道具', 'type': 'related_to', 'description': ''}
                        ]
                    },
                    {
                        'name': '伏笔-未来',
                        'type': 'foreshadowing',
                        'description': '未来には何が待っている？',
                        'relationships': [
                            {'target': 'ドラえもん', 'type': 'related_to', 'description': ''}
                        ]
                    }
                ]
            }
        else:
            # 默认：英文哈利波特
            sample = {
                'keywords': [
                    {
                        'name': 'Harry Potter',
                        'type': 'character',
                        'description': 'The Boy Who Lived',
                        'relationships': []
                    }
                ]
            }
        
        config_path = KeywordManager.get_config_path()
        try:
            import json
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(sample, f, ensure_ascii=False, indent=2)
            logger.info(f"创建示例配置 ({current_lang}): {config_path}")
            return config_path
        except Exception as e:
            logger.error(f"创建示例配置失败: {e}")
            return None
    
    @staticmethod
    def scan_frequency(novel_dir, min_len=2, min_occ=3):
        from datetime import datetime
        freq = {"scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "total_chapters": 0, "words": {}}
        volumes = sorted([f for f in os.listdir(novel_dir) if os.path.isdir(os.path.join(novel_dir, f)) and file_manager.is_numeric_volume_folder(f)])
        ch_idx = 0
        for vol in volumes:
            vol_path = os.path.join(novel_dir, vol)
            chapters = sorted([f for f in os.listdir(vol_path) if f.endswith('.txt')])
            for ch in chapters:
                ch_idx += 1
                ch_path = os.path.join(vol_path, ch)
                try:
                    with open(ch_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if jieba:
                        words = [w.strip() for w in jieba.cut(content) if len(w.strip()) >= min_len and not w.strip().isdigit() and not re.match(r'^[\W_]+$', w.strip())]
                    else:
                        words = re.findall(r'[\u4e00-\u9fff\w]{%d,}' % min_len, content)
                    wc = {}
                    for w in words:
                        wc[w] = wc.get(w, 0) + 1
                    for w, c in wc.items():
                        if c >= min_occ:
                            if w not in freq["words"]:
                                freq["words"][w] = {"chapters": {}, "total_occurrences": 0, "type": "?", "status": "active"}
                            freq["words"][w]["chapters"][str(ch_idx)] = c
                            freq["words"][w]["total_occurrences"] += c
                except:
                    pass
        freq["total_chapters"] = ch_idx
        logger.info(f"频度扫描完成: {ch_idx}章, {len(freq['words'])}词条")
        return freq

keyword_manager = KeywordManager()
