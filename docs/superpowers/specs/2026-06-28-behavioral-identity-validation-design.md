# Validação de identidade comportamental (Layer 3) + limpeza de métrica

**Data:** 2026-06-28
**Status:** implementado (2026-06-28). Validado 21/21 no canônico; parity test verde.

## 1. Contexto e problema

O `archetype_validator` mede identidade **estrutural** (genes — atributos e pesos):
ranks inter-personagem (Turtle = mais HP, Zoner = maior range) e comparações
intra-personagem normalizadas. Isso responde "os genes certos estão lá?", mas **não**
responde a pergunta de pesquisa real: *o personagem ainda joga como o arquétipo?*

Os dois divergem na prática. Exemplo concreto descoberto nesta sessão: o Zoner tem
`w_retreat` alto (✓ estrutural), mas, encurralado na parede, sua intenção RECUAR vira
DEFEND (`combat.py`, mapeamento intenção→ação) — então a identidade de *kite* colapsa em
defesa. Um roster pode marcar 17/17 estrutural e mesmo assim ter identidade **funcional**
quebrada. Enquanto a validação for só de genes, o score não significa o que afirma.

O `fingerprint` já mede comportamento (mix de ações, % fora de range, % stunado), mas é
**descritivo** — não emite asserção de identidade — e algumas de suas métricas estão
**contaminadas por artefato** (encurralamento inflando DEFEND; ATK contado por sub-tick,
diluído pelo cooldown).

## 2. Objetivo e não-objetivos

**Objetivo:** adicionar ao `archetype_validator` uma **Layer 3 — Behavioral** que
comprove, com asserções de pass/fail, que cada personagem *joga* como seu arquétipo,
apoiada em métricas limpas de artefato. Mantém as Layers 1–2 estruturais (o usuário quer
**ambas** — a comparação de atributos continua significativa).

**Não-objetivos (follow-up — ver §7):**
- Split do balde ADV (mesma contaminação do DEFEND, mas não alimenta asserção).
- Consolidação/simplificação geral das tools (spec próprio, futuro).
- Adicionar mecânica de grab (mudança de combate, fora deste escopo).

## 3. Decisões de design (validadas)

1. **Identidade = padrão de ações + comparação estrutural de atributos.** As duas camadas
   coexistem; a comportamental é adicionada, não substitui.
2. **Asserções rank-entre-os-5** (igual à Layer 1): robustas, sem calibrar limiar,
   sobrevivem a mudanças de escala do combate.
3. **Uma asserção primária e limpa por arquétipo** — nada de empilhar sinais redundantes
   ou fracos.
4. **Limpar contaminação só onde ela alimenta uma asserção.** DEFEND→Turtle e ATK→Rushdown
   são obrigatórios (decidem a corretude do validador). Contaminação de métricas
   puramente descritivas (ADV) é cosmética e fica para follow-up.
5. **Grappler não recebe asserção comportamental.** O combate não tem mecânica de
   grab/throw, então a identidade canônica do Grappler ("grab pune bloqueio e fuga") não
   tem representação mecânica — comportamentalmente ele só sobrepõe ao espaço do Rushdown
   (corpo-a-corpo). O relatório marca explicitamente "sem assinatura comportamental —
   mecânica ausente". Achado honesto a registrar na tese: 4 de 5 identidades se expressam
   funcionalmente; a do Grappler não, por falta de mecânica.

## 4. Arquitetura

### 4.1 Refactor `_decide_action` (4 cópias → 1) + parity test

Hoje o bloco de escolha de ação existe em **4 cópias idênticas**: lutador A e B
(desenrolado) × JIT de fitness (`_simulate_combat_jit`) e JIT traced
(`_simulate_combat_traced_jit`). É sincronia mantida na mão — e a credibilidade do
validador comportamental depende do traced simular **exatamente** o mesmo combate que o
fitness evolui. Como vamos instrumentar justamente esse bloco, extrair primeiro:

```python
@njit
def _decide_action(in_range, persist, commit, wagg, wret, wdef,
                   cd_rem, pos, opp_pos, speed, field_size, persist_max):
    # retorna (action, persist, commit, forced_defend)
```

Chamado para A e B nas **duas** variantes (4 cópias → 1). O `forced_defend` (RECUAR sem
espaço de recuo → DEFEND) sai como valor de retorno natural, em vez de um contador
paralelo. numba chama njit de dentro de njit e inlina funções pequenas — performance não
deve mudar. **Não** mexer em movimento / resolução de ataque / decremento de timers
(corretos, fora de escopo).

**Parity test** (novo): para um conjunto de seeds, `_simulate_combat_jit` e
`_simulate_combat_traced_jit` devem produzir desfecho idêntico (winner, end_tick, ko, HP
final). Protege contra divergência futura entre as variantes — vale ter
independentemente do refactor.

### 4.2 Instrumentação do split do DEFEND (única mudança de combate)

O `action` array do trace registra DEFEND (código 3) mas **não** distingue GUARDA
(escolhido) de RECUAR-encurralado (forçado). Adicionar ao trace um registro por tick do
`forced_defend` devolvido pelo `_decide_action` (nova array `forced_defend_arr[tick, i]`
no traced JIT, exposta no `CombatTrace`). O JIT de fitness **não** precisa disso (não
traça) — a instrumentação fica isolada na variante traced.

### 4.3 Métricas que já existem (reuso, sem mudança de combate)

Confirmado em `analyze_matchups.FighterStats` / `MatchupResult`:

| Métrica da asserção | Fonte já existente |
|---|---|
| `mean_dist` (Zoner) | `MatchupResult.avg_distance` |
| `atk_landed` (Rushdown) | `FighterStats.hits_landed` |
| `stun_inflicted` (Combo) | `FighterStats.stun_applied` |
| `def_chosen` (Turtle) | **novo** — derivado do split §4.2 |

`FighterStats` ganha um campo `defend_forced` (populado a partir do `forced_defend_arr`);
`defend_chosen` = `action_counts[DEFEND] − defend_forced`.

### 4.4 Agregação comportamental por personagem (compartilhada)

A Layer 3 precisa do comportamento **agregado por personagem sobre seus 4 matchups** — a
mesma agregação que `fingerprint._fingerprint()` já faz. Extrair essa agregação para um
helper compartilhado, consumido tanto pelo `fingerprint` quanto pela Layer 3, evitando
duplicação (e já alinhando com a futura consolidação de tools). O helper devolve, por
arquétipo, o dicionário de métricas comportamentais médias (incluindo `mean_dist`,
`atk_landed`, `stun_inflicted`, `def_chosen`, `def_forced`).

### 4.5 Layer 3 no `archetype_validator`

Espelha a estrutura das Layers 1–2: lista de asserções `(arquétipo, métrica, rank
esperado, descrição)`, ranqueia os 5 valores, compara rank real vs esperado, entra no
mesmo `ArchetypeValidationReport` e no mesmo relatório/score. O Grappler aparece na seção
com a marcação "sem assinatura comportamental — mecânica ausente" (não conta como
pass nem como fail; fica fora do denominador da Layer 3).

### 4.6 Atualização do `fingerprint`

- Trocar a linha "ATK" (estado ATTACK por sub-tick) por **`atk_landed`** (ataques que
  conectam por luta) — métrica de output, livre da diluição sub-tick.
- Dividir a linha "DEF" em **DEF escolhido** e **DEF forçado** (encurralamento), expondo o
  artefato em vez de escondê-lo.
- Demais métricas (ADV, RET, oor, % stunado) mantidas. RET fica naturalmente mais limpa
  (o caso encurralado migrou para `def_forced`).

## 5. Asserções da Layer 3

| Arquétipo | Asserção | Métrica | Rank |
|---|---|---|---|
| Zoner | luta da maior distância | `mean_dist` (`avg_distance`) | 1 |
| Rushdown | mais ataques conectados por luta | `atk_landed` (`hits_landed`) | 1 |
| Turtle | mais DEFEND escolhido | `def_chosen` | 1 |
| Combo Master | mais stun aplicado no oponente | `stun_inflicted` (`stun_applied`) | 1 |
| Grappler | — sem asserção (mecânica de grab ausente) | — | — |

## 6. Testes e verificação

- **Parity test** (§4.1): fitness-JIT vs traced-JIT, mesmo desfecho para N seeds.
- **Smoke**: os testes existentes continuam passando (`test_combat`, etc.).
- **Sanity no canônico**: rodar `fingerprint`/`validator` no canônico — os Δ do fingerprint
  ficam ~0 (já é a convenção); a Layer 3 no canônico serve de baseline de identidade.
- **Compilação numba**: confirmar que o `_decide_action` compila e que o tempo de execução
  do round-robin não regrediu de forma perceptível.

## 7. Fora de escopo / follow-ups

- **Split do ADV** no fingerprint (balde que mistura avanço-fora-de-range + FRENTE-sem-cd
  + aproximação). Mesma contaminação do DEFEND, mas não alimenta asserção → cosmético.
  Vai para o spec futuro de **revisão/consolidação total das tools**.
- **Consolidação das tools** (concentrar num lugar, remover dados desnecessários e
  repetidos) — spec próprio.
- **Mecânica de grab** para dar identidade comportamental ao Grappler — mudança de combate,
  decisão separada.

## 8. Arquivos afetados

- `src/engine/combat.py` — extrair `_decide_action`; `forced_defend` no traced JIT;
  `CombatTrace` ganha `forced_defend` (array por tick).
- `src/tools/analyze_matchups.py` — `FighterStats.defend_forced`; popular a partir do
  trace; `defend_chosen` derivado.
- `src/tools/fingerprint.py` — usar `atk_landed`; dividir DEF; usar o helper de agregação
  compartilhado.
- `src/tools/archetype_validator.py` — Layer 3 (asserções, ranqueamento, relatório,
  tratamento do Grappler).
- helper de agregação comportamental compartilhado (em `analyze_matchups` ou módulo novo).
- `src/tests/` — parity test; (opcional) teste da Layer 3.
- Docs: atualizar `docs/reference/` (combate/tools) e o CLAUDE.md ao final.
