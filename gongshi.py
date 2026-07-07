from dataclasses import fields
from models import GameEntity

def gongshi(target: GameEntity, field_name: str, formula: str):
    """将 target 的 field_name 设置为公式字符串。"""
    valid = [f.name for f in fields(target)]
    if field_name not in valid:
        raise ValueError(f"字段 '{field_name}' 不存在。可用字段：{valid}")
    setattr(target, field_name, formula)