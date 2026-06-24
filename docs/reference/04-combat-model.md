# 04 — Modelo de combate

Simulação tick a tick 1v1, em `src/engine/combat.py`. Toda a lógica vive em duas
funções `@njit` idênticas em regras (`_simulate_combat_jit` para o fitness,
`_simulate_combat_traced_jit` para instrumentação). API pública:
`simulate_combat`, `simulate_combat_traced`, `simulate_combat_detailed`.

## Campo

- Tamanho: `FIELD_SIZE = 100` unidades; posições clamped a `[0, 100]`.
- Distância inicial: `INITIAL_DISTANCE = 50` (lutadores em 25 e 75).
- `WALL_CORNER_THRESHOLD = 10`: dentro de 10 unidades de uma parede, o lutador é
  considerado encurralado.
- Todos os `range` ≤ 20 < 50 — nenhum personagem ataca no tick 1.

## Resolução sub-tick (`TICK_SCALE = 5`)

Multiplicador que aumenta a resolução temporal de timers e movimento. Sem ele,
`attack_cooldown ∈ [1, 5]` teria só 5 valores discretos, criando platôs no
espaço de fitness. Internamente os timers operam de 5 a 25 sub-ticks.

- Movimento por sub-tick: `speed / TICK_SCALE`
- Cooldown no hit: `round(attack_cooldown × TICK_SCALE)`
- Stun no hit: `round(attacker.stun × TICK_SCALE) − defender.recovery`, com cap

## As 4 ações

`ATTACK` · `ADVANCE` · `RETREAT` · `DEFEND`

## Sistema de decisão (prioridade)

Por sub-tick, do mais alto ao mais baixo. Um personagem stunado perde a ação
(`stun_rem > 0` → ação = −1).

1. **ATTACK** — se está **no próprio range** (`distance ≤ range`) **e** o
   cooldown está pronto (`cd_rem == 0`). Limpa qualquer commitment pendente.
2. **ADVANCE** — se está **fora do próprio range** **ou** encurralado contra a
   parede. Limpa commitment pendente.
3. **HELD COMMITMENT** — se há uma escolha de soft policy ainda dentro da janela
   de persistência (`persist > 0`), repete-a e decrementa o contador.
4. **NEW SOFT POLICY** — sorteia uma de `{ADVANCE, RETREAT, DEFEND}` com
   probabilidade proporcional a `(w_aggressiveness, w_retreat, w_defend)`, fixa a
   escolha e reinicia o contador para `ACTION_PERSISTENCE_SUBTICKS`.

> **Gatilho da soft policy (importante).** Os ramos 3–4 só são alcançados quando
> o personagem está **dentro do próprio range mas com o cooldown não pronto** (e
> não encurralado e não stunado). É a decisão "estou em alcance mas não posso
> bater agora — avanço, recuo ou defendo?". Não depende do range nem do estado do
> *inimigo*.

A soft policy (ramos 3–4) é a fonte estocástica principal do loop.
Implementação: `r = np.random.random() × (wagg + wret + wdef)`; `r < wagg` →
ADVANCE, `r < wagg+wret` → RETREAT, senão DEFEND. Se a soma dos pesos for 0, a
ação é DEFEND.

### Hesitação (`HESITATION_RATE`, variância de player)

A cada tick, com probabilidade `HESITATION_RATE`, mesmo nos ramos
**determinísticos** (ATTACK em range+pronto, ou ADVANCE forçado) o personagem
**hesita**: em vez da ação ótima, cai na amostragem ponderada `(w_agg, w_ret,
w_def)` (a mesma da soft policy). Modela "o player não executa sempre o ótimo" —
variância de execução. Diferente do antigo `ACTION_EPSILON` (removido), a
hesitação é **ponderada pelos pesos**, então respeita a identidade do personagem
(um Rushdown que hesita tende a ADVANCE, um Turtle a DEFEND), em vez de uniforme.

`HESITATION_RATE = 0` reproduz exatamente o combate sem hesitação. O valor é
**provisório e a calibrar** — ver [10-known-issues.md](10-known-issues.md). A
[revisão do combate](11-combat-review.md) mostrou que a hesitação é menos crítica
do que se pensava: a alavanca real é o objetivo por-luta, que aproxima as lutas e
deixa o ruído já existente flipar desfechos.

Os pesos agem de forma **contínua**: um Δ em qualquer peso produz Δ proporcional
na probabilidade da ação, dando ao AG gradiente contínuo nesses genes. A versão
antiga (comparação dura `w_aggressiveness > w_retreat AND ...`) tornava os pesos
*categóricos* — só a ordem importava, magnitudes eram invisíveis à seleção.

### Persistência de ação (`ACTION_PERSISTENCE_SUBTICKS = 10`)

Uma vez sorteada, a ação soft-policy é reusada pelos próximos 10 sub-ticks (≈ 2
ticks lógicos) antes de re-sortear. Simula commitment/momentum e evita
flip-flopping patológico (sem isso, o personagem re-rolaria RETREAT/DEFEND/ADVANCE
5× por tick lógico). O commitment é **quebrado** quando uma prioridade superior
dispara (ATTACK por estar em range + pronto, ou ADVANCE por estar fora de range /
encurralado).

## Fluxo por sub-tick

1. **Escolha de ação** (prioridade acima) para A e B.
2. **Movimento** (ADVANCE/RETREAT) — passo `speed / TICK_SCALE`, clamped ao campo.
3. **Snapshot dos timers** pré-ataque (para o decremento "decrement-stale").
4. **Resolução simultânea** de ataques A→B e B→A.
5. **Decremento de timers stale** — só decrementa timers **não** setados neste tick.

## Regras de combate

- **Dano determinístico:** `damage × (1 − defense)`. Sem variância por hit.
- **DEFEND:** multiplica o dano recebido por `DEFEND_DAMAGE_REDUCTION = 0.4`
  (recebe 40% = 60% de redução).
- **Stun efetivo:** `max(0, round(attacker.stun × TICK_SCALE) − defender.recovery)`,
  com cap em `STUN_CAP_MULTIPLIER × attacker.attack_cooldown × TICK_SCALE`.
  - `STUN_CAP_MULTIPLIER = 0.6 < 1.0` garante que o stun é estritamente menor que
    o cooldown do atacante — o defensor sempre ganha uma janela livre antes do
    próximo hit. Quebra o soft-perma-lock que existia com valores ≥ 1.0.
  - O stun só é aplicado se o novo valor exceder o stun residual atual
    (`stun_t > stun_rem`); não se acumula.
- **Cooldown só em acerto:** o cooldown do atacante só é setado dentro do bloco
  `if dmg > 0.0`. Um ATTACK que sai mas erra (a distância pode ter mudado após o
  movimento) não desperdiça cooldown.
- **Knockback:** empurra o defensor `knockback` unidades para longe do atacante
  após cada hit, clamped ao campo.
- **Recovery:** inteiro em sub-ticks, subtraído diretamente do stun recebido (cada
  unidade tira 1 sub-tick). Ver a justificativa do formato inteiro em
  [05-genetic-algorithm.md](05-genetic-algorithm.md) (mutação) e
  [07-configuration.md](07-configuration.md).

### Decremento pós-ataque (decrement-stale)

Decrementos acontecem no **fim** do tick, comparando o valor atual com o
pré-ataque. Se um ataque setou o timer neste tick (`current > pre`), ele é
preservado até o próximo. Garante que `stun = 1` e `cooldown = 1` (em ticks
lógicos) sejam mínimos com efeito real.

## Condição de vitória

- **KO:** HP de um lado chega a zero.
- **Timeout** (`MAX_TICKS = 500 × TICK_SCALE = 2500` sub-ticks): vence quem tem
  maior HP **percentual** (`hp_atual / hp_max`). Empate de percentual → vence A.

O fitness distingue KO de timeout via *HP-weighted scoring* — ver
[05-genetic-algorithm.md](05-genetic-algorithm.md).
