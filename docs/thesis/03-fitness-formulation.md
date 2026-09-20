# 03 — Formulação do fitness: o que cada termo significa

**Entra em**: Metodologia (formulação do AG).

> As **fórmulas** estão em [`../reference/05-genetic-algorithm.md`](../reference/05-genetic-algorithm.md).
> Aqui está o **significado e a justificativa** de cada escolha, para o texto da
> metodologia.

O fitness escalar tem **dois termos** — exatamente os dois objetivos do NSGA-II,
aqui como soma ponderada: `fitness = -(LAMBDA_DRIFT·drift + LAMBDA_DOMINANCE·dominance)`.

## A linha que separa o que o fitness pode codificar

Antes dos termos, a regra que organiza todos eles — e o argumento que responde à
objeção mais óbvia ao trabalho ("se a identidade está no fitness, você não está
forçando o resultado?"):

> **O fitness pode codificar a PREMISSA, nunca a RESPOSTA.**

- **Premissa:** o que cada arquétipo **é** — os valores canônicos e os genes que o
  definem. É dado de entrada, vindo da FGC, anterior e independente da pergunta de
  equilíbrio. "O Zoner é o personagem definido por alcance" é premissa.
- **Resposta:** quem vence quem, e se equilíbrio e identidade são sequer compatíveis.
  "O Zoner deve vencer o Grappler" é resposta. Codificá-la responderia a pergunta com
  ela mesma.

Daí a assimetria do projeto: **identidade é termo do fitness, o ciclo de vantagens não
é**. Três razões sustentam isso:

1. A pergunta é de **trade-off**, não de emergência espontânea: "dá para equilibrar
   *sem* destruir as identidades?" é uma pergunta sobre **compatibilidade** entre dois
   objetivos. Responder exige procurar pontos que satisfaçam os dois — caso contrário
   só se demonstra que otimizar um sozinho não entrega o outro, que é uma afirmação
   bem mais fraca e quase óbvia.
2. **Penalidade não é restrição.** O AG é livre para destruir a identidade se o
   equilíbrio pagar mais, e é o que acontece: com `LAMBDA_DRIFT = 1.0` ligado o run
   inteiro, o melhor do AG escalar da bateria de 2026-09-18 ficou em **13/23** no
   validador, longe dos 23/23 do canônico — e a parte funcional dele, a Layer 3, em
   **1/5**, no piso dos modelos nulos (p = 0,74). O termo existe e pode perder; ter o termo
   não pré-determina a resposta. (No diagnóstico de 2026-09-16, sob o validador de 21
   asserções que precedeu o `grab_power`, o mesmo fenômeno deu 8/21.)
3. O conteúdo não-trivial da tese nunca foi "a identidade sobreviveu" — é **o preço**:
   quanto de equilíbrio se compra por unidade de drift. Esse é o formato da fronteira
   de Pareto, que é achado empírico, não suposição. E uma fronteira precisa de dois
   objetivos: sem drift no fitness, o braço NSGA-II inteiro deixa de existir.

## As duas réguas de identidade

O erro que a auditoria de 2026-09-16 encontrou não foi "identidade no fitness" — foi os
dois instrumentos do projeto **discordarem sobre o que a palavra significa**. O
`drift_penalty` dava 0,261 para o melhor do AG ("preservada") enquanto o validador dava
8/21 ("destruída") — números daquele diagnóstico, sob o validador de 21 asserções. Não era homogeneização: era **troca de papéis** (o Turtle virou o de
menor HP e maior dano, o Rushdown virou defensivo, o Zoner virou o de menor alcance).
Distância euclidiana é cega a **ranking**, que é o que identidade significa
operacionalmente aqui.

A solução mantém uma régua de cada lado da linha:

| régua | o que mede | onde vive | papel na tese |
|---|---|---|---|
| identidade **estrutural** | os genes continuam reconhecíveis | `drift_penalty`, **no fitness** | premissa: "continue sendo você" |
| identidade **funcional** | o personagem continua *jogando* como ele mesmo | Layer 3 do validador + concordância de ranking comportamental (τ), **post-hoc** | resposta: é o que a tese descobre |

A pergunta de pesquisa diz literalmente *"functional identities"* — comportamento, não
valor de gene. Nada no fitness referencia comportamento, então as réguas funcionais são
*held-out*. **Não são independentes**, e o texto precisa dizer isso: cada asserção da
Layer 3 é consequência quase direta de um gene definidor (o stun infligido vem do gene de
stun, a guarda quebrada do `grab_power`, a distância média do alcance e do recuo), então
comportamento é downstream dos genes que o fitness move. A Layer 3 tem só 5 bits (cada
arquétipo precisa ser o 1º numa métrica); a concordância de ranking — τ de Kendall entre a
ordem dos 5 personagens no canônico e no roster, em cada métrica comportamental, na média
— usa as 5 posições e é contínua, com 0 = acaso. Em contrapartida, as Layers 1-2 do
validador medem o mesmo eixo estrutural que o fitness otimiza e são **parcialmente
endógenas**: um score alto ali em parte reflete a penalidade ter funcionado.

O ciclo de vantagens **não** é régua de identidade: o próprio canônico realiza só 6 das 10
arestas no motor, então não há o que preservar ([02](02-canonical-cycle.md)).

## `drift_penalty` — a operacionalização de "identidade estrutural"

**RMS ponderada** dos desvios normalizados de cada personagem ao seu perfil canônico
(sobre os 11 genes, com os 3 pesos comportamentais reescalados para a soma canônica —
só a razão entre eles afeta o combate). **É a tradução numérica de "preservação de
identidade estrutural"**
— o eixo que a pergunta de pesquisa coloca em tensão com o equilíbrio — e o **verdadeiro
mecanismo anti-homogeneização** (puxa cada personagem para um canônico distinto). Com
`LAMBDA_DRIFT = LAMBDA_DOMINANCE`, identidade e equilíbrio pesam na mesma escala.

**E essa igualdade é o joelho medido da curva, não uma escolha por simetria.** O sweep de
2026-09-17 (5 braços × 5 sementes, orçamento reduzido) mostra que `dominance` fica **plano
em ~0,048** de λ_drift 0,25 a 1,0 e só então explode — 0,19 em λ=2, 0,34 em λ=4, com os
counters duros indo de 0,6 para 7,8 de 10 pares. λ = 1,0 é o **último ponto onde a
identidade sai de graça**: contra λ = 0,25 ele entrega drift 0,070 melhor custando dominance
0,006 pior. Antes, a justificativa era só negativa ("6,0 prendia ao canônico"). Detalhe e a
tabela completa em [04-design-decisions.md](04-design-decisions.md).

Vale dizer no texto que **só a razão entre os dois λ importa**: a seleção é por torneio, que
é ordinal, então escalar os dois pela mesma constante não muda decisão nenhuma. Por isso o
sweep varia um só — variar `λ_drift` com `λ_dominance` fixo percorre a família inteira, de
"equilíbrio pesa 4× mais" a "identidade pesa 4× mais".

Duas escolhas de medição que o texto precisa justificar:

- **Normalização pelo range do bound**, `(x − lo)/(hi − lo)`, e não pelo máximo `x/hi`.
  Dividir por `hi` subestima sistematicamente genes de `lo` alto: o HP vai de 250 a 450,
  então mover 162 pontos é 81% do range e apenas 36% do máximo. É a correção que
  conserta a **ordenação** dos indivíduos por identidade — sob `x/hi` o melhor do AG
  (8/21) aparecia como *menos* deslocado que o `best_dominance` do NSGA-II (11/21).
- **Ponderação pelos genes definidores** (`DRIFT_DEFINING_WEIGHT = 3.0`): mover o alcance
  do Zoner custa 3× mover o stun dele. Os genes definidores são declarados por arquétipo
  e espelham as asserções de ranking do validador. Isso alarga a margem entre indivíduos
  de identidade diferente (gap de 0,017 para 0,043), sem virar restrição dura.

## `dominance_penalty` — balanço global + teto de hard-counter + decisividade (C2)

A decisão de design mais sutil do projeto, e a que mais evoluiu; precisa ser bem
justificada na metodologia, incluindo a trajetória (uma hipótese intermediária foi
falsificada, e a métrica de equilíbrio foi reformulada — ver
[04](04-design-decisions.md)). Sob a formulação **C2**, equilíbrio = **nenhum
personagem domina o roster** (não "cada par a 50%"). A penalidade soma **três
sinais**:

```
dominance = DOMINANCE_GLOBAL_WEIGHT·global_term + DOMINANCE_CAP_WEIGHT·cap_term + DOMINANCE_DECIS_WEIGHT·decis_term
```

### Termo primário — balanço **global** por personagem
`global_term = RMS_i(|WR_global_i − 0.5| / 0.5)`, onde `WR_global` é o win rate
agregado do personagem sobre seus 4 oponentes. O ótimo é "ninguém domina o roster",
mas **não** força cada par a 50%: um boneco a 50% global pode vencer 2 e perder 2 —
exatamente o espaço em que o **ciclo de vantagens** pode existir.

> **Por que global, e não por-matchup?** O primário antigo era a WR **por-matchup**,
> cujo ótimo é *todo par a 50%* — equilíbrio plano. Mas um ciclo exige que pares
> tenham vencedor: otimizar "todo par a 50%" **destrói o ciclo por construção**, e a
> quebra seria um artefato do objetivo, não um achado. Sob C2 o objetivo deixa de
> forçar a quebra, e a emergência do ciclo vira o achado real (ver
> [02-canonical-cycle.md](02-canonical-cycle.md)).

### Termo secundário — teto de hard-counter
`cap_term = RMS_par(max(0, |WR_par − 0.5| − MATCHUP_WR_CAP) / (0.5 − MATCHUP_WR_CAP))`.
Penaliza só o excesso **acima** de `MATCHUP_WR_CAP` (banda `[0.35, 0.65]`). Mantém as
arestas do ciclo como **vantagens** (um par pode ter favorito), barrando apenas os
**counters esmagadores** (ex.: 100×0). Dentro da banda, o par não é penalizado.

### Termo secundário — decisividade por-luta numa banda
Regularizador de **qualidade de luta**. Score por-luta contínuo: KO contribui
`0.5 + 0.5·(HP_frac do vencedor)` (esmaga → ~1.0; ganha no fio → ~0.5); timeout, a
fração de HP%. Decisividade do matchup `D = média(|score − 0.5|)`, com excesso fora da
**banda `[0.02, 0.20]`**. O **teto** (0.20) é o regularizador de verdade: acima dele o
vencedor fecha com mais de 40% de HP de folga, isto é, todo confronto do par é massacre.
O **piso** (0.02) é apenas guarda de degenerescência.

- **Por que mantê-lo?** Guarda contra o **blowout-coinflip**: 55% A-esmaga / 45%
  B-esmaga ⇒ WR global ~50% (primário satisfeito) mas toda luta é um massacre. A
  decisividade por-luta — `média(|score−0.5|)`, não `|média(score)−0.5|` — detecta
  isso (todo blowout dá margem ~0.5).
- **Por que o piso é tão baixo?** Ele já foi 0.10, e nessa altura punia lutas
  *apertadas demais* — empurrando na direção **oposta** ao termo primário, já que
  equilibrar aproxima as lutas. A justificativa original ("luta decidida por 1% parece
  coin-flip") não sobrevive à medição no motor atual: **100% das lutas terminam em KO**,
  então decisividade baixa não é "a luta não aconteceu", é KO no fio — a melhor luta
  possível. O piso ficou em 0.02: acima do roster degenerado (dano mínimo, HP máximo, só
  GUARDA — 0% de KO, D ≤ 0,008) e abaixo de todo par de personagens distintos. Na prática
  penaliza 0 dos 10 pares em operação normal, contra 3–5 quando era 0.10. Dos cinco
  espelhos, pega só o do Zoner — não é ele que defende contra a solução trivial (cinco
  cópias do mesmo personagem); quem defende é o `drift_penalty`.
- **Por que isso importa para a comparação entre algoritmos.** Enquanto o piso mordia,
  era ele — um termo secundário de peso 0,5 — quem decidia AG × NSGA-II: decomposto, o
  NSGA-II era **melhor no termo primário** e perdia no piso. "O AG vence em
  `dominance_penalty`" estava certo como número e errado como leitura. Por isso os três
  termos passaram a ser reportados **separados** nos artefatos.

### Propriedades comuns
- **RMS** (sobre os 5 bonecos no global, sobre os 10 pares nos secundários): extremos
  pesam mais que moderados — impede o AG de esconder um boneco dominante ou um counter
  duro atrás de uma média balanceada.
- **Direcionalmente cego (`|WR − 0.5|`, `|score − 0.5|`):** não codifica quem deveria
  vencer, preservando a não-circularidade ([01](01-question-and-scope.md)).
- **Gradiente:** a objeção histórica ao WR ("em combate determinístico o WR é bimodal,
  sem gradiente") é contornada porque, quando as lutas ficam apertadas, o sorteio de
  intenção flipa desfechos e a WR vira **graduada** (ver
  [`../reference/11-combat-review.md`](../reference/11-combat-review.md)).

## O que o AG otimiza vs. o que é métrica post-hoc

A separação é o ponto científico: a tese argumenta sobre o que o AG **pode otimizar** e
o que **emerge sem ser codificado**.

| Métrica | Otimizada? | Onde aparece |
|---|---|---|
| `dominance_penalty` (global por personagem + teto de hard-counter + decisividade) | **sim** | Fitness e NSGA-II |
| `drift_penalty` (identidade **estrutural**: distância ponderada ao canônico) | **sim** | Fitness e NSGA-II |
| WR **global** por personagem (alvo 50%) | **sim** (termo primário do dominance) | Fitness, relatório, convergência |
| WR **por-matchup** exata (cada par a 50%) | **não** (só o teto de hard-counter) | Relatório post-hoc |
| Diferenciação entre personagens (homogeneização) | não | Métrica post-hoc (`drift_table`) |
| Identidade **funcional** (Layer 3 e concordância de ranking: como o personagem joga) | **não** | Relatório post-hoc — régua *held-out* |
| Ciclo canônico (arestas autorais) | **não** | Relatório post-hoc, descritivo — o canônico só realiza 6/10 |
| Sensibilidade dos genes | não | Validação metodológica ([05](05-methodological-validation.md)) |

> Houve um terceiro termo no fitness (`specialization_penalty`), **removido** — a razão
> e a trajetória dessa decisão estão em [04-design-decisions.md](04-design-decisions.md).
