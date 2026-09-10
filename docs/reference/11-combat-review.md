# 11 — Auditoria do modelo de combate

Estado atual: **auditoria de 2026-09-10**. A revisão anterior (2026-06-23) concluía
que "o combate é bom e não está quebrado"; a auditoria de setembro mostrou que aquela
conclusão vinha de medir no lugar errado — está no fim deste arquivo, com o porquê.

Pergunta da auditoria: cada mecânica representa o que diz representar? Há genes mortos
ou com sinal invertido? O AG consegue enxergar o cromossomo?

Método: varredura de cada gene (a) num **corpo neutro** — todos os bounds no ponto
médio, oponente idêntico — e (b) no **contexto de projeto** de cada gene (o knockback
num zoner contra um rusher, o speed num rusher contra um zoner, e assim por diante);
instrumentação por `CombatTrace` sobre os 10 pares canônicos; espelhos de 4000 lutas
para viés posicional; e um AG curto para confirmar que a paisagem tem gradiente.

## Veredito

**O motor não estava quebrado no geral — mas tinha quatro defeitos específicos, e eles
atingiam exatamente os arquétipos que o AG destruía primeiro.** No meio do espaço de
genes cinco dos sete atributos já respondiam com gradiente limpo e monótono; os dois que
não respondiam (`knockback` e `stun`) são justamente os genes de identidade do Zoner e
do Combo Master. Não era o AG sendo destrutivo: esses genes não pagavam, então mantê-los
custava drift sem retorno.

## Os quatro defeitos, e o que a correção fez

### 1. A regra "fora do alcance → ADVANCE incondicional" matava o jogo de espaçamento

`_decide_action` impunha ADVANCE sempre que `distance > range`, sobrescrevendo a política
do personagem. Um zoner não podia manter distância: assim que a distância passava do
próprio alcance, era obrigado a avançar.

```
zoner (range 20, speed 2) × rusher (range 6, speed 5)
  varrendo o knockback do zoner   0.0 → 0,0%   0.75 → 0,0%   1.5 → 0,0%   2.25 → 0,1%   3.0 → 0,0%
  varrendo o range do zoner       5.0 → 0,0%   8.75 → 0,0%  12.5 → 0,0%  16.25 → 0,0%  20.0 → 0,0%
```

O zoner perdia **100% das lutas independentemente dos dois genes que são a identidade
dele**. E não era o campo: `FIELD_SIZE` de 100 a 800 dava 0,0% igual. Daí saía também o
**sinal invertido do knockback** (−8,4% no corpo neutro, o único gene com derivada
negativa): empurrar o alvo para fora do próprio alcance **obrigava o atacante a
persegui-lo**.

**Correção:** a intenção sorteada vale sempre, com a exceção do impasse (§3 abaixo).

### 2. Atacar e segurar espaço eram mutuamente exclusivos

Com FRENTE e RECUAR exclusivos por 10 sub-ticks, recuar era **puro forfeit de dano** —
e zonear, que é atacar enquanto se segura a distância, não existia como jogada.

**Correção:** dois canais. A intenção governa só a **postura** (ADVANCE / RETREAT /
DEFEND); o **ataque** dispara por regra na resolução (cooldown pronto + em alcance +
postura ≠ DEFEND). Avançar e recuar batem; só a GUARDA abre mão do golpe. O conceito de
"whiff" deixou de existir.

| medida | antes | depois |
|---|---|---|
| zoner × rusher | 0,0% | **49,0%** |
| `knockback` no contexto zoner×rusher | Δ=0,1% (plana) | **Δ=44,3% monótona ↑** (27,4% → 71,6%) |
| `range` no contexto zoner×rusher | Δ=0,0% (plana) | Δ=45,0% |
| `range` no corpo neutro | Δ=46,8% | **Δ=90,5%** |

Emergência coerente: o zoner **lento** (speed 2) joga melhor que o rápido (49,0% vs
25,5%) — recuar depressa te leva à parede mais cedo.

### 3. Passividade era grátis (efeito colateral da correção 1)

Com a intenção sempre respeitada, dois personagens passivos recuavam cada um para a sua
parede e nunca se encontravam: **Zoner×Turtle deu 100% de timeout** com distância média
87,7.

**Correção:** o ADVANCE é imposto **apenas no impasse** — `distance > range_próprio`
**e** `distance > range_do_oponente`, ninguém alcança ninguém. Quem está sob ameaça segue
livre para recuar, então o kite não é afetado e a regra não é explorável. Resultado: **0%
de timeout** nos 10 pares canônicos.

### 4. Os corpos se atravessavam, e o stun era categórico

- **Sem colisão:** **134 atravessamentos de posição por luta** no roster canônico (80.520
  em 600 lutas). A distância colapsava para ~0 e oscilava, anulando o `range` no clinch.
  *Correção:* `_apply_movement`, helper compartilhado pelos dois JITs, com movimento
  simultâneo e parada no ponto de encontro.
  *Ressalva:* o atravessamento era a válvula de escape do encurralamento. Medido depois,
  o canto **não** virou armadilha automática — quem é encurralado perde entre 55% e 100%
  das lutas conforme o par (Zoner×Grappler: preso em 52% das lutas, perdeu 55% delas), e
  o knockback de quem está preso empurra o agressor para longe.
- **Stun arredondado:** `round(stun × round(cd × TICK_SCALE))` deixava o gene contínuo
  `[0, 0.6]` com **4 níveis efetivos** para `cooldown = 1` (10 para `cd = 3`, 16 para
  `cd = 5`). *Correção:* timer contínuo. Δ no bound inteiro 17,2% → **53,5%**; amplitude
  a ±1σ de mutação 6,8% → **17,4%**.

### 5. Viés posicional no desempate

HP% igual (KO duplo ou timeout sem dano) entregava a vitória ao lado A — e
`_run_round_robin` fixa o índice menor como A, então o Zoner é A em 4 pares e o Turtle em
nenhum. Medido em espelho (4000 lutas):

| espelho canônico | KO duplo | WR do lado A | previsto (50 + KOduplo/2) |
|---|---|---|---|
| Rushdown | 10,30% | **54,90%** | 55,15% |
| Combo Master | 3,02% | 50,73% | 51,51% |
| Zoner | 1,23% | 50,88% | 50,61% |

**Correção:** `_decide_winner` devolve `-1` (empate); meia vitória para cada lado no
round-robin, score por-luta `0,5`. Todos os espelhos voltaram a ~50%.

## Estado dos genes depois das correções

Amplitude da WR a **±1σ de mutação** (σ = 10% do range do gene), corpo neutro:

| gene | antes | depois |
|---|---|---|
| range | 36,9% | **92,5%** |
| attack_cooldown | 21,4% | 65,1% |
| damage | 23,4% | 55,5% |
| hp | 19,9% | 43,6% |
| stun | 6,8% | 17,4% |
| speed | 15,9% | 4,1% |
| knockback | 4,4% | 1,3% |

> **Leitura obrigatória do espelho:** o corpo neutro **subestima genes relacionais**.
> `speed` e `knockback` não fazem diferença num espelho (os dois lados têm o mesmo
> valor), mas respondem forte no contexto de projeto — `speed` do rusher contra o zoner
> dá Δ=47,4% monótona, `knockback` do zoner contra o rusher dá Δ=44,3%. Medir gene de
> espaçamento em espelho é o mesmo erro de medir sensibilidade no canônico saturado.

## A paisagem que o AG vê

- 40 indivíduos aleatórios × 10 pares: **71% dos matchups saturados** (WR fora de
  [5%, 95%]). Esperado — indivíduos uniformes nos bounds são extremos por construção.
- AG curto (pop 120, 25 gerações, 80 sims/par): `dominance_penalty` **1,236 → 0,250**,
  os 5 bonecos em WR global **[48,7%, 52,0%]** e, o que importa para a pergunta de
  pesquisa, **espalhamento real por par**: 22% · 34% · 36% · 48% · 50% · 50% · 58% ·
  64% · 70% · 71%. No motor antigo o indivíduo evoluído ficava achatado em [43,5%, 58%].
  **Agora existe espaço para o ciclo de vantagens viver.**
- Pendências que isso abriu (em [`../../REVIEW.md`](../../REVIEW.md) §2): a
  hipersensibilidade dos genes de recurso e a decisividade caindo abaixo do
  `MATCHUP_FLOOR`.

## O que a revisão de 2026-06-23 concluiu, e por que errou

Aquela revisão instrumentou os **10 matchups canônicos** e concluiu: "o combate é bom e
representa bem os arquétipos — não está quebrado; o problema é a formulação do objetivo,
não as mecânicas". A tabela de mix de ações mostrava Zoner com 39% de RETREAT e Turtle
com 43% de DEFEND, e isso foi lido como "os pesos expressam identidade, as mecânicas não
estão mortas".

O erro é de **ponto de medição**: o roster canônico é saturado (Rushdown 100% global,
Turtle 0%, 10/10 hard-counters). Num ponto saturado, *nenhuma* perturbação muda o
desfecho, então nada parece quebrado — e nada parece funcionar tampouco. Medir a fração
de RETREAT prova que a ação é **escolhida**, não que ela **serve para alguma coisa**: o
Zoner recuava 39% do tempo e ainda assim perdia 100%, porque recuar era forfeit de dano.

É exatamente o mesmo efeito de teto que faz a `sensitivity_analysis` classificar 6 dos 7
atributos como "neutros" (item aberto em [`../../REVIEW.md`](../../REVIEW.md) §4). A
lição metodológica: **auditar mecânica exige um ponto não-saturado do espaço** — corpo
neutro para o gradiente bruto, contexto de projeto para genes relacionais.

Duas conclusões daquela revisão continuam de pé e estão registradas em
[`../tcc/04-caminhos-e-decisoes.md`](../tcc/04-caminhos-e-decisoes.md): a hipótese "luta
apertada ⟹ WR ~50%" foi falsificada empiricamente (a decisividade é cega à frequência de
vitória), e por isso a WR voltou como termo primário do `dominance_penalty`.
