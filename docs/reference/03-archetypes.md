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

São **7 atributos** por personagem (`defense` e `recovery` foram removidos do
modelo — ver [04-combat-model.md](04-combat-model.md)). `stun` é uma **fração do
cooldown do atacante** (∈ [0, 0.6]), não mais um valor absoluto.

| Classe | HP | Dmg | Cooldown | Range | Speed | Stun | Knockback |
|---|---|---|---|---|---|---|---|
| Zoner | 300 | 12 | 4 | 18 | 2.5 | 0.10 | 2.0 |
| Rushdown | 320 | 11 | 1 | 10 | 5.0 | 0.10 | 1.0 |
| Combo Master | 350 | 13 | 3 | 10 | 3.0 | 0.55 | 0.5 |
| Grappler | 400 | 20 | 4 | 8 | 2.0 | 0.30 | 0.5 |
| Turtle | 450 | 10 | 5 | 13 | 1.5 | 0.20 | 1.0 |

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
