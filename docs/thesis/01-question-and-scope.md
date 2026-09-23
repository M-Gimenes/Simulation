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
  *post-hoc*, e **separado** da identidade funcional: quem mede identidade é a Layer 3 do
  validador e a concordância de ranking τ; o ciclo é premissa autoral, falsificada em
  2026-09-23 (o próprio canônico realiza só 6/10 dele). Ver
  [02-canonical-cycle.md](02-canonical-cycle.md).

### O argumento de não-circularidade (central, deve aparecer explícito)

Codificar a resposta no fitness tornaria a pergunta **circular**: o ciclo apareceria só
porque foi pago para aparecer. Distinção fina, mas decisiva:
- *penalizar* o drift (soft) = dar um custo à perda de identidade estrutural, mas deixar
  o AG livre para pagá-lo se valer a pena → mede-se o trade-off. E o AG paga: com a
  penalidade ligada o tempo todo, ele troca identidade por equilíbrio — o termo existe e
  pode perder;
- *forçar* o ciclo (hard) = proibir certos resultados → não se mede nada, só se obtém
  o que foi imposto.

A identidade que responde à pergunta — "identidades **funcionais**" — é medida por réguas
que o fitness não toca: o comportamento, post-hoc (a Layer 3 do validador e a concordância
de ranking comportamental com o canônico). Detalhe em
[03-fitness-formulation.md](03-fitness-formulation.md).

## O experimento central

**Equilíbrio com preservação** e **equilíbrio com homogeneização** são **ambos
resultados cientificamente válidos**. Comparar os dois cenários é o experimento:
- o **NSGA-II** torna o trade-off explícito ao percorrer toda a fronteira (de "preserva
  e desequilibra" a "equilibra e homogeneíza");
- o **AG escalar** dá uma solução do trade-off com pesos iguais
  (`LAMBDA_DRIFT = LAMBDA_DOMINANCE`). Medido, ela não cai *sobre* a fronteira: fica além
  da ponta de baixa dominância, e os dois são mutuamente não-dominados — cada algoritmo
  alcança uma parte diferente do trade-off;
- dois **controles** isolam o efeito do método: o AG com `LAMBDA_DRIFT = 0` (equilibrar
  sem o termo de identidade — o contrafactual da pergunta) e o AG sem a semente canônica
  (separa algoritmo de inicialização na comparação com o NSGA-II).

Detalhe de como cada eixo é medido: [03-fitness-formulation.md](03-fitness-formulation.md).

## Escopo (delimitação honesta)

- Modelo de combate é uma **simplificação** de FGCs reais (sem frames por golpe,
  mix-ups, neutral game). Ver limitações em
  [07-findings-and-limitations.md](07-findings-and-limitations.md).
- **5 arquétipos** — suficiente para um ciclo fechado (cada um vence 2, perde 2);
  FGCs reais têm 10+.
- O objeto de teste é o **trade-off equilíbrio × identidade**, não a fidelidade do
  modelo a um jogo específico.
