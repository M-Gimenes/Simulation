# Design — Simplificação e reestruturação do combate

**Data:** 2026-06-27
**Status:** aprovado para implementação (pendente revisão deste spec)
**Relacionado:** `C2_HANDOFF.md` (reformulação C2 do fitness, já implementada no motor)

## 1. Objetivo

Deixar o combate **mais polido, organizado e simples**, mantendo 100% do que o
sistema precisa: (a) 5 identidades distintas, (b) gradiente contínuo de WR para o AG
(necessário ao C2), (c) textura de interação suficiente para um ciclo de vantagens
*poder* emergir (métrica post-hoc).

Dois eixos de mudança: **seleção de ação** (mover o ruído pro nó decisivo, eliminar
gambiarras) e **enxugamento de genes/mecânicas** (cortar redundância e o cluster
barroco de stun) sem perder identidade.

## 2. Decisões (origem: entrevista de brainstorming)

| Tema | Decisão |
|---|---|
| Seleção de ação | Modelo **intenção → execução** (ver §3). Ruído no nó em-range. |
| Hesitação | **Removida** (`HESITATION_RATE`) — subsumida pela amostragem de intenção. |
| Override de canto | **Removido** (`WALL_CORNER_THRESHOLD`) — escape de canto vira emergente. |
| Stun | **Fração do cooldown** (gene ∈ [0, 0.6]); remove `recovery`, `STUN_CAP_MULTIPLIER` e o clamp. |
| Tankiness | **Dropar `defense` passivo**; dano flat; tankiness = `hp` (bound alargado) + ação DEFEND. |
| Knockback | **Mantido** (operação limpa, única, justa). |
| `w_aggressiveness` | Vira intenção **FRENTE** (ATTACK se alcança, senão ADVANCE) — mantido junto de propósito. |
| `TICK_SCALE` | **5** (dial de resolução vs custo; subir só se aparecer platô empírico). |
| Cromossomo | **12 → 10 genes** (7 atributos + 3 pesos). |

## 3. Modelo de seleção de ação

Por sub-tick, se o personagem não está stunado. **`persist` guarda a *intenção*, não a
ação** — a intenção é o plano estável; a ação é re-derivada a cada subtick conforme a
situação.

```
in_range = distancia <= range

se NÃO in_range:
    ação = ADVANCE                         # neutral game: chega no próprio range
    persist = 0                            # ao entrar em range, decide fresco
senão:
    se persist == 0:
        intenção = amostra_ponderada({ FRENTE: w_agg, RECUAR: w_ret, GUARDA: w_def })
        persist  = ACTION_PERSISTENCE_SUBTICKS
    persist -= 1

    se intenção == FRENTE:  ação = ATTACK  se cd pronto, senão ADVANCE
    se intenção == RECUAR:  ação = RETREAT se dá pra recuar, senão DEFEND
    se intenção == GUARDA:  ação = DEFEND
```

`dá pra recuar` = o passo de recuo não bate na parede (não clampa em `[0, FIELD_SIZE]`).
Sem constante de threshold.

### Tabela de casos (a especificação completa do comportamento)

| Situação | Ação | Por quê |
|---|---|---|
| Fora do meu range | ADVANCE | tem que chegar no range pra lutar (neutral game) |
| Em range · FRENTE · cd pronto | ATTACK | bate |
| Em range · FRENTE · cd não pronto | ADVANCE | mantém pressão (rusher cola; atravessa se na parede) |
| Em range · RECUAR · tem espaço atrás | RETREAT | abre distância (zoner kita) |
| Em range · RECUAR · contra a parede | DEFEND | não dá pra abrir indo pra trás → segura, **não anda pra frente** |
| Em range · GUARDA | DEFEND | segura posição |

### Propriedades garantidas

- **Engajamento**: dois defensivos não ficam recuando para sempre — fora de range é
  ADVANCE forçado.
- **Ruído no nó decisivo**: a única fonte estocástica é a amostra de intenção em range,
  alimentando a WR graduada que o C2 precisa.
- **Escape de canto sem pulo (emergente)**: encurralado, o personagem defende (RECUAR/
  GUARDA → DEFEND, sobrevive com −60% dano) e atravessa pro outro lado nas amostras de
  FRENTE (cd longo ⇒ FRENTE vira ADVANCE). Sem override, sem morte certa.
- **Rusher mantém pressão**: FRENTE→ADVANCE em cooldown mantém o rusher colado; o zoner
  (w_agg baixo) kita. ADVANCE na intenção é o que diferencia os dois nos cooldowns.

## 4. Física (resolução de ataque)

- **Stun fracionário.** `stun_efetivo_subticks = round(stun × cooldown_subticks)`, com
  `cooldown_subticks = round(cooldown × TICK_SCALE)` e `stun ∈ [0, 0.6]`. Sem
  `recovery`, sem `STUN_CAP_MULTIPLIER`, sem clamp. Lock impossível por bound
  (0.6 < 1 ⇒ sempre sobra janela ≥ 40% do cooldown). Aplicação mantém semântica de
  máximo (`if stun_efetivo > stun_rem: ...`).
- **Dano flat.** `dano_efetivo = damage × (DEFEND_DAMAGE_REDUCTION se defendendo senão 1.0)`.
  Sai o `× (1 − defense)`.
- **Knockback**: inalterado (resolução simultânea com distância pré-ataque — justa, sem
  viés de ordem).
- **Movimento, cooldown, decremento stale, vitória (KO / HP-share)**: inalterados.

## 5. Cromossomo: 7 atributos + 3 pesos = 10 genes

| Gene | Bound | Nota |
|---|---|---|
| hp | **[250, 450]** | alargado p/ recuperar alcance de EHP perdido com `defense` |
| damage | [10, 20] | igual |
| attack_cooldown | [1, 5] | igual |
| range | [5, 20] | igual |
| speed | [1, 5] | igual |
| **stun** | **[0.0, 0.6]** | nova semântica: fração do cooldown |
| knockback | [0, 3] | igual |
| w_retreat / w_defend / w_aggressiveness | [0, 1] | igual |

**Removidos:** `defense`, `recovery`.

### Canônicos iniciais (ponto de partida — re-tunar via fingerprints)

| Arquétipo | hp | dmg | cd | range | speed | stun(frac) | kb | w_ret | w_def | w_agg |
|---|---|---|---|---|---|---|---|---|---|---|
| Zoner | 300 | 12 | 4 | 18 | 2.5 | 0.10 | 2.0 | 0.60 | 0.20 | 0.30 |
| Rushdown | 320 | 11 | 1 | 10 | 5.0 | 0.10 | 1.0 | 0.05 | 0.10 | 0.90 |
| Combo Master | 350 | 13 | 3 | 10 | 3.0 | 0.55 | 0.5 | 0.05 | 0.20 | 0.70 |
| Grappler | 400 | 20 | 4 | 8 | 2.0 | 0.30 | 0.5 | 0.10 | 0.40 | 0.70 |
| Turtle | 450 | 10 | 5 | 13 | 1.5 | 0.20 | 1.0 | 0.40 | 0.70 | 0.20 |

> Combo Master = maior `stun` (identidade de lockdown). Turtle/Grappler com mais `hp`
> (compensa a perda do `defense` passivo). Valores a calibrar olhando os fingerprints,
> porque (a) `w_agg` mudou de semântica (atacar/avançar) e (b) Turtle virou tanky-ativo.

## 6. Constantes de config

- **Removidas:** `STUN_CAP_MULTIPLIER`, `HESITATION_RATE`, `WALL_CORNER_THRESHOLD`,
  `INTEGER_ATTRIBUTES` (recovery era o único membro).
- **Alteradas:** `ATTRIBUTE_BOUNDS` (remove defense/recovery, alarga hp, redefine stun).
- **Mantidas:** `TICK_SCALE=5`, `ACTION_PERSISTENCE_SUBTICKS`, `DEFEND_DAMAGE_REDUCTION`,
  `FIELD_SIZE`, `INITIAL_DISTANCE`, `MAX_TICKS`.

## 7. Raio de impacto

- `combat.py` — reescrever a seleção de ação (intenção→execução) e a resolução de stun/
  dano, nas **duas** variantes JIT (`_simulate_combat_jit`, `_simulate_combat_traced_jit`).
  Remover params `hesitation`, `stun_cap_mult`, `wall_corner`; remover `recovery`/`defense`
  dos atributos desempacotados.
- `config.py` — §6.
- `archetypes.py` — `AttributeSet` perde `defense`/`recovery`; novos canônicos; stun como fração.
- `character.py` — índices de `Attr` (9→7), `load_genes`/`genes` (12→10), remover integer-clip.
- `fitness.py` — `_archetype_deviation`/drift recalculam sozinhos (menos genes); conferir `_ATTR_MAXES`.
- `archetype_validator.py` — remover asserções de `defense`/`recovery`; manter "CM maior stun"; revisar.
- `fingerprint.py`, `drift_table.py`, `sensitivity_analysis.py`, `viewer.py`, `web_viewer.py`,
  `analyze_matchups.py` — remover colunas/refs de defense/recovery; stun reinterpretado.
- Testes: `test_combat`, `test_base`, `test_fitness`, `test_operators`, `test_archetype_validator`,
  `test_nsga2` — ajustar contagem de genes e asserções.
- **Docs + artigo**: atualizar junto do `C2_HANDOFF.md` (mesma rodada de redação).
- **Invalida todas as rodadas** → re-rodar tudo após calibração.

## 8. Testes (smoke, padrão do projeto)

- `test_combat`: luta roda sem crash; KO/timeout coerentes; **nenhum lock infinito**
  (stun_efetivo < cooldown sempre); cornered escapa (atravessa) em vez de morrer preso.
- `test_base`/`character`: indivíduo tem 10 genes/char; clip respeita novos bounds.
- Comportamento on-concept (via fingerprint manual): rusher ATK/ADV alto; zoner RET alto;
  turtle DEF alto; CM com mais tempo-stunando o oponente.
- Conferir que `stun ∈ [0,0.6]` nunca produz janela livre ≤ 0.

## 9. Riscos e calibração (pós-implementação)

- **Re-tune dos canônicos** (semântica de `w_agg` mudou; Turtle tanky-ativo).
- **`MATCHUP_WR_CAP` (C2)**, **força do stun (bound 0.6)**, **`ACTION_PERSISTENCE_SUBTICKS`**,
  **`TICK_SCALE`** — dials a calibrar olhando matchups/fingerprints/WR.
- Mais timeouts possíveis (ataque não-forçado) → resolução HP-share fica mais usada
  (efeito bom: score contínuo p/ o gradiente C2).
- Possível overshoot cosmético (FRENTE→ADVANCE em range atravessa no ponto-blank) — aceito.

## 10. O que NÃO muda (pontos fixos)

Soft-policy ponderada contínua, persistência (momentum), CRN/seeding do combate, JIT como
única implementação, fitness C2 (global + cap + decisividade), NSGA-II, 5 arquétipos +
ciclo post-hoc.
