"""喵喵分子助手 · 主题层（照搬 MDX Terminal UI 设计稿）。

配色、猫猫表情、小动词、树状符号全部来自设计稿：
- 品牌橙 #e8a27c · 成功绿 #9ccf8a · 提醒黄 #e6c46e · 出错红 #eb7f74 · 路径蓝 #8fb3e0
- 正文 #e6e1db · 弱化 #8a837c · 更弱 #6f6861
- 猫猫表情 = 状态；出错也不凶。
"""
from rich.console import Console
from rich.theme import Theme

BRAND = "#e8a27c"
OK = "#9ccf8a"
WARN = "#e6c46e"
BAD = "#eb7f74"
PATH = "#8fb3e0"
TEXT = "#e6e1db"
MUTED = "#8a837c"
FAINT = "#6f6861"

THEME = Theme({
    "brand": BRAND, "ok": OK, "warn": WARN, "bad": BAD, "path": PATH,
    "text": TEXT, "muted": MUTED, "faint": FAINT,
})

console = Console(theme=THEME, highlight=False)

# 猫猫表情 = 状态。全部 ASCII：设计稿里的宽字符（⌨ ♡ ⊙ つ ω）在 CJK 终端
# 是双宽，窄窗口下会把面板撑到跨行撕裂，所以表情保持纯 ASCII 不破版。
FACES = {
    "idle":      (BRAND, " /\\_/\\\n( o.o )\n > ^ < "),
    "working":   (BRAND, " /\\_/\\\n( o.o )/\n > ^ <  "),
    "success":   (OK,    " /\\_/\\\n( ^.^ )\n > v < "),
    "warning":   (WARN,  " /\\_/\\\n( o_o )\n > ^ < "),
    "error":     (BAD,   " /\\_/\\\n( ;.; )\n > ^ < "),
    "interrupt": (WARN,  " /\\_/\\\n( O.O )\n > ! < "),
    "sleep":     (MUTED, " /\\_/\\  z\n( -.- ) z\n > ^ < "),
}
STATE_COLOR = {"success": OK, "warning": WARN, "error": BAD, "cancelled": WARN,
               "interrupted": WARN, "running": BRAND, "idle": BRAND}
MARK_COLOR = {"✓": OK, "!": WARN, "✗": BAD}

# 小动词 + 闪烁符号（运行中随机出现；符号本身不进猫猫画布，不会破版）
SPIN = ["·", "✢", "✳", "✶", "✻", "✶", "✳", "✢"]
VERBS = ["踩奶中", "舔毛中", "追尾巴中", "翻 OUTCAR 中", "打呼噜中", "数原子中", "伸懒腰中"]

# 工具完成后的一步建议
NEXT_HINT = {
    "audit": "没问题的文件可以直接 /convert 转数据集",
    "convert": "下一步可以 /split 划分训练 / 测试集",
    "extract": "抽好的 POSCAR 可以 /perturb 做微扰",
    "perturb": "微扰结构可以拿去提交计算，或 /vacancy 造空位",
    "vacancy": "空位结构可以 /sample 再随机采样一批",
    "split": "划分结果记得核对 manifest 后再训练",
    "sample": "采出来的结构可以 /collect 归档",
    "collect": "收集完可以 /extract 抽帧",
}


def face(state):
    """返回 (color, 多行猫猫字符串)。"""
    return FACES.get(state, FACES["idle"])


def dot(state="running", mark=None):
    """树状事件圆点 / 标记。"""
    if mark:
        return f"[{MARK_COLOR.get(mark, BRAND)}]{mark}[/]"
    return f"[{STATE_COLOR.get(state, BRAND)}]●[/]"
