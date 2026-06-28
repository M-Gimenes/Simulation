# Combat Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reestruturar o combate (seleção de ação intenção→execução) e enxugar o cromossomo (12→10 genes), mantendo as 5 identidades e o gradiente que o C2 precisa, sem deixar código morto.

**Architecture:** Combate é uma função JIT (numba) com duas variantes (`_simulate_combat_jit` p/ fitness, `_simulate_combat_traced_jit` p/ tools). A seleção de ação vira "amostra de intenção (FRENTE/RECUAR/GUARDA, ponderada por w_agg/w_ret/w_def, com persistência) → execução adaptativa à situação". A física do stun vira fração do cooldown; `defense` e `recovery` saem; dano fica flat.

**Tech Stack:** Python 3, numba (`@njit(cache=True)`), numpy. Testes são **smoke tests** rodados com `py -m src.tests.test_X` (não há pytest). Windows: usar `py`.

## Global Constraints

- Cromossomo final: **7 atributos + 3 pesos = 10 genes/char**. Ordem dos atributos: `hp, damage, attack_cooldown, range, speed, stun, knockback`.
- `stun` é **fração do cooldown**, bound `[0.0, 0.6]`; `stun_efetivo = round(stun × round(cooldown × TICK_SCALE))`. Sem cap, sem recovery. Lock impossível por bound.
- Dano **flat**: `dano = damage × (DEFEND_DAMAGE_REDUCTION se o alvo defende, senão 1.0)`.
- **Zero referências** remanescentes a: `defense`, `recovery`, `STUN_CAP_MULTIPLIER`, `HESITATION_RATE`, `WALL_CORNER_THRESHOLD`, `INTEGER_ATTRIBUTES`, `cornered`, `hesitate` (verificado por grep na Task 5).
- Aplicar **toda** mudança de combate **idêntica nas duas variantes JIT**.
- Tudo que muda de comportamento mantém o JIT como única implementação (sem reimplementar lógica em Python).
- Não commitar em `main`: trabalhar em branch `combat-simplification`.
- Docs em prosa (`docs/reference/*.md`, `CLAUDE.md`, artigo) ficam para a sessão de redação — registrar no handoff (Task 5), NÃO editar aqui. Docstrings/comentários **dentro do código** devem ficar corretos.

---

### Task 0: Branch + baseline verde

**Files:** nenhum (setup)

- [ ] **Step 1: Criar branch**

```bash
git checkout -b combat-simplification
```

- [ ] **Step 2: Rodar a suíte smoke atual e confirmar verde (baseline)**

```bash
py -m src.tests.test_base; py -m src.tests.test_combat; py -m src.tests.test_fitness; py -m src.tests.test_operators; py -m src.tests.test_nsga2; py -m src.tests.test_archetype_validator
```
Expected: cada um imprime "✓ ... passaram" sem traceback. (Anotar qualquer falha pré-existente antes de mudar nada.)

---

### Task 1: Seleção de ação — modelo intenção→execução

Reescreve só o bloco de **decisão** (não a física). Remove `HESITATION_RATE` e `WALL_CORNER_THRESHOLD`. `commit_a/commit_b` passam a guardar **intenção** (0=FRENTE, 1=RECUAR, 2=GUARDA) em vez de ação.

**Files:**
- Modify: `src/engine/combat.py` (imports; assinatura das 2 variantes JIT; bloco de decisão A e B nas 2 variantes; 2 call sites)
- Modify: `src/engine/config.py` (remover `HESITATION_RATE`, `WALL_CORNER_THRESHOLD`)
- Test: `src/tests/test_combat.py`

**Interfaces:**
- Produces: assinatura JIT sem `wall_corner` e `hesitation` (ainda com `stun_cap_mult`, removido na Task 2).

- [ ] **Step 1: Adicionar asserção de regressão em test_combat**

Em `src/tests/test_combat.py`, adicionar (perto das checagens de luta canônica) um teste de que a luta termina e o rusher é majoritariamente agressivo:

```python
from src.engine.individual import Individual
from src.engine.combat import simulate_combat_detailed
from src.engine.archetypes import ARCHETYPE_ORDER, ArchetypeID

ind = Individual.from_canonical()
rush = next(c for c in ind.characters if c.archetype_id == ArchetypeID.RUSHDOWN)
zon  = next(c for c in ind.characters if c.archetype_id == ArchetypeID.ZONER)
_, log = simulate_combat_detailed(rush, zon)
atk = log.action_counts[0][0]; adv = log.action_counts[0][1]
total = sum(log.action_counts[0].values())
assert total > 0
assert (atk + adv) / total > 0.5, f"Rusher deveria ser majoritariamente FRENTE (atk+adv), got {(atk+adv)/total:.2f}"
print("  ✓ rusher majoritariamente FRENTE")
```

- [ ] **Step 2: Rodar e ver passar com o código ATUAL (caracteriza o comportamento atual)**

```bash
py -m src.tests.test_combat
```
Expected: PASS (o rusher já é agressivo hoje). Isso é a rede de regressão para a reescrita.

- [ ] **Step 3: Remover constantes de config**

Em `src/engine/config.py` apagar as linhas:
```python
WALL_CORNER_THRESHOLD = 10  # ...
HESITATION_RATE = 0.10  # ... (e as ~6 linhas de comentário que a seguem, até antes de "# ── Simulação — Resolução temporal")
```

- [ ] **Step 4: Ajustar imports e assinaturas no combat.py**

Em `src/engine/combat.py`, no import de config (linhas ~35-45) remover `HESITATION_RATE` e `WALL_CORNER_THRESHOLD`.
Nas DUAS assinaturas JIT, trocar:
```python
    field_size, initial_distance, wall_corner,
    max_ticks, tick_scale, stun_cap_mult,
    defend_red, persist, hesitation,
```
por:
```python
    field_size, initial_distance,
    max_ticks, tick_scale, stun_cap_mult,
    defend_red, persist,
```

- [ ] **Step 5: Reescrever o bloco de decisão (personagem A) nas DUAS variantes**

Substituir o bloco `if stun_rem_a > 0: ... action_counts[0, action_a] += 1` por:

```python
        if stun_rem_a > 0:
            action_a = -1
        else:
            in_range = distance <= a_range
            if not in_range:
                action_a = 1               # ADVANCE — neutral game (aproxima)
                persist_a = 0
            else:
                if persist_a == 0:
                    tot = a_wagg + a_wret + a_wdef
                    if tot <= 0.0:
                        commit_a = 2       # GUARDA (fallback)
                    else:
                        r = np.random.random() * tot
                        if r < a_wagg:
                            commit_a = 0   # FRENTE
                        elif r < a_wagg + a_wret:
                            commit_a = 1   # RECUAR
                        else:
                            commit_a = 2   # GUARDA
                    persist_a = persist
                persist_a -= 1
                if commit_a == 0:                      # FRENTE
                    action_a = 0 if cd_rem_a == 0 else 1   # ATTACK senão ADVANCE (pressão)
                elif commit_a == 1:                    # RECUAR
                    step = a_speed / tick_scale
                    can_back = (pos_a - step >= 0.0) if pos_a < pos_b else (pos_a + step <= field_size)
                    action_a = 2 if can_back else 3        # RETREAT senão DEFEND (encurralado)
                else:                                  # GUARDA
                    action_a = 3
            active_ticks[0] += 1
            action_counts[0, action_a] += 1
```

> Na variante `_simulate_combat_traced_jit` o bloco é idêntico, exceto que NÃO tem as linhas `active_ticks[0] += 1` e `action_counts[0, action_a] += 1` (a traced não rastreia esses contadores). Aplicar sem essas 2 linhas.

- [ ] **Step 6: Reescrever o bloco de decisão (personagem B) nas DUAS variantes**

Idêntico ao Step 5 trocando sufixo `_a`→`_b`, `pos_a`/`pos_b` invertidos onde aparece a comparação, `a_*`→`b_*`, índice `[0]`→`[1]`:

```python
        if stun_rem_b > 0:
            action_b = -1
        else:
            in_range = distance <= b_range
            if not in_range:
                action_b = 1
                persist_b = 0
            else:
                if persist_b == 0:
                    tot = b_wagg + b_wret + b_wdef
                    if tot <= 0.0:
                        commit_b = 2
                    else:
                        r = np.random.random() * tot
                        if r < b_wagg:
                            commit_b = 0
                        elif r < b_wagg + b_wret:
                            commit_b = 1
                        else:
                            commit_b = 2
                    persist_b = persist
                persist_b -= 1
                if commit_b == 0:
                    action_b = 0 if cd_rem_b == 0 else 1
                elif commit_b == 1:
                    step = b_speed / tick_scale
                    can_back = (pos_b - step >= 0.0) if pos_b < pos_a else (pos_b + step <= field_size)
                    action_b = 2 if can_back else 3
                else:
                    action_b = 3
            active_ticks[1] += 1
            action_counts[1, action_b] += 1
```
(na traced, sem as 2 linhas finais de contagem.)

- [ ] **Step 7: Atualizar os 2 call sites**

Em `src/engine/combat.py`, `_run_jit` (~linha 596) e `simulate_combat_traced` (~linha 627): remover os argumentos `float(WALL_CORNER_THRESHOLD)` e `float(HESITATION_RATE)` das chamadas, deixando:
```python
        float(FIELD_SIZE), float(INITIAL_DISTANCE),
        int(MAX_TICKS), float(TICK_SCALE), float(STUN_CAP_MULTIPLIER),
        float(DEFEND_DAMAGE_REDUCTION), int(ACTION_PERSISTENCE_SUBTICKS),
```

- [ ] **Step 8: Rodar testes**

```bash
py -m src.tests.test_combat; py -m src.tests.test_fitness; py -m src.tests.test_nsga2
```
Expected: PASS (incl. a nova asserção do rusher). Sem traceback de import (confirma que `HESITATION_RATE`/`WALL_CORNER_THRESHOLD` foram removidos limpo).

- [ ] **Step 9: Commit**

```bash
git add src/engine/combat.py src/engine/config.py src/tests/test_combat.py
git commit -m "refactor(combat): seleção de ação intenção→execução; remove hesitação e override de canto"
```

---

### Task 2: Migração de genes + física (stun-fração, drop defense/recovery, dano flat)

Mudança atômica do cromossomo (12→10) e da física. Ordem nova dos atributos: `hp, damage, attack_cooldown, range, speed, stun, knockback` (índices 0–6).

**Files:**
- Modify: `src/engine/config.py` (ATTRIBUTE_BOUNDS, ATTRIBUTE_NAMES, remover STUN_CAP_MULTIPLIER, INTEGER_ATTRIBUTES)
- Modify: `src/engine/archetypes.py` (AttributeSet, 5 canônicos)
- Modify: `src/engine/character.py` (Attr, properties, genes/load_genes, clip, repr, import)
- Modify: `src/engine/combat.py` (unpack, stun, dano, assinatura sem stun_cap_mult, 2 call sites)
- Modify: `src/tools/archetype_validator.py` (asserções e lista de atributos)
- Modify: `src/tests/test_base.py` (refs a defense)
- Test: suíte engine completa

**Interfaces:**
- Produces: `Attr.HP=0, DAMAGE=1, ATTACK_COOLDOWN=2, RANGE=3, SPEED=4, STUN=5, KNOCKBACK=6`. `Character.genes()` retorna 10 floats. `AttributeSet(hp, damage, attack_cooldown, range_, speed, stun, knockback)`.

- [ ] **Step 1: config.py — bounds, names, remover constantes**

Substituir `ATTRIBUTE_BOUNDS` por (7 entradas):
```python
ATTRIBUTE_BOUNDS = [
    (250.0, 450.0),  # hp
    (10.0, 20.0),    # damage
    (1.0, 5.0),      # attack_cooldown
    (5.0, 20.0),     # range
    (1.0, 5.0),      # speed
    (0.0, 0.6),      # stun (fração do cooldown)
    (0.0, 3.0),      # knockback
]
```
Remover o bloco de comentário de `INTEGER_ATTRIBUTES` e a linha `INTEGER_ATTRIBUTES = {8}`.
Remover a linha `STUN_CAP_MULTIPLIER = 0.6` e seu comentário.
Substituir `ATTRIBUTE_NAMES` por:
```python
ATTRIBUTE_NAMES = ["hp", "damage", "attack_cooldown", "range", "speed", "stun", "knockback"]
```

- [ ] **Step 2: archetypes.py — AttributeSet + canônicos**

`AttributeSet` (remover `defense` e `recovery`, ordem nova):
```python
@dataclass(frozen=True)
class AttributeSet:
    hp:              float
    damage:          float
    attack_cooldown: float
    range_:          float
    speed:           float
    stun:            float
    knockback:       float

    def __iter__(self):
        return iter(dataclasses.astuple(self))
```
Trocar os 5 `initial_attributes=AttributeSet(...)`:
```python
# Zoner
AttributeSet(hp=300.0, damage=12.0, attack_cooldown=4.0, range_=18.0, speed=2.5, stun=0.10, knockback=2.0)
# Rushdown
AttributeSet(hp=320.0, damage=11.0, attack_cooldown=1.0, range_=10.0, speed=5.0, stun=0.10, knockback=1.0)
# Combo Master
AttributeSet(hp=350.0, damage=13.0, attack_cooldown=3.0, range_=10.0, speed=3.0, stun=0.55, knockback=0.5)
# Grappler
AttributeSet(hp=400.0, damage=20.0, attack_cooldown=4.0, range_=8.0,  speed=2.0, stun=0.30, knockback=0.5)
# Turtle
AttributeSet(hp=450.0, damage=10.0, attack_cooldown=5.0, range_=13.0, speed=1.5, stun=0.20, knockback=1.0)
```

- [ ] **Step 3: character.py — índices, properties, genes, clip, repr**

`Attr`:
```python
class Attr:
    HP = 0
    DAMAGE = 1
    ATTACK_COOLDOWN = 2
    RANGE = 3
    SPEED = 4
    STUN = 5
    KNOCKBACK = 6
```
Remover as properties `defense` e `recovery`. Manter `stun` (→ `attributes[Attr.STUN]`) e `knockback` (→ `attributes[Attr.KNOCKBACK]`).
Import (linha 13): `from .config import ATTRIBUTE_BOUNDS, WEIGHT_BOUNDS` (remover `INTEGER_ATTRIBUTES`).
`load_genes`: `assert len(genes) == 10, ...`; `self.attributes = list(genes[:7])`; `self.weights = list(genes[7:])`.
`clip`: remover o `if i in INTEGER_ATTRIBUTES: val = float(round(val))`.
`repr`: lista de nomes `["hp","dmg","cd","rng","spd","stun","kb"]`.

- [ ] **Step 4: combat.py — unpack, stun, dano, assinatura**

Nas DUAS variantes, o desempacotamento vira:
```python
    a_hp_max = a_attrs[0]; a_dmg = a_attrs[1]; a_cd = a_attrs[2]
    a_range = a_attrs[3]; a_speed = a_attrs[4]; a_stun = a_attrs[5]; a_kb = a_attrs[6]
```
(idem `b_*`; remover `a_def/b_def/a_rec/b_rec`).

Bloco de stun/dano A→B (e idêntico B→A trocando letras), trocar:
```python
            dmg = a_dmg * (1.0 - b_def)
            if action_b == 3:
                dmg *= defend_red
            if dmg > 0.0:
                stun_t = round(a_stun * tick_scale) - int(b_rec)
                if stun_t < 0:
                    stun_t = 0
                cap = round(stun_cap_mult * a_cd * tick_scale)
                if stun_t > cap:
                    stun_t = cap
```
por:
```python
            dmg = a_dmg
            if action_b == 3:
                dmg *= defend_red
            if dmg > 0.0:
                stun_t = round(a_stun * round(a_cd * tick_scale))   # fração × cooldown_subticks; < cooldown por bound
```
Remover `stun_cap_mult` da assinatura das 2 variantes e dos 2 call sites (a linha `int(MAX_TICKS), float(TICK_SCALE), float(STUN_CAP_MULTIPLIER),` vira `int(MAX_TICKS), float(TICK_SCALE),`). Remover `STUN_CAP_MULTIPLIER` do import.

- [ ] **Step 5: archetype_validator.py — asserções e lista**

- Remover a linha de asserção de `recovery` (≈74) e a de `defense` (≈78).
- Remover a asserção intra de defense (≈123: `(TURTLE, "defense", "damage", ...)`).
- Atualizar a lista de nomes (≈107) para `["hp", "damage", "attack_cooldown", "range_", "speed", "stun", "knockback"]`.
- Conferir que a asserção "Combo Master maior stun" (se existir) permanece; manter as demais (speed do rushdown, hp do turtle, etc.).

- [ ] **Step 6: test_base.py — remover refs a defense**

Linhas ~30/84/86: tirar `Defense={...}` dos prints e a asserção `assert turtle.defense == ...`. Trocar por uma asserção viva equivalente, ex.: `assert turtle.stun == turtle_arch.initial_attributes.stun`.

- [ ] **Step 7: Adicionar asserções de invariante na suíte**

Em `src/tests/test_base.py` (ou test_combat), adicionar:
```python
ind = Individual.from_canonical()
assert len(ind.characters[0].genes()) == 10, "char deve ter 10 genes"
```
Em `src/tests/test_combat.py`, adicionar checagem de no-lock via trace:
```python
from src.engine.combat import simulate_combat_traced
tr = simulate_combat_traced(rush, zon)
import numpy as np
# stun aplicado nunca >= cooldown_subticks do atacante (janela livre garantida)
assert int(tr.stun.max()) < round(max(rush.attack_cooldown, zon.attack_cooldown) * 5), "stun não pode atingir o cooldown (lock)"
print("  ✓ sem stun-lock")
```

- [ ] **Step 8: Rodar a suíte engine completa**

```bash
py -m src.tests.test_base; py -m src.tests.test_combat; py -m src.tests.test_fitness; py -m src.tests.test_operators; py -m src.tests.test_nsga2; py -m src.tests.test_archetype_validator
```
Expected: todos PASS. Se algum importar `defense`/`recovery` → corrigir antes de seguir.

- [ ] **Step 9: Commit**

```bash
git add src/engine/config.py src/engine/archetypes.py src/engine/character.py src/engine/combat.py src/tools/archetype_validator.py src/tests/test_base.py src/tests/test_combat.py
git commit -m "refactor(combat): 10 genes (drop defense/recovery), stun fracionário, dano flat"
```

---

### Task 3: Tools — alinhar exibições ao novo cromossomo

**Files:**
- Modify: `src/tools/viewer.py` (linhas ~308-309)
- Modify: `src/tools/web_viewer.py` (linhas ~105-108, ~434-437)
- Verify-run: `analyze_matchups.py`, `drift_table.py`, `fingerprint.py`, `sensitivity_analysis.py`, `report.py`, `multi_run.py`, `external_validation.py`

**Interfaces:**
- Consumes: `Character` sem `.defense`/`.recovery`; `char.stun` agora é fração.

- [ ] **Step 1: viewer.py**

Linha ~308: remover `Def = {char.defense:.2f}` e ajustar o `Stun` (agora fração): `f"Stun  = {char.stun:.2f} (×cd)   Knock = {char.knockback:.1f}"`. Linha ~309: remover `Recup = {int(char.recovery)}`. Reorganizar as linhas do painel para não deixar rótulo órfão.

- [ ] **Step 2: web_viewer.py**

Linha ~105: remover `"defense": round(char.defense, 2),`. Linha ~108: remover `"recovery": int(char.recovery),`. No bloco JS de labels (~434-437): remover a linha `['Defesa', 'defense', ...]` e `['Recovery (sub-ticks)', 'recovery', ...]`; ajustar o label de stun para fração (ex.: `['Stun (×cooldown)', 'stun', v => v.toFixed(2)]`).

- [ ] **Step 3: Rodar cada tool no canônico (sem crash)**

```bash
py -m src.tools.report; py -m src.tools.analyze_matchups; py -m src.tools.drift_table; py -m src.tools.fingerprint; py -m src.tools.sensitivity_analysis
```
Expected: cada um roda e imprime sem `AttributeError`/`IndexError`. (Se `drift_table`/`fingerprint`/`sensitivity` indexarem genes por nome via `ATTRIBUTE_NAMES`, devem se ajustar sozinhos; se hardcodam defense/recovery, corrigir aqui.)

- [ ] **Step 4: Rodar viewer/web_viewer rapidamente**

```bash
py -m src.tools.viewer --evolved 2>/dev/null || py -m src.tools.viewer
```
Expected: renderiza o painel sem erro. (web_viewer: subir e abrir uma vez, conferir que o JSON dos personagens carrega; encerrar.)

- [ ] **Step 5: Commit**

```bash
git add src/tools/viewer.py src/tools/web_viewer.py
git commit -m "refactor(tools): remover defense/recovery das exibições; stun como fração"
```

---

### Task 4: Auditoria de código morto + handoff + suíte completa

**Files:**
- Modify: `C2_HANDOFF.md` (anexar seção de combate)
- Verify: repo inteiro

- [ ] **Step 1: Grep repo-wide dos símbolos removidos — esperar ZERO**

```bash
py - <<'PY'
import subprocess, sys
pats = ["defense","recovery","STUN_CAP_MULTIPLIER","HESITATION_RATE","WALL_CORNER_THRESHOLD","INTEGER_ATTRIBUTES","cornered","hesitate","a_def","b_def","a_rec","b_rec"]
bad=False
for p in pats:
    r=subprocess.run(["git","grep","-nI",p,"--","src/"],capture_output=True,text=True)
    if r.stdout.strip():
        bad=True; print(f"\n### {p}\n{r.stdout}")
print("\nLIMPO" if not bad else "\nAINDA HÁ REFERÊNCIAS — corrigir")
PY
```
Expected: `LIMPO`. Qualquer hit → remover/ajustar a referência (e re-rodar a suíte). Atenção a falsos-positivos benignos (ex.: a palavra "defense" em comentário de prosa) — mesmo esses devem sair para não enganar.

- [ ] **Step 2: Grep por contagens de gene hardcoded (12/9) que possam ter escapado**

```bash
git grep -nI "== 12\|genes\[:9\]\|genes\[9:\]\|\[8\]\|\[5\]" -- src/ | grep -vi test
```
Expected: nenhuma referência a índice de gene antigo (8=recovery, 5=defense) em `combat`/`character`/tools. Revisar manualmente os hits.

- [ ] **Step 3: Suíte smoke completa**

```bash
py -m src.tests.test_base; py -m src.tests.test_combat; py -m src.tests.test_fitness; py -m src.tests.test_operators; py -m src.tests.test_nsga2; py -m src.tests.test_archetype_validator
```
Expected: todos PASS.

- [ ] **Step 4: Smoke de ponta-a-ponta do AG e NSGA-II (config mínima)**

```bash
py - <<'PY'
from src.engine import ga, nsga2
r = nsga2.run(seed=42, pop_size=20, n_generations=3, verbose=False)
assert len(r.pareto_front) > 0
print("NSGA-II OK:", len(r.pareto_front), "no front")
PY
```
Expected: roda sem erro (valida que fitness/operators/combat fecham com 10 genes).

- [ ] **Step 5: Anexar seção de combate ao handoff**

Em `C2_HANDOFF.md`, adicionar uma seção "Combate (2026-06-27)" listando: o novo modelo intenção→execução, stun-fração, drop defense/recovery, dano flat, constantes removidas, 10 genes, e a lista de **textos a atualizar** na sessão de redação: `docs/reference/04-combat-model.md`, `03-archetypes.md`, `07-configuration.md`, `11-combat-review.md`, `CLAUDE.md` (Key Design Decisions + bounds), e o artigo (Tabela canônica, §3.2 combate, §3.3 representação). Marcar que **todas as rodadas foram invalidadas** (re-rodar após calibração).

- [ ] **Step 6: Commit**

```bash
git add C2_HANDOFF.md
git commit -m "docs(handoff): registrar mudanças de combate p/ a sessão de redação"
```

---

## Calibração (pós-plano, fora do escopo determinístico)

Depois do plano verde, **calibrar** olhando fingerprints/matchups (não é passo mecânico): re-tune dos canônicos (semântica de `w_agg` mudou; Turtle virou tanky-ativo), força do `stun` (bound 0.6), `MATCHUP_WR_CAP` (C2), `ACTION_PERSISTENCE_SUBTICKS`, e `TICK_SCALE` (subir p/ 10 só se aparecer platô). Depois, re-rodar `multi_run`/`external_validation` e regenerar resultados.

## Self-review (feito)

- **Cobertura do spec:** §3 ação → Task 1; §4 física + §5 genes → Task 2; tools (§7) → Task 3; auditoria/no-dead-code + docs deferidas → Task 4. ✓
- **Placeholders:** nenhum passo "TBD"; código concreto em todos os passos de engine; tools/peripherals têm linha exata + mudança (arquivos não relidos têm grep como rede). ✓
- **Consistência de tipos:** `Attr` (0–6), `AttributeSet` (7 campos), `genes()` 10, assinatura JIT sem `wall_corner/hesitation/stun_cap_mult` — coerentes entre Task 1 e 2. ✓
