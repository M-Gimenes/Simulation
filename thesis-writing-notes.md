# Notas de escrita do TCC — 2026-11-27

Respostas às dúvidas da revisão de texto e o que foi corrigido.

## Correções aplicadas

- **§3.1 (Visão geral):** "soma os dois objetivos" não dizia quais. Agora nomeia os dois:
  preservar a identidade estrutural ($P_{drift}$) e equilibrar o elenco ($P_{dom}$).
- **Tabela 3 (tolerância κ):** a legenda passou a dizer o que cada coluna mede e para que
  lado é melhor.
- **Acima da Tabela 4:** saiu a frase "Distinguir os valores medidos... mereceria menos
  confiança".
- **Calibração (acima da Tabela 7):** o primeiro parágrafo descreve o procedimento passo a
  passo; "o valor 1 resultou de uma varredura" virou "foi testado por uma varredura".
- **Limitações:** "Vários parâmetros" → "Alguns parâmetros".

## Tabela 3: o 6-4 menor é bom?

Sim. A coluna do 6-4 é **falso alarme**: com que frequência o ruído faz uma vantagem
saudável (6-4) ser acusada de *hard counter*. Menor é melhor. A coluna do 7-3 é
**detecção**: com que frequência um *counter* de verdade é pego. Maior é melhor.

- κ = 0,20: quase nenhum falso alarme (0,6%), mas só detecta metade dos 7-3.
- κ = 0,10: detecta quase todos, mas acusa metade dos 6-4.
- κ = 0,15: o único que vai bem nas duas (10,6% / 90,9%).

## Mutação de 5%: não é alto?

Um pouco acima da referência usual, mas não é alto.

- 0,05 × 55 genes = 2,75 genes por filho, pouco mais de meio gene por personagem.
- A referência clássica é 1/L ≈ 0,018 (um gene por filho); 5% fica ~2,75× acima.
- O elitismo de 10% guarda os 30 melhores intactos, então uma taxa alta não perde a melhor
  solução.
- O cruzamento copia personagens inteiros, então todo valor novo dentro de um personagem
  vem só da mutação.
- O problema medido é o contrário: nos pesos comportamentais o passo é pequeno demais para
  a busca perceber sob o ruído (análise de sensibilidade). O que pesa é o σ (10% e 2,5%),
  não a taxa.
- Ponto fraco: a taxa nunca foi testada. Está como "projeto" na Tabela 4 e nas Limitações.

Pendente, se quiser: uma frase no texto comparando com 1/L, que precisa de referência
(Bäck 1993 ou Mühlenbein 1992), ainda fora do `.bib` e a conferir na fonte.

## Como foi a calibração (Tabela 7)

Não foi "testar muitas coisas e pegar a melhor".

1. Os quatro valores (λ = 1, pesos 1/0,5/0,5, elitismo 10%, torneio 3) **já existiam**.
   Elitismo e torneio eram valores usuais da literatura; λ = 1 veio de uma eliminação
   anterior (λ = 6 prendia o AG ao canônico).
2. Cada varredura mudou **um parâmetro por vez**, com 5 execuções em orçamento reduzido
   (população 120, 60 gerações).
3. Regra: trocar só se uma alternativa fosse melhor em equilíbrio sem perder em identidade
   (ou o inverso). **Nenhuma foi**, e nenhum valor mudou.

**Pode fazer isso?** Pode. Ajustar parâmetros antes do experimento é prática normal. O que
tornaria ilegítimo é escolher com as mesmas execuções que depois são reportadas, porque
parte do resultado seria sorte da escolha. Aqui são separadas: varreduras nas sementes
1000–1004, bateria nas 42–61. Mesmo "pegar o melhor" seria legítimo nessas condições,
desde que reportado, e a Tabela 7 mostra também o que perdeu.

Detalhe: λ, elitismo e torneio só existem no AG escalar, mas como nada mudou, a calibração
não deu vantagem a ele sobre o NSGA-II.
