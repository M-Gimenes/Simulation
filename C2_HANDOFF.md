# Handoff C2 — pendências de redação (overleaf) + calibração

> **Arquivo temporário.** As mudanças de código (reformulação **C2** do equilíbrio +
> simplificação do combate), os `docs/reference/` e `docs/tcc/`, as **tools de
> reporting** e o `CLAUDE.md` **já estão alinhados**. Resta só **(a)** reescrever o
> `overleaf/` e **(b)** calibrar + re-rodar. Apagar este arquivo depois que o overleaf
> estiver alinhado.
>
> Contexto técnico completo para a redação: `docs/reference/04` (combate), `05`
> (fitness/AG), `07` (config) e `docs/tcc/02` (ciclo), `03` (fitness), `04` (trajetória).

---

## 1. Pendente — `overleaf/artigo-SBC/main.tex`

- **Abstract + resumo:** redefinir a métrica de sucesso de "balanced matchups" para
  **equilíbrio global** (nenhum boneco domina o roster) + estrutura do ciclo.
- **§3.5 "Desbalanço (*dominance*)" e Eq. (2):** reescrever para a fórmula C2 — balanço
  global por personagem (primário) + teto de hard-counter + decisividade.
- **§3.2 combate:** substituir o modelo de prioridades pelo **intenção → execução**;
  atualizar stun (fração do cooldown) e remover a hesitação.
- **§3.3 representação:** contagem de genes 12 → **10** (5×10 = 50) e lista de
  atributos sem `defense`/`recovery`.
- **Tabela canônica:** remover colunas `defense` e `recovery`; `stun` de absoluto para
  fração; canônicos re-tunados (ver `docs/reference/03`).
- **Tabela 2** ("Conf. eq. = pares com WR em [40,60]"): redefinir coluna/critério para
  o headline C2.
- **§4.1/§4.4 + Limitações:** separar as **duas quebras** do ciclo — (1) baseline
  (modelo de combate, segue válido) vs (2) pós-balanceamento (sob C2 o objetivo **não**
  força mais a quebra; a emergência do ciclo vira achado). Atualizar a referência do
  hipervolume para **(2.0, 1.0)**.

---

## 2. Pendente — calibração + re-rodar (todas as rodadas invalidadas)

O motor de combate e o objetivo mudaram; todos os `results/` existentes são pré-C2 e
**não devem ser citados**. Calibrar os provisórios e re-rodar (`report`, `multi_run`,
`external_validation`, fronteira/HV):

- valores canônicos (semântica de `w_agg` mudou; Turtle virou tanky-ativo);
- bound superior do `stun` (fração) e os stuns canônicos;
- `MATCHUP_WR_CAP` (quão duras as arestas do ciclo podem ser);
- `ACTION_PERSISTENCE_SUBTICKS` (comprometimento da intenção);
- `TICK_SCALE` (subir para 10 só se aparecer platô de granularidade).
