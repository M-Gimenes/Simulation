# 04 — Modelo de combate

Simulação tick a tick 1v1, em `src/engine/combat.py`. O loop vive em duas funções
`@njit` (`_simulate_combat_jit` para o fitness, `_simulate_combat_traced_jit` para
instrumentação) que **compartilham dois helpers `@njit`** — `_decide_action`
(postura) e `_apply_movement` (deslocamento com colisão) —, fonte única chamada para
A e B nas duas variantes, garantindo que ambas simulem exatamente o mesmo combate
(mesmo consumo de RNG; coberto por um teste de paridade em `test_combat`). O desfecho
sai de um terceiro helper compartilhado, `_decide_winner`. API pública:
`simulate_combat`, `simulate_combat_traced`, `simulate_combat_detailed`.

## Os dois canais de ação

O modelo separa **o que o lutador decide** de **o que a situação permite**:

| Canal | Quem decide | Valores |
|---|---|---|
| **Postura** (movimento) | a intenção sorteada dos pesos `w_*` | `ADVANCE` · `RETREAT` · `DEFEND` |
| **Ataque** | regra de resolução, não escolha | dispara quando cooldown pronto **e** oponente ao alcance **e** postura ≠ `DEFEND` |

Avançar e recuar **batem**; só a `GUARDA` abre mão do golpe. É isso que torna o
controle de espaço uma estratégia: zonear é atacar enquanto se segura a distância.
Enquanto o ataque era uma postura exclusiva, recuar significava abrir mão do dano, o
Zoner não tinha jogada e o `knockback` tinha derivada **negativa** — empurrar o alvo
para fora do próprio alcance obrigava o atacante a persegui-lo. Trajetória e medições
em [11-combat-review.md](11-combat-review.md).

## Campo e colisão

- Tamanho: `FIELD_SIZE = 100` unidades; posições clamped a `[0, 100]`.
- Distância inicial: `INITIAL_DISTANCE = 50` (lutadores em 25 e 75).
- Todos os `range` ≤ 20 < 50 — nenhum personagem ataca no tick 1.
- **Os corpos não se atravessam.** `_apply_movement` desloca os dois a partir das
  posições do início do sub-tick (movimento simultâneo, nenhum lado chega "primeiro")
  e, se os dois avanços se cruzariam, ambos param no ponto de encontro. A é sempre o
  lado esquerdo (`pos_a ≤ pos_b`) — invariante que elimina os casos de borda de
  direção quando a distância chega a zero.

**Encurralamento** existe como consequência: `RETREAT` recua até a borda e, sem
espaço, cai para `DEFEND`. Esse DEFEND **forçado** é distinguido do **escolhido**
(GUARDA) no `CombatTrace.forced_defend` — a geometria não deve contaminar a métrica
de identidade defensiva (ver `08-tools.md`). O canto não é armadilha automática:
medido no roster canônico, quem é encurralado perde entre 55% e 100% das lutas
conforme o par, e o knockback de quem está preso empurra o agressor para longe.

## Resolução sub-tick (`TICK_SCALE = 5`)

Multiplicador que aumenta a resolução temporal de timers e movimento. Sem ele,
`attack_cooldown ∈ [1, 5]` teria só 5 valores discretos, criando platôs no
espaço de fitness. Internamente o cooldown opera de 5 a 25 sub-ticks.

- Movimento por sub-tick: `speed / TICK_SCALE`
- Cooldown no hit: `round(attack_cooldown × TICK_SCALE)` — inteiro
- Stun no hit: `stun × attack_cooldown × TICK_SCALE` — **contínuo**, ver
  [stun](#stun) abaixo.

## Sistema de decisão: intenção → postura

A cada sub-tick a postura de cada personagem é decidida em **duas fases**. Um
personagem stunado perde o sub-tick (`stun_rem > 0` → postura = −1, antes de
qualquer fase) e não ataca.

### Fase 1 — Intenção

Se não há intenção vigente (`persist == 0`), **sorteia** uma entre
`{FRENTE, RECUAR, GUARDA}` com probabilidade proporcional a
`(w_aggressiveness, w_retreat, w_defend)` e a **mantém por
`ACTION_PERSISTENCE_SUBTICKS` sub-ticks** (commitment/momentum). Se a soma dos pesos
for 0, a intenção é `GUARDA` (fallback).

**A intenção sorteada vale sempre — com uma exceção: o impasse.** Quando
`distance > range_próprio` **e** `distance > range_do_oponente`, ninguém alcança
ninguém e o `ADVANCE` é imposto (o contador de persistência é zerado). Sem isso, dois
personagens passivos recuam cada um para a sua parede e a luta termina por timeout sem
um golpe — medido antes da regra: 100% de timeout em Zoner×Turtle. Quem está **sob
ameaça** (o oponente alcança) segue livre para recuar, então o kite não é afetado e a
regra não é explorável.

### Fase 2 — Postura

| Intenção | Postura |
|---|---|
| **FRENTE** | `ADVANCE` |
| **RECUAR** | `RETREAT` se ainda há espaço para recuar, senão `DEFEND` (encurralado) |
| **GUARDA** | `DEFEND` |

> **A intenção é a única fonte estocástica do loop.** O sorteio é
> `r = np.random.random() × (wagg + wret + wdef)`; `r < wagg` → FRENTE,
> `r < wagg + wret` → RECUAR, senão GUARDA. Uma vez sorteada, a intenção **não é
> interrompida** até o contador zerar — exceto pelo impasse, que força ADVANCE e
> reseta o contador, e por ser stunado.

Os pesos agem de forma **contínua**: um Δ em qualquer peso produz Δ proporcional
na probabilidade da intenção, dando ao AG gradiente contínuo nesses genes. A
versão antiga (comparação dura `w_aggressiveness > w_retreat AND ...`) tornava os
pesos *categóricos* — só a ordem importava, magnitudes eram invisíveis à seleção.

> **Degenerescência de escala:** o sorteio é proporcional, então o comportamento
> depende só da **razão** entre os três pesos. Multiplicar os três por uma constante
> não muda nada no combate, mas muda o `drift_penalty` — pendência aberta em
> [`../../REVIEW.md`](../../REVIEW.md) §5.

### Persistência de intenção (`ACTION_PERSISTENCE_SUBTICKS = 10`)

Uma vez sorteada, a intenção é reusada pelos próximos 10 sub-ticks (≈ 2 ticks
lógicos) antes de re-sortear. Simula commitment/momentum e evita flip-flopping
patológico (sem isso, o personagem re-sortearia a intenção 5× por tick lógico). O
contador é **zerado** no impasse (que força ADVANCE) e quando o personagem é stunado.

## Fluxo por sub-tick

1. **Postura** (intenção → postura) para A e B.
2. **Movimento simultâneo** com colisão (`_apply_movement`).
3. **Snapshot dos timers** pré-ataque (para o decremento "decrement-stale").
4. **Resolução simultânea** de ataques A→B e B→A, pela regra do canal de ataque.
5. **Decremento de timers stale** — só decrementa timers **não** setados neste tick.

## Regras de combate

- **Ataque:** dispara quando `postura ≥ 0 and postura ≠ DEFEND and cd_rem == 0 and
  distance ≤ range`, com a `distance` **pós-movimento**. Não existe "whiff": um ataque
  fora de alcance simplesmente não acontece, e o cooldown segue intacto.
- **Dano flat:** `damage`, sem variância por hit e sem redução passiva. O único
  modificador é a postura `DEFEND` do alvo. (Não existe gene `defense`.)
- **DEFEND:** multiplica o dano recebido por `DEFEND_DAMAGE_REDUCTION = 0.6`
  (`= 1 − 0.4` em `config.py`) — o defensor recebe 60% do dano, i.e. **40% de
  redução**. Defender **não tem custo** além do golpe abdicado: não há chip damage,
  guard break nem stamina, e por isso o eixo de recurso não tem counter à defesa —
  ver o item de guard break em [`../../REVIEW.md`](../../REVIEW.md) §2.
- <a name="stun"></a>**Stun:** `stun_t = stun × attack_cooldown × TICK_SCALE`, em
  ponto flutuante. O gene `stun ∈ [0.0, 0.6]` é uma **fração do próprio cooldown do
  atacante** (em sub-ticks), não um valor absoluto.
  - O timer é **contínuo** (decremento de `1.0` por sub-tick, atordoado enquanto
    `stun_rem > 0`). Com o antigo `round()` o gene tinha só 4 níveis efetivos para um
    atacante de `cooldown = 1` — praticamente categórico, e a amplitude do gene a ±1σ
    de mutação era de 6,8%. Com o timer contínuo passou a 17,4%.
  - Como `stun < 1.0` por bound, o stun aplicado é **estritamente menor que o
    cooldown do atacante** — o defensor sempre ganha uma janela livre antes do
    próximo hit. A invariante é garantida pelo bound do gene (não há
    `STUN_CAP_MULTIPLIER`) e coberta por teste em `test_combat`.
  - O stun só é aplicado se o novo valor exceder o residual atual
    (`stun_t > stun_rem`); não se acumula.
- **Knockback:** empurra o defensor `knockback` unidades para longe do atacante
  após cada hit, clamped ao campo. Com o canal de ataque paralelo o gene passou a ter
  função: no contexto zoner×rusher, varrer o bound leva a WR do zoner de 27,4% a
  71,6% (antes: 0,0% em toda a varredura).

### Decremento pós-ataque (decrement-stale)

Decrementos acontecem no **fim** do tick, comparando o valor atual com o
pré-ataque. Se um ataque setou o timer neste tick (`current > pre`), ele é
preservado até o próximo. Garante que `stun` e `cooldown` mínimos tenham efeito real.

## Condição de vitória

`_decide_winner` devolve `0` (A), `1` (B) ou **`-1` (empate)**:

- **KO:** HP de um lado chega a zero.
- **Timeout** (`MAX_TICKS = 500 × TICK_SCALE = 2500` sub-ticks): vence quem tem
  maior HP **percentual** (`hp_atual / hp_max`).
- **Empate:** os dois terminam com a **mesma** fração de HP — KO duplo (ambos a zero
  no mesmo sub-tick) ou timeout sem diferença. No round-robin vale **meia vitória para
  cada lado**; o score por-luta é `0.5` (margem nula), então a decisividade cai no piso
  e o fitness já pune a luta sem resolução.

> Sem o empate, o desempate cairia sempre para o lado A — que em
> `_run_round_robin` é sempre o arquétipo de índice menor. Era um viés sistemático
> na métrica que o fitness otimiza: medido em espelho, o Rushdown canônico dava
> 54,90% para o lado A (10,3% de KO duplo). Com o empate, todos os espelhos voltam a
> ~50%.

O fitness distingue KO de timeout via *score por-luta contínuo* — ver
[05-genetic-algorithm.md](05-genetic-algorithm.md).
