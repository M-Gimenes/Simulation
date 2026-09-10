# Retomada — estado do projeto em 2026-09-10

Este arquivo é o retrato do **agora**. O levantamento original (2026-09-09, feito após
~2 meses parado) está no histórico do git; o que segue é o que restou dele depois da
rodada de correções.

- Pauta da auditoria de coerência que vem a seguir: [`REVIEW.md`](REVIEW.md).
- Pontos em aberto do sistema: [`docs/reference/10-known-issues.md`](docs/reference/10-known-issues.md).
- Trajetória das decisões: [`docs/tcc/04-caminhos-e-decisoes.md`](docs/tcc/04-caminhos-e-decisoes.md).

---

## 1. Fechado em 2026-09-10

**Persistência dos artefatos.** `results.json` passou a gravar o mesmo contrato do
`nsga2_results.json` — `seed`, `generations_run`, `stop_reason`/`converged`/`stagnated`,
`fitness`, `objectives` e o `history` por geração. A curva de convergência do AG escalar
deixou de exigir re-execução. O `sensitivity_analysis` passou a salvar a matriz Δ WR em
`results/sensitivity/sensitivity_analysis.json`.

**Teste estatístico entre algoritmos.** Novo `src/tools/compare_algorithms.py`:
Mann-Whitney U bicaudal + Â₁₂ de Vargha-Delaney + Holm-Bonferroni sobre as amostras por
semente do `multi_run`. Era o buraco de metodologia mais visível — os dois algoritmos
eram agregados lado a lado e nunca comparados formalmente. `scipy` entrou no
`requirements.txt` só por causa dele.

**Escolha escondida virou explícita.** Qual ponto da fronteira representa cada execução
do NSGA-II no `multi_run` era um literal no código; virou flag
(`--nsga2-representative`) e é gravado no artefato.

**Paralelismo.** `N_WORKERS = None` resolvia para 28 processos nesta máquina: além de
estourar o limite de commit do Windows (`WinError 1455`, que derrubou a primeira
bateria), era **2,2× mais lento** que o ótimo medido. Fixado em 8, com a medição
registrada no `config.py`. O resultado não muda com o nº de workers — verificado por
checksum idêntico de 1 a 28.

**Rastros removidos.** Quatro `random.seed()` que não faziam nada (o RNG do combate é
interno ao Numba) em `sensitivity_analysis`, `analyze_matchups`, `fingerprint` e
`archetype_validator` — junto do docstring que atribuía o pareamento +σ/−σ ao `random`,
e do aviso obsoleto no `08-tools.md` dizendo que o pareamento não funcionava. Também:
banda `[0.30, 0.70]` → `[0.35, 0.65]` em 4 docs, validador `/20` → `/21`, representantes
inexistentes (`best_balance`, `best_matchup`) no help de 3 tools, linhas de uso
`py tool.py` que não rodam, e `viewer._load_evolved` duplicando `Individual.from_results`.

**`10-known-issues.md` reescrito.** Deixou de ser changelog e virou o que está aberto.

**Artefatos regerados.** Todo o `results/` foi refeito com o código atual — os dois
`multi_run` publicados nos artigos vinham de antes do commit `3e64bbd` (28/06), que
mudou `MATCHUP_WR_CAP`, os bounds de dano, os danos canônicos e
`DEFEND_DAMAGE_REDUCTION` de uma vez. A bateria inteira levou 1h24.

## 2. O que a bateria de 2026-09-10 deu

> Resumo de leitura. **A fonte é o JSON**, indicada em cada bloco — não transcrever
> daqui para o texto sem conferir no artefato. Foi exatamente uma cópia solta de números
> (o `values.tex`) que ficou stale por dois meses.

**Agregado de 10 execuções** — fonte `results/multi_run/multi_run_{ga,nsga2}.json`,
sementes 42..51, reavaliadas sob a semente 9999 com 200 sims/matchup:

| | AG escalar | NSGA-II (`best_dominance`) |
|---|---|---|
| `dominance_penalty` | 0,0664 ± 0,0261 | 0,1403 ± 0,0658 |
| `drift_penalty` | 0,2669 ± 0,0149 | 0,2450 ± 0,0554 |
| hard-counters por execução | 0,7 ± 0,9 | 2,7 ± 2,1 |
| sementes que equilibram o roster | **60%** (6/10) | 20% (2/10) |
| hipervolume | — | 1,8084 ± 0,0394 |
| spacing | — | 0,0053 ± 0,0010 |

Os 5 bonecos ficam com WR global em `[40%, 60%]` em **100% das sementes** nos dois
algoritmos. O que separa os 60% dos 20% é o segundo predicado do roster equilibrado:
ausência de hard-counter.

**Comparação estatística** — fonte `results/multi_run/comparison_ga_vs_nsga2.json`:
o AG escalar vence em `dominance_penalty` (mediana 0,066 vs 0,129; p_Holm = 0,018;
Â₁₂ = 0,12, efeito grande) e em hard-counters por execução (0 vs 3; p_Holm = 0,049);
**sem diferença significativa** em `drift_penalty` (p_Holm = 0,769) nem em bonecos em
banda (p_Holm = 1,000). Ressalva obrigatória ao citar: o NSGA-II está representado pelo
`best_dominance`, um **extremo** da fronteira — ver o item de comparável em
[`REVIEW.md`](REVIEW.md).

**Robustez fora do laço** — fonte `results/external_validation/*.json`, 10 condições
novas (sementes 10000+) com 500 sims/matchup:

| Indivíduo | dominance fora do laço | bonecos robustos | pares que tripam | veredito |
|---|---|---|---|---|
| melhor do AG (seed 42) | 0,0279 ± 0,0062 | 5/5 | 0/10 | **ROBUSTO** |
| NSGA-II `best_dominance` | 0,1148 ± 0,0074 | 5/5 | 1/10 | frágil |
| NSGA-II `knee_point` | 0,3443 ± 0,0075 | 5/5 | 7/10 | frágil |
| canônico (baseline) | 1,4162 ± 0,0016 | 1/5 | 10/10 | frágil |

O melhor do AG dava `dominance = 0,0076` **dentro** do laço e 0,0279 fora: degrada 3,7×,
o que confirma algum ajuste à realização do RNG fixada pelo CRN — declarar isso, e
reportar sempre o número de fora. O equilíbrio em si sobrevive.

O canônico reproduz o baseline citado nos artigos (Rushdown 100%, Turtle 0,1%,
10/10 hard-counters), e o `external_validation_nsga2_best_dominance.json` saiu
**byte a byte idêntico** ao que já estava commitado — sinal limpo de reprodutibilidade.

**Sensibilidade** — fonte `results/sensitivity/sensitivity_analysis.json`: só
`attack_cooldown` (5,6%) passa do piso de ruído (1,8%); os outros 6 atributos saem
"neutros". **Não citar esse número como está** — a medição roda no canônico saturado e o
resultado é efeito de teto, não neutralidade de gene (item aberto em
[`REVIEW.md`](REVIEW.md) §4).

## 3. Aberto

### 🔴 Redação (decisão: recomeçar do zero)

A monografia (`overleaf/TCC/`) está ~2 gerações de modelo atrás — `metodologia.tex`
descreve 9 atributos, `defense`/`recovery`, indivíduo de 60 genes, decisão por
prioridade, `specialization_penalty` e a formulação pré-C2 do `dominance_penalty`. Além
disso `main.tex` promete seis capítulos e existem quatro arquivos, com `conclusao.tex`
ainda em branco.

O `values.tex` dos dois artigos também está stale: `\aggDomMean`, `\aggDomStd`,
`\aggDriftMean`, `\aggDriftStd`, `\aggHvMean`, `\aggHvStd`, `\hcPerSeed`,
`\hcPerSeedStd` e `\domCanExt` vêm dos artefatos antigos. Os números novos já existem em
`results/`; falta transcrevê-los.

> `overleaf/artigo-SBC/main.tex` descreve o modelo **atual** corretamente e já tem
> resultados, discussão e conclusão redigidos — a metodologia da monografia se reescreve
> a partir dele.

### 🟡 Calibração e coerência do sistema

Tudo o que estava marcado como *provisório, a calibrar* segue provisório:
`MATCHUP_WR_CAP`, os canônicos re-tunados, `ACTION_PERSISTENCE_SUBTICKS`, `TICK_SCALE`,
os pesos dos três termos do dominance, e o sweep de `LAMBDA_DRIFT` que nunca foi feito.

Somam-se a isso os pontos de coerência levantados durante as correções — o gate de
convergência do AG que é inalcançável na prática, o comparável correto entre escalar e
NSGA-II, a assimetria dos critérios de parada. **Tudo isso está na pauta de
[`REVIEW.md`](REVIEW.md)**, que é o próximo passo do trabalho.
