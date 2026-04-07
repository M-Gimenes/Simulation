"""
Visualizador de combate ASCII — tick a tick.

Uso:
    py viewer.py                           # matchup aleatório (canônico)
    py viewer.py rushdown grappler         # matchup específico
    py viewer.py rushdown grappler --delay 0.03
    py viewer.py --list                    # lista arquétipos disponíveis
    py viewer.py --evolved                 # usa resultado da última execução do AG (results.json)
    py viewer.py --all                     # roda todos os 10 matchups em sequência

Controle durante a luta:
    Enter  → pausa / continua
    Ctrl+C → sai
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.dirname(__file__))

# Força UTF-8 no terminal Windows (necessário para box-drawing e blocos)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from archetypes import ARCHETYPES, ArchetypeID, ARCHETYPE_ORDER
from character import Character
from individual import Individual
from combat import FighterState, Action, _choose_action, _resolve_attack
from config import INITIAL_DISTANCE, MAX_DISTANCE, MAX_TICKS, MIN_DISTANCE

# ── ANSI ──────────────────────────────────────────────────────────────────────

def _enable_ansi_windows() -> None:
    """Habilita ANSI no terminal Windows."""
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

_enable_ansi_windows()

R  = "\033[91m"   # vermelho
G  = "\033[92m"   # verde
Y  = "\033[93m"   # amarelo
B  = "\033[94m"   # azul
M  = "\033[95m"   # magenta
C  = "\033[96m"   # ciano
W  = "\033[97m"   # branco brilhante
DIM= "\033[2m"    # escurecido
BD = "\033[1m"    # negrito
RS = "\033[0m"    # reset
CL = "\033[2J\033[H"  # clear + cursor ao topo

_ANSI_RE = re.compile(r"\033\[[^m]*m")

def _vlen(s: str) -> int:
    """Comprimento visível de uma string (sem ANSI)."""
    return len(_ANSI_RE.sub("", s))

def _pad(s: str, width: int) -> str:
    """Padeia à direita até `width` colunas visíveis."""
    return s + " " * max(0, width - _vlen(s))

# ── Aliases de arquétipo ───────────────────────────────────────────────────────

ALIASES = {
    "zoner":   ArchetypeID.ZONER,
    "z":       ArchetypeID.ZONER,
    "rushdown": ArchetypeID.RUSHDOWN,
    "rd":      ArchetypeID.RUSHDOWN,
    "combo":   ArchetypeID.COMBO_MASTER,
    "cm":      ArchetypeID.COMBO_MASTER,
    "grappler": ArchetypeID.GRAPPLER,
    "grap":    ArchetypeID.GRAPPLER,
    "g":       ArchetypeID.GRAPPLER,
    "turtle":  ArchetypeID.TURTLE,
    "t":       ArchetypeID.TURTLE,
}

# ── Labels de ação ────────────────────────────────────────────────────────────

_ACT_LABEL = {
    Action.ATTACK:  ("ATTACK  ", R),
    Action.ADVANCE: ("ADVANCE ", Y),
    Action.RETREAT: ("RETREAT ", B),
    Action.DEFEND:  ("DEFEND  ", G),
    None:           ("STUNNED ", M),
}

# ── Evento de dano ────────────────────────────────────────────────────────────

@dataclass
class DamageEvent:
    tick: int
    attacker: str
    defender: str
    damage: float
    hp_before: float   # % HP antes
    hp_after: float    # % HP depois
    stun: int
    ko: bool


# ── Barra de HP ───────────────────────────────────────────────────────────────

def _hp_bar(pct: float, width: int = 22) -> str:
    filled = max(0, min(width, round(pct * width)))
    bar = "█" * filled + "░" * (width - filled)
    color = G if pct > 0.60 else (Y if pct > 0.30 else R)
    return f"{color}{bar}{RS}"


# ── Campo de batalha ──────────────────────────────────────────────────────────

_FIELD_W = 54   # largura interna (sem bordas)

def _field_line(distance: float, tag_a: str, tag_b: str) -> str:
    """
    Linha do campo com ambos os lutadores se movendo a partir do centro.
    A posição de cada um é: centro ± distance/2, mapeado para os _FIELD_W chars.
    Quando avançam juntos, os dois convergem para o meio do campo.
    """
    w      = _FIELD_W
    center = w // 2
    half   = distance / MAX_DISTANCE * w / 2

    a_pos = max(0,     min(center - 2, round(center - half)))
    b_pos = max(center + 2, min(w - 4, round(center + half)))

    cells = [" "] * w

    # Marcador A
    ta = (tag_a[:2]).upper()
    cells[a_pos]     = "["
    cells[a_pos + 1] = ta[0]
    cells[a_pos + 2] = ta[1] if len(ta) > 1 else " "
    cells[a_pos + 3] = "]"

    # Linha tracejada entre eles
    for x in range(a_pos + 4, b_pos - 1):
        if (x - a_pos) % 4 == 0:
            cells[x] = "·"

    # Marcador B
    tb = (tag_b[:2]).upper()
    if b_pos + 3 < w:
        cells[b_pos]     = "["
        cells[b_pos + 1] = tb[0]
        cells[b_pos + 2] = tb[1] if len(tb) > 1 else " "
        cells[b_pos + 3] = "]"

    return "│" + "".join(cells) + "│"


# ── Render principal ──────────────────────────────────────────────────────────

def _render(
    tick: int,
    fighters: List[FighterState],
    distance: float,
    actions: List[Optional[int]],
    events: List[DamageEvent],
) -> None:
    names = [f.character.name for f in fighters]
    TW = 62  # terminal width para o frame

    print(CL, end="")

    # ── Cabeçalho
    header = f" {BD}{W}{names[0]}  vs  {names[1]}{RS}"
    tick_s = f"{BD}Tick {tick:04d}/{MAX_TICKS}{RS}"
    gap    = TW - len(names[0]) - len(names[1]) - len(" vs ") - len(f"Tick {tick:04d}/{MAX_TICKS}") - 4
    print(f"{BD}{'═'*TW}{RS}")
    print(f"{BD}{W} {names[0]}  vs  {names[1]}{RS}{' '*gap}{BD}Tick {tick:04d}/{MAX_TICKS}  {RS}")
    print(f"{BD}{'═'*TW}{RS}")
    print()

    # ── Barras de HP
    for i, f in enumerate(fighters):
        pct = f.hp_pct
        bar = _hp_bar(pct)
        tag = f"{BD}{W}{f.character.name:<16}{RS}"
        hp_txt = f"{f.hp:6.1f}/{f.hp_max:.0f}"
        print(f"  {tag}  {bar}  {pct:5.1%}  {DIM}{hp_txt}{RS}")

    print()

    # ── Campo
    border = "─" * (_FIELD_W + 2)
    tag_a = names[0][:2].upper()
    tag_b = names[1][:2].upper()
    fline = _field_line(distance, tag_a, tag_b)
    print(f"  ┌{border}┐")
    print(f"  {fline}")
    print(f"  └{border}┘")
    print(f"  {DIM}{'Distância:':>12} {distance:5.1f} unidades{RS}")
    print()

    # ── Ações lado a lado
    def _act_str(idx: int) -> str:
        act = actions[idx]
        label, color = _ACT_LABEL.get(act, ("???     ", W))
        f  = fighters[idx]
        cd = fighters[idx].cooldown_remaining
        st = fighters[idx].stun_remaining
        cd_s = f"{DIM}CD:{RS}{Y}{cd}{RS}" if cd > 0 else f"{DIM}CD:{RS}{G}rdy{RS}"
        st_s = f"{DIM}STN:{RS}{M}{st}{RS}" if st > 0 else f"{DIM}STN:{RS}{DIM}--{RS}"
        return f"{color}{BD}{label}{RS}  {cd_s}  {st_s}"

    left  = _act_str(0)
    right = _act_str(1)
    print(f"  {_pad(left, 38)}{right}")
    print()

    # ── Log de combate (últimos 6 eventos)
    print(f"  {DIM}── Combat Log {'─'*43}{RS}")
    recent = events[-6:]
    if not recent:
        print(f"  {DIM}  (sem trocas de dano ainda…){RS}")
    for ev in recent:
        stun_tag = f" {M}[stun×{ev.stun}]{RS}" if ev.stun else ""
        ko_tag   = f" {R}{BD}[KO!]{RS}"          if ev.ko   else ""
        atk_col  = R if ev.attacker == names[0] else B
        dmg_col  = Y
        print(
            f"  {DIM}t{ev.tick:04d}{RS}  "
            f"{atk_col}{ev.attacker:<16}{RS}"
            f"→  {dmg_col}-{ev.damage:5.1f} HP{RS}  "
            f"{DIM}{ev.defender}: {ev.hp_before:.0%}→{ev.hp_after:.0%}{RS}"
            f"{stun_tag}{ko_tag}"
        )

    print(f"  {DIM}{'─'*58}{RS}")


# ── Tela final ────────────────────────────────────────────────────────────────

def _render_end(
    winner_idx: int,
    fighters: List[FighterState],
    ticks: int,
    ko: bool,
) -> None:
    TW = 62
    print(CL, end="")
    print(f"\n{BD}{'═'*TW}{RS}")
    print(f"{BD}  COMBATE ENCERRADO — {ticks} ticks  {'(KO)' if ko else '(tempo)'}{RS}")
    print(f"{BD}{'═'*TW}{RS}\n")

    for i, f in enumerate(fighters):
        name  = f.character.name
        bar   = _hp_bar(f.hp_pct, width=30)
        if i == winner_idx:
            tag = f"{G}{BD}★ VENCEDOR{RS}"
        else:
            tag = f"{R}  derrota {RS}"
        print(f"  {BD}{W}{name:<16}{RS}  {bar}  {f.hp_pct:.1%}  {tag}")

    print(f"\n{BD}{'═'*TW}{RS}\n")


# ── Loop de combate (gerador de estados) ──────────────────────────────────────

def run_combat_visual(
    char_a: Character,
    char_b: Character,
    delay: float = 0.06,
) -> None:
    fighters = [
        FighterState(character=char_a, hp=char_a.hp),
        FighterState(character=char_b, hp=char_b.hp),
    ]
    distance   = float(INITIAL_DISTANCE)
    events: List[DamageEvent] = []
    end_tick   = MAX_TICKS
    ko         = False
    winner_idx = 0

    for tick in range(MAX_TICKS):

        # ── KO antecipado
        if not fighters[0].is_alive or not fighters[1].is_alive:
            end_tick = tick
            ko       = True
            break

        # ── Decrementar timers
        for f in fighters:
            if f.stun_remaining  > 0: f.stun_remaining  -= 1
            if f.cooldown_remaining > 0: f.cooldown_remaining -= 1

        # ── Escolha de ação
        actions: List[Optional[int]] = []
        for i in range(2):
            if fighters[i].is_stunned:
                actions.append(None)
            else:
                actions.append(_choose_action(fighters[i], fighters[1 - i], distance))

        # ── Movimento
        delta = 0.0
        for i in range(2):
            if actions[i] == Action.ADVANCE:
                delta -= (fighters[i].character.speed / 100.0) * 5.0
            elif actions[i] == Action.RETREAT:
                delta += (fighters[i].character.speed / 100.0) * 5.0
        distance = max(MIN_DISTANCE, min(MAX_DISTANCE, distance + delta))

        # ── Ataques
        defending        = [a == Action.DEFEND for a in actions]
        pending_knockback = 0.0

        for attacker_idx in range(2):
            if actions[attacker_idx] != Action.ATTACK:
                continue
            if not fighters[attacker_idx].attack_ready:
                continue

            defender_idx   = 1 - attacker_idx
            hp_before_pct  = fighters[defender_idx].hp_pct

            dmg, stun, kb = _resolve_attack(
                attacker=fighters[attacker_idx].character,
                defender_state=fighters[defender_idx],
                defender_is_defending=defending[defender_idx],
                distance=distance,
            )

            if dmg > 0:
                fighters[defender_idx].hp = max(0.0, fighters[defender_idx].hp - dmg)
                if stun > fighters[defender_idx].stun_remaining:
                    fighters[defender_idx].stun_remaining = stun
                pending_knockback += kb

                events.append(DamageEvent(
                    tick=tick,
                    attacker=fighters[attacker_idx].character.name,
                    defender=fighters[defender_idx].character.name,
                    damage=dmg,
                    hp_before=hp_before_pct,
                    hp_after=fighters[defender_idx].hp_pct,
                    stun=stun,
                    ko=not fighters[defender_idx].is_alive,
                ))

            # Cooldown do atacante (disparou ou tentou atacar)
            fighters[attacker_idx].cooldown_remaining = round(
                (100.0 - fighters[attacker_idx].character.cooldown) / 10.0
            )

        if pending_knockback > 0:
            distance = min(MAX_DISTANCE, distance + pending_knockback)

        # ── Render deste tick
        _render(tick, fighters, distance, actions, events)
        time.sleep(delay)

    # ── Resultado final
    if not fighters[0].is_alive and not fighters[1].is_alive:
        winner_idx = 0 if fighters[0].hp_pct >= fighters[1].hp_pct else 1
    elif not fighters[0].is_alive:
        winner_idx = 1
    elif not fighters[1].is_alive:
        winner_idx = 0
    else:
        winner_idx = 0 if fighters[0].hp_pct >= fighters[1].hp_pct else 1

    _render_end(winner_idx, fighters, end_tick, ko)


# ── Carrega personagem de results.json (gerado por main.py) ──────────────────

def _load_evolved(results_path: str) -> Optional[Individual]:
    """Lê o melhor indivíduo salvo pelo AG, se existir."""
    if not os.path.exists(results_path):
        return None
    with open(results_path) as fh:
        data = json.load(fh)

    # Espera estrutura: { "best_individual": [ [14 genes], ... ] }
    if "best_individual" not in data:
        return None

    ind = Individual.from_canonical()
    genes_list = data["best_individual"]
    for char, genes in zip(ind.characters, genes_list):
        char.load_genes(genes)
        char.clip()
    return ind


# ── Entry point ───────────────────────────────────────────────────────────────

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
    args = parser.parse_args()

    if args.list:
        print("\nArquétipos disponíveis:")
        for alias, aid in sorted(ALIASES.items()):
            print(f"  {alias:<12} → {ARCHETYPES[aid].name}")
        print()
        return

    # ── Fonte dos personagens
    if args.evolved:
        ind = _load_evolved(args.results)
        if ind is None:
            print(f"Arquivo '{args.results}' não encontrado ou sem 'best_individual'.")
            print("Rode py main.py primeiro para gerar os personagens evoluídos.")
            sys.exit(1)
        print(f"{G}Carregando personagens evoluídos de '{args.results}'…{RS}\n")
        time.sleep(0.5)
    else:
        ind = Individual.from_canonical()

    chars = {c.archetype.id: c for c in ind.characters}

    # ── Modo: todos os matchups
    if args.all:
        from itertools import combinations
        pairs = list(combinations(list(chars.keys()), 2))
        for id_a, id_b in pairs:
            ca, cb = chars[id_a], chars[id_b]
            print(f"\n{BD}{W}  ▶  {ca.name}  vs  {cb.name}{RS}\n")
            time.sleep(1.0)
            run_combat_visual(ca, cb, delay=args.delay)
            print(f"\n  {DIM}[Enter para próximo matchup, Ctrl+C para sair]{RS}")
            try:
                input()
            except KeyboardInterrupt:
                break
        return

    # ── Modo: matchup específico ou aleatório
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
        time.sleep(1.0)

    try:
        run_combat_visual(chars[id_a], chars[id_b], delay=args.delay)
    except KeyboardInterrupt:
        print(f"\n{DIM}Interrompido.{RS}\n")


if __name__ == "__main__":
    main()
