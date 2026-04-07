"""
Definição dos 5 arquétipos e seus valores iniciais.

Ciclo de vantagens fechado:
  Grappler    → vence Combo Master e Rushdown
  Combo Master→ vence Turtle e Zoner
  Zoner       → vence Grappler e Turtle
  Turtle      → vence Rushdown e Grappler
  Rushdown    → vence Zoner e Combo Master
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Tuple


class ArchetypeID(Enum):
    ZONER = auto()
    RUSHDOWN = auto()
    COMBO_MASTER = auto()
    GRAPPLER = auto()
    TURTLE = auto()


@dataclass(frozen=True)
class ArchetypeDefinition:
    """Metadados imutáveis de um arquétipo."""

    id: ArchetypeID
    name: str
    description: str

    # Valores iniciais dos atributos (escala 0–100)
    # Ordem: hp, damage, cooldown, range, speed, defense, stun, knockback, recovery
    initial_attributes: Tuple[float, ...]

    # Pesos comportamentais iniciais
    # Ordem: w_attack, w_advance, w_retreat, w_defend, w_aggressiveness
    initial_weights: Tuple[float, ...]

    # Quais arquétipos este vence (para validação do ciclo)
    beats: Tuple[ArchetypeID, ...]


# ── Tabela de arquétipos ─────────────────────────────────────────────────────

ARCHETYPES: Dict[ArchetypeID, ArchetypeDefinition] = {
    ArchetypeID.ZONER: ArchetypeDefinition(
        id=ArchetypeID.ZONER,
        name="Zoner",
        description=(
            "Controla espaço com alcance superior e knockback alto. "
            "Ataca antes do inimigo chegar e o empurra para fora de range. "
            "Sofre contra quem fecha distância rápido ou resiste ao stun."
        ),
        #                 hp     dmg   cd   rng  spd   def  stun  kb   rec
        # Identidade: range alto (45), knockback moderado (30 → 3 unidades),
        # HP baixo. cooldown=70 → wait=3 → ataca a cada 4 ticks.
        # kb=30 (3 unidades): empurra inimigos mas não impede RD de fechar distância.
        initial_attributes=(300.0, 10.0, 70.0, 45.0, 35.0, 25.0, 20.0, 30.0, 40.0),
        #                    atk   adv   ret   def   agg
        initial_weights=(0.7, 0.3, 0.5, 0.2, 0.4),
        beats=(ArchetypeID.GRAPPLER, ArchetypeID.TURTLE),
    ),
    ArchetypeID.RUSHDOWN: ArchetypeDefinition(
        id=ArchetypeID.RUSHDOWN,
        name="Rushdown",
        description=(
            "Fecha distância em segundos e sufoca com ataques rápidos. "
            "Se ferra contra defesa sólida e personagens que absorvem pressão."
        ),
        #                 hp     dmg   cd   rng  spd   def  stun  kb   rec
        # Identidade: speed máximo (90), cooldown alto (90 → wait=1 → ataca a
        # cada 2 ticks), range curto (20 — deve chegar perto).
        initial_attributes=(300.0, 11.0, 90.0, 20.0, 90.0, 30.0, 35.0, 20.0, 25.0),
        #                    atk   adv   ret   def   agg
        initial_weights=(0.8, 0.9, 0.1, 0.1, 0.9),
        beats=(ArchetypeID.ZONER, ArchetypeID.COMBO_MASTER),
    ),
    ArchetypeID.COMBO_MASTER: ArchetypeDefinition(
        id=ArchetypeID.COMBO_MASTER,
        name="Combo Master",
        description=(
            "Alta velocidade fecha distância, stun extremo encadeia combos. "
            "Neutraliza tanques e zoners com lockdown. "
            "Perde para pressão antes de poder configurar os combos."
        ),
        #                 hp     dmg   cd   rng  spd   def  stun  kb   rec
        # Identidade: stun máximo (80), speed alto (85), cooldown alto (85 →
        # wait=2 → ataca a cada 3 ticks). Cap de stun = 2 → trava oponente
        # 2 de 3 ticks. Dano=12: penetra moderadamente defesas altas.
        initial_attributes=(300.0, 12.0, 85.0, 20.0, 85.0, 35.0, 80.0, 20.0, 65.0),
        #                    atk   adv   ret   def   agg
        initial_weights=(0.9, 0.7, 0.2, 0.2, 0.7),
        beats=(ArchetypeID.TURTLE, ArchetypeID.ZONER),
    ),
    ArchetypeID.GRAPPLER: ArchetypeDefinition(
        id=ArchetypeID.GRAPPLER,
        name="Grappler",
        description=(
            "Tank que pune corpo a corpo com burst pesado e stun. "
            "Alta recuperação resiste aos combos adversários. "
            "Sofre contra distância — range mínimo exige encosto total."
        ),
        #                 hp     dmg   cd   rng  spd   def  stun  kb   rec
        # Identidade: HP alto (450), damage máximo (15), defense=65,
        # recovery=85 (resiste stuns), range mínimo (15).
        # cooldown=30 → wait = round((100-30)/10) = 7 → ataque pesado e lento.
        # kb=10 (1 unidade): knockback simbólico — não empurra inimigo para fora
        # do melee range, mantendo Grappler no corpo a corpo após cada hit.
        initial_attributes=(450.0, 15.0, 30.0, 15.0, 30.0, 65.0, 55.0, 10.0, 85.0),
        #                    atk   adv   ret   def   agg
        initial_weights=(0.9, 0.7, 0.1, 0.5, 0.8),
        beats=(ArchetypeID.COMBO_MASTER, ArchetypeID.RUSHDOWN),
    ),
    ArchetypeID.TURTLE: ArchetypeDefinition(
        id=ArchetypeID.TURTLE,
        name="Turtle",
        description=(
            "Muralha viva — absorve tudo e contra-ataca com paciência. "
            "Derrota agressivos pela atrito. "
            "Perde para quem não se expõe ou quebra a defesa com stun."
        ),
        #                 hp      dmg   cd   rng  spd   def  stun  kb   rec
        # Identidade: HP máximo (500), defense máxima (90), recovery alto (80).
        # Damage baixo (6) — vence pelo atrito de HP%, não pelo burst.
        # cooldown=35 → wait = round((100-35)/10) = 6 → ataca a cada 7 ticks.
        initial_attributes=(500.0,  6.0, 35.0, 35.0, 25.0, 90.0, 25.0, 30.0, 80.0),
        #                    atk   adv   ret   def   agg
        initial_weights=(0.3, 0.2, 0.6, 0.5, 0.1),
        beats=(ArchetypeID.RUSHDOWN, ArchetypeID.GRAPPLER),
    ),
}

# Lista ordenada (garante indexação consistente no cromossomo)
ARCHETYPE_ORDER: List[ArchetypeID] = [
    ArchetypeID.ZONER,
    ArchetypeID.RUSHDOWN,
    ArchetypeID.COMBO_MASTER,
    ArchetypeID.GRAPPLER,
    ArchetypeID.TURTLE,
]

NUM_ARCHETYPES = len(ARCHETYPE_ORDER)
