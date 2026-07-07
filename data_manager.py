import json, os, sys
from models import GameEntity
from dataclasses import fields

def _get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(_get_app_dir(), 'data')
ENTITIES_FILE = os.path.join(DATA_DIR, 'entities.json')

SKILL_CATEGORY_INDEX = {
    "法": 1, "枪": 2, "刀": 3, "斧": 4, "弓": 5,
    "巨刃": 6, "剑盾": 7, "手铐": 8, "吉他": 9, "其他": 10
}
BUFF_CATEGORY_INDEX = {
    "法": 1, "枪": 2, "刀": 3, "斧": 4, "弓": 5,
    "巨刃": 6, "剑盾": 7, "手铐": 8, "吉他": 9, "幻想": 10, "其他": 11
}

SKILL_CATEGORY_NAMES = list(SKILL_CATEGORY_INDEX.keys())
BUFF_CATEGORY_NAMES = list(BUFF_CATEGORY_INDEX.keys())

def _ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(ENTITIES_FILE):
        with open(ENTITIES_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

def _generate_skill_id(category: str, user_id: int) -> int:
    idx = SKILL_CATEGORY_INDEX.get(category, 10)
    return 1000 + idx * 10 + user_id

def _generate_buff_id(category: str, user_id: int) -> int:
    idx = BUFF_CATEGORY_INDEX.get(category, 11)
    return 2000 + idx * 10 + user_id

def load_all_entities() -> list[GameEntity]:
    _ensure_data_dir()
    with open(ENTITIES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    entities = []
    # 获取 GameEntity 所有合法字段
    valid_fields = set(GameEntity.__dataclass_fields__.keys())
    for item in data:
        # 过滤掉不在当前模型中的旧字段
        filtered = {k: v for k, v in item.items() if k in valid_fields}
        # 补全缺失的新字段为默认值
        for field in GameEntity.__dataclass_fields__:
            if field not in filtered:
                # 获取默认值
                default = GameEntity.__dataclass_fields__[field].default
                if default is None:
                    default = 0 if field == '编号' else ''
                filtered[field] = default
        entities.append(GameEntity(**filtered))
    return entities

def save_all_entities(entities: list[GameEntity]):
    with open(ENTITIES_FILE, 'w', encoding='utf-8') as f:
        json.dump([e.__dict__ for e in entities], f, ensure_ascii=False, indent=2)

# ---------- 面板 ----------
def load_panel() -> GameEntity | None:
    for e in load_all_entities():
        if e.编号 == 0:
            return e
    return None

def save_panel(panel: GameEntity):
    entities = load_all_entities()
    entities = [e for e in entities if e.编号 != 0]
    entities.append(panel)
    save_all_entities(entities)

# ---------- 技能 ----------
def load_skills() -> list[GameEntity]:
    return [e for e in load_all_entities() if 1000 <= e.编号 < 2000 and e.编号 != 0]

def save_skills(skills: list[GameEntity]):
    entities = [e for e in load_all_entities() if not (1000 <= e.编号 < 2000)]
    entities.extend(skills)
    save_all_entities(entities)

def add_skill(skill: GameEntity, auto_id=True):
    entities = load_all_entities()
    if auto_id:
        user_short = skill.编号 if 1 <= skill.编号 <= 9 else 1
        skill.编号 = _generate_skill_id(skill.类别, user_short)
        while any(e.编号 == skill.编号 for e in entities):
            current_short = (skill.编号 - 1000 - SKILL_CATEGORY_INDEX[skill.类别]*10) + 1
            if current_short > 9:
                raise ValueError("该类别技能序号已满")
            skill.编号 = _generate_skill_id(skill.类别, current_short)
    else:
        if any(e.编号 == skill.编号 for e in entities):
            raise ValueError(f"技能编号 {skill.编号} 已存在")
    entities.append(skill)
    save_all_entities(entities)

def update_skill(skill: GameEntity):
    entities = load_all_entities()
    for i, e in enumerate(entities):
        if e.编号 == skill.编号:
            entities[i] = skill
            save_all_entities(entities)
            return
    raise ValueError(f"技能编号 {skill.编号} 不存在")

def delete_skill(skill_id: int):
    entities = [e for e in load_all_entities() if e.编号 != skill_id]
    save_all_entities(entities)

def get_skill_by_id(skill_id: int) -> GameEntity | None:
    for e in load_skills():
        if e.编号 == skill_id:
            return e
    return None

def get_skill_by_name(name: str) -> GameEntity | None:
    for e in load_skills():
        if e.名称 == name:
            return e
    return None

# ---------- Buff ----------
def load_buffs() -> list[GameEntity]:
    return [e for e in load_all_entities() if 2000 <= e.编号 < 3000 and e.编号 != 0]

def save_buffs(buffs: list[GameEntity]):
    entities = [e for e in load_all_entities() if not (2000 <= e.编号 < 3000)]
    entities.extend(buffs)
    save_all_entities(entities)

def add_buff(buff: GameEntity, auto_id=True):
    entities = load_all_entities()
    if auto_id:
        user_short = buff.编号 if 1 <= buff.编号 <= 9 else 1
        buff.编号 = _generate_buff_id(buff.类别, user_short)
        while any(e.编号 == buff.编号 for e in entities):
            current_short = (buff.编号 - 2000 - BUFF_CATEGORY_INDEX[buff.类别]*10) + 1
            if current_short > 9:
                raise ValueError("该类别Buff序号已满")
            buff.编号 = _generate_buff_id(buff.类别, current_short)
    else:
        if any(e.编号 == buff.编号 for e in entities):
            raise ValueError(f"Buff编号 {buff.编号} 已存在")
    entities.append(buff)
    save_all_entities(entities)

def update_buff(buff: GameEntity):
    entities = load_all_entities()
    for i, e in enumerate(entities):
        if e.编号 == buff.编号:
            entities[i] = buff
            save_all_entities(entities)
            return
    raise ValueError(f"Buff编号 {buff.编号} 不存在")

def delete_buff(buff_id: int):
    entities = [e for e in load_all_entities() if e.编号 != buff_id]
    save_all_entities(entities)

def get_buff_by_id(buff_id: int) -> GameEntity | None:
    for e in load_buffs():
        if e.编号 == buff_id:
            return e
    return None

def get_buff_by_name(name: str) -> GameEntity | None:
    for e in load_buffs():
        if e.名称 == name:
            return e
    return None

# ---------- 预设导入导出（兼容旧版本）----------
def export_preset(selected_skills: list[GameEntity], selected_buffs: list[GameEntity], file_path: str):
    preset = {
        "type": "preset",
        "skills": [s.__dict__ for s in selected_skills],
        "buffs": [b.__dict__ for b in selected_buffs]
    }
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(preset, f, ensure_ascii=False, indent=2)

def import_preset(file_path: str) -> tuple[list[GameEntity], list[GameEntity]]:
    with open(file_path, 'r', encoding='utf-8') as f:
        preset = json.load(f)
    current = load_all_entities()
    # 获取有效字段名集合
    valid_fields = {f.name for f in fields(GameEntity)}

    # 分别处理技能和Buff，避免导入后重复
    skills = [e for e in current if 1000 <= e.编号 < 2000]
    buffs = [e for e in current if 2000 <= e.编号 < 3000]

    skill_dict = {s.编号: s for s in skills}
    buff_dict = {b.编号: b for b in buffs}

    for sdata in preset.get('skills', []):
        # 过滤未知字段
        filtered = {k: v for k, v in sdata.items() if k in valid_fields}
        # 补全缺失字段为0
        for f in valid_fields:
            if f not in filtered:
                filtered[f] = "0"
        sk = GameEntity(**filtered)
        # 导入的技能编号可能冲突，保留导入的
        skill_dict[sk.编号] = sk

    for bdata in preset.get('buffs', []):
        filtered = {k: v for k, v in bdata.items() if k in valid_fields}
        for f in valid_fields:
            if f not in filtered:
                filtered[f] = "0"
        bf = GameEntity(**filtered)
        buff_dict[bf.编号] = bf

    new_skills = sorted(skill_dict.values(), key=lambda x: x.编号)
    new_buffs = sorted(buff_dict.values(), key=lambda x: x.编号)
    return new_skills, new_buffs