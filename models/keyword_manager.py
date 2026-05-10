import os
import json
import re
import logging
from collections import defaultdict
from core.config_manager import ConfigManager
from core.file_manager import file_manager, get_novel_dir, get_novel_config_dir, ensure_novel_config_dir
try:
    import jieba
except ImportError:
    jieba = None

logger = logging.getLogger(__name__)

class KeywordManager:
    """关键词管理器 - 支持拆分存储"""
    
    KEYWORD_TYPES = {
        'foreshadowing': {'color': '#ff6b6b', 'label': '伏笔'},
        'character': {'color': '#4ecdc4', 'label': '人物'},
        'skill': {'color': '#ffe66d', 'label': '技能'},
        'location': {'color': '#95e1d3', 'label': '地点'},
        'item': {'color': '#dda0dd', 'label': '物品'},
        'relationship': {'color': '#87ceeb', 'label': '关系'},
        'custom': {'color': '#c0c0c0', 'label': '自定义'}
    }

    ENTITY_TYPES = {'character', 'skill', 'location', 'item'}
    FACTION_FIELDS = {'structure', 'template', 'roles'}

    @staticmethod
    def get_config_path():
        ensure_novel_config_dir()
        return os.path.join(get_novel_config_dir(), '.novel-enhancer.json')

    @staticmethod
    def _get_data_dir():
        ensure_novel_config_dir()
        return get_novel_config_dir()

    @staticmethod
    def _get_split_paths():
        d = KeywordManager._get_data_dir()
        return {
            'entities':       os.path.join(d, 'entities.json'),
            'relationships':  os.path.join(d, 'relationships.json'),
            'factions':       os.path.join(d, 'factions.json'),
            'workspace':      os.path.join(d, 'workspace.json'),
        }

    @staticmethod
    def _has_split_files():
        paths = KeywordManager._get_split_paths()
        return os.path.exists(paths['entities'])

    @staticmethod
    def _load_from_split():
        paths = KeywordManager._get_split_paths()
        entities = []
        relationships = []
        import json
        try:
            if os.path.exists(paths['entities']):
                with open(paths['entities'], 'r', encoding='utf-8') as f:
                    entities = json.load(f)
            if os.path.exists(paths['relationships']):
                with open(paths['relationships'], 'r', encoding='utf-8') as f:
                    relationships = json.load(f)
            if os.path.exists(paths['factions']):
                with open(paths['factions'], 'r', encoding='utf-8') as f:
                    factions = json.load(f)
                    entities.extend(factions)
            if os.path.exists(paths['workspace']):
                with open(paths['workspace'], 'r', encoding='utf-8') as f:
                    workspace = json.load(f)
                    if isinstance(workspace, list):
                        entities.extend(workspace)
                    elif isinstance(workspace, dict) and 'keywords' in workspace:
                        entities.extend(workspace['keywords'])
            for kw in entities:
                if 'related' in kw and 'relationships' not in kw:
                    kw['relationships'] = [
                        {'target': t, 'type': 'related_to', 'description': ''}
                        for t in kw.pop('related')
                    ]
            return entities
        except Exception as e:
            logger.error(f"从拆分文件加载失败: {e}")
            return []

    @staticmethod
    def _save_split(keywords):
        paths = KeywordManager._get_split_paths()
        entities = []
        relationships = []
        factions = []
        workspace = []
        import json

        for kw in keywords:
            kw_type = kw.get('type', 'custom')
            if kw_type in KeywordManager.ENTITY_TYPES:
                entities.append(kw)
            elif kw_type == 'faction':
                factions.append(kw)
            else:
                workspace.append(kw)

        for kw in keywords:
            for rel in kw.get('relationships', []):
                if isinstance(rel, dict):
                    relationships.append({
                        'source': kw.get('name', ''),
                        'source_type': kw.get('type', ''),
                        'target': rel.get('target', ''),
                        'type': rel.get('type', ''),
                        'description': rel.get('description', '')
                    })

        ok = True
        try:
            with open(paths['entities'], 'w', encoding='utf-8') as f:
                json.dump(entities, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存 entities.json 失败: {e}")
            ok = False
        try:
            with open(paths['relationships'], 'w', encoding='utf-8') as f:
                json.dump(relationships, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存 relationships.json 失败: {e}")
            ok = False
        try:
            with open(paths['factions'], 'w', encoding='utf-8') as f:
                json.dump(factions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存 factions.json 失败: {e}")
            ok = False
        try:
            with open(paths['workspace'], 'w', encoding='utf-8') as f:
                json.dump(workspace, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存 workspace.json 失败: {e}")
            ok = False
        return ok

    @staticmethod
    def migrate_to_split():
        """一次性迁移：将旧 .novel-enhancer.json 写入拆分文件"""
        import json
        config_path = KeywordManager.get_config_path()
        if not os.path.exists(config_path):
            return False
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            keywords = data.get('keywords', [])
            if keywords:
                KeywordManager._save_split(keywords)
                logger.info(f"迁移完成: {len(keywords)} 条关键词写入拆分文件")
                return True
            return False
        except Exception as e:
            logger.error(f"迁移失败: {e}")
            return False

    @staticmethod
    def load_keywords():
        """加载关键词配置（优先从拆分文件加载，回退到旧文件）"""
        if KeywordManager._has_split_files():
            return KeywordManager._load_from_split()

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
        """保存关键词配置（同时写入旧文件和拆分文件）"""
        config_path = KeywordManager.get_config_path()
        ok_old = True
        try:
            import json
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({'keywords': keywords}, f, ensure_ascii=False, indent=2)
            logger.info(f"关键词已保存到 {config_path}")
        except Exception as e:
            logger.error(f"保存关键词(旧格式)失败: {e}")
            ok_old = False

        ok_split = KeywordManager._save_split(keywords)
        return ok_old and ok_split

    @staticmethod
    def load_faction_structure(faction_name):
        """
        从keywords.json的faction条目提取structure字段

        Args:
            faction_name: 组织名称（如"天府联盟"）

        Returns:
            dict: structure对象，包含template, roles, metadata等
                  若无structure字段则返回空字典 {}
                  若找不到该组织则返回 None

        注意：此方法具有完全的向后兼容性，
        即使旧的keywords.json中faction条目没有structure字段也不会报错，
        而是返回空字典{}供调用者判断。
        """
        try:
            keywords = KeywordManager.load_keywords()
            faction_kw = next(
                (kw for kw in keywords if kw.get('type') == 'faction' and kw.get('name') == faction_name),
                None
            )
            if faction_kw is None:
                logger.warning(f"未找到组织: {faction_name}")
                return None
            return faction_kw.get('structure', {})
        except Exception as e:
            logger.error(f"加载组织结构失败 [{faction_name}]: {e}")
            return {}

    @staticmethod
    def save_faction_structure(faction_name, structure):
        """
        写回structure字段到对应词条
        
        Args:
            faction_name: 组织名称
            structure: 完整的structure字典
        
        Returns:
            bool: 是否成功保存
        """
        try:
            keywords = KeywordManager.load_keywords()
            faction_kw = next(
                (kw for kw in keywords if kw.get('type') == 'faction' and kw.get('name') == faction_name),
                None
            )
            if faction_kw is None:
                logger.error(f"未找到组织，无法保存结构: {faction_name}")
                return False
            from datetime import datetime
            structure['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            faction_kw['structure'] = structure
            return KeywordManager.save_keywords(keywords)
        except Exception as e:
            logger.error(f"保存组织结构失败 [{faction_name}]: {e}")
            return False

    @staticmethod
    def get_faction_members(faction_name):
        """
        解析structure.roles + relationships，返回成员列表及职位信息
        
        Returns:
            list: [
                {
                    'name': '萧炎',
                    'role_id': 'leader_1',
                    'title': '盟主',
                    'parent_role': None,
                    'level': 0,
                    'type': 'character'  # 从keywords中获取
                },
                ...
            ]
            仅包含已分配成员的职位（member字段非空）
        """
        try:
            structure = KeywordManager.load_faction_structure(faction_name)
            if not structure:
                logger.warning(f"组织无结构数据或不存在: {faction_name}")
                return []
            keywords = KeywordManager.load_keywords()
            kw_map = {kw.get('name'): kw.get('type', 'unknown') for kw in keywords}
            roles = structure.get('roles', {})
            members = []
            for role_id, role_info in roles.items():
                member_name = role_info.get('member')
                if not member_name:
                    continue
                member_entry = {
                    'name': member_name,
                    'role_id': role_id,
                    'title': role_info.get('title', ''),
                    'parent_role': role_info.get('parent_role'),
                    'level': role_info.get('level', 0),
                    'type': kw_map.get(member_name, 'unknown')
                }
                members.append(member_entry)
            members.sort(key=lambda x: x.get('level', 0))
            return members
        except Exception as e:
            logger.error(f"获取组织成员失败 [{faction_name}]: {e}")
            return []

    @staticmethod
    def build_family_tree(root_name, faction_name=None, depth_limit=5, visited=None):
        """
        基于family关系构建多叉树字典
        
        Args:
            root_name: 根节点人物名称
            faction_name: 可选，限定特定组织内的成员
            depth_limit: 最大递归深度，防止无限循环
        
        Returns:
            dict: {
                'name': str,
                'gender': 'male'|'female'|'unknown',  # 从keywords获取或默认unknown
                'spouse': None|dict,  # 配偶节点（递归调用）
                'children': [dict],   # 子女列表（递归调用）
                'parents': [dict],     # 父母列表
                'generation': int,     # 代际（根=0）
                'metadata': {...}      # 其他信息
            }
            或 None（如果root_name不存在）
        """
        if visited is None:
            visited = set()
        if root_name in visited or depth_limit <= 0:
            return None
        visited.add(root_name)
        try:
            keywords = KeywordManager.load_keywords()
            root_kw = next((kw for kw in keywords if kw.get('name') == root_name), None)
            if root_kw is None:
                logger.warning(f"构建族谱树时未找到人物: {root_name}")
                return None
            gender = root_kw.get('gender', 'unknown')
            relationships = root_kw.get('relationships', [])
            spouse_node = None
            children_nodes = []
            parents_nodes = []
            faction_members = set()
            if faction_name:
                faction_structure = KeywordManager.load_faction_structure(faction_name)
                if faction_structure:
                    roles = faction_structure.get('roles', {})
                    for role_info in roles.values():
                        member = role_info.get('member')
                        if member:
                            faction_members.add(member)
            for rel in relationships:
                target_name = rel.get('target')
                rel_type = rel.get('type', '')
                if not target_name:
                    continue
                if faction_name and target_name not in faction_members:
                    continue
                # 接受更多家庭关系类型
                if rel_type == 'spouse' or rel_type == 'romance':
                    spouse_node = KeywordManager.build_family_tree(
                        target_name, faction_name, depth_limit - 1, visited.copy()
                    )
                elif rel_type in ('parent', 'father', 'mother', 'family'):
                    parent_node = KeywordManager.build_family_tree(
                        target_name, faction_name, depth_limit - 1, visited.copy()
                    )
                    if parent_node:
                        parents_nodes.append(parent_node)
                elif rel_type in ('child', 'son', 'daughter', 'family'):
                    child_node = KeywordManager.build_family_tree(
                        target_name, faction_name, depth_limit - 1, visited.copy()
                    )
                    if child_node:
                        children_nodes.append(child_node)
            tree_node = {
                'name': root_name,
                'gender': gender,
                'spouse': spouse_node,
                'children': children_nodes,
                'parents': parents_nodes,
                'generation': 0,
                'metadata': {
                    'description': root_kw.get('description', ''),
                    'personality': root_kw.get('personality', '')
                }
            }
            return tree_node
        except Exception as e:
            logger.error(f"构建族谱树失败 [{root_name}]: {e}")
            return None

    @staticmethod
    def _validate_faction_structure(structure):
        """
        数据验证逻辑
        
        Returns:
            tuple: (is_valid: bool, errors: list[str])
        
        检测规则：
        1. 循环引用检测（A→B→A）
           - DFS遍历parent_role链
           - 检测到重复访问则报错并指出环路
        2. 成员唯一性检查
           - 同一member不能出现在两个不同role_id中
           - 收集所有member值，检查重复
        3. max限制检查
           - 对每个role统计实际分配数 vs max
           - max不为空且实际>max则警告（不阻止）
        """
        errors = []
        if not isinstance(structure, dict):
            return False, ['structure必须为字典类型']
        roles = structure.get('roles', {})
        if not roles:
            return True, []
        
        visited_for_cycle = set()
        cycle_path = []

        def dfs_detect_cycle(role_id):
            if role_id in visited_for_cycle:
                cycle_start_idx = cycle_path.index(role_id) if role_id in cycle_path else -1
                if cycle_start_idx >= 0:
                    cycle_str = ' → '.join(cycle_path[cycle_start_idx:] + [role_id])
                    errors.append(f"检测到循环引用: {cycle_str}")
                return True
            visited_for_cycle.add(role_id)
            cycle_path.append(role_id)
            role_info = roles.get(role_id, {})
            parent_role = role_info.get('parent_role')
            if parent_role and parent_role in roles:
                dfs_detect_cycle(parent_role)
            cycle_path.pop()
            return False

        for role_id in roles:
            visited_for_cycle.clear()
            cycle_path.clear()
            dfs_detect_cycle(role_id)
        
        for role_id, role_info in roles.items():
            max_limit = role_info.get('max')
            if max_limit is not None:
                member_count = 1 if role_info.get('member') else 0
                if member_count > max_limit:
                    errors.append(f"职位超员警告: '{role_id}'最大允许{max_limit}人，当前{member_count}人")
        is_valid = len([e for e in errors if '警告' not in e]) == 0
        return is_valid, errors

    @staticmethod
    def get_templates_file_path():
        """
        获取架构模板文件的路径
        
        Returns:
            str: faction_templates.json的完整路径
        """
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, 'data', 'faction_templates.json')

    @staticmethod
    def load_faction_templates():
        """
        加载所有架构模板（预设 + 用户自定义）
        
        Returns:
            dict: 模板字典 {template_id: template_data}
                  若文件不存在则返回仅包含预设模板的默认字典
        """
        templates_path = KeywordManager.get_templates_file_path()
        default_templates = {
            "sect": {
                "id": "sect",
                "name": "宗门架构",
                "name_en": "Sect Structure",
                "supports_genealogy": False,
                "levels": [
                    {"id": "leader", "label": "宗主/掌门", "max": 1, "required": True},
                    {"id": "elder", "label": "长老", "max": None, "required": False},
                    {"id": "core_disciple", "label": "核心弟子", "max": 10, "required": False},
                    {"id": "disciple", "label": "弟子", "max": None, "required": False},
                    {"id": "outer_disciple", "label": "外门弟子", "max": None, "required": False}
                ]
            },
            "family": {
                "id": "family",
                "name": "家族架构",
                "name_en": "Family Structure",
                "supports_genealogy": True,
                "levels": [
                    {"id": "patriarch", "label": "族长", "max": 1, "required": True},
                    {"id": "matriarch", "label": "主母/族母", "max": 1, "required": False},
                    {"id": "elder", "label": "宗老", "max": None, "required": False},
                    {"id": "core_member", "label": "核心成员", "max": 20, "required": False},
                    {"id": "member", "label": "族人", "max": None, "required": False}
                ]
            },
            "western_council": {
                "id": "western_council",
                "name": "西方宪议",
                "name_en": "Western Council",
                "supports_genealogy": False,
                "levels": [
                    {"id": "chairman", "label": "议长/首长", "max": 1, "required": True},
                    {"id": "senator", "label": "议员", "max": None, "required": False},
                    {"id": "advisor", "label": "顾问", "max": 20, "required": False},
                    {"id": "staff", "label": "职员", "max": None, "required": False}
                ]
            },
            "campus": {
                "id": "campus",
                "name": "校园架构",
                "name_en": "Campus Structure",
                "supports_genealogy": False,
                "levels": [
                    {"id": "principal", "label": "院长/校长", "max": 1, "required": True},
                    {"id": "vice_principal", "label": "副院长/副校长", "max": 3, "required": False},
                    {"id": "dean", "label": "主任/系主任", "max": 10, "required": False},
                    {"id": "teacher", "label": "教师", "max": None, "required": False},
                    {"id": "student", "label": "学生", "max": None, "required": False}
                ]
            },
            "bandit": {
                "id": "bandit",
                "name": "山寨架构",
                "name_en": "Bandit Gang",
                "supports_genealogy": False,
                "levels": [
                    {"id": "chief", "label": "大当家", "max": 1, "required": True},
                    {"id": "second_chief", "label": "二当家", "max": 2, "required": False},
                    {"id": "elite", "label": "精英", "max": 20, "required": False},
                    {"id": "follower", "label": "喽啰", "max": None, "required": False}
                ]
            }
        }
        
        if not os.path.exists(templates_path):
            logger.warning(f"模板文件不存在，使用内置默认模板: {templates_path}")
            return default_templates
        
        try:
            with open(templates_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            templates = data.get('templates', {})
            if not templates:
                logger.warning(f"模板文件为空，使用内置默认模板")
                return default_templates
            logger.info(f"成功加载 {len(templates)} 个架构模板")
            return templates
        except Exception as e:
            logger.error(f"加载架构模板失败: {e}，使用内置默认模板")
            return default_templates

    @staticmethod
    def save_faction_templates(templates):
        """
        保存架构模板（包含用户新增的自定义模板）
        
        Args:
            templates: 完整的模板字典 {template_id: template_data}
    
        Returns:
            bool: 是否成功保存
        """
        try:
            templates_path = KeywordManager.get_templates_file_path()
            data = {
                "_meta": {
                    "version": "1.0",
                    "description": "组织职能架构模板定义",
                    "created_at": "2026-01-15"
                },
                "templates": templates
            }
            
            import os
            dir_path = os.path.dirname(templates_path)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            with open(templates_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"架构模板已保存到 {templates_path}，共 {len(templates)} 个模板")
            return True
        except Exception as e:
            logger.error(f"保存架构模板失败: {e}")
            return False

    @staticmethod
    def get_template_by_id(template_id):
        """
        获取单个模板定义

        Args:
            template_id: 模板ID（如'sect', 'family'等）

        Returns:
            dict: 模板数据，若不存在返回None
        """
        try:
            templates = KeywordManager.load_faction_templates()
            return templates.get(template_id)
        except Exception as e:
            logger.error(f"获取模板失败 [{template_id}]: {e}")
            return None

    @staticmethod
    def migrate_faction_structures():
        """
        一键迁移工具：扫描所有faction词条，为无structure的条目初始化默认架构

        功能：
        - 加载所有keywords
        - 筛选type=='faction'的词条
        - 检查每个词条是否有structure字段
        - 对无structure的词条，使用默认模板（western_council）初始化空结构
        - 保存更新后的keywords

        Returns:
            dict: {
                'total_factions': int,      # 总共多少个组织
                'migrated': int,            # 成功迁移的数量
                'skipped': int,             # 已有结构跳过的数量
                'details': [                # 详细信息列表
                    {
                        'name': str,       # 组织名称
                        'status': str,     # 'migrated' | 'skipped' | 'error'
                        'message': str     # 说明信息
                    }
                ]
            }

        注意：
        - 此方法会修改keywords.json文件！调用前应提示用户确认
        - 默认使用western_council模板作为初始结构（用户可后续修改）
        - 初始化的structure中roles为空字典{}，template设为'custom'
        """
        try:
            keywords = KeywordManager.load_keywords()
            factions = [kw for kw in keywords if kw.get('type') == 'faction']
            
            total_factions = len(factions)
            migrated = 0
            skipped = 0
            details = []
            
            from datetime import datetime
            
            for faction in factions:
                faction_name = faction.get('name', '未知组织')
                try:
                    if not faction.get('structure'):
                        default_structure = {
                            'template': 'custom',
                            'roles': {},
                            'metadata': {
                                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'source': 'migration_tool',
                                'note': '由迁移工具自动初始化'
                            }
                        }
                        faction['structure'] = default_structure
                        migrated += 1
                        details.append({
                            'name': faction_name,
                            'status': 'migrated',
                            'message': f'已初始化默认结构（custom模板）'
                        })
                        logger.info(f"迁移工具: 为组织 '{faction_name}' 初始化了默认structure")
                    else:
                        skipped += 1
                        details.append({
                            'name': faction_name,
                            'status': 'skipped',
                            'message': '已存在structure字段，跳过'
                        })
                except Exception as e:
                    details.append({
                        'name': faction_name,
                        'status': 'error',
                        'message': f'处理失败: {str(e)}'
                    })
                    logger.error(f"迁移工具: 处理组织 '{faction_name}' 时出错: {e}")
            
            if migrated > 0:
                save_success = KeywordManager.save_keywords(keywords)
                if not save_success:
                    logger.error("迁移工具: 保存更新后的keywords失败")
                    return {
                        'total_factions': total_factions,
                        'migrated': 0,
                        'skipped': skipped,
                        'details': [{'name': '系统', 'status': 'error', 'message': '保存文件失败'}]
                    }
            
            logger.info(f"迁移工具完成: 总共{total_factions}个组织，迁移{migrated}个，跳过{skipped}个")
            
            return {
                'total_factions': total_factions,
                'migrated': migrated,
                'skipped': skipped,
                'details': details
            }
            
        except Exception as e:
            logger.error(f"迁移工具执行失败: {e}")
            return {
                'total_factions': 0,
                'migrated': 0,
                'skipped': 0,
                'details': [{'name': '系统', 'status': 'error', 'message': f'执行异常: {str(e)}'}]
            }

    @staticmethod
    def get_factions_without_structure():
        """
        获取所有缺少structure字段的faction词条列表（只读，不修改数据）

        用于：
        - UI上显示"有X个组织需要初始化架构"的提示
        - 让用户决定是否执行迁移

        Returns:
            list: [
                {
                    'name': str,       # 组织名称
                    'description': str # 组织描述（如果有）
                },
                ...
            ]
            若所有组织都有structure则返回空列表[]
        """
        try:
            keywords = KeywordManager.load_keywords()
            factions_without_structure = []
            
            for kw in keywords:
                if kw.get('type') == 'faction':
                    if not kw.get('structure'):
                        factions_without_structure.append({
                            'name': kw.get('name', '未知组织'),
                            'description': kw.get('description', '')
                        })
            
            logger.info(f"查询到 {len(factions_without_structure)} 个组织缺少structure字段")
            return factions_without_structure
            
        except Exception as e:
            logger.error(f"查询缺少structure的组织失败: {e}")
            return []

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
    def remove_relationship(from_name, to_name, rel_type):
        keywords = KeywordManager.load_keywords()
        from_kw = next((kw for kw in keywords if kw.get('name') == from_name), None)
        if not from_kw or 'relationships' not in from_kw:
            return False
        from_kw['relationships'] = [r for r in from_kw['relationships'] if not (r.get('target') == to_name and r.get('type') == rel_type)]
        return KeywordManager.save_keywords(keywords)
    
    @staticmethod
    def delete_keyword(name):
        keywords = KeywordManager.load_keywords()
        keywords = [kw for kw in keywords if kw.get('name') != name]
        for kw in keywords:
            if 'relationships' in kw:
                kw['relationships'] = [r for r in kw['relationships'] if r.get('target') != name]
        return KeywordManager.save_keywords(keywords)
    
    @staticmethod
    def rename_keyword(old_name, new_name):
        keywords = KeywordManager.load_keywords()
        for kw in keywords:
            if kw.get('name') == old_name:
                kw['name'] = new_name
            if 'relationships' in kw:
                for rel in kw['relationships']:
                    if rel.get('target') == old_name:
                        rel['target'] = new_name
        return KeywordManager.save_keywords(keywords)
    
    @staticmethod
    def update_keyword(name, kw_type, description, color):
        keywords = KeywordManager.load_keywords()
        for kw in keywords:
            if kw.get('name') == name:
                if kw_type is not None:
                    kw['type'] = kw_type
                if description is not None:
                    kw['description'] = description
                if color is not None:
                    kw['color'] = color
                break
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
    def _load_stopwords():
        stopwords_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'res', 'stopwords.json')
        try:
            with open(stopwords_path, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception:
            logger.warning(f"停用词文件加载失败: {stopwords_path}")
            return set()
    
    @staticmethod
    def _detect_stale_words(freq, stale_ratio=3.0, stale_gap=3):
        total_ch = freq.get("total_chapters", 0)
        if total_ch < 5:
            return
        words = freq.get("words", {})
        split_idx = max(1, total_ch // 3)
        min_occ = ConfigManager.get_int('Frequency', 'min_occurrences', fallback=3)
        for w, info in words.items():
            dist = info.get("chapter_distribution", [])
            if not dist or len(dist) < 3:
                continue
            front_count = sum(dist[:split_idx])
            back_count = sum(dist[split_idx:])
            is_stale = False
            if front_count >= min_occ and back_count <= 1 and front_count / max(1, back_count) >= stale_ratio:
                is_stale = True
            if len(dist) >= stale_gap and all(v == 0 for v in dist[-stale_gap:]) and info.get("total_occurrences", 0) >= min_occ:
                is_stale = True
            info["is_stale"] = is_stale
    
    @staticmethod
    def scan_frequency(novel_dir, min_len=2, min_occ=3):
        from datetime import datetime
        ensure_novel_config_dir()
        freq_file_path = os.path.join(get_novel_config_dir(), ".frequency.json")
        existing = {}
        if os.path.exists(freq_file_path):
            try:
                with open(freq_file_path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except Exception:
                pass
        
        freq = {"scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "total_chapters": 0, "words": {}}
        
        use_stopwords = ConfigManager.get_int('Frequency', 'filter_stopwords', fallback=1) == 1
        use_keywords_only = ConfigManager.get_int('Frequency', 'keywords_only', fallback=0) == 1
        stopwords = set()
        if use_stopwords:
            stopwords = KeywordManager._load_stopwords()
            user_sw_path = os.path.join(get_novel_config_dir(), "user_stopwords.json")
            if os.path.exists(user_sw_path):
                try:
                    with open(user_sw_path, 'r', encoding='utf-8') as f:
                        user_words = json.load(f)
                    if isinstance(user_words, list):
                        stopwords.update(user_words)
                except Exception:
                    pass
        
        keywords_list = KeywordManager.load_keywords() if not use_keywords_only else None
        kw_name_set = None
        if use_keywords_only and keywords_list:
            kw_name_set = set(kw.get('name', '') for kw in keywords_list)
        
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
                        words = [w.strip() for w in jieba.cut(content) if len(w.strip()) >= min_len]
                    else:
                        words = re.findall(r'[\u4e00-\u9fff\w]{%d,}' % min_len, content)
                    
                    filtered = []
                    for w in words:
                        w = w.strip()
                        if not w or w.isdigit() or re.match(r'^[\W_]+$', w):
                            continue
                        if use_stopwords and w in stopwords:
                            continue
                        if use_keywords_only and kw_name_set and w not in kw_name_set:
                            continue
                        filtered.append(w)
                    
                    wc = {}
                    for w in filtered:
                        wc[w] = wc.get(w, 0) + 1
                    for w, c in wc.items():
                        if c >= min_occ:
                            if w not in freq["words"]:
                                freq["words"][w] = {"chapters": {}, "total_occurrences": 0, "type": "?", "status": "active", "chapter_distribution": [], "is_stale": False}
                            if "chapter_distribution" not in freq["words"][w]:
                                freq["words"][w]["chapter_distribution"] = []
                            freq["words"][w]["chapters"][str(ch_idx)] = c
                            freq["words"][w]["total_occurrences"] += c
                except Exception:
                    pass
        
        freq["total_chapters"] = ch_idx
        
        for w in freq["words"]:
            dist = freq["words"][w].get("chapter_distribution", [])
            if not dist:
                total_chapters = freq["total_chapters"]
                dist = [0] * total_chapters
                chapters_dict = freq["words"][w].get("chapters", {})
                for ch_str, count in chapters_dict.items():
                    try:
                        ci = int(ch_str)
                        if 0 <= ci - 1 < total_chapters:
                            dist[ci - 1] = count
                    except ValueError:
                        pass
                freq["words"][w]["chapter_distribution"] = dist
        
        if keywords_list:
            kw_name_map = {kw.get('name', ''): kw.get('type', '?') for kw in keywords_list}
            for w, info in freq["words"].items():
                if w in kw_name_map:
                    info["type"] = kw_name_map[w]
        
        stale_ratio = ConfigManager.get_float('Frequency', 'stale_ratio', fallback=3.0)
        stale_gap = ConfigManager.get_int('Frequency', 'stale_gap', fallback=3)
        KeywordManager._detect_stale_words(freq, stale_ratio, stale_gap)
        
        freq["is_replace"] = existing.get("is_replace", {})
        
        logger.info(f"频度扫描完成: {ch_idx}章, {len(freq['words'])}词条")
        return freq

keyword_manager = KeywordManager()
