# test.py
from panel_builder import build_panel
from gongshi import gongshi
from jisuan import _resolve_panel_in_order, calc_skill_damage, calc_single_hit
from daoru import import_skill, import_buff
from evaluator import resolve_target
from copy import deepcopy
from models import Mianban, Skill, Buff

# ========== 工具函数 ==========
def print_panel(m_def, title="面板"):
    m = _resolve_panel_in_order(m_def)
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")
    print(f"固定主属性: {m.固定主属性}")
    print(f"百分比主属性: {m.百分比主属性}%")
    print(f"转化系数: {m.转化系数}")
    print(f"额外固定攻击力: {m.额外固定攻击力}")
    print(f"额外百分比攻击力: {m.额外百分比攻击力}%")
    print(f"精炼攻击力: {m.精炼攻击力}")
    print(f"元素攻击力: {m.元素攻击力}")
    print(f"暴击固定值: {m.暴击固定值}")
    print(f"急速固定值: {m.急速固定值}")
    print(f"幸运固定值: {m.幸运固定值}")
    print(f"精通固定值: {m.精通固定值}")
    print(f"全能固定值: {m.全能固定值}")
    print(f"敌人物理防御: {m.敌人物理防御}")
    print(f"敌人法术防御: {m.敌人法术防御}")
    print(f"防御系数常数: {m.防御系数常数}")
    print(f"物理百分比穿防: {m.物理百分比穿防}%")
    print(f"物理固定穿防: {m.物理固定穿防}")
    print(f"法术百分比穿防: {m.法术百分比穿防}%")
    print(f"法术固定穿防: {m.法术固定穿防}")
    print(f"攻击力终值: {m.攻击力终值:.2f}")
    print(f"暴击: {m.暴击:.2f}%")
    print(f"急速: {m.急速:.2f}%")
    print(f"幸运: {m.幸运:.2f}%")
    print(f"精通: {m.精通:.2f}%")
    print(f"全能: {m.全能:.2f}%")
    print(f"爆伤: {m.爆伤:.2f}%")
    print(f"一般增伤: {m.一般增伤:.2f}%")
    print(f"元素增伤: {m.元素增伤:.2f}%")
    print(f"全能增伤: {m.全能增伤:.2f}%")
    print(f"赛季增伤: {m.赛季增伤:.2f}%")
    print(f"最终增伤: {m.最终增伤:.2f}%")

# ==================== 第一步：构建初始面板 ====================
print(">>> 第一步：构建初始面板")
m_def = build_panel(
    固定主属性=5000,
    百分比主属性=100,            # 100%
    转化系数=0.5,
    额外固定攻击力=1000,
    额外百分比攻击力=50,         # 50%
    精炼攻击力=1000,
    元素攻击力=500,
    暴击固定值=50000,
    急速固定值=50000,
    幸运固定值=50000,
    精通固定值=50000,
    全能固定值=28000,
    爆伤="60",                   # 60%
    一般增伤="10",               # 10%
    元素增伤="10",               # 明确填10%
    全能增伤="0.35*全能",        # 默认公式
    赛季增伤="0",
    最终增伤="0"
)
print_panel(m_def, "初始面板")

# ==================== 第二步：引入公式 ====================
print("\n>>> 第二步：使用 gongshi 设置公式（爆伤=50%+暴击*0.5，元素增伤=5%+精通*0.65）")
gongshi(m_def, '爆伤', '50 + 暴击*0.5')
gongshi(m_def, '元素增伤', '5 + 精通*0.65')
print_panel(m_def, "应用公式后")

# ==================== 第三步：暴击+10%，精通固定值+10000 ====================
print("\n>>> 第三步：暴击百分比直接+10%，精通固定值+10000")
old_baoji_formula = m_def.暴击
new_baoji_formula = f"({old_baoji_formula}) + 10"
gongshi(m_def, '暴击', new_baoji_formula)
m_def.精通固定值 += 10000
print_panel(m_def, "修改后（重新解析公式）")

# ==================== 技能导入（法术伤害） ====================
print("\n>>> 导入技能（法术伤害）")
skill_str1 = "1,冰矛,法术,300%,500,1,0,0,0,0,0,100%,10%,0,0,0"
skill_str2 = "2,陨星,法术,200%,500,1,0,0,0,0,0,100%,10%,0,0,0"
skill1_def = import_skill(skill_str1)
skill2_def = import_skill(skill_str2)

# 获取纯数值面板
m_num = _resolve_panel_in_order(m_def)

# 技能解析上下文
ctx_skill = {
    '暴击': m_num.暴击, '急速': m_num.急速, '幸运': m_num.幸运,
    '精通': m_num.精通, '全能': m_num.全能, '爆伤': m_num.爆伤,
    '一般增伤': m_num.一般增伤, '元素增伤': m_num.元素增伤,
    '全能增伤': m_num.全能增伤, '赛季增伤': m_num.赛季增伤,
    '最终增伤': m_num.最终增伤,
    '固定主属性': m_num.固定主属性, '百分比主属性': m_num.百分比主属性,
    '转化系数': m_num.转化系数, '额外固定攻击力': m_num.额外固定攻击力,
    '额外百分比攻击力': m_num.额外百分比攻击力,
    '精炼攻击力': m_num.精炼攻击力, '元素攻击力': m_num.元素攻击力,
    '暴击固定值': m_num.暴击固定值, '急速固定值': m_num.急速固定值,
    '幸运固定值': m_num.幸运固定值, '精通固定值': m_num.精通固定值,
    '全能固定值': m_num.全能固定值,
}

skill1_num = resolve_target(skill1_def, ctx_skill)
skill2_num = resolve_target(skill2_def, ctx_skill)

print("\n--- 冰矛 解析后 ---")
print(f"伤害类型: {skill1_num.伤害类型}")
print(f"技能倍率: {skill1_num.技能倍率}")
print(f"技能固定值: {skill1_num.技能固定值}")
print(f"hit数: {skill1_num.hit数}")
print(f"暴击: {skill1_num.暴击}%")
print(f"爆伤: {skill1_num.爆伤}%")
print(f"一般增伤: {skill1_num.一般增伤}%")
print(f"元素增伤: {skill1_num.元素增伤}%")

print("\n--- 陨星 解析后 ---")
print(f"伤害类型: {skill2_num.伤害类型}")
print(f"技能倍率: {skill2_num.技能倍率}")
print(f"技能固定值: {skill2_num.技能固定值}")
print(f"hit数: {skill2_num.hit数}")
print(f"暴击: {skill2_num.暴击}%")
print(f"爆伤: {skill2_num.爆伤}%")
print(f"一般增伤: {skill2_num.一般增伤}%")

# 伤害计算
dmg1 = calc_skill_damage(m_def, skill1_def)
dmg2 = calc_skill_damage(m_def, skill2_def)
print(f"\n冰矛期望伤害: {dmg1:.2f}")
print(f"陨星期望伤害: {dmg2:.2f}")

# ==================== Buff 测试 ====================
print("\n>>> Buff 测试")
# 灌注：元素攻击力+150，暴击+3%
buff1_str = "1,灌注,0,0,0,0,0,150,0,0,0,0,0,0,3%,0,0,0,0,0,0,0,0,0,0,0"
# 博人：额外攻击力百分比+26%
buff2_str = "2,博人,0,0,0,26%,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0"
buff1 = import_buff(buff1_str)
buff2 = import_buff(buff2_str)

m_def_buff1 = deepcopy(m_def)
m_def_buff2 = deepcopy(m_def_buff1)

from buffed import buffed

# 应用灌注
buffed(buff1, m_def_buff1)
print("\n--- 应用灌注后 ---")
print_panel(m_def_buff1, "灌注后面板")
dmg1_b1 = calc_skill_damage(m_def_buff1, skill1_def)
dmg2_b1 = calc_skill_damage(m_def_buff1, skill2_def)
print(f"冰矛期望伤害: {dmg1_b1:.2f}")
print(f"陨星期望伤害: {dmg2_b1:.2f}")

# 再堆叠博人
buffed(buff2, m_def_buff2)
print("\n--- 堆叠博人后 ---")
print_panel(m_def_buff2, "灌注+博人后面板")
dmg1_b2 = calc_skill_damage(m_def_buff2, skill1_def)
dmg2_b2 = calc_skill_damage(m_def_buff2, skill2_def)
print(f"冰矛期望伤害: {dmg1_b2:.2f}")
print(f"陨星期望伤害: {dmg2_b2:.2f}")

# ==================== 抗性穿防测试 ====================
print("\n>>> 抗性穿防测试：法防穿防100%")
# 在现有堆叠博人的面板基础上，设置法术百分比穿防为100
m_def_fullpen = deepcopy(m_def_buff2)
gongshi(m_def_fullpen, '法术百分比穿防', '100')
print_panel(m_def_fullpen, "法防穿防100%后面板")
dmg1_pen = calc_skill_damage(m_def_fullpen, skill1_def)
dmg2_pen = calc_skill_damage(m_def_fullpen, skill2_def)
print(f"冰矛期望伤害 (穿防100%): {dmg1_pen:.2f}")
print(f"陨星期望伤害 (穿防100%): {dmg2_pen:.2f}")