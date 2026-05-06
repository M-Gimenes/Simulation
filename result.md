Análise completa da run

---

  Progressão do dom_min — escada de melhoria

  Gen  0:  0.790  (inicial)
  Gen  8:  0.548  (-30%)
  Gen 15:  0.460  (-16%)
  Gen 25:  0.271  (-41%)  ← maior salto
  Gen 46:  0.160  (-41%)  ← maior salto
  Gen 72:  0.130  (-19%)
  Gen 96:  0.115  (-12%)  ← final
  Redução total de 85% (0.790 → 0.115). O padrão é saudável: platôs de 7–14 gerações entre saltos, o algoritmo explorou bem antes de convergir.

---

  Os representantes finais

  best_dominance — dom=0.115, drift=0.152
  O melhor equilíbrio encontrado. Derivou ~15% dos valores canônicos para conseguir isso. É o resultado principal da tua tese.

  best_drift — dom=0.937, drift=0.000
  O build canônico puro. Péssimo equilíbrio. Confirma a hipótese: os arquétipos canônicos não são balanceados — e isso é esperado.

  knee_point — dom=0.531, drift=0.108
  Deveria ser o "melhor dos dois mundos", mas dom=0.531 é alto. Indica que a curva de Pareto não tem um cotovelo suave — ela tem formato mais parecido com L invertido:
   você paga pouco drift pra ganhar muito equilíbrio até certo ponto, depois o retorno diminui drasticamente.

  ideal_point = best_dominance
  Faz sentido — com 2 objetivos, o ponto ideal utópico é o canto inferior esquerdo da fronteira, que coincide com o melhor em dominance.

---

  O que dom=0.115 significa na prática

  Com MATCHUP_THRESHOLD=0.10 e a fórmula RMS:

  sqrt(mean(excess²)) = 0.115

  Se alguns matchups têm excess≈0.18: |WR - 0.5| = 0.28 → WR ≈ 78%. Ainda há matchups desequilibrados — o GA não atingiu convergência completa (que exigiria todos
  dentro de 60%).

---

  Para a tese

  O resultado central é justamente esse contraste:

  ┌───────────┬───────────┬───────┬──────────────────────────────────────┐
  │  Solução  │ Dominance │ Drift │            Interpretação             │
  ├───────────┼───────────┼───────┼──────────────────────────────────────┤
  │ Canônica  │ 0.937     │ 0.000 │ Identidade perfeita, balanço péssimo │
  ├───────────┼───────────┼───────┼──────────────────────────────────────┤
  │ Melhor GA │ 0.115     │ 0.152 │ 85% melhor balanço, ~15% de deriva   │
  └───────────┴───────────┴───────┴──────────────────────────────────────┘

  O NSGA-II mapeou esse trade-off de forma clara. A conclusão natural é: balanço competitivo exige ceder algo da identidade dos arquétipos — e a fronteira de Pareto
  quantifica exatamente quanto.
