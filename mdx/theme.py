"""MDX 高对比猫猫主题（设计稿 3a：亮 ANSI 16 色 + 原版 ASCII 猫）。

颜色规范（设计稿）：青=命令/提示符/标题 · 绿=成功 · 黄=警告/猫 · 红=错误 · 品红=品牌 · 灰=标签。
防破版规范：凡参与对齐的字符只用 ASCII（o - | + . = >）；
CJK 本身两格等宽可安全出现在任意行；✦ ❯ ● ･ ω 等 Ambiguous 字符只允许
出现在行尾或无边框行（后面没有需要对齐的东西）。
"""
from rich.console import Console
from rich.theme import Theme

CYAN = "bright_cyan"      # #5ff5ff 命令、提示符、标题
GREEN = "bright_green"    # #5fff87 成功
YELLOW = "bright_yellow"  # #ffe55f 警告、猫
RED = "bright_red"        # #ff5f5f 错误
MAGENTA = "bright_magenta"  # #ff5fd2 品牌
DIM = "grey62"            # 标签、路径、提示

THEME = Theme({
    "brand": CYAN, "cat": YELLOW, "accent": MAGENTA,
    "ok": GREEN, "warn": YELLOW, "err": RED,
    "dim": DIM, "text": "white",
})

console = Console(theme=THEME, highlight=False)

# 原版 ASCII 猫（表情 = 状态）
FACES = {
    "idle":      (YELLOW, " /\\_/\\\n( o.o )\n > ^ < "),
    "working":   (YELLOW, " /\\_/\\\n( o.o )/\n > ^ <  "),
    "success":   (GREEN,  " /\\_/\\\n( ^.^ )\n > v < "),
    "warning":   (YELLOW, " /\\_/\\\n( o_o )\n > ^ < "),
    "error":     (RED,    " /\\_/\\\n( ;.; )\n > ^ < "),
    "interrupt": (YELLOW, " /\\_/\\\n( O.O )\n > ! < "),
    "sleep":     (DIM,    " /\\_/\\  z\n( -.- ) z\n > ^ < "),
}
STATE_COLOR = {"success": GREEN, "warning": YELLOW, "error": RED, "cancelled": YELLOW,
               "interrupted": YELLOW, "running": CYAN, "idle": YELLOW}

# 行内心情猫（ASCII kaomoji，可安全出现在任何行）
MOODS = {"ok": "(=^.^=)", "warn": "(=o.o=)", "err": "(=;.;=)", "sleep": "(=-.-=)z",
         "idle": "(=o.o=)", "work": "(=^.^=)"}

SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"  # 仅用于无边框行
VERBS = ["喵～ 检查中 checking", "喵～ 翻文件中 scanning", "喵～ 数原子中 counting", "喵～ 踩奶中 kneading"]

NEXT_HINT = {
    "audit": "没问题的文件可以 21 转数据集",
    "convert": "下一步可以 22 划分训练/测试集",
    "extract": "抽好的 POSCAR 可以 01 做微扰",
    "perturb": "微扰结构可以提交计算, 或 02 造空位",
    "vacancy": "空位结构可以 04 再采样一批",
    "split": "划分结果记得核对 manifest 后再训练",
    "sample": "采出来的结构可以 12 收集归档",
    "collect": "收集完可以 03 抽帧",
}

AUTHOR = "Zemeng FENG, Kui XU"
AFFILIATION = "Institute of Advanced Materials, Nanjing Tech University"
REPO = "github.com/WhiteCrosstheRiver/MDX"


def face(state):
    """返回 (rich样式名, 多行猫猫字符串)。"""
    return FACES.get(state, FACES["idle"])


def mood(kind):
    return MOODS.get(kind, MOODS["idle"])
