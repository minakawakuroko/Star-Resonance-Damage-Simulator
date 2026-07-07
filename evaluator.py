import math
from simpleeval import simple_eval
from models import GameEntity

def get_functions():
    return {
        'floor': math.floor, 'ceil': math.ceil,
        'round': round, 'max': max, 'min': min,
        'abs': abs, 'int': int, 'float': float,
        'sqrt': math.sqrt, 'pow': pow,
        'log': math.log, 'log10': math.log10,
        'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
    }

def eval_expr(expr, context: dict) -> float:
    if isinstance(expr, (int, float)):
        return float(expr)
    if isinstance(expr, str):
        expr = expr.strip()
        if expr == '':
            return 0.0
        try:
            return simple_eval(expr, names=context, functions=get_functions())
        except Exception as e:
            try:
                return float(expr)
            except:
                return 0.0
    return float(expr)

def resolve_target(target: GameEntity, context: dict):
    from dataclasses import fields
    kwargs = {}
    local_ctx = dict(context)
    for f in fields(target):
        if f.name in ('编号', '名称', '类别', '伤害类型', 'buffci', '输入参数', '输出参数'):
            kwargs[f.name] = getattr(target, f.name)
            continue
        val = getattr(target, f.name)
        if isinstance(val, str):
            try:
                kwargs[f.name] = eval_expr(val, local_ctx)
            except:
                kwargs[f.name] = 0.0
            if f.name == '技能倍率' and 1000 <= target.编号 < 2000:
                kwargs[f.name] /= 100.0
        else:
            kwargs[f.name] = float(val) if isinstance(val, (int, float)) else val
        if isinstance(kwargs[f.name], (int, float)):
            local_ctx[f.name] = kwargs[f.name]
    return GameEntity(**kwargs)