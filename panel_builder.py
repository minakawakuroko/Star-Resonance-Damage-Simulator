import json, os, sys
from models import GameEntity

def _get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PANEL_CONSTANTS_FILE = os.path.join(_get_app_dir(), 'data', 'panel_constants.json')
PANEL_CACHE_FILE = os.path.join(_get_app_dir(), 'data', 'panel_inputs.json')

DEFAULT_CONSTANTS = {
    "暴击常数": 50000,
    "急速常数": 50000,
    "幸运常数": 50000,
    "精通常数": 50000,
    "全能常数": 28000
}

def load_panel_constants():
    if os.path.exists(PANEL_CONSTANTS_FILE):
        with open(PANEL_CONSTANTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return DEFAULT_CONSTANTS.copy()

def save_panel_constants(constants):
    os.makedirs(os.path.dirname(PANEL_CONSTANTS_FILE), exist_ok=True)
    with open(PANEL_CONSTANTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(constants, f, ensure_ascii=False, indent=2)

def load_panel_inputs() -> dict:
    """读取用户上次保存的面板输入值"""
    if os.path.exists(PANEL_CACHE_FILE):
        with open(PANEL_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_panel_inputs(inputs: dict):
    """保存用户输入的面板值到本地文件"""
    os.makedirs(os.path.dirname(PANEL_CACHE_FILE), exist_ok=True)
    with open(PANEL_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(inputs, f, ensure_ascii=False, indent=2)

def build_panel(
    站街主属性="5000",
    装备主属性百分比="0", 天赋来源主属性百分比="0", 幻想主属性百分比="0", 其他主属性百分比="0",
    转化系数="0.5",
    武器固定攻击力="0", 模组固定攻击力="0", 其他固定攻击力="0",
    装备攻击力百分比="0", 天赋攻击力百分比="0", 其他攻击力百分比="0",
    精炼攻击力="1000",
    本元素攻击力="0", 全元素攻击力="0",
    本元素攻击力百分比="0", 全元素攻击力百分比="0",
    暴击固定值="50000", 急速固定值="50000", 幸运固定值="50000",
    精通固定值="50000", 全能固定值="28000",
    一般增伤="10",
    本元素增伤="0", 全元素增伤="0",
    敌人物理防御="9945", 敌人法术防御="2018", 防御系数常数="23205",
    爆伤="60",
    百分比穿防="0", 固定穿防="0"
) -> GameEntity:
    m = GameEntity()
    m.编号 = 0
    m.名称 = "面板"
    m.类别 = "面板"

    try:
        sum_percent = float(装备主属性百分比) + float(天赋来源主属性百分比) + float(幻想主属性百分比) + float(其他主属性百分比)
        fixed_main = float(站街主属性) / (1 + sum_percent / 100.0)
        m.固定主属性 = str(round(fixed_main, 4))
    except:
        m.固定主属性 = "0"

    m.百分比主属性 = str(sum_percent)
    m.转化系数 = str(转化系数)

    try:
        extra_fixed = float(武器固定攻击力) + float(模组固定攻击力) + float(其他固定攻击力)
        m.额外固定攻击力 = str(extra_fixed)
    except:
        m.额外固定攻击力 = "0"

    try:
        extra_percent = float(装备攻击力百分比) + float(天赋攻击力百分比) + float(其他攻击力百分比)
        m.额外百分比攻击力 = str(extra_percent)
    except:
        m.额外百分比攻击力 = "0"

    m.精炼攻击力 = str(精炼攻击力)
    m.本元素攻击力 = str(本元素攻击力)
    m.全元素攻击力 = str(全元素攻击力)
    m.本元素攻击力百分比 = str(本元素攻击力百分比)
    m.全元素攻击力百分比 = str(全元素攻击力百分比)

    m.暴击固定值 = str(暴击固定值)
    m.急速固定值 = str(急速固定值)
    m.幸运固定值 = str(幸运固定值)
    m.精通固定值 = str(精通固定值)
    m.全能固定值 = str(全能固定值)

    m.敌人物理防御 = str(敌人物理防御)
    m.敌人法术防御 = str(敌人法术防御)
    m.防御系数常数 = str(防御系数常数)
    m.百分比穿防 = str(百分比穿防)
    m.固定穿防 = str(固定穿防)

    # 从配置文件读取常数
    constants = load_panel_constants()
    crit_const = constants.get("暴击常数", 50000)
    haste_const = constants.get("急速常数", 50000)
    luck_const = constants.get("幸运常数", 50000)
    mastery_const = constants.get("精通常数", 50000)
    omni_const = constants.get("全能常数", 28000)

    m.暴击 = f"5 + 暴击固定值/(暴击固定值+{crit_const})*100"
    m.急速 = f"急速固定值/(急速固定值+{haste_const})*100"
    m.幸运 = f"5 + 幸运固定值/(幸运固定值+{luck_const})*100"
    m.精通 = f"6 + 精通固定值/(精通固定值+{mastery_const})*100"
    m.全能 = f"全能固定值/(全能固定值+{omni_const})*100"

    m.爆伤 = str(爆伤)
    m.一般增伤 = str(一般增伤)
    m.本元素增伤 = str(本元素增伤)
    m.全元素增伤 = str(全元素增伤)
    m.元素增伤 = "0"
    m.赛季增伤 = "0"
    m.最终增伤 = "0"

    m.hit数 = "0"
    m.是否幸运 = "0"
    m.是否是幸运一击 = "0"
    return m