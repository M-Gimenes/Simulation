# Handoff C2 — reformulação do equilíbrio (global em vez de por-matchup)

> **Arquivo temporário.** Documenta as mudanças de **código** feitas na sessão de
> 2026-06-27 para a próxima sessão **corrigir os textos** (artigo, docs, CLAUDE.md) e
> **realinhar as tools de reporting**. Apagar depois que textos + tools estiverem
> alinhados.

---

## 1. O que mudou conceitualmente (a decisão "C2")

**Problema diagnosticado.** O `dominance_penalty` antigo tinha como termo primário o
desbalanço de WR **por-matchup** (`|WR_par − 0.5|/0.5`, sem banda morta). O ótimo
desse termo é *todo par a 50%* — equilíbrio **plano**, que por construção é
**incompatível com o ciclo de vantagens** (um ciclo exige que pares tenham vencedor).
Otimizar aquilo destruía o ciclo, e a quebra era explicada (no artigo) como "mecânicas
omitidas" — explicação correta só para o baseline, errada para o indivíduo balanceado.

Observação do autor que originou a correção: a ideia *original* da WR era medir o
**global do boneco** (ele pode estar 50% global e ainda vencer 2 / perder 2 = ciclo).
Isso existia só como diagnóstico (`FitnessDetail.winrates`) e havia sumido do objetivo.

**C2 (escolhida).** Equilíbrio = **nenhum boneco globalmente dominante** (WR global →
50%), **não** cada par a 50%. Mais um **teto de hard-counter** (impede counters
esmagadores tipo 100×0, mantendo as arestas do ciclo como *vantagens* dentro de uma
banda) e a **fórmula** da decisividade inalterada (os valores da banda foram ajustados depois). Tudo continua **cego à direção** —
o ciclo segue métrica **post-hoc**, não codificado. Resultado: o ciclo passa a ser
**expressável** pelo sistema; "o ciclo emerge das identidades preservadas?" vira o
achado real (e C2 é robusto ao próprio fracasso: se emergir, ótimo; se o plano
dominar mesmo com espaço, isso também é achado honesto).

---

## 2. Nova fórmula do `dominance_penalty` (já no código)

```
dominance = GLOBAL_W · global_term  +  CAP_W · cap_term  +  DECIS_W · decis_term

global_term = RMS_{i=1..5}  ( |WR_global_i − 0.5| / 0.5 )                       # PRIMÁRIO
cap_term    = RMS_{pares=1..10} ( max(0, |WR_par − 0.5| − MATCHUP_WR_CAP) / (0.5 − MATCHUP_WR_CAP) )  # teto hard-counter
decis_term  = RMS_{pares=1..10} ( decisividade fora de [MATCHUP_FLOOR, MATCHUP_THRESHOLD] )           # qualidade (inalterado)
```

com `GLOBAL_W=1.0`, `CAP_W=0.5`, `DECIS_W=0.5`. Máximo teórico do `dominance` = **2.0**
(era 1.5). Todos os termos são RMS de excessos normalizados em ~[0,1].

Sanity check empírico (canônico, `test_fitness`): `dominance ≈ 1.34`, `drift = 0`
(calculado sob a banda anterior 0.10/0.05; aproximado).
Coerente — Grappler 100% / Zoner ~1% global puxam `global_term`; os 10 blowouts puxam
`cap_term` e `decis_term`.

---

## 3. Mudanças de código já aplicadas (esta sessão)

### `src/engine/config.py`
- **Removido:** `DOMINANCE_WR_WEIGHT`.
- **Adicionado:** `DOMINANCE_GLOBAL_WEIGHT = 1.0`, `DOMINANCE_CAP_WEIGHT = 0.5`,
  `MATCHUP_WR_CAP = 0.20` (banda hard-counter = [0.30, 0.70]; ajustado pelo usuário; provisório),
  `GLOBAL_CONVERGENCE_THRESHOLD = 0.10`.
- **Mantido:** `DOMINANCE_DECIS_WEIGHT = 0.5`, `MATCHUP_THRESHOLD = 0.20`,
  `MATCHUP_FLOOR = 0.10` (ajustados pelo usuário; provisórios).
- **`MATCHUP_CONVERGENCE_THRESHOLD = 0.10`:** mantido, mas **agora só usado pelas
  tools** (reporting secundário "matchup apertado"). O AG **não** usa mais.
- **`HYPERVOLUME_REFERENCE`:** `(1.5, 1.0)` → **`(2.0, 1.0)`** (novo máx de dominance).

> **Todos os valores de peso/cap são PROVISÓRIOS — calibrar.** `MATCHUP_WR_CAP=0.30`
> em especial define quão "duras" as arestas do ciclo podem ser (0.25 mais rígido,
> 0.35 mais permissivo).

### `src/engine/fitness.py`
- Imports: troca `DOMINANCE_WR_WEIGHT` por `DOMINANCE_GLOBAL_WEIGHT`,
  `DOMINANCE_CAP_WEIGHT`, `MATCHUP_WR_CAP`.
- `_dominance_penalty(...)`: **nova assinatura** `(winrates, matchup_winrates,
  matchup_decisiveness)` — passou a receber a WR global por boneco. Corpo reescrito
  conforme §2 (docstring atualizada).
- Call site em `evaluate_detail_n`: passa `winrates` (já calculado logo acima).
- `FitnessDetail` **não mudou** (mantém `winrates` por boneco e `matchup_winrates`).
  Decisão consciente de não adicionar campos de breakdown (global/cap/decis) — manter
  enxuto. Se o artigo quiser reportar o breakdown, adicionar lá.

### `src/engine/ga.py`
- Imports: troca `MATCHUP_CONVERGENCE_THRESHOLD` por `GLOBAL_CONVERGENCE_THRESHOLD` e
  `MATCHUP_WR_CAP`.
- Convergência: gate inalterado (`dominance_penalty <= 1e-9`); a **confirmação**
  deixou de exigir "todo par a 50%" e passou a exigir **(a)** todo boneco com WR
  global dentro de `GLOBAL_CONVERGENCE_THRESHOLD` de 50% **e (b)** nenhum par além de
  `MATCHUP_WR_CAP` (sem counter duro). Docstring do módulo atualizada.

### `src/engine/nsga2.py`
- **Sem mudança de código** — herda `dominance_penalty` via `evaluate_objectives`. Só
  o ponto de referência do HV (em config) mudou.

### Testes (já passando)
- `src/tests/test_nsga2.py`: imports + `dom_max = GLOBAL + CAP + DECIS` (= 2.0).
- `src/tests/test_fitness.py`: assert de range do fitness afrouxado p/ `-4.0 < f <= 0`
  (dom agora vai até ~2.0).
- `test_fitness` e `test_nsga2` **passam**; `ga.py` e as tools importam OK.

---

## 4. PENDENTE — tools de reporting (NÃO tocadas; alinhar junto com os textos)

Estas ainda reportam a métrica antiga ("confronto equilibrado = |WR_par − 0.5| ≤
0.10"), que sob C2 deixou de ser o headline. Não quebram, mas **enganam** se lidas como
antes. Realinhar:

- **`src/tools/multi_run.py`** (`_seed_record`/`_aggregate`/`_print_summary`):
  headline deve virar **por personagem** (fração de sementes com WR global em
  [0.40,0.60]) + **contagem de hard-counters** (pares fora de [0.20,0.80]); "all
  balanced" = 5 bonecos equilibrados **e** 0 counters duros. Banda por-matchup vira
  leitura secundária.
- **`src/tools/external_validation.py`** (`_condition_record`/`_aggregate`/
  `_print_summary`): "robusto" deve ser **WR global por boneco** dentro da banda em
  *todas* as condições + sem counter duro emergente — não mais "matchup ±10%".
  Atenção: o JSON commitado de external_validation está **obsoleto** (gerado pré-C2).
- **`src/tools/analyze_matchups.py`** (`classify_balance`, `BAL_LO/BAL_HI`,
  `DOMINANCE_THRESHOLD`): hoje marca 70-30 como "✗ desbalanceado"; sob C2 isso é
  **aresta de ciclo**, não falha. Repontuar o veredito por-par para
  `MATCHUP_WR_CAP` (✗ só = counter duro) e manter WR global por boneco (alvo 50%) +
  ciclo como leitura estrutural principal.

Sugestão: extrair os dois predicados para uma fonte única (ex.: helpers no
`fitness.py`) e fazer tools + `ga.py` consumirem — evita banda hardcoded espalhada.
(Não fiz agora para não introduzir helper sem consumidor antes de o reporting ser
redesenhado.)

---

## 5. PENDENTE — textos a reescrever

Todos os **resultados são `\ph{}` placeholders** e **todas as rodadas estão
invalidadas** (mudou o objetivo) — re-rodar tudo (`report`, `multi_run`,
`external_validation`, fronteira/HV) depois de calibrar.

- **`overleaf/artigo-SBC/main.tex`:**
  - Abstract + resumo: "balanced matchups (\ph{eq-*})" — redefinir métrica de sucesso
    para **equilíbrio global + estrutura do ciclo**.
  - §3.5 "Desbalaço (*dominance*)" e **Eq. (2)**: reescrever para a fórmula §2 (global
    primário + teto hard-counter + decisividade). Hoje descreve WR por-matchup.
  - Tabela 2 ("Conf. eq. = pares com WR em [40,60]"): redefinir coluna/critério.
  - §4.1/§4.4 + Limitações: o enquadramento "ciclo quebra ⟹ mecânicas omitidas" muda.
    Separar as **duas quebras**: (1) baseline (modelo de combate — segue válido) vs
    (2) pós-balanceamento (sob C2 o plano **não** força mais a quebra; emergência do
    ciclo vira achado). Atualizar ref. do HV para (2.0, 1.0).
- **`docs/reference/05-genetic-algorithm.md`:** fórmula do `dominance_penalty`.
- **`docs/reference/07-configuration.md`:** tabela de constantes (novas/removida/cap/HV).
- **`docs/reference/03-archetypes.md`:** nota do ciclo (agora expressável; emergência
  post-hoc).
- **`docs/reference/11-combat-review.md`:** a atualização de 2026-06-24 ("WR voltou
  como termo primário por-matchup") foi **superada** por C2 — anexar nota.
- **`docs/tcc/02-ciclo-canonico.md`:** papel do ciclo migra de "palco que quebra" para
  "estrutura expressável cuja emergência é o achado".
- **`CLAUDE.md`** (seção *Key Design Decisions* + *Hyperparameters*): descrição do
  `dominance_penalty`, "Two fitness terms", "Direction-blind dominance", "Convergence
  criteria" e bullets de hiperparâmetros.

---

## Combate (2026-06-27)

### Novo modelo de combate: intenção → execução

O loop JIT foi reescrito em duas fases por tick:

**Fase 1 — Intenção (quando em range):** o personagem sorteia uma *intenção*
(`FRENTE / RECUAR / GUARDA`) via `random.choices` ponderado por
`(w_aggressiveness, w_retreat, w_defend)`, mantida por `ACTION_PERSISTENCE_SUBTICKS`
ticks (comprometimento/momentum).

**Fase 2 — Execução:** a intenção determina a ação concreta:
- `FRENTE` → `ATTACK` se cooldown=0, senão `ADVANCE` (pressão sem desperdício de cooldown)
- `RECUAR` → `RETREAT` se houver espaço, senão `DEFEND` (encurralado)
- `GUARDA` → `DEFEND`

Fora do range próprio: `ADVANCE` incondicional (neutral game).

O modelo anterior tinha 4 prioridades hierárquicas independentes (ATTACK → ADVANCE →
COMMITMENT → NEW SOFT POLICY) com hesitação (`HESITATION_RATE`) como segunda fonte
estocástica. O novo modelo **elimina a hesitação** — estocasticidade vem apenas do
sorteio de intenção, que nunca interrompe uma intenção em andamento (sem flip-flop
por tick).

### stun como fração

```python
stun_t = round(a_stun * round(a_cd * tick_scale))
```

`stun` agora é uma **fração do próprio cooldown do atacante** em sub-ticks (bound
`[0.0, 0.6]`). Antes era valor absoluto em sub-ticks independente do cooldown.
Consequência: stun aplicado é **sempre < cooldown do atacante**, garantindo janela de
ação livre ao defensor. O `STUN_CAP_MULTIPLIER` explícito foi removido — o bound de
gene (`stun < 1.0`) garante a invariante matematicamente.

### defense e recovery removidos

- **`defense`** (redução passiva de dano) foi removido dos genes e do JIT. Dano agora
  é flat: `dmg = a_dmg`, modificado apenas pela ação `DEFEND` (que aplica
  `DEFEND_DAMAGE_REDUCTION`). O gene `defense` não existe mais — 7 atributos, não 9.
- **`recovery`** (subtração de stun recebido) foi removido dos genes e do JIT. Stun
  bruto é aplicado diretamente (sujeito ao bound de fração acima).

### Constantes removidas de config.py

| Constante             | Motivo                                              |
|-----------------------|-----------------------------------------------------|
| `HESITATION_RATE`     | Hesitação eliminada — estocasticidade só via intenção |
| `WALL_CORNER_THRESHOLD` | Cornering removido — RETREAT recua até borda (0/FIELD_SIZE) |
| `STUN_CAP_MULTIPLIER` | Cap garantido pelo bound do gene (`stun < 1.0`)     |
| `INTEGER_ATTRIBUTES`  | `recovery` (único int) foi removido                 |

### 10 genes por personagem

Antes: 9 atributos (`hp, damage, cooldown, range, speed, defense, stun, recovery, knockback`)
       + 3 pesos = **12 genes**.

Agora: 7 atributos (`hp, damage, cooldown, range, speed, stun, knockback`)
       + 3 pesos = **10 genes**. Individuo = 5 × 10 = **50 genes** total.

`stun` passou de índice 6 para índice 5 no array de atributos (ver `Attr` em
`character.py`). O índice `[5]` em `combat.py` é válido (stun novo).

---

### Auditoria de código morto — resultado: LIMPO

Grep em `src/` para os símbolos removidos:
`defense, recovery, STUN_CAP_MULTIPLIER, HESITATION_RATE, WALL_CORNER_THRESHOLD,
INTEGER_ATTRIBUTES, cornered, hesitate, a_def, b_def, a_rec, b_rec`

**Resultado: nenhum hit.** O código está limpo.

Índices de gene verificados:
- `[8]` (índice antigo de recovery) → nenhum hit em `src/` ✓
- `[5]` → todos os hits são `a_stun`/`b_stun` (índice atual de stun, válido) ✓
- `== 12` → único hit é `test_archetype_validator.py:79` (conta de asserções, não genes) ✓

---

### Suíte de testes — resultado: todos passam

```
test_base              ✓ (10 genes OK, 50 genes/individual OK)
test_combat            ✓ (stun-lock invariant + seed_combat + traced)
test_fitness           ✓ (range -4.0 < f <= 0, cache, invalidação)
test_operators         ✓ (torneio, cruzamento, mutação, nova geração)
test_nsga2             ✓
test_archetype_validator ✓
NSGA-II e2e (3 gens)   ✓ (16 no front)
```

---

### Flavor text estale em archetypes.py — listar, NÃO reescrever agora

As `description` dos arquétipos referenciam mecânicas removidas. Decisão de redação —
ajustar na sessão de textos:

| Arquétipo    | Trecho estale                                                           | Mecânica removida |
|--------------|-------------------------------------------------------------------------|-------------------|
| **Rushdown** | "Se ferra contra alta defesa e personagens que absorvem pressão."       | `defense` (passivo) |
| **Grappler** | "Recuperação alta resiste aos combos adversários."                      | `recovery`          |
| **Turtle**   | "Perde para quem quebra a defesa com stun."                             | `defense` (passivo) |

---

### Textos a atualizar na próxima sessão de redação

**CLAUDE.md:**
- Seção "Priority-based action selection" (~linhas 154-162): descreve o modelo antigo
  de 4 prioridades hierárquicas. Substituir pela descrição intenção→execução acima.
- Seção "Action persistence": menciona que ATTACK/cornered interrompem commitment.
  Cornering não existe mais; o novo modelo mantém intenção até o fim do contador.
- Seção "Architecture" (combat.py): lista hesitação como "2ª fonte de estocasticidade".
  Remover — única fonte agora é o sorteio de intenção.
- Seção "Key Design Decisions": remover bullets de `STUN_CAP_MULTIPLIER`, `recovery`
  (subtração inteira), `defense` (redução passiva), nota "cooldown only on hit / if dmg>0"
  (continua válida, mas o contexto da `defense` sumiu — revisar). Atualizar stun
  para a semântica de fração.
- Seção "Hyperparameters" (~linha 215): remover `HESITATION_RATE` da lista.

**docs/reference/04-combat-model.md:**
- `WALL_CORNER_THRESHOLD` + cornering removidos.
- `HESITATION_RATE` + hesitação removidos.
- Stun: era valor absoluto, agora fração × cooldown_subticks; sem `STUN_CAP_MULTIPLIER`.
- `recovery`: removido dos genes e do JIT.
- `defense`: removido dos genes e do JIT.
- Sistema de prioridades: substituir pelos 3 estados de intenção + execução.

**docs/reference/07-configuration.md:**
- Remover linhas de `HESITATION_RATE`, `WALL_CORNER_THRESHOLD`, `STUN_CAP_MULTIPLIER`,
  `INTEGER_ATTRIBUTES`.
- Atualizar bounds: `defense` e `recovery` não existem mais em `ATTRIBUTE_BOUNDS`.
- Atualizar semântica do `stun` (era sub-ticks absoluto, agora fração ∈ [0.0, 0.6]).

**docs/reference/10-known-issues.md:**
- Issue de calibração de `HESITATION_RATE` agora obsoleta — remover ou arquivar.
- Achado "recovery-neutro" (estava em aberto): fechado — recovery foi removido.

**docs/reference/11-combat-review.md:**
- WR graduada era creditada à hesitação (`HESITATION_RATE`). Hesitação foi removida;
  a gradação agora vem de `ACTION_PERSISTENCE_SUBTICKS` + sorteio de intenção. Atualizar.
- Análise de recovery: seção cobre recovery como gene — agora obsoleta. Anotar.

**docs/reference/03-archetypes.md:**
- Tabela canônica: remover colunas `defense` e `recovery`, stun era absoluto (ex. Grappler
  `recovery=4` sub-ticks), agora é fração (`stun=0.30`). Atualizar semântica.
- Semântica dos pesos: sem mudança estrutural, mas verificar contexto.

**docs/reference/05-genetic-algorithm.md:**
- Contagem de genes: atualizar de 12 para 10 por personagem, 60 para 50 total.
- `drift_penalty` computado sobre 10 genes (não 12).

**overleaf/artigo-SBC/main.tex:**
- Tabela canônica: remover colunas `defense` e `recovery`; atualizar `stun` de absoluto
  para fração; atualizar contagem de genes (12→10).
- §3.2 combate: atualizar modelo de prioridades e mecanismo de stun/hesitação.
- §3.3 representação: atualizar contagem de genes (12→10) e lista de atributos.

---

### Aviso: todas as rodadas anteriores estão invalidadas

O motor de combate mudou (genes, JIT, fórmula de stun). Todos os `results/` existentes
foram gerados com o modelo antigo e **não devem ser citados**. Re-rodar após calibrar:

**Itens de calibração (fora do escopo desta task — ver brief):**
- Valores canônicos: semântica de `w_agg` mudou; Turtle virou tanky-ativo; re-tune dos
  canônicos conforme novo modelo.
- Força do stun: `stun` agora é fração [0.0, 0.6] — calibrar o bound superior e os
  valores canônicos (Combo Master `stun=0.55` era sub-ticks, agora fração).
- `MATCHUP_WR_CAP` (C2): definir quão duras as arestas do ciclo podem ser.
- `ACTION_PERSISTENCE_SUBTICKS`: calibrar comprometimento de intenção.
- `TICK_SCALE`: subir para 10 apenas se aparecer platô de granularidade.
