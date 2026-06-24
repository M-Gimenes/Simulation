"""
Visualizador de combate ASCII — tick a tick.

Uso:
    py viewer.py                           # matchup aleatório (canônico)
    py viewer.py rushdown grappler         # matchup específico
    py viewer.py rushdown grappler --delay 0.04
    py viewer.py --list                    # lista arquétipos disponíveis
    py viewer.py --evolved                 # usa resultado da última execução do AG
    py viewer.py --nsga2                   # usa knee_point do NSGA-II
    py viewer.py --nsga2 best_balance      # usa representante específico do NSGA-II
    py viewer.py --all                     # roda todos os 10 matchups em sequência
    py viewer.py --no-vs                   # pula a tela de apresentação

Ctrl+C → sai a qualquer momento.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from dataclasses import dataclass
from itertools import combinations
from typing import List, Optional, Tuple

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.engine.archetypes import ARCHETYPE_ALIASES, ARCHETYPE_ORDER, ARCHETYPES, ArchetypeID
from src.engine.character import Character
from src.engine.combat import Action, CombatTrace, simulate_combat_traced
from src.engine.config import FIELD_SIZE, MAX_TICKS
from src.engine.individual import Individual
from src.engine.paths import GA_RESULTS_PATH


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

def _ctr(s: str, w: int) -> str:
    v = _vlen(s)
    left = max(0, (w - v) // 2)
    return " " * left + s + " " * max(0, w - v - left)


# ─── Layout / paletas ─────────────────────────────────────────────────────────

TW       = 78
ARENA_W  = 70
TOK      = 4
LOG_N    = 8

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
    None:           M,
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


# ─── Eventos de dano (derivados do trace) ─────────────────────────────────────

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


def _extract_events(trace: CombatTrace, chars: Tuple[Character, Character]) -> List[DamageEvent]:
    """Lê damage_dealt do trace e produz lista de DamageEvent para o log."""
    events: List[DamageEvent] = []
    hp_max = (chars[0].hp, chars[1].hp)
    for t in range(trace.end_tick):
        for att in (0, 1):
            dmg = float(trace.damage_dealt[t, att])
            if dmg <= 0.0:
                continue
            defender = 1 - att
            hp_after = float(trace.hp[t, defender])
            hp_before = hp_after + dmg
            events.append(DamageEvent(
                tick=t,
                attacker_idx=att,
                attacker=chars[att].name,
                defender=chars[defender].name,
                damage=dmg,
                hp_before=hp_before / hp_max[defender],
                hp_after=hp_after / hp_max[defender],
                stun=int(trace.stun_applied[t, att]),
                ko=hp_after <= 0.0,
            ))
    return events


# ─── HP bar / campo ───────────────────────────────────────────────────────────

def _hp_bar(pct: float, width: int = 22) -> str:
    filled = max(0, min(width, round(pct * width)))
    color  = G if pct > 0.60 else (Y if pct > 0.30 else R)
    return f"{color}{'█' * filled}{'░' * (width - filled)}{RS}"


_FIELD_W = 54

def _field_line(pos_a: float, pos_b: float, tag_a: str, tag_b: str) -> str:
    w     = _FIELD_W
    tag_w = 4

    def to_col(p: float) -> int:
        return max(0, min(w - tag_w, round(p / FIELD_SIZE * (w - tag_w))))

    a_col = to_col(pos_a)
    b_col = to_col(pos_b)

    cells = [" "] * w

    lo = min(a_col, b_col) + tag_w
    hi = max(a_col, b_col)
    for x in range(lo, hi):
        if (x - lo) % 4 == 0:
            cells[x] = "·"

    tb = (tag_b[:2]).upper()
    if b_col + tag_w <= w:
        cells[b_col]     = "["
        cells[b_col + 1] = tb[0]
        cells[b_col + 2] = tb[1] if len(tb) > 1 else " "
        cells[b_col + 3] = "]"

    ta = (tag_a[:2]).upper()
    cells[a_col]     = "["
    cells[a_col + 1] = ta[0]
    cells[a_col + 2] = ta[1] if len(ta) > 1 else " "
    cells[a_col + 3] = "]"

    return "│" + "".join(cells) + "│"


# ─── Render por tick ──────────────────────────────────────────────────────────

@dataclass
class _Frame:
    """Snapshot per-tick para passar ao render — derivado do trace."""
    tick:     int
    char:     Tuple[Character, Character]
    pos:      Tuple[float, float]
    hp:       Tuple[float, float]
    action:   Tuple[Optional[Action], Optional[Action]]
    cooldown: Tuple[int, int]
    stun:     Tuple[int, int]


def _frame_at(trace: CombatTrace, chars: Tuple[Character, Character], t: int) -> _Frame:
    def _act(code: int) -> Optional[Action]:
        return None if code < 0 else Action(int(code))
    return _Frame(
        tick=t,
        char=chars,
        pos=(float(trace.pos[t, 0]), float(trace.pos[t, 1])),
        hp=(float(trace.hp[t, 0]), float(trace.hp[t, 1])),
        action=(_act(int(trace.action[t, 0])), _act(int(trace.action[t, 1]))),
        cooldown=(int(trace.cooldown[t, 0]), int(trace.cooldown[t, 1])),
        stun=(int(trace.stun[t, 0]), int(trace.stun[t, 1])),
    )


def _render(frame: _Frame, events_so_far: List[DamageEvent]) -> None:
    print(CL, end="")

    chars = frame.char
    name_a, name_b = chars[0].name, chars[1].name
    title = f"{BD}{name_a}{RS}  {DARK}vs{RS}  {BD}{name_b}{RS}"
    tick_s = f"{DARK}Tick {frame.tick:04d}/{MAX_TICKS}{RS}"

    print(f"{BD}{'═'*TW}{RS}")
    print(f"  {_pad(title, TW - 22)}{tick_s}")
    print(f"{BD}{'═'*TW}{RS}\n")

    for i in (0, 1):
        char = chars[i]
        col  = _ACOLOR.get(char.archetype.id, W)
        pct  = frame.hp[i] / char.hp if char.hp > 0 else 0.0
        bar  = _hp_bar(pct, 22)
        pct_col = G if pct > 0.6 else (Y if pct > 0.3 else R + BD)
        print(
            f"  {BD}{col}{char.name:<15}{RS}  {bar}  "
            f"{pct_col}{pct:5.1%}{RS}  "
            f"{DARK}{frame.hp[i]:6.1f}/{char.hp:.0f}{RS}"
        )
    print()

    distance = abs(frame.pos[1] - frame.pos[0])
    border = "─" * (_FIELD_W + 2)
    tag_a, tag_b = name_a[:2].upper(), name_b[:2].upper()
    print(f"  ┌{border}┐")
    print(f"  {_field_line(frame.pos[0], frame.pos[1], tag_a, tag_b)}")
    print(f"  └{border}┘")
    print(
        f"  {DIM}{'Distância:':>12} {distance:5.1f}   "
        f"{tag_a}:{frame.pos[0]:5.1f}  {tag_b}:{frame.pos[1]:5.1f}{RS}\n"
    )

    def _panel(i: int) -> str:
        act = frame.action[i]
        col = _ACT_COLOR.get(act, M)
        cd, st = frame.cooldown[i], frame.stun[i]
        cd_s = f"{G}{BD}rdy{RS}" if cd == 0 else f"{Y}{cd:2d}t{RS}"
        st_s = f"{M}{BD}{st:2d}{RS}" if st > 0 else f"{DARK}--{RS}"
        return (
            f"{col}{BD}{_ACT_ICON[act]} {_ACT_NAME[act]}{RS}  "
            f"{DARK}CD:{RS}{cd_s}  {DARK}STN:{RS}{st_s}"
        )

    half = TW // 2 - 1
    print(f"  {_pad(_panel(0), half)}  {_panel(1)}\n")

    print(f"  {DARK}── Combat Log {'─'*38}{RS}")
    recent = events_so_far[-LOG_N:]
    if not recent:
        print(f"  {DARK}  (sem dano ainda…){RS}")
    for ev in recent:
        atk_col = _ACOLOR.get(chars[ev.attacker_idx].archetype.id, W)
        stun_s  = f" {M}[stun×{ev.stun}]{RS}" if ev.stun else ""
        ko_s    = f" {R}{BD}[ KO! ]{RS}"     if ev.ko   else ""
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
        return [
            f"HP    = {char.hp:.0f}",
            f"Dano  = {char.damage:.0f}   CD = {char.attack_cooldown:.0f}t",
            f"Vel   = {char.speed:.0f}   Alcance= {char.range_:.0f}",
            f"Def   = {char.defense:.2f}   Stun   = {char.stun:.1f}",
            f"Recup = {int(char.recovery)}",
        ]

    print(CL, end="")
    print(f"\n{BD}{'═'*TW}{RS}")
    print(_ctr(f"{BD}{W}* * *  BATALHA!  * * *{RS}", TW))
    print(f"{BD}{'═'*TW}{RS}\n")

    HL = TW // 2 - 3
    desc_a = char_a.archetype.description[:HL - 4]
    desc_b = char_b.archetype.description[:HL - 4]

    print(
        f"  {_ctr(f'{col_a}{BD}{char_a.name}{RS}', HL)}    "
        f"{_ctr(f'{col_b}{BD}{char_b.name}{RS}', HL)}"
    )
    print(f"  {'─'*HL}    {'─'*HL}")

    for la, lb in zip(_stat_block(char_a), _stat_block(char_b)):
        print(f"  {col_a}{_pad(la, HL)}{RS}    {col_b}{lb}{RS}")

    print(f"\n  {DARK}{desc_a}…{RS}")
    print(f"  {DARK}{desc_b}…{RS}")

    print(f"\n{BD}{'═'*TW}{RS}")
    print(_ctr(f"{DARK}a combater em {delay:.1f}s…{RS}", TW))
    print()
    time.sleep(delay)


# ─── End screen ───────────────────────────────────────────────────────────────

def _render_end(
    trace: CombatTrace,
    chars: Tuple[Character, Character],
    events: List[DamageEvent],
) -> None:
    print(CL, end="")
    reason = "K.O.!" if trace.ko else f"TEMPO ESGOTADO ({MAX_TICKS} ticks)"
    print(f"\n{BD}{'═'*TW}{RS}")
    print(_ctr(f"{BD}{W}COMBATE ENCERRADO  —  {reason}{RS}", TW))
    print(f"{BD}{'═'*TW}{RS}\n")

    final_hp = (
        float(trace.hp[-1, 0]) if trace.end_tick > 0 else chars[0].hp,
        float(trace.hp[-1, 1]) if trace.end_tick > 0 else chars[1].hp,
    )

    for i in (0, 1):
        char = chars[i]
        col  = _ACOLOR.get(char.archetype.id, W)
        pct  = final_hp[i] / char.hp if char.hp > 0 else 0.0
        bar  = _hp_bar(pct, 28)
        tag  = (
            f"{G}{BD}  ★ VENCEDOR ★  {RS}"
            if i == trace.winner else f"{R}    derrota    {RS}"
        )
        print(f"  {BD}{col}{char.name:<15}{RS}  {bar}  {pct:.1%}  {tag}")
    print()

    dmg   = [sum(ev.damage for ev in events if ev.attacker_idx == i) for i in (0, 1)]
    hits  = [sum(1         for ev in events if ev.attacker_idx == i) for i in (0, 1)]
    stuns = [sum(1 for ev in events if ev.attacker_idx == i and ev.stun > 0) for i in (0, 1)]
    cols  = [_ACOLOR.get(chars[i].archetype.id, W) for i in (0, 1)]

    w = TW - 4
    print(f"  {DARK}{'─'*w}{RS}")
    print(f"  {DARK}{'Estatísticas de combate':^{w}}{RS}")
    print(f"  {DARK}{'─'*w}{RS}")
    print(f"  {'':20}  {'Hits':>6}  {'Dano total':>12}  {'Stuns':>6}  {'Avg dmg':>9}")
    for i in (0, 1):
        avg = (dmg[i] / hits[i]) if hits[i] > 0 else 0.0
        print(
            f"  {cols[i]}{BD}{chars[i].name:<20}{RS}"
            f"  {hits[i]:>6}"
            f"  {dmg[i]:>11.1f}"
            f"  {stuns[i]:>6}"
            f"  {avg:>7.1f}/hit"
        )

    print(
        f"\n  {DARK}Duração: {trace.end_tick} ticks   "
        f"Total de golpes: {len(events)}{RS}"
    )
    print(f"\n{BD}{'═'*TW}{RS}\n")


# ─── Loop visual ──────────────────────────────────────────────────────────────

def run_combat_visual(
    char_a: Character,
    char_b: Character,
    delay:   float = 0.06,
    show_vs: bool  = True,
) -> None:
    if show_vs:
        _render_vs(char_a, char_b, delay=max(0.5, delay * 15))

    trace = simulate_combat_traced(char_a, char_b)
    chars = (char_a, char_b)
    events = _extract_events(trace, chars)

    events_streamed: List[DamageEvent] = []
    next_event = 0
    for t in range(trace.end_tick):
        while next_event < len(events) and events[next_event].tick <= t:
            events_streamed.append(events[next_event])
            next_event += 1
        _render(_frame_at(trace, chars, t), events_streamed)
        time.sleep(delay)

    _render_end(trace, chars, events)


# ─── Loaders / entry ──────────────────────────────────────────────────────────

ALIASES = ARCHETYPE_ALIASES


def _load_evolved(results_path: str) -> Optional[Individual]:
    import os
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Visualizador de combate ASCII",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("char_a", nargs="?", default=None,
                        help="Arquétipo A (ex: rushdown, grappler, cm…)")
    parser.add_argument("char_b", nargs="?", default=None,
                        help="Arquétipo B")
    parser.add_argument("--delay", type=float, default=0.06,
                        help="Segundos entre ticks (default 0.06)")
    parser.add_argument("--list", action="store_true",
                        help="Lista arquétipos disponíveis e sai")
    parser.add_argument("--all", action="store_true",
                        help="Roda todos os 10 matchups em sequência")
    parser.add_argument("--evolved", action="store_true",
                        help="Usa personagens do último AG (results.json)")
    parser.add_argument("--nsga2", metavar="REP", nargs="?", const="knee_point",
                        help="Usa representante do NSGA-II "
                             "(knee_point|best_balance|best_matchup|best_drift). "
                             "Default: knee_point")
    parser.add_argument("--results", default=str(GA_RESULTS_PATH),
                        help="Caminho para o arquivo de resultados do AG")
    parser.add_argument("--no-vs", action="store_true",
                        help="Pula a tela de apresentação (VS screen)")
    args = parser.parse_args()

    if args.list:
        print("\nArquétipos disponíveis:")
        for alias, aid in sorted(ALIASES.items()):
            print(f"  {alias:<12} → {ARCHETYPES[aid].name}")
        print()
        return

    if args.nsga2:
        ind = Individual.from_nsga2(representative=args.nsga2)
        print(f"{G}Carregando personagens NSGA-II ({args.nsga2})…{RS}\n")
        time.sleep(0.4)
    elif args.evolved:
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
        for id_a, id_b in combinations(ARCHETYPE_ORDER, 2):
            run_combat_visual(chars[id_a], chars[id_b], delay=args.delay, show_vs=show_vs)
        return

    if args.char_a and args.char_b:
        try:
            id_a = ALIASES[args.char_a.lower()]
            id_b = ALIASES[args.char_b.lower()]
        except KeyError:
            print(f"Arquétipo inválido. Disponíveis: {', '.join(sorted(ALIASES.keys()))}")
            sys.exit(1)
    else:
        id_a, id_b = random.sample(ARCHETYPE_ORDER, 2)

    run_combat_visual(chars[id_a], chars[id_b], delay=args.delay, show_vs=show_vs)


if __name__ == "__main__":
    main()
