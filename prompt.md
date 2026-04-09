# Sessão — Balanceamento de Combate (combat.py)

    ## Prompt de continuação

    > "As minhas definições de score não estão satisfazendo corretamente para a criação
    > de uma mecânica equilibrada entre os bonecos (ignorando a parte da AG por enquanto,
    > apenas a simulação). Preciso calibrar isso melhor para refletir as porcentagens de
    > vantagem de cada uma mais ou menos certo. Do jeito que está agora alguns ganham 100%
    > e outros perdem 100%. Talvez seja necessário nerfar um boneco ou outro, ou bufar tbm.
    > Mas sinto que o problema principal é os scores de ação."

    ## O que foi identificado

    ### Bug corrigido (mas não salvo ainda)
    -`combat.py` linha ~294: `end_tick` não era inicializado antes do loop `for tick in       range(MAX_TICKS)`. Se um lutador morria no último tick, o loop terminava sem `break`
      e `end_tick` ficava indefinido → `UnboundLocalError`.
    - **Fix:** adicionar `end_tick = MAX_TICKS` antes do loop.

    ### Problema principal a resolver
    Os scores de ação em`_choose_action()` (combat.py ~linha 145) estão desequilibrados.
    Problemas conhecidos documentados no CLAUDE.md:

    1.**Zoner > Grappler ~35-40% WR** — `score_retreat` só dispara quando inimigo já está
       em range. Zoner não consegue recuar proativamente para manter distância.

    2.**CM > Turtle = 0% WR** — Turtle KO CM porque `score_attack` em T=0.1 compete
       com `score_advance=0` e `score_defend≈0`, dando CM só ~41% de probabilidade de
       atacar quando em range. Além disso, ATTACK fora de range não causa dano mas
       consome cooldown.

    ### Scores atuais (resumo)
    ```python
    score_attack  = w_attack  * me_hit                        # só se attack_ready
    score_advance = w_advance * (1 - me_hit) * w_aggressiveness  # só se fora de range
    score_retreat = w_retreat * enemy_hit * (1 - me_hit)
    score_defend  = w_defend  * enemy_hit  * (1 - me_hit)

    Candidatos de fix

    - Elevar SCORE_TEMPERATURE (atualmente 0.1) para reduzir determinismo
    - Adicionar bônus de proximidade em score_advance quando já está em range
    - Fazer ATTACK ser gatilhado apenas se in_range (evitar cooldown desperdiçado)
    - Fazer Zoner calcular score_retreat baseado em distância relativa ao seu range,
    não só quando inimigo está literalmente em range

    Próximo passo

    Reescrever _choose_action() com scores mais expressivos e testar com o
    script de verificação de matchups do CLAUDE.md.
    ```
