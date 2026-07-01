# 04 — Modelo de combate

Simulação tick a tick 1v1, em `src/engine/combat.py`. O loop vive em duas funções
`@njit` (`_simulate_combat_jit` para o fitness, `_simulate_combat_traced_jit` para
instrumentação) que **compartilham a decisão de ação** via o helper `@njit`
`_decide_action` — fonte única, chamada para A e B nas duas variantes, garantindo
que ambas simulem exatamente o mesmo combate (mesmo consumo de RNG; coberto por um
teste de paridade em `test_combat`). API pública: `simulate_combat`,
`simulate_combat_traced`, `simulate_combat_detailed`.

## Campo

- Tamanho: `FIELD_SIZE = 100` unidades; posições clamped a `[0, 100]`.
- Distância inicial: `INITIAL_DISTANCE = 50` (lutadores em 25 e 75).
- Todos os `range` ≤ 20 < 50 — nenhum personagem ataca no tick 1.

Não há conceito de "encurralamento" (cornering): RETREAT simplesmente recua até a
borda (0 ou `FIELD_SIZE`) e, quando não há mais espaço para recuar, o personagem
cai para DEFEND (ver execução abaixo). Esse DEFEND **forçado** (RECUAR sem espaço)
é distinguido do DEFEND **escolhido** (GUARDA) no `CombatTrace.forced_defend` — a
geometria não deve contaminar a métrica de identidade defensiva (ver `08-tools.md`,
fingerprint e Layer 3 do validador).

## Resolução sub-tick (`TICK_SCALE = 5`)

Multiplicador que aumenta a resolução temporal de timers e movimento. Sem ele,
`attack_cooldown ∈ [1, 5]` teria só 5 valores discretos, criando platôs no
espaço de fitness. Internamente os timers operam de 5 a 25 sub-ticks.

- Movimento por sub-tick: `speed / TICK_SCALE`
- Cooldown no hit: `round(attack_cooldown × TICK_SCALE)`
- Stun no hit: `round(stun × round(attack_cooldown × TICK_SCALE))` — ver
  [stun](#stun) abaixo.

## As 4 ações

`ATTACK` · `ADVANCE` · `RETREAT` · `DEFEND`

## Sistema de decisão: intenção → execução

A cada sub-tick, a ação de cada personagem é decidida em **duas fases**. Um
personagem stunado perde a ação (`stun_rem > 0` → ação = −1, antes de qualquer
fase).

### Fase 1 — Intenção (só quando em range)

- **Fora do próprio range** (`distance > range`): a intenção é ignorada — o
  personagem faz `ADVANCE` incondicional (neutral game, aproxima) e zera o
  contador de persistência.
- **Dentro do próprio range** (`distance ≤ range`): se não há intenção vigente
  (`persist == 0`), **sorteia uma intenção** entre `{FRENTE, RECUAR, GUARDA}` com
  probabilidade proporcional a `(w_aggressiveness, w_retreat, w_defend)` e a
  **mantém por `ACTION_PERSISTENCE_SUBTICKS` sub-ticks** (commitment/momentum).
  Se a soma dos pesos for 0, a intenção é `GUARDA` (fallback).

### Fase 2 — Execução

A intenção vigente determina a ação concreta do sub-tick:

| Intenção | Ação concreta |
|---|---|
| **FRENTE** | `ATTACK` se o cooldown está pronto (`cd_rem == 0`), senão `ADVANCE` (pressão sem desperdiçar cooldown) |
| **RECUAR** | `RETREAT` se ainda há espaço para recuar, senão `DEFEND` (sem mais recuo possível) |
| **GUARDA** | `DEFEND` |

> **A intenção é a única fonte estocástica do loop.** O sorteio é
> `r = np.random.random() × (wagg + wret + wdef)`; `r < wagg` → FRENTE,
> `r < wagg + wret` → RECUAR, senão GUARDA. Uma vez sorteada, a intenção **não é
> interrompida** até o contador de persistência zerar (não há flip-flop por
> sub-tick) — exceto por sair do range, que força ADVANCE e reseta o contador, e
> por ser stunado.

Os pesos agem de forma **contínua**: um Δ em qualquer peso produz Δ proporcional
na probabilidade da intenção, dando ao AG gradiente contínuo nesses genes. A
versão antiga (comparação dura `w_aggressiveness > w_retreat AND ...`) tornava os
pesos *categóricos* — só a ordem importava, magnitudes eram invisíveis à seleção.

### Persistência de intenção (`ACTION_PERSISTENCE_SUBTICKS = 10`)

Uma vez sorteada, a intenção é reusada pelos próximos 10 sub-ticks (≈ 2 ticks
lógicos) antes de re-sortear. Simula commitment/momentum e evita flip-flopping
patológico (sem isso, o personagem re-sortearia a intenção 5× por tick lógico). O
contador é **zerado** ao sair do range (que força ADVANCE) e quando o personagem
é stunado.

## Fluxo por sub-tick

1. **Escolha de ação** (intenção → execução) para A e B.
2. **Movimento** (ADVANCE/RETREAT) — passo `speed / TICK_SCALE`, clamped ao campo.
3. **Snapshot dos timers** pré-ataque (para o decremento "decrement-stale").
4. **Resolução simultânea** de ataques A→B e B→A.
5. **Decremento de timers stale** — só decrementa timers **não** setados neste tick.

## Regras de combate

- **Dano flat:** `damage`, sem variância por hit e sem redução passiva. O único
  modificador é a ação `DEFEND` do alvo. (Não existe gene `defense`.)
- **DEFEND:** multiplica o dano recebido por `DEFEND_DAMAGE_REDUCTION = 0.6`
  (`= 1 − 0.4` em `config.py`) — o defensor recebe 60% do dano, i.e. **40% de
  redução**.
- <a name="stun"></a>**Stun:** `stun_t = round(stun × round(attack_cooldown × TICK_SCALE))`.
  O gene `stun ∈ [0.0, 0.6]` é uma **fração do próprio cooldown do atacante** (em
  sub-ticks), não um valor absoluto.
  - Como `stun < 1.0` por bound, o stun aplicado é **estritamente menor que o
    cooldown do atacante** — o defensor sempre ganha uma janela livre antes do
    próximo hit. A invariante é garantida matematicamente pelo bound do gene (não
    há mais `STUN_CAP_MULTIPLIER` explícito). A garantia depende do acoplamento
    `stun_bound × TICK_SCALE`: com `cd_min = 1` e `TICK_SCALE = 5`, o cooldown em
    sub-ticks é ≥ 5, e `round(0.6 × 5) = 3 < 5`. Ver
    [07-configuration.md](07-configuration.md).
  - O stun só é aplicado se o novo valor exceder o stun residual atual
    (`stun_t > stun_rem`); não se acumula.
- **Cooldown só em acerto:** o cooldown do atacante só é setado dentro do bloco de
  resolução, que só executa quando o ATTACK está **em range no momento da
  resolução** (`cd_rem == 0 and distance ≤ range`). Um ATTACK escolhido mas que
  sai de range após o movimento daquele tick não entra no bloco — não desperdiça
  cooldown.
- **Knockback:** empurra o defensor `knockback` unidades para longe do atacante
  após cada hit, clamped ao campo.

### Decremento pós-ataque (decrement-stale)

Decrementos acontecem no **fim** do tick, comparando o valor atual com o
pré-ataque. Se um ataque setou o timer neste tick (`current > pre`), ele é
preservado até o próximo. Garante que `stun = 1` e `cooldown = 1` (em sub-ticks)
sejam mínimos com efeito real.

## Condição de vitória

- **KO:** HP de um lado chega a zero.
- **Timeout** (`MAX_TICKS = 500 × TICK_SCALE = 2500` sub-ticks): vence quem tem
  maior HP **percentual** (`hp_atual / hp_max`). Empate de percentual → vence A.

O fitness distingue KO de timeout via *score por-luta contínuo* — ver
[05-genetic-algorithm.md](05-genetic-algorithm.md).
