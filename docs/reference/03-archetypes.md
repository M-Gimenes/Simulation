# 03 — Arquétipos

Definidos em `src/engine/archetypes.py` como `ArchetypeDefinition` congeladas.
Os valores canônicos **não são hardcoded no motor** — servem como semente da
população inicial e baseline de medição de drift. O AG diverge livremente.

## Os 5 arquétipos

| Arquétipo | Conceito FGC |
|---|---|
| **Zoner** | Controla espaço com alcance máximo e knockback; ataca antes do inimigo chegar e o empurra para fora de range. |
| **Rushdown** | Fecha distância em segundos e sufoca com ataques rápidos. |
| **Combo Master** | Velocidade fecha distância, stun extremo encadeia combos; neutraliza tanques e zoners por lockdown. |
| **Grappler** | Tank que pune corpo a corpo com burst máximo de dano. |
| **Turtle** | Muralha viva — absorve tudo e contra-ataca com paciência; vence agressivos por atrito de HP%. |

## Valores canônicos (semente inicial)

São **8 atributos** por personagem (`defense` e `recovery` foram removidos do
modelo — ver [04-combat-model.md](04-combat-model.md)). `stun` é uma **fração do
cooldown do atacante** (∈ [0, 0.6]) e `grab_power` é a **fração da guarda quebrada**
(∈ [0, 1]), ambos relativos, não absolutos.

> **Fonte única:** `src/engine/archetypes.py` → `ARCHETYPES`. A tabela
> espelha o código; **em divergência, o código vence** — ao mudar um canônico,
> atualize lá e só reflita aqui.

| Classe | HP | Dmg | Cooldown | Range | Speed | Stun | Knockback | Grab |
|---|---|---|---|---|---|---|---|---|
| Zoner | 300 | 20 | 4 | 18 | 2.5 | 0.10 | 2.0 | 0.05 |
| Rushdown | 320 | 16 | 1 | 10 | 5.0 | 0.10 | 1.0 | 0.20 |
| Combo Master | 350 | 18 | 3 | 10 | 3.0 | 0.55 | 0.5 | 0.30 |
| Grappler | 400 | 27 | 4 | 8 | 2.0 | 0.30 | 0.5 | **0.90** |
| Turtle | 450 | 15 | 5 | 13 | 1.5 | 0.20 | 1.0 | 0.15 |

O `grab_power` do Grappler é o valor que realiza, no motor, a justificativa FGC da
aresta "Grappler vence Turtle" da tabela do ciclo: *"grab é o counter canônico ao
bloqueio"*. Até 2026-09-16 essa justificativa não tinha mecanismo nenhum.

### Genes definidores

Além dos valores, cada arquétipo declara em `ArchetypeDefinition.defining_genes` os
genes nos quais ele ocupa um **extremo por design** — o que o torna reconhecível.
Espelham as asserções inter-personagem da Layer 1 do validador (fonte única da
premissa) e pesam `DRIFT_DEFINING_WEIGHT` no `drift_penalty`.

| Classe | genes definidores |
|---|---|
| Zoner | `range`, `knockback`, `w_retreat` |
| Rushdown | `speed`, `attack_cooldown`, `w_aggressiveness` |
| Combo Master | `stun` |
| Grappler | `damage`, `grab_power` |
| Turtle | `hp`, `attack_cooldown`, `speed`, `w_defend` |

A assimetria é informativa e não acidental. O **Combo Master** tem um gene definidor só
(`stun`). O **Grappler** tinha só `damage` até a entrada do agarrão (2026-09-16), que lhe
deu `grab_power` como segundo gene definidor **e** a assinatura comportamental que
faltava na Layer 3 — as duas lacunas eram a mesma coisa.

É declaração de **premissa** (o que o arquétipo é), nunca de resposta (quem vence
quem — `beats`, que o fitness jamais referencia). Consequência: as Layers 1-2 do
validador passam a medir o mesmo eixo que o fitness otimiza, e são **parcialmente
endógenas**; a leitura post-hoc de identidade fica com a **Layer 3** e o ciclo.

### Pesos comportamentais canônicos

| Classe | w_retreat | w_defend | w_aggressiveness |
|---|---|---|---|
| Zoner | 0.60 | 0.20 | 0.30 |
| Rushdown | 0.05 | 0.10 | 0.90 |
| Combo Master | 0.05 | 0.20 | 0.70 |
| Grappler | 0.10 | 0.40 | 0.70 |
| Turtle | 0.40 | 0.70 | 0.20 |

Os pesos ponderam o sorteio de **intenção** quando o personagem está em range
(ver [04-combat-model.md](04-combat-model.md)): `w_aggressiveness` → FRENTE
(ATTACK ou, se em cooldown, ADVANCE), `w_retreat` → RECUAR (RETREAT ou, sem
espaço, DEFEND), `w_defend` → GUARDA (DEFEND). Semântica esperada:
`w_aggressiveness` alto = empurra através de ameaças (Rushdown, Grappler, Combo
Master); `w_retreat > w_defend` = pipoca/kita (Zoner); `w_defend ≥ w_retreat` =
absorve segurando posição (Turtle).

Os bounds de cada gene e a calibração estão em
[07-configuration.md](07-configuration.md).

## Ciclo de vantagens canônico

Cada arquétipo vence 2 e perde para 2 — um torneio regular de 5 nós. Codificado
no campo `beats` de cada `ArchetypeDefinition`.

| Vencedor | Perdedores | Motivo FGC |
|---|---|---|
| Rushdown | Zoner, Combo Master | pressão não deixa iniciar setup |
| Zoner | Grappler, Turtle | controla espaço, fica fora da zona de punição |
| Grappler | Rushdown, Turtle | grab/burst pune fuga e combos rápidos; grab é o counter ao bloqueio |
| Combo Master | Grappler, Zoner | Grappler lento morre pra combo; burst converte um acerto |
| Turtle | Rushdown, Combo Master | bloqueio absorve pressão e quebra setup de combo |

> **O ciclo não está codificado em nenhuma penalidade do fitness.** É medido
> *post-hoc* como métrica de avaliação (ver `analyze_matchups` em
> [08-tools.md](08-tools.md)). Forçá-lo tornaria a pergunta de pesquisa circular.

### Justificativa por arquétipo

- **Zoner:** controla espaço com alcance máximo e knockback. Perde para quem
  fecha rápido (Rushdown) ou converte um acerto em burst (Combo Master).
- **Rushdown:** explode quem precisa de setup. Sofre contra absorvedores de
  pressão (Turtle) e burst alto em contra-ataque (Grappler).
- **Combo Master:** encadeia combos via stun — Grappler lento não escapa, Zoner
  morre para um acerto convertido. Perde para pressão constante (Rushdown) e
  para quem bloqueia o setup (Turtle).
- **Grappler:** se encosta, acabou — burst máximo. Grab é o counter canônico ao
  bloqueio (Turtle). Sofre contra rápidos (Rushdown) e contra o stun do Combo
  Master.
- **Turtle:** vive do erro do outro — destrói agressivos por atrito de HP%.
  Bloqueia o setup do Combo Master. Perde para controle de distância (Zoner) e
  para o grab do Grappler.

O status epistemológico do ciclo (construção do autor, operacionalização entre
várias defensáveis) está em [tcc/02-ciclo-canonico.md](../tcc/02-ciclo-canonico.md).
