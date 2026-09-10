# Retomada — estado do projeto em 2026-09-10 (fim do dia)

Este arquivo é o retrato do **agora**. O levantamento original (2026-09-09) e a rodada
de correções de metodologia estão no histórico do git; o que segue é o estado depois da
**auditoria de coerência** e da **reforma do motor de combate**.

- Pauta da auditoria, com tudo o que foi verificado e o que segue aberto: [`REVIEW.md`](REVIEW.md).
- **Ordem de execução do que falta:** [`REVIEW.md` §8](REVIEW.md).
- Auditoria do combate, com os números antes/depois: [`docs/reference/11-combat-review.md`](docs/reference/11-combat-review.md).
- Pontos em aberto do sistema: [`docs/reference/10-known-issues.md`](docs/reference/10-known-issues.md).
- Trajetória das decisões: [`docs/tcc/04-caminhos-e-decisoes.md`](docs/tcc/04-caminhos-e-decisoes.md).

---

## 0. Comece por aqui

1. **O ambiente não sobe sozinho.** `.venv/` é gitignored e o Python do sistema (3.14)
   não tem `numpy`/`numba`/`scipy`. Rode `.\setup.ps1` antes de qualquer coisa.
2. **`results/` está OBSOLETO.** Todo artefato lá descreve o motor anterior à reforma de
   2026-09-10. Não cite número nenhum de `results/`, e não regenere a bateria ainda — ela
   só deve rodar no passo 7 da ordem, com o fitness e a calibração já fechados.
3. **O próximo passo é o 2 da ordem: A + B**, e ele começa com uma decisão do usuário
   (ver §3 abaixo). Não é código: é definir a régua de identidade e a de equilíbrio.

## 1. O que foi feito em 2026-09-10

### Auditoria de coerência (`REVIEW.md`)

A pauta foi percorrida inteira. Cada item ganhou uma linha `**Verificado:**` com a
medição que sustenta ou derruba o que estava só afirmado, e o §0 virou um sumário de
incongruências com estado. Oito achados **novos**, que não estavam na pauta original —
os quatro de combate foram corrigidos no mesmo dia, os outros seguem abertos.

### Reforma do motor de combate

A preocupação era "o combate está quebrado em algum sentido?" — não havia dado nenhum
sobre isso. Havia. Detalhe completo com tabelas em
[`11-combat-review.md`](docs/reference/11-combat-review.md); em resumo:

| | antes | depois |
|---|---|---|
| **M1** intenção sobrescrita por ADVANCE forçado fora do alcance | zoner perde **100%** com *qualquer* range (5→20) e *qualquer* knockback (0→3); `knockback` com derivada **negativa** | intenção vale sempre; `range` no corpo neutro Δ=46,8% → **Δ=90,5%** |
| **M1b** ataque exclusivo com o movimento | recuar = forfeit de dano; zonear não existia como jogada | dois canais: postura escolhida, ataque por regra. zoner×rusher 0,0% → **49,0%**; `knockback` no contexto Δ=0,1% → **Δ=44,3% ↑** |
| **M2** corpos se atravessando | **134 atravessamentos/luta** | colisão, movimento simultâneo, A sempre à esquerda |
| **M3** stun arredondado | **4 níveis efetivos** com `cooldown=1`; amplitude ±1σ = 6,8% | timer contínuo; Δ 17,2% → **53,5%**, amplitude **17,4%** |
| **D** desempate por HP% igual | espelho do Rushdown **54,90%** para o lado A | empate como 3º desfecho (`winner = -1`, meia vitória); espelhos ~50% |
| impasse | com M1 sozinho: Zoner×Turtle **100% de timeout** | ADVANCE imposto só quando ninguém alcança ninguém → **0% de timeout** |

Sobre a ressalva de que o atravessamento existia para evitar encurralamento: medido
depois da colisão, **o canto não virou armadilha automática** — quem é encurralado perde
entre 55% e 100% conforme o par, e o knockback de quem está preso empurra o agressor.
Manter sob observação na recalibração.

**O que isso destravou.** Um AG curto (pop 120, 25 gerações, 80 sims/par) leva o
`dominance_penalty` de 1,236 a 0,250, com os 5 bonecos em WR global [48,7%, 52,0%] e
**espalhamento real por par**: 22% · 34% · 36% · 48% · 50% · 50% · 58% · 64% · 70% · 71%.
No motor antigo o evoluído ficava achatado em [43,5%, 58%]. **Agora existe espaço para o
ciclo de vantagens viver** — que é a condição para a pergunta de pesquisa fazer sentido.

Código tocado: `src/engine/combat.py` (três helpers `@njit` compartilhados agora —
`_decide_action`, `_apply_movement`, `_decide_winner`), `src/engine/fitness.py` (empate
no round-robin e no score por-luta), `analyze_matchups`, `viewer`, `web_viewer`, e os dois
testes que codificavam o modelo antigo. `Action` deixou de ter `ATTACK`: virou postura de
três valores, e o `CombatTrace` ganhou o canal `attacked`. Os 6 smoke tests passam.

## 2. A leitura macro do modelo — 4 eixos, 1 ainda incoerente

| eixo | do que é feito | estado |
|---|---|---|
| **Espaço** | range, speed, knockback, posição, campo, colisão | ✅ coerente após M1+M1b+M2 |
| **Tempo** | cooldown, stun, persistência da intenção | ✅ coerente após M3. Ressalva: a persistência (10 sub-ticks) é **maior que o cooldown mínimo** (5), então quem tem `cooldown=1` e sorteia GUARDA abre mão de duas janelas de ataque |
| **Recurso** | hp, damage, DEFEND | ❌ **sem counter** — ver §4 |
| **Política** | 3 pesos, amostragem proporcional | contínua, mas **cega ao estado** (não olha HP, distância nem se o oponente está stunado) e com degenerescência de escala (só a razão importa) |

## 3. Próximo passo: A + B (passo 2 da ordem)

Não começa com código. Começa com duas decisões:

**(A) Qual é a régua de identidade que o fitness otimiza?** O `drift_penalty` dá 0,261
para o melhor do AG e 0,271 para o `best_dominance` do NSGA-II — praticamente empatados —
enquanto o validador de identidade dá **7/21 contra 13/21**. A diferenciação par-a-par
dá 0,92 ("preservada"). Os dois medidores que o projeto usa não enxergam o que
aconteceu: não foi homogeneização, foi **troca de papéis** (o Turtle virou o boneco de
menor HP e maior dano, o Rushdown virou defensivo, o Zoner virou o de menor alcance).
Drift é distância euclidiana cega a **ranking**; diferenciação mede espalhamento, não
correspondência. Opções na mesa: incorporar a estrutura de ranking do validador ao eixo
de identidade, ponderar o drift pelos genes definidores de cada arquétipo, ou manter e
declarar. Detalhe em [`REVIEW.md`](REVIEW.md) §3.

**(B) O `dominance_penalty` continua sendo um número composto, e o piso de decisividade
continua no fitness?** Decomposto, o NSGA-II é **melhor que o AG no termo primário**
(global 0,0327 vs 0,0406); ele perde por um hard-counter e sobretudo pelo **piso de
decisividade**. Ou seja "o AG vence em `dominance_penalty`" é verdade como número e falso
como leitura. Some-se a isso um fato novo do motor reformado: no AG curto, os 10 pares
deram decisividade entre 0,05 e 0,13 contra `MATCHUP_FLOOR = 0,10` — o piso passou a
morder em quase todo par. Detalhe em [`REVIEW.md`](REVIEW.md) §4.

Depois vêm, nesta ordem: **E** (gate de convergência), **C** (sub-convergência do
NSGA-II), **H** (recalibrar canônicos), **R** (grab), bateria completa, **F** e **G**,
menores e docs. A tabela está em [`REVIEW.md` §8](REVIEW.md).

## 4. O grab / quebra de guarda (item R) — anotado para quando chegar a vez

**Decisão registrada: entra no escopo, mas só depois de fechar A, B e C.**

DEFEND reduz 40% do dano e **não tem custo** — não há chip damage, quebra de guarda nem
stamina. O counter canônico ao bloqueio, em qualquer jogo de luta, é o grab: exatamente a
mecânica ausente do Grappler. A mesma lacuna produz três sintomas hoje tratados como
problemas separados:

1. o eixo Recurso sem contrapartida — defender indefinidamente não é punível;
2. a Layer 3 do validador com 4 asserções para 5 arquétipos (o Grappler não tem
   assinatura comportamental distinta do Rushdown);
3. a aresta "Grappler vence Turtle" do ciclo canônico — cuja justificativa na tabela do
   `CLAUDE.md` é literalmente *"grab é o counter canônico ao bloqueio"* — sem realização
   no motor.

Quatro esboços de desenho e as perguntas a responder antes de escolher (alcance próprio?
cooldown próprio? efeito contra quem **não** defende?) estão em
[`REVIEW.md`](REVIEW.md) §2, item R. Nenhum decidido.

## 5. Aberto — redação

Sem mudança desde a rodada anterior, e agora com um agravante: a reforma do motor tornou
**todos** os números publicados obsoletos.

A monografia (`overleaf/TCC/`) está várias gerações de modelo atrás — `metodologia.tex`
descreve 9 atributos, `defense`/`recovery`, indivíduo de 60 genes, decisão por prioridade,
`specialization_penalty` e a formulação pré-C2 do `dominance_penalty`. `main.tex` promete
seis capítulos e existem quatro arquivos, com `conclusao.tex` em branco. Decisão anterior:
recomeçar do zero a partir de `overleaf/artigo-SBC/main.tex`, que descreve o modelo
melhor — **mas mesmo ele agora descreve um motor que não existe mais** (ação única em vez
de dois canais, sem colisão, sem empate).

O `values.tex` (idêntico nos dois artigos) já estava stale (`\\aggDomMean`, `\\aggDriftMean`,
`\\aggHvMean`, `\\hcPerSeed`, `\\domCanExt`) e agora está inteiramente obsoleto. Registrado
também em [`REVIEW.md`](REVIEW.md) §6: `\\domAg` usa o número **dentro** do laço enquanto as
outras três células da mesma linha coincidem com os de fora — a única célula com vantagem
de proveniência é justamente a do AG.

Bibliografia: Derrac et al. 2011, Arcuri & Briand 2011 e Vargha & Delaney 2000 são citadas
nos docs e no código e **não estão** em nenhum dos três `.bib`.
