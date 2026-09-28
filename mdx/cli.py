"""喵喵分子助手 · 命令行界面（完全照搬 MDX Terminal UI 设计稿）。

对话式 agent CLI 的节奏：欢迎卡片 → 输入框 → 带小动词的思考动画 → 树状结果。
猫猫表情跟着状态变，出错也不凶。无 TTY 自动收起猫猫和颜色：一行一事件带时间戳。
"""
import argparse
import datetime
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

from rich.box import ROUNDED
from rich.panel import Panel
from rich.text import Text

from . import __version__
from .catalog import BY_ID, TOOLS, validate
from .operations import discover, run as run_tool
from .theme import (BAD, BRAND, FACES, FAINT, MUTED, NEXT_HINT, OK, PATH, SPIN,
                    VERBS, console, dot, face)

try:
    from prompt_toolkit.completion import Completion, Completer, PathCompleter
except ImportError:  # 允许在未装 prompt_toolkit 时使用非交互命令
    Completion = Completer = PathCompleter = None

CONFIG_DIR = Path.home() / ".mdx"
CONFIG_PATH = CONFIG_DIR / "config.json"

# 自然语言关键词 → 工具（按优先级，命中第一个即停）
KEYWORDS = {
    "audit": ["完整性", "检查", "收敛", "nelm"],
    "convert": ["转换", "extxyz", "数据集", "转xyz", "转 xyz"],
    "extract": ["抽帧", "抽轨迹", "截帧", "帧间隔", "轨迹取样"],
    "perturb": ["微扰", "扰动", "加噪", "应变"],
    "vacancy": ["空位", "缺原子", "移除原子", "去原子"],
    "split": ["划分", "训练测试", "train", "test"],
    "sample": ["采样", "抽样", "随机抽取", "抽取结构"],
    "collect": ["收集", "汇总", "归集"],
}

PROGRESS_RE = re.compile(r"处理 (\d+)/(\d+)")


# ---------------------------------------------------------------- 助手解析

def parse_command(text):
    """把一行输入解析为动作；无法识别时 tool 为 None。"""
    input_ = text.strip().lower()
    if not input_:
        return None
    if input_.startswith("/"):
        name = input_.lstrip("/").split()[0]
        if name in {"h", "help", "帮助"}:
            return {"help": True}
        if name in {"q", "quit", "exit", "退出", "bye"}:
            return {"quit": True}
        if name in {"ls", "tools", "工具"}:
            return {"list": True}
        if name == "env":
            return {"env": True}
        if name == "clear":
            return {"clear": True}
        if name in FACES:
            return {"cat": name}
        return {"tool": BY_ID.get(name)}
    for tool_id, words in KEYWORDS.items():
        if any(word in input_ for word in words):
            return {"tool": BY_ID[tool_id], "understood": input_}
    return {"tool": None, "text": text}


# ---------------------------------------------------------------- 显示小件

def note(message, state="idle", mark=None):
    """一行事件：圆点 + 人话。"""
    console.print(f"{dot(state, mark)} {message}")


def tree_line(text, depth=1):
    console.print(f"{'  ' * depth}[muted]└[/] {text}")


def cat_says(state, message, sub=None):
    """猫猫 + 一句话（完成 / 出错 / 中断时出现，说完就收）。"""
    color, art = face(state)
    body = Text()
    body.append(art + "\n", style=color)
    body.append(message, style="text")
    if sub:
        body.append("\n" + sub, style="muted")
    console.print(Panel(body, border_style=color, padding=(0, 1), box=ROUNDED))


def prompt_parameters(ui, tool, overrides=None):
    """逐项询问参数，回车取默认值；overrides 跳过对应项。"""
    overrides = overrides or {}
    params = {}
    if not tool["fields"]:
        return params
    note(f"「{tool['name']}」参数（直接回车使用默认值）")
    for spec in tool["fields"]:
        default = overrides.get(spec["key"], spec["default"])
        suffix = f"{spec['min']}–{spec['max']}" if spec["key"] != "seed" else "0–2147483647"
        raw = input(f"    {spec['label']} [{default}] ({suffix}): ").strip()
        if not raw:
            params[spec["key"]] = default
            continue
        try:
            value = float(raw)
            assert spec["min"] <= value <= spec["max"]
            params[spec["key"]] = int(value) if spec["step"] == 1 else value
        except (ValueError, AssertionError):
            note(f"{spec['label']} 应该是数字（{spec['min']}–{spec['max']}），先用默认值 {spec['default']} 啦",
                 state="warning")
            params[spec["key"]] = spec["default"]
    return params


def humanize_error(exc):
    """设计稿 07：错误 → (一句人话, 可直接复制的修复命令, 备注)。"""
    text = str(exc)
    lowered = text.lower()
    if "no module named" in lowered:
        mod = lowered.split("no module named")[-1].strip(" '\"。 ")
        if mod in {"ase", "numpy"}:
            return f"缺少依赖 {mod}", "python -m pip install --user ase numpy", "/audit 这类检查工具不需要它"
        return f"缺少依赖 {mod}", f"python -m pip install --user {mod}", None
    if "没有该工具支持的输入文件" in text:
        return "这个目录里没找到需要的输入文件", "/tools 看每个工具要什么 · cd 到计算目录再试", None
    if "不存在" in text or "no such" in lowered:
        return text, "检查一下路径，输入时可以按 Tab 补全", None
    if "nelm" in lowered or "收敛" in text or "CONTCAR" in text:
        return text, "如果计算确实没跑完，等它结束或调大 NELM 再 /convert", None
    return text, None


# ---------------------------------------------------------------- 工具执行

def count_inputs(project):
    counts = {}
    for _, kind in discover(Path(project)):
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def confirm_card(tool, params, output, n_inputs, session_flags):
    """设计稿 03：执行前确认。返回 True / False / "edit"。"""
    if session_flags.get("no_ask") or not sys.stdin.isatty():
        return True
    body = Text()
    body.append(f"{tool['name']} ", style="bold")
    body.append(f"· {n_inputs} 个输入文件\n", style="muted")
    for f in tool["fields"]:
        body.append(f"{f['key']:<14}", style="muted")
        body.append(f"{params.get(f['key'], f['default'])}\n")
    body.append(f"{'输出':<14}", style="muted")
    body.append(f"{output}\n", style="path")
    body.append("\n要开始吗？", style="text")
    console.print(Panel(body, border_style=FAINT, padding=(0, 1), box=ROUNDED))
    console.print(f"[{BRAND}]❯ 1. 开始[/]\n  2. 开始，本次会话别再问\n  3. 改一下参数 [faint](e)[/]")
    choice = input("").strip().lower()
    if choice == "2":
        session_flags["no_ask"] = True
        return True
    if choice in {"e", "3"}:
        return "edit"
    return choice in {"", "1", "y"}


def plain_log(tool, message):
    """设计稿 10：无 TTY 一行一事件，带时间戳和等级，方便 grep。"""
    level = "INFO"
    if any(k in message for k in ("失败", "✗", "错误")):
        level = "ERROR"
    elif any(k in message for k in ("跳过", "未", "提示", "!", "WARN")):
        level = "WARN"
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{stamp} {level:<5} {tool} {message}")


def execute(ui, tool_id, params, project=None, output=None, ask=None, session_flags=None):
    session_flags = session_flags if session_flags is not None else {}
    tool = BY_ID[tool_id]
    interactive = sys.stdout.isatty()

    if project is None:
        project = (ask or input)("    数据目录（Tab 可补全路径）: ").strip()
    project = Path(project).expanduser().resolve()
    if not project.is_dir():
        message, fix, _ = humanize_error(f"目录不存在：{project}")
        note(message, state="error")
        if fix:
            tree_line(fix)
        return
    n_inputs = sum(count_inputs(project).values())
    stamp = time.strftime("%Y%m%d-%H%M%S")
    output = Path(output).expanduser().resolve() if output else project.parent / f"mdx-out/{tool_id}-{stamp}"

    answer = confirm_card(tool, params, output, n_inputs, session_flags)
    if answer == "edit":
        params = prompt_parameters(ui, tool, params)
    elif not answer:
        note("那先不跑，需要的时候再叫我～")
        return

    output.mkdir(parents=True, exist_ok=True)
    rng = random.Random(stamp)
    verb = rng.choice(VERBS)
    started = time.monotonic()
    result = None
    error = None
    interrupted = False

    if not interactive:
        plain_log(tool_id, f"start project={project} params={params}")

    state = {"lines": [], "progress": None}

    def log(message):
        if not interactive:
            plain_log(tool_id, message)
            return
        match = PROGRESS_RE.search(message)
        if match:
            state["progress"] = (int(match[1]), int(match[2]))
        state["lines"].append(message)

    try:
        if interactive:
            from rich.live import Live

            def card():
                secs = time.monotonic() - started
                frame = SPIN[int(secs * 6) % len(SPIN)]
                box = Text()
                box.append(f"{frame} {verb}… ", style=BRAND)
                box.append(f"({secs:.0f}s · Ctrl-C 中断)", style="muted")
                prog = state["progress"]
                if prog:
                    done, total = prog
                    pct = min(100, int(done * 100 / max(total, 1)))
                    n = round(pct / 4)
                    box.append(f"\n[{'█' * n}{'░' * (25 - n)}] {pct}%  {done}/{total}", style=BRAND)
                for line in state["lines"][-5:]:
                    box.append(f"\n[muted]└[/] {line}")
                return Panel(box, border_style=FAINT, padding=(0, 1), box=ROUNDED)

            with Live(card(), console=console, refresh_per_second=6,
                      transient=True, vertical_overflow="crop"):
                result = run_tool(tool_id, project, output, params, log, lambda: False)
        else:
            result = run_tool(tool_id, project, output, params, log, lambda: False)
    except KeyboardInterrupt:
        interrupted = True
    except (ValueError, InterruptedError) as exc:
        error = str(exc)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    elapsed = time.monotonic() - started
    if not interactive:
        if interrupted:
            plain_log(tool_id, "interrupted")
        elif error:
            plain_log(tool_id, f"fail {error}")
        else:
            plain_log(tool_id, f"done records={result['records']} output={output}")
        return

    # 收尾：树状结果（设计稿 04/05/06/09）
    console.print()
    if interrupted:
        note(f"已中断 · 用时 {elapsed:.0f}s", state="warning")
        tree_line(f"已生成的留在 [path]{output}[/]")
        cat_says("interrupt", "好的停下了！部分结果已经保留", "manifest: status = interrupted")
    elif error:
        message, fix, extra = humanize_error(error)
        note(message, state="error")
        if fix:
            tree_line(fix)
        if extra:
            console.print(f"      [faint]{extra}[/]")
        cat_says("error", "没关系，改好了再叫我～")
    else:
        issues = result.get("issues", 0)
        note(f"{tool['name']} 完成 · {result['records']} 条记录 · {elapsed:.0f}s",
             state="success", mark="✓")
        tree_line(f"[path]{output}[/]")
        console.print("    [muted]├[/] manifest.json [muted]参数 · 来源 · 可复现[/]")
        if issues:
            console.print(f"    [muted]└[/] {issues} 条完整性提示 [warn]先看一眼再用于训练[/]")
            cat_says("warning", f"有 {issues} 条提示，多半是没跑完的计算",
                     f"之后 /convert 会自动跳过 ✗ 项 · {NEXT_HINT.get(tool_id, '')}")
        else:
            cat_says("success", f"搞定喵～ {NEXT_HINT.get(tool_id, '')}")


# ---------------------------------------------------------------- 清单与环境

def print_tools(ui, short=False):
    cwd_counts = count_inputs(Path.cwd())
    for group in ["计算检查", "结构准备", "数据处理"]:
        tools = [t for t in TOOLS if t["group"] == group]
        if not tools:
            continue
        note(group)
        for tool in tools:
            need = next(iter(re.findall(r"[A-Za-z]+", tool["files"])), "")
            have = need.lower() in cwd_counts or need in cwd_counts
            flag = "" if have else f"  [faint]缺 {need}[/]"
            if short:
                console.print(f"    [brand]/{tool['id']}[/]  {tool['name']}{flag}")
            else:
                console.print(f"    [brand]/{tool['id']}[/]  {tool['name']}  [muted][{tool['files']}]{flag}[/]")
                console.print(f"      [muted]{tool['description']}[/]")
    console.print()


def show_env(ui):
    import importlib.util
    import platform
    note("运行环境（本机实际值）")
    rows = [
        ("Python", platform.python_version()),
        ("平台", platform.platform()),
        ("ASE", "✓ 已安装" if importlib.util.find_spec("ase") else "✗ 未安装（结构类工具不可用）"),
        ("NumPy", "✓ 已安装" if importlib.util.find_spec("numpy") else "✗ 未安装"),
        ("程序目录", str(project_root())),
    ]
    for key, value in rows:
        console.print(f"  [muted]{key:<10}[/]{value}")
    console.print()


# ---------------------------------------------------------------- 安装

def bin_candidates():
    """按优先级返回候选 bin 目录（用户级优先，不碰系统目录）。"""
    home = Path.home()
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        return [local / "Programs" / "mdx", home / "bin"]
    return [home / ".local" / "bin", home / "bin",
            Path("/usr/local/bin"), Path("/opt/homebrew/bin")]


def choose_bin(ui, explicit=None):
    if explicit:
        target = Path(explicit).expanduser().resolve()
        target.mkdir(parents=True, exist_ok=True)
        return target, "指定目录"
    # 设计稿 11：扫描出的 bin 位置做成选项，标注是否在 PATH
    candidates = bin_candidates()
    path_set = {Path(p) for p in os.environ.get("PATH", "").split(os.pathsep)}
    console.print(Panel("[bold]装到哪里？[/]\n[muted]只写入一个启动脚本 · 不建虚拟环境 · 不装包 · 不碰系统目录[/]",
                        border_style=FAINT, padding=(0, 1), box=ROUNDED))
    shown = candidates[:2]
    for i, c in enumerate(shown, 1):
        mark = "[ok]在 PATH 里 · 推荐[/]" if c in path_set else "[warn]不在 PATH，需要手动加[/]"
        prefix = f"[{BRAND}]❯ {i}. {c}[/]" if i == 1 else f"{i}. {c}"
        console.print(f"{prefix}  {mark}")
    console.print(f"  3. 自己指定… [faint](--dir)[/]")
    choice = input("").strip()
    if choice == "2" and len(candidates) > 1:
        target = candidates[1]
    elif choice == "3":
        target = Path(input("bin 目录: ").strip()).expanduser()
    else:
        target = candidates[0]
    target.mkdir(parents=True, exist_ok=True)
    return target, ("在 PATH 里" if target in path_set else "不在 PATH，需要手动加")


def launcher_body(bin_dir, python, root):
    if os.name == "nt":
        return (f'@echo off\r\nset "PYTHONPATH={root}"\r\n'
                f'@"{python}" -m mdx %*\r\n')
    return (f"#!/usr/bin/env bash\n"
            f"# MDX launcher — generated by `mdx install`, safe to delete\n"
            f'export PYTHONPATH="{root}"\n'
            f'exec "{python}" -m mdx "$@"\n')


def install(explicit_dir=None, dry_run=False, ui=None):
    python = sys.executable
    root = str(Path(__file__).resolve().parent.parent)
    if explicit_dir or not sys.stdin.isatty():
        if explicit_dir:
            bin_dir = Path(explicit_dir).expanduser().resolve()
            bin_dir.mkdir(parents=True, exist_ok=True)
            reason = "指定目录"
        else:
            bin_dir = bin_candidates()[0]
            bin_dir.mkdir(parents=True, exist_ok=True)
            reason = "推荐位置"
    else:
        bin_dir, reason = choose_bin(ui)
    name = "mdx.bat" if os.name == "nt" else "mdx"
    target = bin_dir / name
    in_path = any(p == bin_dir for p in (Path(p) for p in os.environ.get("PATH", "").split(os.pathsep)))

    console.print(f"\n  [muted]安装位置[/]  [path]{target}[/] [muted]（{reason}）[/]")
    console.print(f"  [muted]解释器[/]    {python}")
    console.print(f"  [muted]程序目录[/]  {root} [muted]（启动器只指向这里，不复制、不安装包）[/]")
    if dry_run:
        console.print("\n  [warn]◆ dry-run[/] 未写入任何文件。")
        return

    target.write_text(launcher_body(bin_dir, python, root), encoding="utf-8", newline="\n" if os.name != "nt" else None)
    if os.name != "nt":
        target.chmod(0o755)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(dict(
        bin=str(target), python=python, root=root,
        installed=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")),
        ensure_ascii=False, indent=2), encoding="utf-8")

    note(f"装好了 [path]{target}[/]", state="success", mark="✓")
    if in_path:
        tree_line("现在任何目录都能直接敲 [brand]mdx[/] · 卸载 [brand]mdx uninstall[/]")
    else:
        tree_line(f"[warn]{bin_dir} 不在 PATH 中[/]，加入 PATH：")
        if os.name == "nt":
            console.print(f'      setx PATH "%PATH%;{bin_dir}"   [faint]然后重开终端[/]')
        else:
            console.print(f'      echo \'export PATH="$PATH:{bin_dir}"\' >> ~/.bashrc && source ~/.bashrc')
    console.print()


def uninstall(ui=None):
    if not CONFIG_PATH.exists():
        note("未找到安装记录（~/.mdx/config.json）", state="error")
        raise SystemExit(1)
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    launcher = Path(config["bin"])
    launcher.unlink(missing_ok=True)
    CONFIG_PATH.unlink()
    note(f"已删除 {launcher} 与安装记录；程序目录 {config['root']} 未动。", state="success", mark="✓")


# ---------------------------------------------------------------- 更新

def project_root():
    return Path(__file__).resolve().parent.parent


def update(ui=None, reinstall=False):
    root = project_root()
    if not (root / ".git").exists():
        note(f"{root} 不是 git 仓库，没法自动更新；先手动同步代码吧", state="error")
        raise SystemExit(1)
    result = subprocess.run(["git", "pull", "--ff-only"], cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        # 设计稿 12：没法安全快进
        note("本地有改动，没法安全快进", state="error")
        tree_line("先 [path]git stash[/] 或提交，再试一次")
        raise SystemExit(1)
    if "Already up to date" in result.stdout or "已经是最新的" in result.stdout:
        note("已经是最新版本", state="success", mark="✓")
        return
    console.print(result.stdout.strip())
    if reinstall:
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(root), "--quiet"], check=False)
        note("依赖有变化，已重新注册")
    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if Path(config["root"]) != root or Path(config["python"]) != Path(sys.executable):
            install()
    note("更新完成", state="success", mark="✓")


# ---------------------------------------------------------------- 交互 REPL

COMPLETION_META = {f"/{t['id']}": f"{t['name']}（{t['files']}）" for t in TOOLS}
COMPLETION_META.update({"/cat": "看猫猫", "/tools": "工具清单", "/env": "运行环境", "/help": "帮助",
                        "/clear": "清屏", "/exit": "退出", "/motion": "动画开关", "/mascot": "猫开关"})

COMPLETIONS = {**{f"/{t['id']}": None for t in TOOLS},
               "/tools": None, "/env": None, "/help": None, "/clear": None, "/exit": None,
               "/cat": list(FACES), "/gallery": None,
               "/motion": ["on", "off"], "/mascot": ["on", "off"]}

if Completer is not None:  # prompt_toolkit 可用时才定义交互补全器
    class CommandCompleter(Completer):
        """前缀匹配命令补全（菜单里带说明），/cat 之类还有子命令。"""

        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            word = document.get_word_before_cursor(WORD=True) if not text.endswith(" ") else ""
            tokens = text.split()
            if word.startswith("/") and len(tokens) <= 1:
                for key in sorted(COMPLETIONS):
                    if key.startswith(word.lower()):
                        yield Completion(key, start_position=-len(word),
                                         display=key, display_meta=COMPLETION_META.get(key, ""))
                return
            first = tokens[0].lstrip("/").lower() if tokens else ""
            subs = COMPLETIONS.get("/" + first)
            if isinstance(subs, (list, tuple)):
                last = "" if text.endswith(" ") else word
                for item in sorted(subs):
                    if item.startswith(last.lower()):
                        yield Completion(item, start_position=-len(last), display=item)

    class MDXCompleter(Completer):
        """命令补全 + 路径补全：工具命令后的参数按路径补全。"""

        def __init__(self):
            self.commands = CommandCompleter()
            self.paths = PathCompleter(expanduser=True)

        def path_completions(self, word):
            # PathCompleter 把整段文本当路径，因此只喂最后一个词
            from prompt_toolkit.document import Document
            sub = Document(word, len(word))
            yield from self.paths.get_completions(sub, None)

        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            tokens = text.lstrip().split()
            first = tokens[0].lstrip("/").lower() if tokens else ""
            word = "" if text.endswith(" ") else tokens[-1] if tokens else ""
            looks_like_path = bool(word) and ("\\" in word or "/" in word or word.startswith("~"))
            in_tool_arg = first in BY_ID and (len(tokens) > 1 or text.endswith(" "))
            bare_path = looks_like_path and tokens and not tokens[0].startswith("/")
            if in_tool_arg or bare_path:
                yield from self.path_completions(word)
                return
            yield from self.commands.get_completions(document, complete_event)


def make_path_prompt(session):
    """带 Tab 路径补全的数据目录询问。"""
    from prompt_toolkit.completion import PathCompleter
    completer = PathCompleter(expanduser=True, only_directories=True)

    def ask(prompt_text):
        return session.prompt([("class:brand", prompt_text)], completer=completer).strip()
    return ask


def welcome_card():
    """设计稿 01：启动 · 欢迎卡片。"""
    cwd = Path.cwd()
    counts = count_inputs(cwd)
    detail = " · ".join(f"{v} {k}" for k, v in sorted(counts.items())) or "还没发现输入文件"
    color, art = face("idle")
    body = Text()
    body.append(art + "\n\n", style=color)
    body.append("✻ 欢迎回来！ MDX 分子模拟助手 ", style=color)
    body.append(f"v{__version__}\n", style="muted")
    body.append("纯本地 · 不联网 · 每个任务独立目录 + manifest\n", style="muted")
    body.append("目录 ", style="muted")
    body.append(f"{cwd} ", style="path")
    body.append(f"· {detail}\n", style="muted")
    body.append("Authors ", style="faint")
    body.append("Zemeng Feng", style=color)
    body.append(" · ", style="faint")
    body.append("Kui Xu\n", style=color)
    body.append("Nanjing Tech University, Institute of Advanced Materials\n", style="faint")
    body.append("试试：", style="muted")
    body.append("/audit", style="brand")
    body.append(" 检查计算 · ", style="muted")
    body.append("帮我抽帧", style="text")
    body.append(" · ", style="muted")
    body.append("/tools", style="brand")
    body.append(" 看全部", style="muted")
    console.print(Panel(body, border_style=color, padding=(1, 2), box=ROUNDED))


def interactive(ui, *, debug=False):
    if not sys.stdin.isatty() or not ui.interactive:
        note("交互模式需要终端（TTY）。无交互请用：mdx run <工具> --project <目录>", state="warning")
        return 2
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.styles import Style

    no_color = "NO_COLOR" in os.environ or ui.console.no_color or ui.options.plain
    style = Style.from_dict({
        "brand": "bold" if no_color else BRAND,
        "muted": "" if no_color else MUTED,
        "inputmark": "bold" if no_color else f"bold {BRAND}",
    })
    session = PromptSession(history=InMemoryHistory(), completer=MDXCompleter(),
                            complete_while_typing=True, reserve_space_for_menu=4,
                            style=style, erase_when_done=True, mouse_support=False,
                            refresh_interval=.25 if ui.motion else 0)

    welcome_card()
    session_flags = {"no_ask": False}
    stats = {"ok": 0, "fail": 0}
    ctrl_c = 0

    while True:
        start = time.monotonic()

        def message():
            elapsed = time.monotonic() - start
            state = "sleep" if elapsed > 45 else "idle"
            if ui.motion and ui.reaction is not None:
                previous, since = ui.reaction
                if time.monotonic() - since < 1.2:
                    state = previous
            color, art = face(state)
            pieces = [("class:brand", row + "\n") for row in art.splitlines()]
            pieces.append(("class:inputmark", "› "))
            return pieces

        try:
            line = session.prompt(message).strip()
            ctrl_c = 0
        except KeyboardInterrupt:
            ctrl_c += 1
            if ctrl_c >= 2:
                break
            console.print("[warn]再按一次 Ctrl-C 退出[/]")
            continue
        except EOFError:
            break
        if not line:
            continue
        console.print(f"[muted]›[/] {line}")

        if line.startswith("/"):
            cmd = line.lstrip("/").split()[0]
            if cmd in {"exit", "quit", "q", "退出"}:
                break
            if cmd == "clear":
                ui.console.clear()
                continue
            if cmd in {"help", "tools"}:
                print_tools(ui)
                continue
            if cmd == "env":
                show_env(ui)
                continue
            if cmd in FACES:
                color, art = face(cmd)
                console.print(art, style=color)
                console.print()
                continue
            if cmd in {"motion", "mascot"}:
                tokens = line.split()
                if len(tokens) != 2 or tokens[1] not in {"on", "off"}:
                    note(f"用法：/{cmd} on|off", state="warning")
                else:
                    from dataclasses import replace
                    key = "animate" if cmd == "motion" else "cat"
                    ui.options = replace(ui.options, **{key: tokens[1] == "on"})
                    note(f"{cmd}: {tokens[1]}")
                continue

        parsed = parse_command(line)
        if parsed is None:
            continue
        if parsed.get("tool") is None:
            # 设计稿 08：听不懂就坦白
            note("喵？这个我还不会", state="idle")
            tree_line("只认本地关键词，不联网 · [brand]/tools[/] 看我会的 8 件事")
            continue
        tool = parsed["tool"]
        if parsed.get("understood"):
            # 设计稿 08：先复述理解
            note(f"我理解成 [brand]/{tool['id']}[/] [muted]（本地关键词规则）[/]")
        tokens = line.split()
        inline_project = tokens[1] if len(tokens) > 1 and not tokens[1].startswith("-") else None
        ask = make_path_prompt(session) if inline_project is None else None
        params = prompt_parameters(ui, tool)
        before = (stats["ok"], stats["fail"])
        execute(ui, tool["id"], params, project=inline_project, ask=ask, session_flags=session_flags)
        stats["fail" if session_flags.get("last_fail") else "ok"] += 1

    # 设计稿 12：退出 · 猫猫睡觉 + 会话小结
    color, art = face("sleep")
    body = Text()
    body.append(art + "\n", style=color)
    body.append(f"拜拜～ 本次跑了 {stats['ok'] + stats['fail']} 个任务\n", style="text")
    body.append(f"✓ {stats['ok']} · ✗ {stats['fail']} · 输出都在 ./mdx-out/", style="muted")
    console.print(Panel(body, border_style=FAINT, padding=(0, 1), box=ROUNDED))
    return 0


# ---------------------------------------------------------------- 入口

def parser():
    p = argparse.ArgumentParser(
        prog="mdx", description=f"喵喵分子助手 v{__version__}（MDX · 终端 UI）")
    p.add_argument("--version", action="version", version=f"mdx {__version__}")
    p.add_argument("--no-animation", "--no-motion", action="store_true", help="动画保持静态")
    p.add_argument("--no-cat", action="store_true", help="隐藏猫猫")
    p.add_argument("--plain", action="store_true", help="无颜色、无猫猫、无动画")
    p.add_argument("--fps", type=float, default=6, help="任务刷新率 1–12（默认 6）")
    sub = p.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="直接执行一个工具（无交互，适合作业脚本）")
    run_p.add_argument("tool", choices=sorted(BY_ID))
    run_p.add_argument("--project", required=True, help="数据目录")
    run_p.add_argument("--params", default="", help='JSON 参数，例如 \'{"count": 3}\'')
    run_p.add_argument("--output", default="", help="输出目录（默认 <数据目录旁>/mdx-out/<tool>-<时间>）")

    sub.add_parser("tools", help="列出全部工具")
    sub.add_parser("chat", help="进入交互助手（默认）")

    cat_p = sub.add_parser("cat", help="看猫猫表情")
    cat_p.add_argument("state", nargs="?", default="all", choices=["all", *FACES])

    sub.add_parser("gallery", help="打印全部猫猫表情")

    inst_p = sub.add_parser("install", help="把 mdx 启动器安装到 bin 目录（自动扫描推荐位置）")
    inst_p.add_argument("--dir", default="", help="手动指定 bin 目录")
    inst_p.add_argument("--dry-run", action="store_true", help="只显示将安装到哪，不写文件")

    sub.add_parser("uninstall", help="删除 bin 启动器与安装记录")
    up_p = sub.add_parser("update", help="从远端 git 拉取更新")
    up_p.add_argument("--reinstall", action="store_true", help="更新后重新 pip install -e")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    no_motion = args.no_animation or os.environ.get("MDX_NO_ANIMATION") == "1"
    no_cat = args.no_cat or os.environ.get("MDX_NO_CAT") == "1"
    from .ui import TerminalUI, UIOptions
    ui = TerminalUI(UIOptions(animate=not no_motion, cat=not no_cat, plain=args.plain,
                              fps=min(max(args.fps, 1), 12)))
    try:
        if args.command == "run":
            try:
                params = json.loads(args.params) if args.params else {}
                params = validate(args.tool, params)
            except (ValueError, TypeError) as exc:
                note(f"参数错误：{exc}", state="error")
                return 1
            flags = {"no_ask": True}  # run 是无交互模式，不弹确认
            execute(ui, args.tool, params, project=args.project,
                    output=args.output or None, session_flags=flags)
            if flags.get("interrupted"):
                return 130
            return 1 if flags.get("last_fail") else 0
        elif args.command == "tools":
            print_tools(ui)
        elif args.command == "install":
            install(args.dir or None, args.dry_run, ui)
        elif args.command == "uninstall":
            uninstall(ui)
        elif args.command == "update":
            update(ui, args.reinstall)
        elif args.command == "cat":
            if args.state == "all":
                for name in FACES:
                    color, art = face(name)
                    console.print(f"[muted]{name:<10}[/]")
                    console.print(art, style=color)
                    console.print()
            else:
                color, art = face(args.state)
                console.print(art, style=color)
        elif args.command == "gallery":
            for name in FACES:
                color, art = face(name)
                console.print(f"[muted]{name:<10}[/]")
                console.print(art, style=color)
                console.print()
        else:
            return interactive(ui) or 0
        return 0
    except KeyboardInterrupt:
        note("已中断。", state="warning")
        return 130
