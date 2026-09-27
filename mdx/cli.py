"""MDX 命令行界面：字符猫 UI（用户设计）+ 真实工具后端 + 自安装/自更新。

显示层来自 MDX_Cat_CLI 设计（TerminalUI / 字符猫动效 / #D97757 品牌色），
只替换显示，不改动科学计算与执行语义（见该设计 docs/INTEGRATION.md）。
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from . import __version__
from .catalog import BY_ID, TOOLS, validate
from .cat import MOTIONS, get_motion
from .operations import run as run_tool
from .ui import BRAND, TerminalUI, UIOptions

# 补全相关（prompt_toolkit 仅在交互 REPL 中导入使用）
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

RESPONSES = {
    "success": "完成了，干得漂亮。",
    "warning": "上面有需要留意的信息。",
    "error": "操作失败了，详情见上。",
    "cancelled": "已停止，随时开始下一条。",
    "paused": "还在这里，慢慢来。",
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
        if name in MOTIONS:
            return {"cat": name}
        return {"tool": BY_ID.get(name)}
    for tool_id, words in KEYWORDS.items():
        if any(word in input_ for word in words):
            return {"tool": BY_ID[tool_id]}
    return {"tool": None, "text": text}


def prompt_parameters(ui, tool, overrides=None):
    """逐项询问参数，回车取默认值；overrides 跳过对应项。"""
    overrides = overrides or {}
    params = {}
    if not tool["fields"]:
        return params
    ui.note(f"「{tool['name']}」参数（直接回车使用默认值）")
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
            ui.note(f"{spec['label']} 无效，使用默认值 {spec['default']}", state="warning")
            params[spec["key"]] = spec["default"]
    return params


# ---------------------------------------------------------------- 工具执行

def execute(ui, tool_id, params, project=None, output=None, ask=None):
    tool = BY_ID[tool_id]
    if project is None:
        project = (ask or input)("    数据目录（Tab 可补全路径）: ").strip()
    project = Path(project).expanduser().resolve()
    if not project.is_dir():
        ui.note(f"目录不存在：{project}", state="error")
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    output = Path(output).expanduser().resolve() if output else project.parent / f"mdx-{tool_id}-{stamp}"
    output.mkdir(parents=True, exist_ok=True)

    with ui.task(f"{tool['name']}", state="loading", detail=str(project)) as task:
        task.update(state="thinking", title="准备输入文件")

        def log(message):
            task.log(message)
            if "发现" in message:
                task.update(state="running", detail=message)

        error = None
        try:
            result = run_tool(tool_id, project, output, params, log, lambda: False)
        except (ValueError, InterruptedError) as exc:
            error = str(exc)
            task.finish(state="error", title=f"{tool['name']} 失败")
        except KeyboardInterrupt:
            task.finish(state="cancelled")
            return
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            task.finish(state="error", title=f"{tool['name']} 失败")
        else:
            task.finish(state="success", title=f"{tool['name']} 完成")
            task.detail = f"输出 → {output}"
            task.meta = f"{result['records']} 条记录已写入 manifest.json" + (
                f"；{result['issues']} 条有完整性提示" if result.get("issues") else "")
        if error:
            task.detail = error
            ui.note(error, state="error")


# ---------------------------------------------------------------- 清单与环境

def print_tools(ui, short=False):
    for group in ["计算检查", "结构准备", "数据处理"]:
        tools = [t for t in TOOLS if t["group"] == group]
        if not tools:
            continue
        ui.note(f"{group}", state="idle")
        rows = []
        for tool in tools:
            if short:
                rows.append((f"/{tool['id']}", tool["name"]))
            else:
                rows.append((f"/{tool['id']}  {tool['name']} [{tool['files']}]", tool["description"]))
        ui.pairs(rows)
    ui.console.print()


def show_env(ui):
    import importlib.util
    import platform
    ui.note("运行环境（本机实际值）")
    ui.pairs([
        ("Python", platform.python_version()),
        ("平台", platform.platform()),
        ("ASE", "已安装" if importlib.util.find_spec("ase") else "未安装（结构类工具不可用）"),
        ("NumPy", "已安装" if importlib.util.find_spec("numpy") else "未安装"),
        ("程序目录", str(project_root())),
        ("服务", "纯本地，不联网"),
    ])
    ui.console.print()


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
    existing = [c for c in bin_candidates() if c.is_dir() and os.access(c, os.W_OK)]
    if existing:
        return existing[0], "已存在的用户 bin 目录"
    for candidate in bin_candidates():
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate, "新建的用户 bin 目录"
        except OSError:
            continue
    ui.note("找不到可写的 bin 目录，请用 --dir 手动指定", state="error")
    raise SystemExit(1)


def launcher_body(bin_dir, python, root):
    if os.name == "nt":
        return (f'@echo off\r\nset "PYTHONPATH={root}"\r\n'
                f'@"{python}" -m mdx %*\r\n')
    return (f"#!/usr/bin/env bash\n"
            f"# MDX launcher — generated by `mdx install`, safe to delete\n"
            f'export PYTHONPATH="{root}"\n'
            f'exec "{python}" -m mdx "$@"\n')


def install(explicit_dir=None, dry_run=False, ui=None):
    ui = ui or TerminalUI(UIOptions(plain=not sys.stdout.isatty()))
    python = sys.executable
    root = str(Path(__file__).resolve().parent.parent)
    bin_dir, reason = choose_bin(ui, explicit_dir)
    name = "mdx.bat" if os.name == "nt" else "mdx"
    target = bin_dir / name
    in_path = any(p == bin_dir for p in (Path(p) for p in os.environ.get("PATH", "").split(os.pathsep)))

    ui.pairs([
        ("安装位置", f"{target}（{reason}）"),
        ("解释器", python),
        ("程序目录", f"{root}（启动器只指向这里，不复制、不安装包）"),
    ])
    if dry_run:
        ui.note("dry-run：未写入任何文件。", state="warning")
        return

    target.write_text(launcher_body(bin_dir, python, root), encoding="utf-8", newline="\n" if os.name != "nt" else None)
    if os.name != "nt":
        target.chmod(0o755)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    import datetime
    CONFIG_PATH.write_text(json.dumps(dict(
        bin=str(target), python=python, root=root,
        installed=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")),
        ensure_ascii=False, indent=2), encoding="utf-8")

    ui.note(f"已安装 → {target}", state="success")
    if in_path:
        ui.note("现在可以在任何目录直接运行：mdx")
    else:
        ui.note(f"{bin_dir} 不在 PATH 中。请加入 PATH，例如：", state="warning")
        if os.name == "nt":
            ui.console.print(f'    setx PATH "%PATH%;{bin_dir}"   然后重开终端')
        else:
            ui.console.print(f"    echo 'export PATH=\"$PATH:{bin_dir}\"' >> ~/.bashrc && source ~/.bashrc")
        ui.console.print(f"    或临时使用：{target}")
    ui.console.print()


def uninstall(ui=None):
    ui = ui or TerminalUI()
    if not CONFIG_PATH.exists():
        ui.note("未找到安装记录（~/.mdx/config.json）", state="error")
        raise SystemExit(1)
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    launcher = Path(config["bin"])
    launcher.unlink(missing_ok=True)
    CONFIG_PATH.unlink()
    ui.note(f"已删除 {launcher} 与安装记录；程序目录 {config['root']} 未动。", state="success")


# ---------------------------------------------------------------- 更新

def project_root():
    return Path(__file__).resolve().parent.parent


def update(ui=None, reinstall=False):
    ui = ui or TerminalUI(UIOptions(plain=not sys.stdout.isatty()))
    root = project_root()
    if not (root / ".git").exists():
        ui.note(f"{root} 不是 git 仓库，无法自动更新；请手动同步代码。", state="error")
        raise SystemExit(1)
    with ui.task("git pull", state="loading", detail=str(root)) as task:
        result = subprocess.run(["git", "pull", "--ff-only"], cwd=root, capture_output=True, text=True)
        task.log(result.stdout.strip() or result.stderr.strip())
        if result.returncode != 0:
            task.finish(state="error", title="git pull 失败")
            task.detail = "可能有本地改动或网络问题"
            return
        if "Already up to date" in result.stdout or "已经是最新的" in result.stdout:
            task.finish(state="success", title="已是最新版本")
            return
    if reinstall:
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(root), "--quiet"], check=False)
        ui.note("已重新以可编辑模式注册。")
    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if Path(config["root"]) != root or Path(config["python"]) != Path(sys.executable):
            install(ui=ui)
    ui.note("更新完成。", state="success")


# ---------------------------------------------------------------- 交互 REPL

COMPLETION_META = {f"/{t['id']}": f"{t['name']}（{t['files']}）" for t in TOOLS}
COMPLETION_META.update({"/cat": "看猫猫动效", "/tools": "工具清单", "/env": "运行环境",
                        "/motion": "动画开关", "/mascot": "猫开关", "/help": "帮助",
                        "/clear": "清屏", "/exit": "退出"})

COMPLETIONS = {**{f"/{t['id']}": None for t in TOOLS},
               "/tools": None, "/env": None, "/help": None, "/clear": None, "/exit": None,
               "/cat": list(MOTIONS), "/gallery": None,
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
            # 工具命令的参数位置、或直接输入路径 → 路径补全；否则命令补全
            if in_tool_arg or bare_path:
                yield from self.path_completions(word)
                return
            yield from self.commands.get_completions(document, complete_event)


def make_path_prompt(session):
    """带 Tab 路径补全的数据目录询问（复用 REPL 的输入框样式）。"""
    from prompt_toolkit.completion import PathCompleter
    completer = PathCompleter(expanduser=True, only_directories=True)
    def ask(prompt_text):
        return session.prompt([("class:brand", prompt_text)], completer=completer).strip()
    return ask


def interactive(ui, *, debug=False):
    if not sys.stdin.isatty() or not ui.interactive:
        ui.note("交互模式需要终端（TTY）。无交互请用：mdx run <工具> --project <目录>", state="warning")
        return 2
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.styles import Style

    no_color = "NO_COLOR" in os.environ or ui.console.no_color
    style = Style.from_dict({
        "brand": "bold" if no_color else f"bold {BRAND}",
        "cat": "" if no_color else BRAND,
        "muted": "" if no_color else "#888888",
        "inputmark": "bold" if no_color else f"bold {BRAND}",
    })
    session = PromptSession(history=InMemoryHistory(), completer=MDXCompleter(),
                            complete_while_typing=False, reserve_space_for_menu=3,
                            style=style, erase_when_done=True, mouse_support=False,
                            refresh_interval=.25 if ui.motion else 0)

    while True:
        start = time.monotonic()

        def message():
            elapsed = time.monotonic() - start
            state = "paused" if elapsed > 45 else "idle"
            phase = elapsed
            if ui.motion and ui.reaction is not None:
                previous, since = ui.reaction
                if time.monotonic() - since < 1.2:
                    state, phase = previous, time.monotonic() - since
            motion = get_motion(state)
            response = RESPONSES.get(state, "随时待命")
            info = [f"MDX v{__version__}", "分子模拟 · 结构准备 · 数据集构建",
                    str(Path.cwd()), response, "/tools  /cat  /env  /help"]
            pieces = []
            if ui.options.cat and ui.console.width >= 64 and ui.console.height >= 12:
                for i, row in enumerate(motion.at(phase, ui.options.animate)):
                    pieces.extend([("class:cat", row), ("", "  "),
                                   ("class:brand" if i == 0 else "class:muted", info[i]), ("", "\n")])
            else:
                if ui.options.cat:
                    pieces.append(("class:cat", motion.face + "  "))
                pieces.append(("class:brand", f"MDX v{__version__}\n"))
            pieces.append(("class:inputmark", "\nmdx ❯ "))
            return pieces

        try:
            line = session.prompt(message).strip()
        except KeyboardInterrupt:
            continue
        except EOFError:
            ui.note("再见。", state="cancelled")
            return 0
        if not line:
            continue
        ui.console.print(f"mdx ❯ {line}", style="brand")

        if line.startswith("/"):
            cmd = line.lstrip("/").split()[0]
            if cmd in {"exit", "quit", "q", "退出"}:
                ui.note("再见。", state="cancelled")
                return 0
            if cmd == "clear":
                ui.console.clear()
                continue
            if cmd == "help":
                print_tools(ui)
                continue
            if cmd == "tools":
                print_tools(ui)
                continue
            if cmd == "env":
                show_env(ui)
                continue
            if cmd in MOTIONS:
                from .demo import play_one
                play_one(ui, cmd)
                continue
            if cmd in {"motion", "mascot"}:
                tokens = line.split()
                if len(tokens) != 2 or tokens[1] not in {"on", "off"}:
                    ui.note(f"用法：/{cmd} on|off", state="warning")
                else:
                    from dataclasses import replace
                    key = "animate" if cmd == "motion" else "cat"
                    ui.options = replace(ui.options, **{key: tokens[1] == "on"})
                    ui.note(f"{cmd}: {tokens[1]}")
                continue

        parsed = parse_command(line)
        if parsed is None:
            continue
        if parsed.get("tool") is None:
            ui.note(f"没认出「{parsed.get('text', line)}」。/tools 查看全部命令。", state="warning")
            continue
        tool = parsed["tool"]
        tokens = line.split()
        inline_project = tokens[1] if len(tokens) > 1 else None
        params = prompt_parameters(ui, tool)
        ask = make_path_prompt(session) if inline_project is None else None
        execute(ui, tool["id"], params, project=inline_project, ask=ask)


# ---------------------------------------------------------------- 入口

def parser():
    p = argparse.ArgumentParser(prog="mdx", description=f"MDX 分子模拟命令行助手 v{__version__}（字符猫 UI）")
    p.add_argument("--version", action="version", version=f"mdx {__version__}")
    p.add_argument("--no-animation", "--no-motion", action="store_true", help="猫姿势保持静态")
    p.add_argument("--no-cat", action="store_true", help="隐藏猫")
    p.add_argument("--plain", action="store_true", help="无颜色、无猫、无动画")
    p.add_argument("--fps", type=float, default=8, help="任务刷新率 1–12（默认 8）")
    sub = p.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="直接执行一个工具（无交互）")
    run_p.add_argument("tool", choices=sorted(BY_ID))
    run_p.add_argument("--project", required=True, help="数据目录")
    run_p.add_argument("--params", default="", help='JSON 参数，例如 \'{"count": 3}\'')
    run_p.add_argument("--output", default="", help="输出目录（默认 数据目录旁 mdx-<tool>-<时间>）")

    sub.add_parser("tools", help="列出全部工具")
    sub.add_parser("chat", help="进入交互助手（默认）")

    cat_p = sub.add_parser("cat", help="预览猫猫动效")
    cat_p.add_argument("state", nargs="?", default="all", choices=["all", *MOTIONS])
    cat_p.add_argument("--seconds", type=float, default=2.4)

    sub.add_parser("gallery", help="打印全部静态猫姿势")

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
    ui = TerminalUI(UIOptions(animate=not no_motion, cat=not no_cat, plain=args.plain,
                              fps=min(max(args.fps, 1), 12)))
    try:
        if args.command == "run":
            try:
                params = json.loads(args.params) if args.params else {}
                params = validate(args.tool, params)
            except (ValueError, TypeError) as exc:
                ui.note(f"参数错误：{exc}", state="error")
                return 1
            execute(ui, args.tool, params, project=args.project, output=args.output or None)
        elif args.command == "tools":
            ui.note(f"MDX v{__version__} · 工具库（共 {len(TOOLS)} 个）")
            print_tools(ui)
        elif args.command == "install":
            install(args.dir or None, args.dry_run, ui)
        elif args.command == "uninstall":
            uninstall(ui)
        elif args.command == "update":
            update(ui, args.reinstall)
        elif args.command == "cat":
            from .demo import play
            play(ui, args.state, args.seconds)
        elif args.command == "gallery":
            from .demo import gallery
            gallery(ui)
        else:
            ui.note(f"{'MDX'} v{__version__} · 分子模拟命令行助手", state="idle")
            ui.console.print("字符猫 UI | /tools 查看工具 · /cat 看猫猫 · /env 环境 · /help 帮助", style="muted")
            ui.console.print()
            return interactive(ui) or 0
        return 0
    except KeyboardInterrupt:
        ui.note("已中断。", state="cancelled")
        return 130


if __name__ == "__main__":
    sys.exit(main())
