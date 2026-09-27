"""Reusable status API. The UI consumes CPU-side snapshots, never GPU tensors."""
from __future__ import annotations
from dataclasses import dataclass
import math
import os
from pathlib import Path
import threading
import time
from typing import Any

from rich.console import Console, ConsoleOptions, RenderResult, Group
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from . import __version__
from .cat import WIDTH, get_motion

BRAND = "#D97757"
THEME = Theme({
    "brand": f"bold {BRAND}", "cat": BRAND, "muted": "dim",
    "ok": "green", "warning": "yellow", "error": "red",
})
STATE_STYLE = {"success": "ok", "warning": "warning", "error": "error", "cancelled": "muted"}
STATE_MARK = {"success": "+", "warning": "!", "error": "x", "cancelled": "-", "paused": "="}


def safe(value: Any) -> str:
    """Render paths/messages literally; disallow control-sequence injection."""
    return "".join(c if c.isprintable() else " " for c in str(value))


@dataclass(frozen=True)
class UIOptions:
    animate: bool = True
    cat: bool = True
    plain: bool = False
    fps: float = 8

    def __post_init__(self) -> None:
        if not math.isfinite(self.fps) or not 1 <= self.fps <= 12:
            raise ValueError("fps must be between 1 and 12")


class TerminalUI:
    def __init__(self, options: UIOptions | None = None, console: Console | None = None):
        self.options = options or UIOptions()
        self.console = console or Console(
            theme=THEME, highlight=False, markup=False,
            no_color=self.options.plain or "NO_COLOR" in os.environ,
            force_terminal=False if self.options.plain else None,
        )
        self.console.push_theme(THEME)
        self._active: CatTask | None = None
        self.reaction: tuple[str, float] | None = None

    @property
    def interactive(self) -> bool:
        return self.console.is_terminal and not self.console.is_dumb_terminal and not self.options.plain

    @property
    def motion(self) -> bool:
        return self.interactive and self.options.animate

    def task(self, title: str, *, state: str = "running", total: float | None = None,
             detail: str = "", demo: bool = False) -> CatTask:
        return CatTask(self, title, state=state, total=total, detail=detail, demo=demo)

    def header(self) -> None:
        title = Text("MDX", style="brand")
        title.append(f" v{__version__}", style="muted")
        title.append("  Molecular Dynamics + MLP")
        self.console.print(title)
        self.console.print(Text("Cat UI edition | /demo  /cat  /doctor  /help", style="muted"))
        self.console.print()

    def react(self, state: str) -> None:
        """Schedule a short response in the next prompt; never delay a task."""
        get_motion(state)
        self.reaction = (state, time.monotonic())

    def note(self, message: str, *, state: str = "idle") -> None:
        get_motion(state)
        if state in {"success", "warning", "error", "cancelled"}:
            self.react(state)
        text = Text(f"{STATE_MARK.get(state, '.')} ", style=STATE_STYLE.get(state, "brand"))
        text.append(safe(message))
        self.console.print(text)

    def pairs(self, pairs: list[tuple[str, Any]]) -> None:
        table = Table.grid(padding=(0, 2), expand=False)
        table.add_column(style="muted")
        table.add_column(overflow="fold")
        for key, value in pairs:
            table.add_row(Text("  " + safe(key)), Text(safe(value)))
        self.console.print(table)

    def card(self, state: str, title: str, *, detail: str = "", meta: str = "",
             completed: float | None = None, total: float | None = None,
             elapsed: float = 0, phase_elapsed: float = 0, demo: bool = False,
             animate: bool = True) -> Table:
        """Pure rendering, usable by tests and adapters without starting a loop."""
        motion = get_motion(state)
        width = self.console.width
        title_line = Text()
        if demo:
            title_line.append("[UI DEMO] ", style="warning")
        title_line.append(f"{STATE_MARK.get(state, '.')} ", style=STATE_STYLE.get(state, "brand"))
        title_line.append(safe(title), style="bold")
        lines: list[Text] = [title_line, Text(safe(detail), style="muted")]
        if total is not None:
            n = min(max(completed or 0, 0), total)
            fraction = n / total
            if width >= 64:
                slots = 18
                fill = min(slots, int(fraction * slots))
                bar = Text("[", style="muted")
                bar.append("=" * fill, style="brand")
                bar.append("-" * (slots - fill) + "]", style="muted")
                bar.append(f" {fraction:6.1%}  {n:g}/{total:g}")
            else:
                bar = Text(f"{fraction:.0%}  {n:g}/{total:g}")
            lines.append(bar)
        else:
            lines.append(Text(""))
        lines.append(Text(safe(meta), style="muted"))
        lines.append(Text(f"{state} | {elapsed:.1f}s", style="muted"))
        table = Table.grid(padding=(0, 2), expand=False)
        if self.options.cat and not self.options.plain and width >= 64 and self.console.height >= 12:
            table.add_column(width=WIDTH, no_wrap=True)
            table.add_column(overflow="fold")
            frame = motion.at(phase_elapsed, animate)
            # One cell per column: wrapped metadata must never tear the cat apart.
            table.add_row(Text("\n".join(frame), style="cat"), Group(*lines))
        else:
            table.add_column(overflow="fold")
            if self.options.cat and not self.options.plain:
                table.add_row(Text(motion.face, style="cat"))
            for line in lines:
                if line.plain:
                    table.add_row(line)
        return table


class _TaskRenderable:
    def __init__(self, task: CatTask):
        self.task = task

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        yield self.task.render()


class CatTask:
    """One active task per TerminalUI. Exceptions propagate after UI cleanup.

    Call update with Python scalars from existing logging/progress boundaries.
    Do not call GPU .item()/.cpu() from the refresh callback. No such calls exist here.
    """
    def __init__(self, ui: TerminalUI, title: str, *, state: str,
                 total: float | None, detail: str, demo: bool):
        get_motion(state)
        if total is not None and (not math.isfinite(total) or total <= 0):
            raise ValueError("total must be positive and finite")
        self.ui = ui
        self.title = title
        self.detail = detail
        self.meta = ""
        self.state = state
        self.demo = demo
        self.completed = 0.0
        self.total = total
        self._start = 0.0
        self._phase_start = 0.0
        self._live: Live | None = None
        self._lock = threading.RLock()
        self._last_refresh = 0.0
        self._entered = False
        self._finished_state = "success"
        self._finished_title: str | None = None

    def __enter__(self) -> CatTask:
        if self.ui._active is not None:
            raise RuntimeError("MDX supports one active cat task per UI; update the existing task")
        if self._entered:
            raise RuntimeError("CatTask cannot be reused")
        self._entered = True
        self.ui._active = self
        self._start = self._phase_start = time.monotonic()
        try:
            if self.ui.interactive:
                self._live = Live(
                    _TaskRenderable(self), console=self.ui.console,
                    refresh_per_second=self.ui.options.fps,
                    auto_refresh=self.ui.options.animate, transient=True,
                    screen=False, vertical_overflow="crop",
                    redirect_stdout=True, redirect_stderr=True,
                )
                self._live.start(refresh=True)
            else:
                label = "[UI DEMO] " if self.demo else ""
                self.ui.note(label + self.title + (" | " + self.detail if self.detail else ""), state=self.state)
        except BaseException:
            try:
                if self._live:
                    self._live.stop()
            finally:
                self.ui._active = None
            raise
        return self

    def update(self, *, completed: float | None = None, advance: float | None = None,
               state: str | None = None, title: str | None = None,
               detail: str | None = None, meta: str | None = None) -> None:
        if not self._entered or self.ui._active is not self:
            raise RuntimeError("update() must run inside the task context")
        if completed is not None and advance is not None:
            raise ValueError("use completed or advance, not both")
        if state is not None:
            get_motion(state)
        for number in (completed, advance):
            if number is not None and (not math.isfinite(number) or number < 0):
                raise ValueError("progress values must be finite and nonnegative")
        with self._lock:
            n = self.completed if completed is None else float(completed)
            if advance is not None:
                n += advance
            self.completed = min(n, self.total) if self.total is not None else n
            if state is not None and state != self.state:
                self.state = state
                self._phase_start = time.monotonic()
            for attr, value in (("title", title), ("detail", detail), ("meta", meta)):
                if value is not None:
                    setattr(self, attr, value)
        # In reduced-motion mode refresh only on updates, at most 4 Hz.
        now = time.monotonic()
        if self._live and not self.ui.options.animate and now - self._last_refresh >= .25:
            self._last_refresh = now
            self._live.refresh()

    def log(self, message: str) -> None:
        self.ui.console.print(Text(safe(message)))

    def finish(self, *, state: str = "success", title: str | None = None) -> None:
        """Choose the normal-exit result. An actual exception always overrides it."""
        get_motion(state)
        with self._lock:
            self._finished_state = state
            self._finished_title = title

    def render(self) -> Table:
        with self._lock:
            now = time.monotonic()
            return self.ui.card(
                self.state, self.title, detail=self.detail, meta=self.meta,
                completed=self.completed, total=self.total,
                elapsed=now - self._start, phase_elapsed=now - self._phase_start,
                demo=self.demo, animate=self.ui.options.animate,
            )

    def __exit__(self, exc_type, exc, traceback) -> bool:
        try:
            if self._live:
                self._live.stop()
        finally:
            self.ui._active = None
        if exc_type is not None:
            interrupted = issubclass(exc_type, (KeyboardInterrupt, SystemExit))
            self.state = "cancelled" if interrupted else "error"
            label = "Cancelled" if interrupted else "Failed"
            self.title = f"{label}: {self.title}"
            self.detail = "Task interrupted." if interrupted else safe(exc)
            self.meta = ""
        else:
            self.state = self._finished_state
            self.title = self._finished_title or f"Completed: {self.title}"
        self.ui.react(self.state)
        elapsed = time.monotonic() - self._start
        if self.ui.interactive:
            self.ui.console.print(self.ui.card(
                self.state, self.title, detail=self.detail, meta=self.meta,
                completed=self.completed, total=self.total, elapsed=elapsed,
                demo=self.demo, animate=False,
            ))
            self.ui.console.print()
        else:
            label = "[UI DEMO] " if self.demo else ""
            self.ui.note(f"{label}{self.title} | {self.state} | {elapsed:.2f}s", state=self.state)
            if exc_type is not None and self.detail:
                self.ui.console.print(Text("  " + self.detail))
        return False
