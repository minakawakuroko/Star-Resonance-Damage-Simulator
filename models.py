from dataclasses import dataclass, field

@dataclass
class GameEntity:
    编号: int = 0
    名称: str = ""
    类别: str = ""
    伤害类型: str = "0"

    固定主属性: str = "0"
    百分比主属性: str = "0"
    转化系数: str = "0"
    额外固定攻击力: str = "0"
    额外百分比攻击力: str = "0"
    精炼攻击力: str = "0"
    本元素攻击力: str = "0"
    全元素攻击力: str = "0"
    本元素攻击力百分比: str = "0"
    全元素攻击力百分比: str = "0"
    暴击固定值: str = "0"
    急速固定值: str = "0"
    幸运固定值: str = "0"
    精通固定值: str = "0"
    全能固定值: str = "0"
    敌人物理防御: str = "0"
    敌人法术防御: str = "0"
    防御系数常数: str = "0"
    百分比穿防: str = "0"
    固定穿防: str = "0"
    暴击: str = "0"
    急速: str = "0"
    幸运: str = "0"
    精通: str = "0"
    全能: str = "0"
    爆伤: str = "0"
    一般增伤: str = "0"
    本元素增伤: str = "0"
    全元素增伤: str = "0"
    元素增伤: str = "0"
    赛季增伤: str = "0"
    最终增伤: str = "0"

    技能倍率: str = "0"
    技能固定值: str = "0"
    hit数: str = "1"
    是否幸运: str = "1"
    是否是幸运一击: str = "0"

    # 新增词条
    绿值主属性: str = "0"
    绿值攻击力: str = "0"
    雷印: str = "0"

    # 参数传递
    输入参数: str = ""
    输出参数: str = ""

    主属性固定值: str = "0"
    主属性百分比: str = "0"
    攻击力固定值: str = "0"
    元素攻击力固定值: str = "0"
    元素攻击力百分比: str = "0"

    buffci: list[int] = field(default_factory=list)