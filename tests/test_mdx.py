import json
from pathlib import Path

import pytest

from mdx import cli
from mdx.catalog import validate, TOOLS
from mdx.operations import audit_outcar, discover

OUTCAR_OK = """external program\n NELM = 60\n Iteration 1( 12)\n Iteration 2( 30)\n General timing and accounting:\n"""
OUTCAR_STUCK = """ NELM = 60\n Iteration 1( 60)\n"""


# ---------------- 工具契约 ----------------

def test_validate_rejects_unknown_tool():
    with pytest.raises(ValueError):
        validate("nope", {})


def test_validate_defaults_and_int_coercion():
    result = validate("perturb", {"count": 3})
    assert result["count"] == 3 and result["seed"] == 42


def test_validate_rejects_out_of_range_and_unknown_keys():
    for bad in ({"count": 0}, {"count": 1.5}, {"nonsense": 1}):
        with pytest.raises(ValueError):
            validate("perturb", bad)


def test_every_tool_contract_validates_with_defaults():
    for tool in TOOLS:
        assert isinstance(validate(tool["id"], {}), dict)


# ---------------- 完整性检查与文件发现 ----------------

def test_audit_outcar(tmp_path):
    ok = tmp_path / "OK"
    ok.mkdir()
    (ok / "OUTCAR").write_text(OUTCAR_OK, encoding="utf-8")
    (ok / "CONTCAR").write_text("stuffed", encoding="utf-8")
    report = audit_outcar(ok / "OUTCAR")
    assert report["completed"] and report["last_iteration"] == 30 and not report["issues"]

    bad = tmp_path / "BAD"
    bad.mkdir()
    (bad / "OUTCAR").write_text(OUTCAR_STUCK, encoding="utf-8")
    report = audit_outcar(bad / "OUTCAR")
    assert not report["completed"]
    assert "最后电子步达到 NELM" in report["issues"]
    assert "缺少 CONTCAR" in report["issues"]


def test_discover_skips_hidden_dirs(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "POSCAR").write_text("x", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "POSCAR").write_text("x", encoding="utf-8")
    found = {p.relative_to(tmp_path).as_posix() for p, _ in discover(tmp_path)}
    assert found == {"sub/POSCAR"}


# ---------------- 助手解析 ----------------

def test_parse_slash_command():
    parsed = cli.parse_command("/audit")
    assert parsed["tool"]["id"] == "audit"


def test_parse_chinese_keyword():
    assert cli.parse_command("帮我检查一下收敛")["tool"]["id"] == "audit"
    assert cli.parse_command("抽帧间隔10")["tool"]["id"] == "extract"


def test_parse_quit_and_unknown():
    assert cli.parse_command("/q") == {"quit": True}
    assert cli.parse_command("/nope")["tool"] is None
    assert cli.parse_command("随便说点啥")["tool"] is None


# ---------------- 安装与更新 ----------------

def test_install_dry_run_writes_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "CONFIG_PATH", tmp_path / "config.json")
    cli.install(str(tmp_path / "bin"), dry_run=True)
    assert not (tmp_path / "bin").exists() or not any((tmp_path / "bin").iterdir())
    assert "dry-run" in capsys.readouterr().out


def test_install_creates_launcher_and_config(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "CONFIG_DIR", tmp_path / ".mdx")
    monkeypatch.setattr(cli, "CONFIG_PATH", tmp_path / ".mdx" / "config.json")
    cli.install(str(tmp_path / "bin"))
    launcher = tmp_path / "bin" / ("mdx.bat" if cli.os.name == "nt" else "mdx")
    assert launcher.exists()
    config = json.loads((tmp_path / ".mdx" / "config.json").read_text(encoding="utf-8"))
    assert Path(config["bin"]) == launcher
    assert str(Path(config["root"]).resolve()) == str(cli.project_root())
    body = launcher.read_text(encoding="utf-8")
    assert "-m mdx" in body


def test_uninstall_removes_launcher(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "CONFIG_DIR", tmp_path / ".mdx")
    monkeypatch.setattr(cli, "CONFIG_PATH", tmp_path / ".mdx" / "config.json")
    cli.install(str(tmp_path / "bin"))
    cli.uninstall()
    assert not (tmp_path / ".mdx" / "config.json").exists()


def test_update_fails_cleanly_outside_git(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "project_root", lambda: tmp_path)
    with pytest.raises(SystemExit):
        cli.update()


# ---------------- 字符猫 UI ----------------

def test_cat_canvas_fixed_footprint():
    from mdx.cat import HEIGHT, WIDTH, MOTIONS
    for motion in MOTIONS.values():
        for frame in motion.frames:
            assert len(frame) == HEIGHT
            assert all(len(row) == WIDTH for row in frame)
            assert all(row.isascii() for row in frame)


def test_get_motion_unknown_state():
    from mdx.cat import get_motion
    with pytest.raises(ValueError):
        get_motion("dancing")


def test_terminal_ui_card_noninteractive():
    from mdx.ui import TerminalUI, UIOptions
    ui = TerminalUI(UIOptions(plain=True))
    table = ui.card("running", "demo", detail="d", meta="m", completed=1, total=2)
    assert table is not None


def test_task_lifecycle_success_and_error(capsys):
    from mdx.ui import TerminalUI, UIOptions
    ui = TerminalUI(UIOptions(plain=True))
    with ui.task("demo", state="running", total=2) as task:
        task.update(completed=1)
        task.log("step")
        task.finish(state="success", title="好了")
    out = capsys.readouterr().out
    assert "好了" in out
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        pass
    try:
        with ui.task("bad", state="running"):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    out = capsys.readouterr().out
    assert "boom" in out


def test_install_still_prints_dry_run(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "CONFIG_PATH", tmp_path / "config.json")
    cli.install(str(tmp_path / "bin"), dry_run=True)
    assert "dry-run" in capsys.readouterr().out


# ---------------- Tab 补全 ----------------

def complete_text(text):
    from prompt_toolkit.document import Document
    completer = cli.MDXCompleter()
    doc = Document(text, len(text))
    return [c.text for c in completer.get_completions(doc, None)]


def test_complete_commands_by_prefix():
    assert "/audit" in complete_text("/au")
    assert {"/audit", "/tools", "/cat"} <= set(complete_text("/"))
    assert complete_text("/zombie") == []


def test_complete_subcommands():
    assert "success" in complete_text("/cat ")
    assert "success" in complete_text("/cat s")
    assert "on" in complete_text("/motion ")


def test_complete_paths_after_tool():
    home = Path.home()
    fragment = f"{home}/AppData/Local/Temp/md"
    res = complete_text(f"/audit {fragment}")
    assert any("mdx" in fragment + r for r in res), res


def test_complete_paths_directly():
    fragment = str(Path.home() / "AppData/Local/Temp/md")
    res = complete_text(fragment)
    assert any("mdx" in fragment + r for r in res), res


def test_command_completions_have_meta():
    from prompt_toolkit.document import Document
    completer = cli.MDXCompleter()
    doc = Document("/aud", 4)
    item = next(iter(completer.commands.get_completions(doc, None)))
    assert item.text == "/audit" and "计算完整性检查" in (item.display_meta_text or "")


# ---------------- 窄窗口防破版 ----------------

def test_all_faces_ascii_and_narrow():
    # 宽字符在 CJK 终端是双宽，会把面板撑到跨行撕裂
    from mdx.theme import FACES
    for name, (color, art) in FACES.items():
        assert art.isascii(), f"{name} 含非 ASCII 字符"
        for line in art.splitlines():
            assert len(line) <= 12, f"{name} 行太宽: {line!r}"


def test_welcome_card_and_cat_card_render_at_60_cols(capsys):
    # 60 列窄终端下面板边框必须保持完整（每行等宽、首尾为边框）
    from mdx import cli
    from mdx.theme import console
    console.width = 60
    try:
        with console.capture() as capture:
            cli.welcome_card()
            cli.cat_says("success", "搞定喵～")
    finally:
        console.width = None
    out = capture.get()
    assert out
    for line in out.splitlines():
        # ASCII 边框：行首行尾必须配对，不允许内容越过边框
        if line.startswith("+"):
            assert line.endswith("+"), repr(line)
        elif line.startswith("|"):
            assert line.endswith("|"), repr(line)
