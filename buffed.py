from models import GameEntity

def _add_str_formula(target_str: str, add_str: str) -> str:
    if add_str == "0":
        return target_str
    if target_str == "0":
        return add_str
    return f"({target_str}) + ({add_str})"

# 字段映射：将 Buff 的某些字段重定向到攻击力公式实际使用的字段
FIELD_MAPPING = {
    "主属性固定值": "固定主属性",
    "主属性百分比": "百分比主属性",
    "攻击力固定值": "额外固定攻击力",
}

# 排除字段：这些字段不参与拼接，因为它们是由其他字段动态计算的
EXCLUDED_FIELDS = {'元素增伤', '全能增伤', '输入参数', '输出参数'}

def buffed(buff: GameEntity, target: GameEntity):
    """将 buff 的所有字段以字符串形式拼接到 target 上（原地修改），并自动映射关键字段"""
    for field in GameEntity.__dataclass_fields__:
        if field in ('编号', '名称', '类别', '伤害类型', 'buffci', '输入参数', '输出参数'):
            continue
        if field in EXCLUDED_FIELDS:
            continue
        b_val = getattr(buff, field)
        if isinstance(b_val, str) and b_val != "0":
            target_field = FIELD_MAPPING.get(field, field)
            original = getattr(target, target_field)
            setattr(target, target_field, _add_str_formula(original, b_val))
    target.buffci.append(buff.编号)