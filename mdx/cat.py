"""Hand-authored ASCII motion frames; every frame has the same cell footprint.

No image protocols, emoji, font files, GPU use, or external animation assets.
The cat stays warm orange; status text, not the entire cat, changes color.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

WIDTH = 22
HEIGHT = 5
Frame = tuple[str, ...]


def canvas(*lines: str) -> Frame:
    if len(lines) > HEIGHT or any(len(s) > WIDTH for s in lines):
        raise ValueError("Cat frame exceeds its fixed canvas")
    if any(not s.isascii() for s in lines):
        raise ValueError("Cat frames must be ASCII")
    return tuple(s.ljust(WIDTH) for s in lines) + (" " * WIDTH,) * (HEIGHT - len(lines))


@dataclass(frozen=True)
class Motion:
    frames: tuple[Frame, ...]
    fps: float
    description: str
    face: str  # Narrow-terminal fallback.

    def at(self, seconds: float, animate: bool = True) -> Frame:
        if not animate:
            return self.frames[0]
        t = max(0.0, seconds) if math.isfinite(seconds) else 0.0
        return self.frames[int(t * self.fps) % len(self.frames)]


I = canvas("", r"    /\_/\ ", r"   ( o.o )", r"    /   \__", r"   (u___u)_/")
IB = canvas("", r"    /\_/\ ", r"   ( -.- )", r"    /   \__", r"   (u___u)_/")
IT = canvas("", r"    /\_/\ ", r"   ( o.o )", r"    /   \_)", r"   (u___u)")
T1 = canvas("            ?", r"    /\_/\ ", r"   ( o.o )", r"    /  o\__", r"   (u___u)_/")
T2 = canvas("              ?", r"    /\_/\ ", r"   ( o.o )", r"    /o  \__", r"   (u___u)_/")
T3 = canvas("            ...", r"    /\_/\ ", r"   ( -.- )", r"    /  o\__", r"   (u___u)_/")
L1 = canvas("", r"    /\_/\ ", r"   ( o.o )", r"   o/   \__", r"    (___u)_/")
L2 = canvas("", r"    /\_/\ ", r"   ( o.o )", r"    /   \o_", r"   (u___)_/")
R1 = canvas("", r"        /\_/\ ", r"  ~____( o.o )", r" /     __ > /", r"(_/---(_/        ..")
R2 = canvas(r"         /\_/\ ", r"   ~____( o.o )", r"  /     __ > /", r" (_/---(_/      ...", "")
R3 = canvas("", r"        /\_/\ ", r"  ~____( o.o )", r" /     __ > /", r"  \_)---\_)       .")
R4 = canvas(r"       /\_/\ ", r" ~____( o.o )", r"/     __ > /", r" \_)---\_)     ....", "")
C1 = canvas("", r"    /\_/\    .-----.", r"   ( o.o )   | >_  |", r"    /u u\____|     |", r"   (_____)   '-----'")
C2 = canvas("", r"    /\_/\    .-----.", r"   ( o.o )   | >   |", r"    / u \_u__|     |", r"   (_____)   '-----'")
C3 = canvas("", r"    /\_/\    .-----.", r"   ( -.- )   | >_  |", r"    /u  \__u_|     |", r"   (_____)   '-----'")
S1 = canvas("", r"    /\_/\ ", r"   ( ^.^ )", r"   o/   \o", r"    (___)~")
S2 = canvas(r"    /\_/\   *", r"   ( ^.^ )", r"  \o     o/", r"    (___)~", "")
S3 = canvas(r" *  /\_/\ ", r"   ( ^.^ )", r"   o/   \o", r"    (___)~", "")
W1 = canvas("             !", r"    /\_,/", r"   ( o.o )", r"    /   \__", r"   (u___u)_/")
W2 = canvas("             !", r"    \,_/\ ", r"   ( o.o )", r"    /   \__", r"   (u___u)_/")
E1 = canvas("", r"   _/\_/\_", r"   ( ;.; )", r"    /   \__", r"   (u___u)_/")
E2 = canvas("", r"   _/\_/\_", r"   ( -.- )", r"    /   \__", r"   (u___u)_/")
P1 = canvas("           z", r"    /\_/\ ", r"   ( -.- )", r"    /   \__", r"   (u___u)_/")
P2 = canvas("           z Z", r"    /\_/\ ", r"   ( -.- )", r"    /   \__", r"   (u___u)_/")
P3 = canvas("           z Z z", r"    /\_/\ ", r"   ( -.- )", r"    /   \_)", r"   (u___u)")
X1 = canvas("", r"    /\_/\ ", r"   ( o.o )", r"   o/   \__", r"    (___u)_/")
X2 = canvas("", r"    /\_/\ ", r"   ( o.o )", r"  o /   \__", r"    (___u)_/")

MOTIONS: dict[str, Motion] = {
    "idle": Motion((I,) * 12 + (IT,) * 6 + (I,) * 4 + (IB, IB, I), 4, "Blink + tail swish", "(=o.o=)"),
    "thinking": Motion((T1, T1, T2, T2, T3, T1), 2, "Paw to chin + head movement", "(=o.o=)?"),
    "loading": Motion((L1, I, L2, I), 4, "Alternating front paws", "(=o.o=)~"),
    "running": Motion((R1, R2, R3, R4), 8, "Four-frame running gait", "~(=o.o=)>"),
    "training": Motion((C1, C2, C1, C2, C3, C2), 5, "Typing paws + blinking cursor", "(=o.o=)[>_]"),
    "success": Motion((S1, S2, S3, S2, S1, S1), 4, "Hop + raised paws", "(=^.^=)"),
    "warning": Motion((W1, W1, W1, W2, W2, W2), 2, "Attentive ears; no flashing", "(=o.o=)!"),
    "error": Motion((E1,) * 6 + (E2,), 2, "Drooped ears + slow blink", "(=;.;=)"),
    "paused": Motion((P1, P1, P2, P2, P3, P3), 2, "Sleeping + drifting z's", "(=-.-=)z"),
    "cancelled": Motion((X1, X2, X1, X2, I, I), 3, "Small goodbye wave", "(=o.o=)/"),
}


def get_motion(state: str) -> Motion:
    try:
        return MOTIONS[state]
    except KeyError as exc:
        raise ValueError(f"Unknown cat state {state!r}. Choose: {', '.join(MOTIONS)}") from exc
