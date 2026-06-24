# 01 — Pergunta de pesquisa e escopo

**Entra em**: Introdução, Objetivos.

## Pergunta central

> Um Algoritmo Genético consegue atingir equilíbrio competitivo entre 5 arquétipos
> distintos **sem destruir suas identidades funcionais**?

## A decisão metodológica que sustenta a tese: não forçar identidade

- Os valores canônicos dos arquétipos servem como **semente da população inicial** e
  como **baseline de medição de drift** — nunca como restrição rígida. O AG evolui
  livremente; o desvio é *penalizado* de forma suave (`LAMBDA_DRIFT`), nunca
  *hard-constrained*.
- O **ciclo canônico de vantagens** (quem vence quem) **não é codificado em nenhuma
  penalidade** — é medido *post-hoc*.

### O argumento de não-circularidade (central, deve aparecer explícito)

Codificar o ciclo (ou a identidade) no fitness tornaria a pergunta **circular**: o AG
"preservaria identidade" apenas porque foi pago para preservar. Ao manter identidade
como algo **medido, não imposto**, o resultado — preservou ou não? — passa a ser um
achado genuíno, não um artefato da função objetivo. Distinção fina, mas decisiva:
- *penalizar* o drift (soft) = dar um custo à perda de identidade, mas deixar o AG
  livre para pagá-lo se valer a pena → mede-se o trade-off;
- *forçar* o ciclo (hard) = proibir certos resultados → não se mede nada, só se obtém
  o que foi imposto.

## O experimento central

**Equilíbrio com preservação** e **equilíbrio com homogeneização** são **ambos
resultados cientificamente válidos**. Comparar os dois cenários é o experimento:
- o **NSGA-II** torna o trade-off explícito ao percorrer toda a fronteira (de "preserva
  e desequilibra" a "equilibra e homogeneíza");
- o **AG escalar** dá um ponto dessa fronteira, com `LAMBDA_DRIFT = LAMBDA_DOMINANCE`
  (pesos iguais).

Detalhe de como cada eixo é medido: [03-formulacao-do-fitness.md](03-formulacao-do-fitness.md).

## Escopo (delimitação honesta)

- Modelo de combate é uma **simplificação** de FGCs reais (sem frames por golpe,
  mix-ups, neutral game). Ver limitações em
  [07-achados-e-limitacoes.md](07-achados-e-limitacoes.md).
- **5 arquétipos** — suficiente para um ciclo fechado (cada um vence 2, perde 2);
  FGCs reais têm 10+.
- O objeto de teste é o **trade-off equilíbrio × identidade**, não a fidelidade do
  modelo a um jogo específico.
