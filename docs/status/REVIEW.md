# Revisão

Duas revisões: a do **sistema**, fechada, e a do **texto da monografia**, em andamento. Este
arquivo guarda só o que ainda orienta trabalho; o que já virou decisão está nos docs.

---

## 1. Auditoria do sistema — fechada

Aberta em 2026-09-10 e fechada em 2026-09-21, com cerca de 50 itens, incluindo a auditoria
do zero (Z1–Z13). O porquê de cada decisão, com os números, está em
[`docs/thesis/04-design-decisions.md`](../thesis/04-design-decisions.md). O que foi
encerrado, listado para não reabrir, está em
[`docs/reference/10-known-issues.md`](../reference/10-known-issues.md) §4, e os limites
declarados e as perguntas ainda abertas, na §2 do mesmo arquivo. As tabelas item a item
(M1–R, Z1–Z13) e a ordem de execução ficam no git:
`git show 37a3587:docs/status/REVIEW.md`.

---

## 2. Revisão da monografia (`overleaf/TCC`)

Registro das revisões de **texto** da monografia, para que uma revisão não desfaça a outra.
Duas passadas até aqui: a de 2026-09-29 (commits `5844005`, `f2568b3`, `37a3587`) e a de
2026-09-30 (leitura externa, texto contra `results/`, referências contra as fontes).

### 2.1 Regras

1. **Base de evidência congelada:** bateria de 2026-09-23 e validação externa de
   2026-09-29. Nenhum item desta seção pede experimento novo nem mudança de código.
2. **Item fechado só reabre com:** (a) um número dos artefatos que o contradiga, (b) um
   contraexemplo lógico, ou (c) o trecho da fonte citada. Preferência de redação não reabre.
3. **Afirmação que depende de resolução carrega a régua** ("a 1000 lutas por par"). Quando
   uma régua muda, toda afirmação feita nela é reverificada. Foi a falta disso que derrubou
   duas leituras depois da troca de 200 para 1000 lutas: o controle λ = 0 (pega em 23/09) e
   a "simetria perfeita" (T1, que passou pela revisão de 29/09).
4. **Verbo pelo tipo de evidência:** "mostra"/"mede" só para comparação com controle ou
   medição direta; mecanismo é "consistente com". A mesma forma no resumo, nos resultados,
   na discussão e na conclusão.
5. **Propagação na mesma passada:** tese → `CLAUDE.md` → `docs/reference/` →
   `docs/thesis/04` (porquê) e `07` (achado) → esta seção.
6. **Depois da passada de 2026-09-30, revisão só por checklist:** números contra artefatos,
   texto contra esta seção, compilação. Leitura aberta nova, só por pessoa externa.

### 2.2 Fechado em 2026-09-29 — mantido

Mecanismo da perda de identidade em dois estágios; sensibilidade dos pesos com a janela dos
atributos (12 a 17 pp: a política pesa no combate); o viés da régua grosseira **não**
explica a virada do controle λ = 0; canônico entre os 11 melhores da geração 0; o híbrido
"aproxima-se" da identidade do NSGA-II; diferenciação só descritiva; `dominance` da
validação externa sobre a amostra somada; "não antagônicos" restrito ao peso adotado;
"replica" restrito ao elenco validado e ao laço de otimização (no resumo).

### 2.3 Fechado em 2026-09-30

Todos os itens abaixo foram aplicados na passada de 2026-09-30, com a propagação da regra 5
(`CLAUDE.md`, `docs/reference/08`, `10` e `12`, `docs/thesis/02`, `04`, `06`, `07` e `09`).
A monografia compila sem referência nem citação indefinida (112 páginas). Na mesma passada,
e pelo mesmo achado, entraram:
- em T2, a ressalva em `discussao.tex:59` ("diferenças grandes de taxa de dano, como as do
  canônico, tendem a produzir hierarquias");
- em T4, o nome completo dos autores de Chen et al. no `.bib`, e a saída de
  `livingstone2006coevolution`: o artigo é de 2005 e propõe uma IA hierárquica para jogos
  de estratégia, não o teste de equilíbrio que a frase lhe atribuía;
- em T5, "Browne e Maire ampliaram a abordagem" virou "de forma independente, aplicaram";
  o survey de Togelius et al. registra que os trabalhos foram independentes;
- em T9, a réplica instrumentada da semente 42 na limitação "análises com um único
  elenco";
- em T10, `discussao.tex:37` ("presa ao ponto de partida");
- nos menores, a frase da fase 2 do híbrido em `metodologia.tex:602` perdeu "em vez de
  reutilizar os sorteios já vistos", e o detalhe foi para `10-known-issues`.

**Achados novos ou com evidência nova — obrigatórios.**

| # | Afirmação e onde | Evidência | Correção |
|---|---|---|---|
| T1 | "Tão equilibrado quanto a simetria perfeita, dentro do ruído": resumo, `resultados.tex:21,90`, `discussao.tex:11`, `conclusao.tex:110`, `CLAUDE.md` (Measurement) | `baselines.json`: espelhos com `dominance` 0,106 (Zoner, dos quais 0,085 é o piso de decisividade), 0,025, 0,012, 0,013, 0,011; termo global médio dos espelhos 0,014. AG: 0,0355 [0,025; 0,042], termo global 0,032. DP de medição 0,006. Z13 (18/09) concluiu "dentro do ruído" a 200 lutas, certo naquela régua; a de 1000 derrubou | "Próximo da simetria": todos os personagens em banda, termo global 0,032 contra 0,014 dos espelhos. Explicar o espelho do Zoner em `resultados.tex:21` |
| T2 | "Equilíbrio global com pares decididos força a intransitividade": `protocolo.tex:250`, `discussao.tex:61`, `CLAUDE.md`, `thesis/04` (Leituras corrigidas) | Contraexemplo: ordem estrita com margens 0,05 dá taxas globais de 55% a 45%, todas as arestas decididas (limiar 0,008) e 0 tríades | "Minimizar o termo global favorece a intransitividade; a banda não a exige" |
| T3 | Gingold como base do ciclo entre arquétipos: `introducao.tex:6`, `ref_teorico.tex:22,31` | O artigo trata do ciclo entre **ações** da luta; o §3.1 prova que "sem escolha imbatível, o grafo é cíclico". A revisão de 29/09 conferiu só os metadados | Citar como analogia declarada; o ciclo entre arquétipos é extensão do autor |
| T4 | Chen et al.: "classes", "mono-objetivo" (`ref_teorico.tex:149`, `introducao.tex:35`); "coevolução de estratégias" (`discussao.tex:88`, `conclusao.tex:128`) | Balanceiam raças, por coevolução cooperativa (CCEA + PIPE) das funções de atributo; modelo por turnos; tratam o balanceamento como multiobjetivo | "Raças"; "sem fronteira de Pareto"; para coevolução de estratégias, Leigh et al. 2008 (entra no `.bib`) |
| T5 | Togelius et al. "situa o balanceamento como categoria": `ref_teorico.tex:151` | Não é categoria da taxonomia; aparece como critério de avaliação em exemplos | Reescrever a frase |
| T6 | "Os mesmos autores recomendam Â₁₂": `ref_teorico.tex:138` | Derrac et al. não tratam de tamanho de efeito | Atribuir só a Arcuri & Briand |
| T7 | Política "aleatória da população inicial" (`discussao.tex:33`) e "rumo à mistura uniforme" (`resultados.tex:245`) | Tabela de política: no λ = 0 os cinco recuam 0,19 a 0,28 (sorteada: 1/3); no AG, 0,17 a 0,23 fora o Zoner | Descrever o observado: um perfil comum, com pouco recuo; sem "aleatória" |

**Completam a passada de 2026-09-29 — a decisão fica, muda a redação.**

| # | Onde | O que falta |
|---|---|---|
| T8 | Resumo | Manter "mostra que parte da perda decorre da seleção escalar"; o mecanismo vira "consistente com", como em `discussao.tex:48` |
| T9 | `conclusao.tex:119` (contribuição 3) | O estágio 1 é pressão da soma, não ruído (`discussao.tex:44`) |
| T10 | `conclusao.tex:120,130` (contribuição 4, trabalho futuro) | "O passo decide" e "presos ao ponto de partida" → passo pequeno **e** ruído da soma escalar, como em `discussao.tex:33`; o NSGA-II move a política com o mesmo passo |
| T11 | `discussao.tex:70`, `resultados.tex:190` | Título "produz significância espúria" → a redação da contribuição 5; "não custa equilíbrio" → "não custou equilíbrio mensurável" (contribuição 2) |
| T12 | `conclusao.tex:110` | "Fora das condições de treino" → "fora do laço de otimização", como no resumo |
| T13 | `resultados.tex:350` | Manter 3/20 no laço e acrescentar a checagem reavaliada: o `scalar_optimum` bate o AG na soma em 18/20; o híbrido bate o `scalar_optimum` em 14/20 |
| T14 | `docs/thesis/04:1901-1909` | Ainda atribui a virada ao viés da régua; `f2568b3` alinhou o 07 e o 12, não o 04 |
| T15 | `protocolo.tex:323` | A validação externa é de 29/09, não de 23/09 |
| T16 | `resultados.tex:49` | "0,28" escrito à mão → `\trajDriftTrinta` |

**Menores — na mesma passada, sem reabrir.** p empírico "igualam ou superam"
(`protocolo.tex:146`); "cerca de 6" é a média dos 35 nulos (`protocolo.tex:134`); coluna
"Margem" da tabela do ciclo é média das margens medianas; legenda da tabela de equilíbrio
promete quartis de t_g; dano do Turtle não é definidor (`metodologia.tex:124`); "dois
deles" (`metodologia.tex:650`, o σ dos pesos é o terceiro); velocidade 3,51 contra piso
3,46; campo 80, em que o Zoner melhora (`discussao.tex:77`); controle sem semente com efeito
médio também em τ e L1-2 (`resultados.tex:192`); argumento do ciclo com 200 lutas
(`protocolo.tex:246`); uma frase dizendo que o teste pareado entrou depois da bateria de
21/09 (`protocolo.tex:182,234`); Volz et al. 2016 nos trabalhos relacionados; tirar
`preuss2012balanced` do `.bib` (fonte nunca localizada, não citada).

**Não mexer — decidido.** O `knee_point` na validação externa (rodar de novo é retrabalho,
e o n = 1 já está declarado); o binomial com arestas somadas (a conclusão é a mesma nos dois
testes); o reteste de τ com três medições (o texto já diz); a fase 2 do híbrido, que
reavalia a fronteira no stream da geração 75 e ressemeia o gerador (vai para
`docs/reference/10-known-issues.md`, sem mudar código, que invalidaria a bateria); a
citação de Gingold no artigo da Latinware, que só muda se a versão final ainda aceitar.
