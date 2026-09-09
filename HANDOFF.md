# Retomada — estado do projeto em 2026-09-09

Levantamento feito após ~2 meses parado: onde a coisa parou, o que já estava
resolvido, e os buracos que sobraram. O histórico das decisões segue em
[`docs/reference/10-known-issues.md`](docs/reference/10-known-issues.md); este
arquivo é o retrato do **agora**.

---

## 1. Onde parou

| Período | Frente | Estado |
|---|---|---|
| até 30/06 | Sistema (motor, fitness, tools) | Estável — último commit em `src/` é 30/06 e só mexeu em comentários |
| 01/07 | Rodadas + plots (`nsga2_results`, `external_validation`, fronteira) | Gerados |
| 14/08 | Redação dos artigos (SBC + Latin.Science) | Concluídos, sem placeholders pendentes |
| — | **Monografia (`overleaf/TCC/`)** | **Parada e desatualizada** ← ponto de retomada |

Os 5 últimos commits são polimento do `overleaf/artigo-latinware-2026/main.tex`.

**Sanidade verificada nesta revisão:** os 6 smoke tests passam; a avaliação do
canônico reproduz exatamente o ponto `best_drift` da fronteira salva
(`dominance = 1.4154`, `drift = 0`); o `analyze_matchups` canônico reproduz o
baseline citado nos artigos (7/10 blowouts, Rushdown 100%, Turtle 0%, 5/10 arestas
do ciclo mantidas). O código está redondo — ~0,02 s por avaliação de indivíduo em
12 núcleos.

## 2. O que estava sendo resolvido (tudo encerrado)

Trajetória completa em `docs/tcc/04-caminhos-e-decisoes.md`:

1. Seed não reproduzia (RNG do Numba é interno) → `seed_combat()` + Common Random Numbers.
2. `specialization_penalty` não media o que dizia → removido; escalar e NSGA-II
   passaram a otimizar os mesmos 2 eixos.
3. WR bimodal, sem gradiente → objetivo virou decisividade por luta… que se revelou
   **cego à frequência de vitória** (hipótese "luta apertada ⟹ WR 50%" falsificada) →
   WR voltou como termo primário.
4. WR por-matchup força equilíbrio plano, incompatível com o ciclo por construção →
   reformulação **C2**: primário = WR global por personagem + teto de hard-counter +
   decisividade.
5. `LAMBDA_DRIFT` 6.0 → 1.0 (com 6.0 o AG escalar ficava preso ao canônico).
6. Simplificação do combate: fora `defense`, `recovery`, hesitação, cornering; `stun`
   virou fração do cooldown; decisão virou intenção→execução. 10 genes/personagem.

Nada disso está pendente. O que sobrou é o que segue.

---

## 3. Buracos, por prioridade

### 🔴 3.1 Números publicados nos artigos vêm de um modelo anterior à calibração final

Checagem forense nos artefatos (comparando o campo `hard_counter` gravado com o
`MATCHUP_WR_CAP` que o teria produzido):

| Artefato | Cap detectado | Veredito |
|---|---|---|
| `results/multi_run/multi_run_ga.json` | **0.20** | ❌ anterior a `3e64bbd` |
| `results/multi_run/multi_run_nsga2.json` | **0.20** | ❌ anterior a `3e64bbd` |
| `results/external_validation/external_validation_canonical.json` | schema antigo (`winrates`) | ❌ anterior ao realinhamento C2 |
| `results/external_validation/external_validation_nsga2_best_dominance.json` | 0.15 | ✅ atual |
| `results/nsga2_results.json`, `results/results.json`, plot 20260701 | — | ✅ atual (confirmado por reavaliação) |

O commit `3e64bbd` (28/06) mudou de uma vez: `MATCHUP_WR_CAP` 0.20→0.15, bounds de
dano [10,20]→[15,30], os danos canônicos dos 5 arquétipos e
`DEFEND_DAMAGE_REDUCTION` 0.5→0.6. Os dois `multi_run` são **anteriores** a tudo isso.

**Consequência em `values.tex`** (fonte única dos dois artigos) — estão stale:
`\aggDomMean`, `\aggDomStd`, `\aggDriftMean`, `\aggDriftStd`, `\aggHvMean`,
`\aggHvStd`, `\hcPerSeed`, `\hcPerSeedStd`, `\domCanExt`.

São exatamente os números do parágrafo de estatística agregada (SBC linhas 687–700;
Latinware 459–464) — o parágrafo que sustenta a frase-tese *"em N execuções, X%
equilibraram o roster"*. Sinal de apoio: `\domCanExt` = 1,11 contra 1,4154 medido
agora no canônico, que é praticamente determinístico.

**Custo de refazer: baixo.** ~0,02 s por avaliação serial em 12 núcleos → a bateria
(`multi_run` ga + nsga2, 10 sementes cada, mais `external_validation` do canônico)
deve caber em cerca de uma hora. É o item de maior retorno por hora do projeto.

### 🔴 3.2 A monografia está ~2 gerações de modelo atrás, e faltam 3 capítulos

`overleaf/TCC/textuais/metodologia.tex` (527 linhas) descreve um sistema que não
existe mais:

- **nove** atributos, incluindo `defense` e `recovery`; indivíduo de 5×12 = **60 genes**
  (hoje: 7 atributos + 3 pesos = 50)
- bounds antigos (HP 300–400, dano 10–20)
- `\subsection{Sistema de decisão por prioridade}` — prioridade decrescente,
  substituída por intenção→execução
- `\subsection{Specialization penalty}` — termo **removido** do fitness em 24/06
- `dominance_penalty` na formulação por-matchup com `MATCHUP_THRESHOLD = 0.10`
  (formulação pré-C2)
- `S_eff = min(S_raw, S_cap)` com `STUN_CAP_MULTIPLIER` e `Recovery` — constante e
  gene que não existem
- encurralamento contra parede — removido

Além disso, `overleaf/TCC/main.tex` promete seis capítulos e existem quatro arquivos,
sendo `conclusao.tex` ainda o texto-modelo em branco. **Faltam `implementacao.tex`,
`resultados.tex`, `discussao.tex` e a conclusão de verdade.**

> Lado bom: `overleaf/artigo-SBC/main.tex` descreve o modelo **atual corretamente** e
> já tem resultados, discussão e conclusão redigidos. A metodologia da monografia se
> reescreve a partir dele (expandindo), não do zero.

### 🟡 3.3 Artefatos que os Resultados pedem e que não existem

- `main.py` salva só `{"best_individual": [...]}` — **sem seed, sem fitness, sem
  objetivos, sem `history`**. O `result.history` (`GenerationStats` por geração) é
  impresso e descartado. A curva de convergência do AG escalar, listada como Resultado
  nº 2 em `docs/tcc/06-resultados-a-apresentar.md`, **não tem artefato** — precisa
  re-rodar com persistência.
- `src/tools/sensitivity_analysis.py` só imprime; não salva nada. A tabela de
  sensibilidade citada na validação metodológica também não tem artefato.
- `external_validation` só foi rodado para `best_dominance` — mas os dois artigos
  destacam o **`knee_point`** como o ponto interessante (identidade quase intacta). O
  knee não tem sustentação de robustez.
- `results/results.json` não registra a seed (o `nsga2_results.json` registra) —
  assimetria de reprodutibilidade.

### 🟡 3.4 Calibração declarada "provisória" e nunca feita

`CLAUDE.md` marca explicitamente como *provisórios, a calibrar*: `MATCHUP_WR_CAP`
(0.15), os canônicos re-tunados, `ACTION_PERSISTENCE_SUBTICKS` (10) e `TICK_SCALE`
(5). Não há no repo nenhum experimento variando qualquer um deles — e o instrumento
para comparar configurações já existe (hipervolume por configuração). O próprio
Latinware admite isso em trabalhos futuros. Também nunca foi feito o **sweep de
`LAMBDA_DRIFT`**, que seria a demonstração de que o AG escalar é *um ponto* da
fronteira que o NSGA-II mapeia.

### 🟡 3.5 Buracos de metodologia (estruturais, não bugs)

- **Sem teste estatístico.** `docs/tcc/08-metodologias-da-literatura.md` cita
  Mann-Whitney/Wilcoxon como prática padrão ao comparar configurações; o `multi_run`
  agrega média±σ de AG e NSGA-II mas nunca os compara formalmente. Buraco mais fácil de
  tapar e mais visível para quem lê método.
- **Equilíbrio condicionado a uma política fixa.** Os pesos `w_*` são a política; se
  existe exploit, ninguém o procura. É o item 2.1 (coevolução), decidido como trabalho
  futuro — decisão legítima, mas é a objeção mais forte ao resultado, então precisa
  aparecer explicitamente na Discussão, não só em Trabalhos Futuros.
- **Crossover só por bloco de personagem**: recombinação intra-personagem depende 100%
  da mutação.
- **Round-robin uniforme**: não modela matchmaking (jogadores escolhendo matchups
  favoráveis).
- **Grappler sem asserção comportamental** (o modelo não representa grab) — 4 asserções
  de Layer 3 para 5 arquétipos.

### 🟢 3.6 Drift de documentação (rápido)

- Banda antiga `[0.30, 0.70]` / `[30%, 70%]` ainda citada em: `docs/tcc/03:48`,
  `docs/tcc/04:107`, `docs/tcc/06:62`, `docs/tcc/08:41`. Correto hoje: `[0.35, 0.65]`.
- `docs/tcc/06-resultados-a-apresentar.md:20` diz "Validador (score /20)"; o validador
  roda **21/21** (17 estruturais + 4 comportamentais).
- `src/tools/archetype_validator.py:2` — docstring diz "17 asserções estruturais
  (12 inter + 5 intra)", sem mencionar a Layer 3 que ele mesmo executa.
- `main.py:2` — docstring ainda anuncia `--plot-3d`, flag removida.
- `docs/reference/10-known-issues.md` ainda afirma "todas as rodadas anteriores estão
  invalidadas" e "pendente: rodar o multi_run real". Meia-verdade hoje: o `multi_run`
  foi rodado, mas com o modelo pré-calibração (§3.1). Reescrever com o estado real.

---

## 4. Ordem sugerida

1. **Persistir o que falta** (`main.py`: seed + objetivos + `history` no
   `results.json`; saída JSON do `sensitivity_analysis`) — mudança pequena, evita
   re-rodar duas vezes.
2. **Re-rodar a bateria** (`multi_run` ga + nsga2; `external_validation` do canônico e
   do `knee_point`) e atualizar `values.tex` — destrava a correção dos dois artigos e
   já produz os números que os Resultados da monografia vão usar. ~1 h de CPU.
3. **Reescrever `metodologia.tex`** a partir do `artigo-SBC/main.tex`, e escrever
   `implementacao` / `resultados` / `discussao` / `conclusao`.
4. Limpar o drift de docs (§3.6) e reescrever o `10-known-issues.md`.
