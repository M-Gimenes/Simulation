"""
Visualizador de combate ASCII — tick a tick.

Uso:
    py viewer.py                           # matchup aleatório (canônico)
    py viewer.py rushdown grappler         # matchup específico
    py viewer.py rushdown grappler --delay 0.04
    py viewer.py --list                    # lista arquétipos disponíveis
    py viewer.py --evolved                 # usa resultado da última execução do AG
    py viewer.py --all                     # roda todos os 10 matchups em sequência
    py viewer.py --no-vs                   # pula a tela de apresentação

Ctrl+C → sai a qualquer momento.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from itertools import combinations
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.dirname(__file__))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from archetypes import ARCHETYPES, ArchetypeID, ARCHETYPE_ORDER
from character import Character
from individual import Individual
from combat import (
    FighterState, Action, _choose_action, _resolve_attack, _softmax,
)
from config import INITIAL_DISTANCE, MAX_DISTANCE, MAX_TICKS, MIN_DISTANCE


# ─── ANSI ────────────────────────────────────────────────────────────────────

def _enable_ansi_windows() -> None:
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(
            ctypes.windll.kernel32.GetStdHandle(-11), 7)

_enable_ansi_windows()

R    = "\033[91m";  G    = "\033[92m";  Y    = "\033[93m"
B    = "\033[94m";  M    = "\033[95m";  C    = "\033[96m"
W    = "\033[97m";  DIM  = "\033[2m";   BD   = "\033[1m"
RS   = "\033[0m";   CL   = "\033[2J\033[H";  DARK = "\033[90m"

_ANSI_RE = re.compile(r"\033\[[^m]*m")

def _vlen(s: str) -> int:
    return len(_ANSI_RE.sub("", s))

def _pad(s: str, w: int) -> str:
    return s + " " * max(0, w - _vlen(s))

def _rpad(s: str, w: int) -> str:
    return " " * max(0, w - _vlen(s)) + s

def _ctr(s: str, w: int) -> str:
    v = _vlen(s)
    left = max(0, (w - v) // 2)
    return " " * left + s + " " * max(0, w - v - left)


# ─── Layout constants ─────────────────────────────────────────────────────────

TW       = 78   # terminal frame width
ARENA_W  = 70   # arena interior width (between │ │ borders)
TOK      = 4    # fighter token width: [XX]
LOG_N    = 8    # entries shown in combat log


# ─── Archetype & action palettes ─────────────────────────────────────────────

_ACOLOR = {
    ArchetypeID.RUSHDOWN:     R,
    ArchetypeID.ZONER:        C,
    ArchetypeID.COMBO_MASTER: M,
    ArchetypeID.GRAPPLER:     Y,
    ArchetypeID.TURTLE:       G,
}

_ACT_COLOR = {
    Action.ATTACK:  R,
    Action.ADVANCE: Y,
    Action.RETREAT: B,
    Action.DEFEND:  G,
    None:           M,   # stunned
}

_ACT_ICON = {
    Action.ATTACK:  "[*]",
    Action.ADVANCE: "[>]",
    Action.RETREAT: "[<]",
    Action.DEFEND:  "[D]",
    None:           "[~]",
}

_ACT_NAME = {
    Action.ATTACK:  "ATAQUE ",
    Action.ADVANCE: "AVANCA ",
    Action.RETREAT: "RECUA  ",
    Action.DEFEND:  "DEFENDE",
    None:           "STUNNED",
}

ALIASES = {
    "zoner":    ArchetypeID.ZONER,    "z":    ArchetypeID.ZONER,
    "rushdown": ArchetypeID.RUSHDOWN, "rd":   ArchetypeID.RUSHDOWN,
    "combo":    ArchetypeID.COMBO_MASTER, "cm": ArchetypeID.COMBO_MASTER,
    "grappler": ArchetypeID.GRAPPLER, "grap": ArchetypeID.GRAPPLER, "g": ArchetypeID.GRAPPLER,
    "turtle":   ArchetypeID.TURTLE,   "t":    ArchetypeID.TURTLE,
}


# ─── Damage event ─────────────────────────────────────────────────────────────

@dataclass
class DamageEvent:
    tick:         int
    attacker_idx: int
    attacker:     str
    defender:     str
    damage:       float
    hp_before:    float
    hp_after:     float
    stun:         int
    ko:           bool


# ─── HP bar ───────────────────────────────────────────────────────────────────

def _hp_bar(pct: float, width: int = 22) -> str:
    filled = max(0, min(width, round(pct * width)))
    color  = G if pct > 0.60 else (Y if pct > 0.30 else R)
    return f"{color}{'█' * filled}{'░' * (width - filled)}{RS}"


# ─── Action probability recomputation ────────────────────────────────────────
# Mirrors the scoring logic in combat._choose_action to get per-action probs.

def _compute_probs(
    me:       FighterState,
    enemy:    FighterState,
    distance: float,
) -> List[float]:
    c, e = me.character, enemy.character
    dmg_me   = c.damage   / 100.0
    dmg_en   = e.damage   / 100.0
    def_me   = c.defense  / 100.0
    in_rng_me = 1.0 if distance <= c.range_ else 0.0
    in_rng_en = 1.0 if distance <= e.range_ else 0.0
    rdy_me  = 1.0 if me.attack_ready else 0.0
    rdy_en  = 1.0 if (enemy.attack_ready and not enemy.is_stunned) else 0.0
    me_hit   = in_rng_me * rdy_me
    en_hit   = in_rng_en * rdy_en
    my_dmg   = me_hit  * dmg_me
    raw_risk = en_hit  * dmg_en * (1.0 - def_me)

    s_atk = (-1e9 if not me.attack_ready
             else c.w_attack * me_hit * (my_dmg - raw_risk))
    s_adv = (-1e9 if in_rng_me
             else c.w_advance * (1.0 - me_hit)
                  * (dmg_me - dmg_en * (1.0 - def_me) + c.w_aggressiveness))
    s_ret = c.w_retreat * en_hit * (raw_risk - my_dmg)
    s_def = c.w_defend  * en_hit * (raw_risk * 0.8)
    return _softmax([s_atk, s_adv, s_ret, s_def])


def _prob_inline(probs: List[float], tag: str, col: str) -> str:
    """Compact single-line probability display: RD[ATK:44% ADV:5% RET:3% DEF:48%]"""
    parts = " ".join([
        f"{R}ATK:{probs[0]:.0%}{RS}",
        f"{Y}ADV:{probs[1]:.0%}{RS}",
        f"{B}RET:{probs[2]:.0%}{RS}",
        f"{G}DEF:{probs[3]:.0%}{RS}",
    ])
    return f"{col}{BD}{tag}{RS}[{parts}]"


# ─── Arena ────────────────────────────────────────────────────────────────────

def _arena_lines(
    fighters:   List[FighterState],
    distance:   float,
    actions:    List[Optional[int]],
    hit_flashes: List[Tuple[int, float]],   # [(attacker_idx, dmg), ...]
) -> List[str]:
    """
    Build 3 arena content rows (no border):

      Row 0  air   — fighter heads (o / *o*), hit-flash damage numbers
      Row 1  field — fighter tokens [XX]/{XX}, range zones (> < !), stun sparks
      Row 2  floor — ─ ground line

    Range zones:
      >  yellow  — A's attack range extending right of A's token
      <  cyan    — B's attack range extending left of B's token
      !  red     — overlap: both fighters are in each other's range
    """
    W = ARENA_W

    char_a = fighters[0].character
    char_b = fighters[1].character

    # ── Pixel mapping ───────────────────────────────────────────────────────
    # A is always on the left, B on the right.
    # Both converge toward the center as distance shrinks.
    half_px = max(TOK + 2, int(distance / MAX_DISTANCE * (W - 4) / 2))
    ctr     = W // 2
    a_left  = max(0, ctr - half_px)
    b_left  = min(W - TOK, ctr + half_px - TOK + 1)
    b_left  = max(b_left, a_left + TOK + 2)   # never overlap

    # ── Range extents in pixels ─────────────────────────────────────────────
    rng_a_px    = max(0, int(char_a.range_ / MAX_DISTANCE * W))
    rng_b_px    = max(0, int(char_b.range_ / MAX_DISTANCE * W))
    rng_a_end   = min(W - 1, a_left + TOK + rng_a_px - 1)   # A's rightmost range pixel
    rng_b_start = max(0,     b_left - rng_b_px)              # B's leftmost range pixel

    # ── Token strings ────────────────────────────────────────────────────────
    na = char_a.name[:2].upper()
    nb = char_b.name[:2].upper()
    tok_a = "{" + na + "}" if actions[0] is None else "[" + na + "]"
    tok_b = "{" + nb + "}" if actions[1] is None else "[" + nb + "]"

    # ── Build char arrays ────────────────────────────────────────────────────
    air   = [" "] * W
    field = [" "] * W
    floor = ["─"] * W

    # Range zones (drawn first; tokens will overwrite)
    for x in range(a_left + TOK, rng_a_end + 1):
        if x < W: field[x] = ">"
    for x in range(rng_b_start, b_left):
        if x < W: field[x] = "<"
    # Overlap zone
    ol_s = max(a_left + TOK, rng_b_start)
    ol_e = min(rng_a_end + 1, b_left)
    for x in range(ol_s, ol_e):
        if x < W: field[x] = "!"

    # Stun "sparks" above stunned fighters (on field row flanking the token)
    if actions[0] is None:
        for dx, ch in enumerate("~"):
            x = a_left + TOK
            if x + dx < W: field[x + dx] = ch
    if actions[1] is None:
        for dx, ch in enumerate("~"):
            x = b_left - 1
            if x + dx < W: field[x + dx] = ch

    # Fighter tokens (overwrite range zone)
    for k, ch in enumerate(tok_a):
        if a_left + k < W: field[a_left + k] = ch
    for k, ch in enumerate(tok_b):
        if b_left + k < W: field[b_left + k] = ch

    # Heads on air row
    head_a = "*o*" if actions[0] is None else " o "
    head_b = "*o*" if actions[1] is None else " o "
    for k, ch in enumerate(head_a):
        if a_left + k < W: air[a_left + k] = ch
    for k, ch in enumerate(head_b):
        if b_left + k < W: air[b_left + k] = ch

    # Hit-flash numbers on air row (between the two fighters)
    gap_start = a_left + TOK
    gap_end   = b_left - 1
    gap_ctr   = (gap_start + gap_end) // 2
    for att_idx, dmg in hit_flashes:
        flash = f"-{dmg:.0f}!"
        flen  = len(flash)
        if att_idx == 0:   # A hit B → flash near B's side of the gap
            fx = max(gap_start, gap_end - flen)
        else:               # B hit A → flash near A's side of the gap
            fx = gap_start
        fx = max(0, min(W - flen, fx))
        for k, ch in enumerate(flash):
            if 0 <= fx + k < W:
                air[fx + k] = ch

    # ── Colorize ─────────────────────────────────────────────────────────────
    col_a  = _ACT_COLOR.get(actions[0], W)
    col_b  = _ACT_COLOR.get(actions[1], W)
    arc_a  = _ACOLOR.get(char_a.archetype.id, W)
    arc_b  = _ACOLOR.get(char_b.archetype.id, W)
    hcol_a = M if actions[0] is None else arc_a
    hcol_b = M if actions[1] is None else arc_b

    # Determine which air-row positions carry a hit-flash char
    flash_px: set = set()
    for att_idx, dmg in hit_flashes:
        flash = f"-{dmg:.0f}!"
        flen  = len(flash)
        gap_start2 = a_left + TOK
        gap_end2   = b_left - 1
        if att_idx == 0:
            fx = max(gap_start2, gap_end2 - flen)
        else:
            fx = gap_start2
        fx = max(0, min(W - flen, fx))
        for k in range(flen):
            flash_px.add(fx + k)

    def colorize(arr: List[str], row: int) -> str:
        out = []
        for x, ch in enumerate(arr):
            in_ta = (a_left <= x < a_left + TOK) and row == 1
            in_tb = (b_left <= x < b_left + TOK) and row == 1
            in_ha = (a_left <= x < a_left + len(head_a)) and row == 0
            in_hb = (b_left <= x < b_left + len(head_b)) and row == 0
            in_ra = (a_left + TOK <= x <= rng_a_end) and row == 1 and not in_tb
            in_rb = (rng_b_start  <= x <  b_left)    and row == 1 and not in_ta
            in_ov = in_ra and in_rb
            is_fl = (row == 0 and x in flash_px and ch != " ")

            if   in_ta:              color = BD + col_a
            elif in_tb:              color = BD + col_b
            elif in_ha:              color = BD + hcol_a
            elif in_hb:              color = BD + hcol_b
            elif is_fl:              color = BD + Y
            elif in_ov:              color = BD + R
            elif in_ra:              color = Y
            elif in_rb:              color = C
            elif ch == "─":          color = DARK
            elif ch == " ":          color = ""
            else:                    color = DARK

            out.append(f"{color}{ch}{RS}" if color else ch)
        return "│" + "".join(out) + "│"

    return [colorize(air, 0), colorize(field, 1), colorize(floor, 2)]


# ─── Single-tick render ────────────────────────────────────────────────────────

def _render(
    tick:        int,
    fighters:    List[FighterState],
    distance:    float,
    actions:     List[Optional[int]],
    events:      List[DamageEvent],
    hit_flashes: List[Tuple[int, float]],
) -> None:
    print(CL, end="")

    arc_a = _ACOLOR.get(fighters[0].character.archetype.id, W)
    arc_b = _ACOLOR.get(fighters[1].character.archetype.id, W)
    names = [f.character.name for f in fighters]

    # ── Header ──────────────────────────────────────────────────────────────
    title   = f"{BD}{arc_a}{names[0]}{RS} {BD}{W}vs{RS} {BD}{arc_b}{names[1]}{RS}"
    tick_s  = f"{DARK}Tick {BD}{tick:04d}{RS}{DARK}/{MAX_TICKS:04d}{RS}"
    prog    = int(tick / MAX_TICKS * 20)
    prog_s  = f"{DARK}[{BD}{'█'*prog}{'░'*(20-prog)}{RS}{DARK}]{RS}"
    print(f"{BD}{'═'*TW}{RS}")
    print(f"  {_pad(title, TW - 28)}{prog_s}  {tick_s}")
    print(f"{BD}{'═'*TW}{RS}\n")

    # ── HP bars ─────────────────────────────────────────────────────────────
    for i, f in enumerate(fighters):
        col   = _ACOLOR.get(f.character.archetype.id, W)
        pct   = f.hp_pct
        bar   = _hp_bar(pct, 22)
        name_s = f"{BD}{col}{f.character.name:<15}{RS}"
        pct_col = G if pct > 0.6 else (Y if pct > 0.3 else R + BD)
        pct_s  = f"{pct_col}{pct:5.1%}{RS}"
        hp_s   = f"{DARK}{f.hp:6.1f}/{f.hp_max:.0f}{RS}"
        print(f"  {name_s}  {bar}  {pct_s}  {hp_s}")
    print()

    # ── Arena ────────────────────────────────────────────────────────────────
    bdr   = "─" * (ARENA_W + 2)
    arena = _arena_lines(fighters, distance, actions, hit_flashes)
    print(f"  {DARK}┌{bdr}┐{RS}")
    for ln in arena:
        print(f"  {ln}")
    print(f"  {DARK}└{bdr}┘{RS}")

    # ── Distance & range status ──────────────────────────────────────────────
    in_a  = distance <= fighters[0].character.range_
    in_b  = distance <= fighters[1].character.range_
    tag_a = names[0][:2].upper()
    tag_b = names[1][:2].upper()
    dist_s = f"{DARK}dist:{RS}{BD}{distance:5.1f}{RS}"
    ra_s = (f"{R}{BD}!! {tag_a} IN RANGE{RS}"
            if in_a else f"{DARK}   {tag_a} out of range{RS}")
    rb_s = (f"{R}{BD}!! {tag_b} IN RANGE{RS}"
            if in_b else f"{DARK}   {tag_b} out of range{RS}")
    # Arena legend
    legend = (f"{DARK}>{RS}{Y}range-A{RS}  "
              f"{DARK}!{RS}{R}{BD}overlap{RS}  "
              f"{DARK}<{RS}{C}range-B{RS}")
    print(f"  {dist_s}   {ra_s}   {rb_s}")
    print(f"  {legend}\n")

    # ── Action + status panels ───────────────────────────────────────────────
    def _panel(idx: int) -> str:
        act  = actions[idx]
        f    = fighters[idx]
        col  = _ACT_COLOR.get(act, M)
        icon = _ACT_ICON.get(act, "[?]")
        aname= _ACT_NAME.get(act, "???    ")
        cd   = f.cooldown_remaining
        st   = f.stun_remaining
        cd_s = f"{G}{BD}rdy{RS}" if cd == 0 else f"{Y}{cd:2d}t{RS}"
        st_s = f"{M}{BD}{st:2d}{RS}" if st > 0 else f"{DARK}--{RS}"
        return f"{col}{BD}{icon} {aname}{RS}  {DARK}CD:{RS}{cd_s}  {DARK}STN:{RS}{st_s}"

    half = TW // 2 - 1
    print(f"  {_pad(_panel(0), half)}  {_panel(1)}")

    # ── Softmax probability breakdown ────────────────────────────────────────
    def _prob_str(idx: int) -> str:
        f   = fighters[idx]
        col = _ACOLOR.get(f.character.archetype.id, W)
        tag = f.character.name[:2].upper()
        if f.is_stunned:
            return f"{M}{BD}{tag}[      STUNNED      ]{RS}"
        pr = _compute_probs(f, fighters[1 - idx], distance)
        return _prob_inline(pr, tag, col)

    print(f"  {_pad(_prob_str(0), half)}  {_prob_str(1)}\n")

    # ── Character stats ──────────────────────────────────────────────────────
    def _stat_row(char: Character, col: str) -> str:
        wait = round((100.0 - char.cooldown) / 10.0)
        tag  = char.name[:2].upper()
        return (
            f"  {col}{BD}{tag}{RS}"
            f"  {DARK}dmg{RS}={BD}{char.damage:3.0f}{RS}"
            f"  {DARK}wait{RS}={BD}{wait}t{RS}"
            f"  {DARK}spd{RS}={BD}{char.speed:3.0f}{RS}"
            f"  {DARK}rng{RS}={BD}{char.range_:3.0f}{RS}"
            f"  {DARK}def{RS}={BD}{char.defense:3.0f}{RS}"
            f"  {DARK}stun{RS}={BD}{char.stun:3.0f}{RS}"
            f"  {DARK}rec{RS}={BD}{char.recovery:3.0f}{RS}"
        )

    print(_stat_row(fighters[0].character, arc_a))
    print(_stat_row(fighters[1].character, arc_b))
    print()

    # ── Combat log ───────────────────────────────────────────────────────────
    print(f"  {DARK}── Combat Log {'─'*38}{RS}")
    recent = events[-LOG_N:]
    if not recent:
        print(f"  {DARK}  (sem dano ainda…){RS}")
    for ev in recent:
        atk_col = _ACOLOR.get(fighters[ev.attacker_idx].character.archetype.id, W)
        stun_s  = f" {M}[stun×{ev.stun}]{RS}" if ev.stun   else ""
        ko_s    = f" {R}{BD}[ KO! ]{RS}"        if ev.ko    else ""
        arrow   = "-->>--" if ev.attacker_idx == 0 else "--<<--"
        hp_col  = R if ev.hp_after < 0.3 else (Y if ev.hp_after < 0.6 else DARK)
        print(
            f"  {DARK}t{ev.tick:04d}{RS}  "
            f"{atk_col}{BD}{ev.attacker:<14}{RS}"
            f"{DARK}{arrow}{RS}  "
            f"{R}{BD}-{ev.damage:5.1f}hp{RS}  "
            f"{DARK}{ev.defender}: {RS}"
            f"{hp_col}{ev.hp_before:.0%}→{ev.hp_after:.0%}{RS}"
            f"{stun_s}{ko_s}"
        )
    print(f"  {DARK}{'─'*54}{RS}")


# ─── VS / pre-fight screen ────────────────────────────────────────────────────

def _render_vs(char_a: Character, char_b: Character, delay: float = 1.5) -> None:
    col_a = _ACOLOR.get(char_a.archetype.id, W)
    col_b = _ACOLOR.get(char_b.archetype.id, W)

    def _stat_block(char: Character) -> List[str]:
        wait = round((100.0 - char.cooldown) / 10.0)
        return [
            f"HP    = {char.hp:.0f}",
            f"Dano  = {char.damage:.0f}   Espera = {wait}t",
            f"Vel   = {char.speed:.0f}   Alcance= {char.range_:.0f}",
            f"Def   = {char.defense:.0f}   Stun   = {char.stun:.0f}",
            f"Recup = {char.recovery:.0f}",
        ]

    print(CL, end="")
    print(f"\n{BD}{'═'*TW}{RS}")
    print(_ctr(f"{BD}{W}* * *  BATALHA!  * * *{RS}", TW))
    print(f"{BD}{'═'*TW}{RS}\n")

    HL = TW // 2 - 3
    desc_a = char_a.archetype.description[:HL - 4]
    desc_b = char_b.archetype.description[:HL - 4]

    print(f"  {_ctr(f'{col_a}{BD}{char_a.name}{RS}', HL)}    "
          f"{_ctr(f'{col_b}{BD}{char_b.name}{RS}', HL)}")
    print(f"  {'─'*HL}    {'─'*HL}")

    blk_a = _stat_block(char_a)
    blk_b = _stat_block(char_b)
    for la, lb in zip(blk_a, blk_b):
        print(f"  {col_a}{_pad(la, HL)}{RS}    {col_b}{lb}{RS}")

    print(f"\n  {DARK}{desc_a}…{RS}")
    print(f"  {DARK}{desc_b}…{RS}")

    print(f"\n{BD}{'═'*TW}{RS}")
    print(_ctr(f"{DARK}a combater em {delay:.1f}s…{RS}", TW))
    print()
    time.sleep(delay)


# ─── End screen ───────────────────────────────────────────────────────────────

def _render_end(
    winner_idx: int,
    fighters:   List[FighterState],
    ticks:      int,
    ko:         bool,
    events:     List[DamageEvent],
) -> None:
    print(CL, end="")
    reason = "K.O.!" if ko else f"TEMPO ESGOTADO ({MAX_TICKS} ticks)"
    print(f"\n{BD}{'═'*TW}{RS}")
    print(_ctr(f"{BD}{W}COMBATE ENCERRADO  —  {reason}{RS}", TW))
    print(f"{BD}{'═'*TW}{RS}\n")

    for i, f in enumerate(fighters):
        col  = _ACOLOR.get(f.character.archetype.id, W)
        bar  = _hp_bar(f.hp_pct, 28)
        tag  = (f"{G}{BD}  ★ VENCEDOR ★  {RS}"
                if i == winner_idx else f"{R}    derrota    {RS}")
        print(f"  {BD}{col}{f.character.name:<15}{RS}  {bar}  {f.hp_pct:.1%}  {tag}")

    print()

    # Combat summary
    dmg    = [sum(ev.damage for ev in events if ev.attacker_idx == i) for i in range(2)]
    hits   = [sum(1         for ev in events if ev.attacker_idx == i) for i in range(2)]
    stuns  = [sum(1 for ev in events if ev.attacker_idx == i and ev.stun > 0) for i in range(2)]

    names = [f.character.name for f in fighters]
    cols  = [_ACOLOR.get(f.character.archetype.id, W) for f in fighters]

    w = TW - 4
    print(f"  {DARK}{'─'*w}{RS}")
    print(f"  {DARK}{'Estatísticas de combate':^{w}}{RS}")
    print(f"  {DARK}{'─'*w}{RS}")
    print(f"  {'':20}  {'Hits':>6}  {'Dano total':>12}  {'Stuns':>6}  {'Alcance?':>8}")
    for i in range(2):
        in_r = [ev for ev in events if ev.attacker_idx == i and
                ev.damage > 0]
        # average damage per hit
        avg  = (dmg[i] / hits[i]) if hits[i] > 0 else 0.0
        print(f"  {cols[i]}{BD}{names[i]:<20}{RS}"
              f"  {hits[i]:>6}"
              f"  {dmg[i]:>11.1f}"
              f"  {stuns[i]:>6}"
              f"  {avg:>7.1f}/hit")

    print(f"\n  {DARK}Duração: {ticks} ticks   "
          f"Total de golpes: {len(events)}{RS}")
    print(f"\n{BD}{'═'*TW}{RS}\n")


# ─── Visual combat loop ────────────────────────────────────────────────────────

def run_combat_visual(
    char_a: Character,
    char_b: Character,
    delay:   float = 0.06,
    show_vs: bool  = True,
) -> None:
    if show_vs:
        _render_vs(char_a, char_b, delay=max(0.5, delay * 15))

    fighters = [
        FighterState(character=char_a, hp=char_a.hp),
        FighterState(character=char_b, hp=char_b.hp),
    ]
    distance   = float(INITIAL_DISTANCE)
    events:    List[DamageEvent]          = []
    end_tick   = MAX_TICKS
    ko         = False
    winner_idx = 0

    for tick in range(MAX_TICKS):

        # Early-KO check
        if not fighters[0].is_alive or not fighters[1].is_alive:
            end_tick = tick
            ko       = True
            break

        # Phase 1: Decrement timers
        for f in fighters:
            if f.stun_remaining    > 0: f.stun_remaining    -= 1
            if f.cooldown_remaining > 0: f.cooldown_remaining -= 1

        # Phase 2: Choose actions
        actions: List[Optional[int]] = []
        for i in range(2):
            if fighters[i].is_stunned:
                actions.append(None)
            else:
                actions.append(_choose_action(fighters[i], fighters[1 - i], distance))

        # Phase 3: Movement
        delta = 0.0
        for i in range(2):
            if actions[i] == Action.ADVANCE:
                delta -= (fighters[i].character.speed / 100.0) * 5.0
            elif actions[i] == Action.RETREAT:
                delta += (fighters[i].character.speed / 100.0) * 5.0
        distance = max(MIN_DISTANCE, min(MAX_DISTANCE, distance + delta))

        # Phase 4: Simultaneous attacks
        defending    = [a == Action.DEFEND for a in actions]
        pending_kb   = 0.0
        hit_flashes: List[Tuple[int, float]] = []

        for att_idx in range(2):
            if actions[att_idx] != Action.ATTACK:
                continue
            if not fighters[att_idx].attack_ready:
                continue

            def_idx    = 1 - att_idx
            hp_before  = fighters[def_idx].hp_pct

            dmg, stun, kb = _resolve_attack(
                attacker=fighters[att_idx].character,
                defender_state=fighters[def_idx],
                defender_is_defending=defending[def_idx],
                distance=distance,
            )

            if dmg > 0:
                fighters[def_idx].hp = max(0.0, fighters[def_idx].hp - dmg)
                if stun > fighters[def_idx].stun_remaining:
                    fighters[def_idx].stun_remaining = stun
                pending_kb += kb
                hit_flashes.append((att_idx, dmg))

                events.append(DamageEvent(
                    tick=tick,
                    attacker_idx=att_idx,
                    attacker=fighters[att_idx].character.name,
                    defender=fighters[def_idx].character.name,
                    damage=dmg,
                    hp_before=hp_before,
                    hp_after=fighters[def_idx].hp_pct,
                    stun=stun,
                    ko=not fighters[def_idx].is_alive,
                ))

            # Cooldown fires even on miss
            fighters[att_idx].cooldown_remaining = round(
                (100.0 - fighters[att_idx].character.cooldown) / 10.0
            )

        if pending_kb > 0:
            distance = min(MAX_DISTANCE, distance + pending_kb)

        _render(tick, fighters, distance, actions, events, hit_flashes)
        time.sleep(delay)

    # Determine winner
    if not fighters[0].is_alive and not fighters[1].is_alive:
        winner_idx = 0 if fighters[0].hp_pct >= fighters[1].hp_pct else 1
    elif not fighters[0].is_alive:
        winner_idx = 1
    elif not fighters[1].is_alive:
        winner_idx = 0
    else:
        winner_idx = 0 if fighters[0].hp_pct >= fighters[1].hp_pct else 1

    _render_end(winner_idx, fighters, end_tick, ko, events)


# ─── Load evolved characters ──────────────────────────────────────────────────

def _load_evolved(results_path: str) -> Optional[Individual]:
    if not os.path.exists(results_path):
        return None
    with open(results_path) as fh:
        data = json.load(fh)
    if "best_individual" not in data:
        return None
    ind = Individual.from_canonical()
    for char, genes in zip(ind.characters, data["best_individual"]):
        char.load_genes(genes)
        char.clip()
    return ind


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Visualizador de combate ASCII",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("char_a", nargs="?", default=None,
                        help="Arquétipo A (ex: rushdown, grappler, cm…)")
    parser.add_argument("char_b", nargs="?", default=None,
                        help="Arquétipo B")
    parser.add_argument("--delay",   type=float, default=0.06,
                        help="Segundos entre ticks (default 0.06)")
    parser.add_argument("--list",    action="store_true",
                        help="Lista arquétipos disponíveis e sai")
    parser.add_argument("--all",     action="store_true",
                        help="Roda todos os 10 matchups em sequência")
    parser.add_argument("--evolved", action="store_true",
                        help="Usa personagens do último AG (results.json)")
    parser.add_argument("--results", default="results.json",
                        help="Caminho para o arquivo de resultados do AG")
    parser.add_argument("--no-vs",   action="store_true",
                        help="Pula a tela de apresentação (VS screen)")
    args = parser.parse_args()

    if args.list:
        print("\nArquétipos disponíveis:")
        for alias, aid in sorted(ALIASES.items()):
            print(f"  {alias:<12} → {ARCHETYPES[aid].name}")
        print()
        return

    if args.evolved:
        ind = _load_evolved(args.results)
        if ind is None:
            print(f"Arquivo '{args.results}' não encontrado ou sem 'best_individual'.")
            print("Rode py main.py primeiro para gerar os personagens evoluídos.")
            sys.exit(1)
        print(f"{G}Carregando personagens evoluídos de '{args.results}'…{RS}\n")
        time.sleep(0.4)
    else:
        ind = Individual.from_canonical()

    chars = {c.archetype.id: c for c in ind.characters}
    show_vs = not args.no_vs

    if args.all:
        pairs = list(combinations(list(chars.keys()), 2))
        for id_a, id_b in pairs:
            ca, cb = chars[id_a], chars[id_b]
            try:
                run_combat_visual(ca, cb, delay=args.delay, show_vs=show_vs)
            except KeyboardInterrupt:
                print(f"\n{DIM}Interrompido.{RS}\n")
                return
            print(f"\n  {DARK}[Enter para próximo matchup  •  Ctrl+C para sair]{RS}")
            try:
                input()
            except KeyboardInterrupt:
                return
        return

    if args.char_a and args.char_b:
        id_a = ALIASES.get(args.char_a.lower())
        id_b = ALIASES.get(args.char_b.lower())
        if id_a is None:
            print(f"Arquétipo desconhecido: '{args.char_a}'. Use --list para ver opções.")
            sys.exit(1)
        if id_b is None:
            print(f"Arquétipo desconhecido: '{args.char_b}'. Use --list para ver opções.")
            sys.exit(1)
    else:
        id_a, id_b = random.sample(list(chars.keys()), 2)
        print(f"\n{BD}Matchup aleatório: {chars[id_a].name} vs {chars[id_b].name}{RS}\n")
        time.sleep(0.8)

    try:
        run_combat_visual(chars[id_a], chars[id_b], delay=args.delay, show_vs=show_vs)
    except KeyboardInterrupt:
        print(f"\n{DIM}Interrompido.{RS}\n")


if __name__ == "__main__":
    main()
