# 01 — Pergunta de pesquisa e escopo

**Entra em**: Introdução, Objetivos.

## Pergunta central

> Um Algoritmo Genético consegue atingir equilíbrio competitivo entre 5 arquétipos
> distintos **sem destruir suas identidades funcionais**?

## A decisão metodológica que sustenta a tese: o fitness codifica a premissa, nunca a resposta

- **Premissa** é o que cada arquétipo **é** — os valores canônicos e os genes que o
  definem. Ela entra no fitness como **penalidade** de desvio (`drift_penalty`, via
  `LAMBDA_DRIFT`), nunca como restrição rígida: o AG é livre para se afastar dela. Os
  canônicos também servem de semente da população inicial do AG escalar.
- **Resposta** é quem vence quem e se equilíbrio e identidade são compatíveis. O **ciclo
  canônico de vantagens** **não é codificado em nenhuma penalidade** — é medido
  *post-hoc*, junto da identidade **funcional** (como o personagem joga).

### O argumento de não-circularidade (central, deve aparecer explícito)

Codificar a resposta no fitness tornaria a pergunta **circular**: o ciclo apareceria só
porque foi pago para aparecer. Distinção fina, mas decisiva:
- *penalizar* o drift (soft) = dar um custo à perda de identidade estrutural, mas deixar
  o AG livre para pagá-lo se valer a pena → mede-se o trade-off. E o AG paga: com a
  penalidade ligada o tempo todo, ele troca identidade por equilíbrio — o termo existe e
  pode perder;
- *forçar* o ciclo (hard) = proibir certos resultados → não se mede nada, só se obtém
  o que foi imposto.

A identidade que responde à pergunta — "identidades **funcionais**" — é medida por uma
régua que o fitness não toca: comportamento e ciclo, post-hoc. Detalhe em
[03-formulacao-do-fitness.md](03-formulacao-do-fitness.md).

## O experimento central

**Equilíbrio com preservação** e **equilíbrio com homogeneização** são **ambos
resultados cientificamente válidos**. Comparar os dois cenários é o experimento:
- o **NSGA-II** torna o trade-off explícito ao percorrer toda a fronteira (de "preserva
  e desequilibra" a "equilibra e homogeneíza");
- o **AG escalar** dá uma solução do trade-off com pesos iguais
  (`LAMBDA_DRIFT = LAMBDA_DOMINANCE`). Medido, ela não cai *sobre* a fronteira: fica além
  da ponta de baixa dominância, e os dois são mutuamente não-dominados — cada algoritmo
  alcança uma parte diferente do trade-off.

Detalhe de como cada eixo é medido: [03-formulacao-do-fitness.md](03-formulacao-do-fitness.md).

## Escopo (delimitação honesta)

- Modelo de combate é uma **simplificação** de FGCs reais (sem frames por golpe,
  mix-ups, neutral game). Ver limitações em
  [07-achados-e-limitacoes.md](07-achados-e-limitacoes.md).
- **5 arquétipos** — suficiente para um ciclo fechado (cada um vence 2, perde 2);
  FGCs reais têm 10+.
- O objeto de teste é o **trade-off equilíbrio × identidade**, não a fidelidade do
  modelo a um jogo específico.
