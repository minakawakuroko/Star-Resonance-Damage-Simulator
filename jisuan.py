"""
伤害计算模块（新模型）
输入为最终技能面板（GameEntity），已包含面板+技能+所有Buff的合并结果。
支持外部参数上下文。
"""
from models import GameEntity
from evaluator import resolve_target

def calc_damage_from_entity(entity: GameEntity, extra_context: dict = None, 防御系数=1.0):
    ctx = {}
    if extra_context:
        ctx.update(extra_context)
    resolved = resolve_target(entity, ctx)

    固定主属性 = resolved.固定主属性
    百分比主属性 = resolved.百分比主属性
    转化系数 = resolved.转化系数
    额外固定攻击力 = resolved.额外固定攻击力
    额外百分比攻击力 = resolved.额外百分比攻击力
    精炼攻击力 = resolved.精炼攻击力
    本元素攻击力 = resolved.本元素攻击力
    全元素攻击力 = resolved.全元素攻击力
    元素攻击力总和 = 本元素攻击力 + 全元素攻击力

    百分比穿防 = resolved.百分比穿防
    固定穿防 = resolved.固定穿防
    敌人物理防御 = resolved.敌人物理防御
    敌人法术防御 = resolved.敌人法术防御
    防御系数常数 = resolved.防御系数常数

    暴击 = resolved.暴击
    爆伤 = resolved.爆伤
    一般增伤 = resolved.一般增伤
    # 元素增伤 = 本元素 + 全元素
    元素增伤 = resolved.本元素增伤 + resolved.全元素增伤
    全能 = resolved.全能
    全能增伤 = 0.35 * 全能
    赛季增伤 = resolved.赛季增伤
    最终增伤 = resolved.最终增伤

    技能倍率 = resolved.技能倍率
    技能固定值 = resolved.技能固定值
    伤害类型 = resolved.伤害类型

    绿值主属性 = resolved.绿值主属性
    绿值攻击力 = resolved.绿值攻击力
    雷印 = resolved.雷印

    # 攻击力计算（加入绿值）
    主属性基础 = 固定主属性 * (1 + 百分比主属性 / 100)
    主属性最终 = 主属性基础 + 绿值主属性
    攻击力基础 = 主属性最终 * 转化系数 + 额外固定攻击力
    攻击力终值 = 攻击力基础 * (1 + 额外百分比攻击力 / 100) + 绿值攻击力

    try:
        dmg_type = int(float(伤害类型))
    except:
        dmg_type = 0

    if dmg_type == 0:
        base_def = 敌人物理防御
    else:
        base_def = 敌人法术防御

    effective_def = max(0.0, base_def - 固定穿防) * (1 - min(百分比穿防, 100.0) / 100)
    defense_mult = 1.0 - (effective_def / (effective_def + 防御系数常数)) if (effective_def + 防御系数常数) != 0 else 1.0

    base_atk_total = 攻击力终值 * defense_mult + 精炼攻击力 + 元素攻击力总和

    # 雷印加成倍率
    雷印加成 = 1 + 雷印 / 100
    raw = base_atk_total * 技能倍率 * 雷印加成 + 技能固定值

    zone_一般 = 1 + 一般增伤 / 100
    zone_元素 = 1 + 元素增伤 / 100
    zone_全能 = 1 + 全能增伤 / 100
    zone_赛季 = 1 + 赛季增伤 / 100
    zone_最终 = 1 + 最终增伤 / 100
    base_damage = raw * zone_一般 * zone_元素 * zone_全能 * zone_赛季 * zone_最终

    crit_chance = min(暴击, 100.0) / 100
    crit_dmg = 爆伤 / 100
    expected = base_damage * (1 + crit_chance * crit_dmg)

    details = []
    details.append(f"    【伤害公式拆解】")
    details.append(f"    攻击力终值 = {攻击力终值:.2f} (绿值主属性={绿值主属性:.2f}, 绿值攻击力={绿值攻击力:.2f})")
    details.append(f"    防御后系数 = {defense_mult:.4f} (基础防{base_def}, 总穿{百分比穿防:.1f}%+{固定穿防})")
    details.append(f"    攻击区 = ({攻击力终值:.2f} * {defense_mult:.4f}) + {精炼攻击力} + {元素攻击力总和:.2f} = {base_atk_total:.2f}")
    details.append(f"    技能倍率 = {技能倍率:.4f}, 雷印加成 = {雷印加成:.4f}, 固定值 = {技能固定值}")
    details.append(f"    原始伤害 = {base_atk_total:.2f} * {技能倍率:.4f} * {雷印加成:.4f} + {技能固定值} = {raw:.2f}")
    details.append(f"    增伤系数: 一般={zone_一般:.4f} ({一般增伤}%), 元素={zone_元素:.4f} (本元素{resolved.本元素增伤}%+全元素{resolved.全元素增伤}%), 全能={zone_全能:.4f} ({全能增伤:.2f}%), 赛季={zone_赛季:.4f}, 最终={zone_最终:.4f}")
    details.append(f"    基础伤害 = {raw:.2f} * {zone_一般:.4f} * {zone_元素:.4f} * {zone_全能:.4f} * {zone_赛季:.4f} * {zone_最终:.4f} = {base_damage:.2f}")
    details.append(f"    暴击率 = {crit_chance:.2%}, 爆伤 = {crit_dmg:.2%}")
    details.append(f"    期望伤害 = {base_damage:.2f} * (1 + {crit_chance:.4f} * {crit_dmg:.4f}) = {expected:.2f}")

    return round(expected, 2), details