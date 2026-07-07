from models import GameEntity

def _parse_percent(val: str) -> str:
    val = val.strip()
    if val.endswith('%'):
        return str(float(val[:-1]))
    return val

def import_skill(line: str) -> GameEntity:
    line = line.replace('，', ',').replace(' ', '')
    parts = [p for p in line.split(',') if p.strip() != '']
    if len(parts) < 2:
        raise ValueError(f"技能导入数据至少需要编号和名称，当前: {line}")
    # 技能有效字段（GameEntity 包含的字段）
    # 编号, 名称, 类别, 伤害类型, 技能倍率, 技能固定值, hit数,
    # 百分比穿防, 固定穿防, 暴击, 幸运, 爆伤,
    # 一般增伤, 本元素增伤, 全元素增伤, 元素增伤, 赛季增伤, 最终增伤,
    # 是否幸运, 是否是幸运一击, 输入参数, 输出参数 ... 等等，我们只解析常用字段，其余保持默认0
    # 为简化，我们只解析旧格式中可能出现的字段，并按顺序映射
    # 顺序参考用户提供的原 daoru.py 格式：编号,名称,类别,伤害类型,技能倍率,技能固定值,hit数,百分比穿防,固定穿防,暴击,幸运,爆伤,一般增伤,元素增伤,全能增伤,赛季增伤,最终增伤,是否幸运,是否是幸运一击
    # 现在模型没有元素增伤和全能增伤的直接字段（元素增伤由本元素+全元素计算，全能增伤由0.35*全能计算），所以导入时忽略这两项，或者映射到本元素/全元素？但旧数据可能有这些字段，为兼容，我们丢弃不存在的字段。
    # 我们构建一个字典，只填充 GameEntity 存在的字段
    entity = GameEntity()
    # 编号
    try:
        entity.编号 = int(parts[0])
    except:
        entity.编号 = 0
    entity.名称 = parts[1] if len(parts) > 1 else ""
    entity.类别 = parts[2] if len(parts) > 2 and parts[2] else "其他"
    # 伤害类型
    if len(parts) > 3:
        dt = parts[3].strip()
        entity.伤害类型 = "1" if dt == "法术" else "0"
    # 技能倍率（兼容百分数或已处理格式）
    if len(parts) > 4:
        bl_str = parts[4].strip()
        if bl_str.endswith('%'):
            bl_val = float(bl_str[:-1]) / 100.0
            entity.技能倍率 = f"({bl_val})/100"
        else:
            # 可能是数字或已处理公式，直接存储？但为统一格式，包装一下
            if bl_str:
                entity.技能倍率 = f"({bl_str})/100"
    # 技能固定值
    if len(parts) > 5: entity.技能固定值 = parts[5]
    # hit数
    if len(parts) > 6: entity.hit数 = parts[6] if parts[6] else "1"
    # 百分比穿防
    if len(parts) > 7: entity.百分比穿防 = _parse_percent(parts[7]) if parts[7] else "0"
    # 固定穿防
    if len(parts) > 8: entity.固定穿防 = parts[8] if parts[8] else "0"
    # 暴击
    if len(parts) > 9: entity.暴击 = _parse_percent(parts[9]) if parts[9] else "0"
    # 幸运
    if len(parts) > 10: entity.幸运 = _parse_percent(parts[10]) if parts[10] else "0"
    # 爆伤
    if len(parts) > 11: entity.爆伤 = _parse_percent(parts[11]) if parts[11] else "0"
    # 一般增伤
    if len(parts) > 12: entity.一般增伤 = _parse_percent(parts[12]) if parts[12] else "0"
    # 旧元素增伤（忽略）
    # 旧全能增伤（忽略）
    # 赛季增伤
    if len(parts) > 15: entity.赛季增伤 = _parse_percent(parts[15]) if parts[15] else "0"
    # 最终增伤
    if len(parts) > 16: entity.最终增伤 = _parse_percent(parts[16]) if parts[16] else "0"
    # 是否幸运
    if len(parts) > 17: entity.是否幸运 = parts[17] if parts[17] else "1"
    # 是否是幸运一击
    if len(parts) > 18: entity.是否是幸运一击 = parts[18] if parts[18] else "0"
    return entity

def import_buff(line: str) -> GameEntity:
    line = line.replace('，', ',').replace(' ', '')
    parts = [p for p in line.split(',') if p.strip() != '']
    if len(parts) < 2:
        raise ValueError(f"Buff导入数据至少需要编号和名称，当前: {line}")
    entity = GameEntity()
    try:
        entity.编号 = int(parts[0])
    except:
        entity.编号 = 0
    entity.名称 = parts[1] if len(parts) > 1 else ""
    entity.类别 = parts[2] if len(parts) > 2 and parts[2] else "其他"
    # Buff 字段映射（兼容旧版，有些字段已改名）
    # 主属性固定值 -> 固定主属性（通过 buffed 映射，但导入时直接设置对应字段）
    idx = 3
    if len(parts) > idx: entity.主属性固定值 = parts[idx]; idx+=1
    if len(parts) > idx: entity.主属性百分比 = _parse_percent(parts[idx]) if parts[idx] else "0"; idx+=1
    if len(parts) > idx: entity.攻击力固定值 = parts[idx]; idx+=1
    if len(parts) > idx: entity.额外百分比攻击力 = _parse_percent(parts[idx]) if parts[idx] else "0"; idx+=1
    if len(parts) > idx: entity.精炼攻击力 = parts[idx]; idx+=1
    if len(parts) > idx: entity.元素攻击力固定值 = parts[idx]; idx+=1
    if len(parts) > idx: entity.元素攻击力百分比 = _parse_percent(parts[idx]) if parts[idx] else "0"; idx+=1
    if len(parts) > idx: entity.技能倍率 = _parse_percent(parts[idx]) if parts[idx] else "0"; idx+=1   # 倍率增加改为技能倍率
    if len(parts) > idx: entity.暴击固定值 = parts[idx]; idx+=1
    if len(parts) > idx: entity.急速固定值 = parts[idx]; idx+=1
    if len(parts) > idx: entity.幸运固定值 = parts[idx]; idx+=1
    if len(parts) > idx: entity.精通固定值 = parts[idx]; idx+=1
    if len(parts) > idx: entity.暴击 = _parse_percent(parts[idx]) if parts[idx] else "0"; idx+=1
    if len(parts) > idx: entity.急速 = _parse_percent(parts[idx]) if parts[idx] else "0"; idx+=1
    if len(parts) > idx: entity.幸运 = _parse_percent(parts[idx]) if parts[idx] else "0"; idx+=1
    if len(parts) > idx: entity.精通 = _parse_percent(parts[idx]) if parts[idx] else "0"; idx+=1
    if len(parts) > idx: entity.爆伤 = _parse_percent(parts[idx]) if parts[idx] else "0"; idx+=1
    if len(parts) > idx: entity.百分比穿防 = _parse_percent(parts[idx]) if parts[idx] else "0"; idx+=1
    if len(parts) > idx: entity.固定穿防 = parts[idx]; idx+=1
    if len(parts) > idx: entity.一般增伤 = _parse_percent(parts[idx]) if parts[idx] else "0"; idx+=1
    if len(parts) > idx: entity.元素增伤 = _parse_percent(parts[idx]) if parts[idx] else "0"; idx+=1   # 旧版元素增伤
    if len(parts) > idx: entity.全能增伤 = _parse_percent(parts[idx]) if parts[idx] else "0"; idx+=1   # 忽略
    if len(parts) > idx: entity.赛季增伤 = _parse_percent(parts[idx]) if parts[idx] else "0"; idx+=1
    if len(parts) > idx: entity.最终增伤 = _parse_percent(parts[idx]) if parts[idx] else "0"; idx+=1
    # 其他新增字段保持默认
    return entity