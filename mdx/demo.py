"""字符猫动效演示（/cat、/gallery），适配本包 TerminalUI。"""
import time

from .cat import MOTIONS, get_motion


def play_one(ui, state, seconds=2.4):
    """播放单个动效（交互终端下用 Live，否则打印静态帧）。"""
    motion = get_motion(state)
    if not ui.interactive:
        ui.console.print(motion.face, style="cat")
        return
    from rich.live import Live
    start = time.monotonic()
    def render():
        phase = time.monotonic() - start
        return ui.card(state, f"/cat {state}", detail=motion.description,
                       meta=f"{state} | {phase:.1f}s", phase_elapsed=phase, animate=ui.options.animate)
    with Live(render(), console=ui.console, refresh_per_second=ui.options.fps,
              transient=True, vertical_overflow="crop"):
        while time.monotonic() - start < seconds:
            time.sleep(1 / max(ui.options.fps, 1))
    ui.console.print(render())
    ui.console.print()


def play(ui, state="all", seconds=2.4):
    states = list(MOTIONS) if state == "all" else [state]
    for name in states:
        play_one(ui, name, seconds if not (state == "all" and name == "idle") else 3.2)


def gallery(ui):
    ui.note("全部静态姿势（字符猫 · #D97757）")
    for name, motion in MOTIONS.items():
        ui.console.print()
        rows = "\n".join(motion.frames[0])
        ui.console.print(f"{name:<10}", style="brand", end="")
        ui.console.print(rows, style="cat")
        ui.console.print(f"           {motion.description}", style="muted")
    ui.console.print()
