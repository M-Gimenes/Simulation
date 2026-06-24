# 11 — Revisão do modelo de combate (2026-06-23)

Auditoria de representação do combate: cada mecânica representa o que diz
representar? Há dinâmicas mortas/degeneradas? O sistema é bom o suficiente?
Feita instrumentando os 10 matchups canônicos (200 sims cada, seed fixo) e
medindo distribuição de ações, stun, espaçamento, KO/timeout e duração.

> Sinal-chave: **RETREAT e DEFEND só vêm da soft-policy** (os ramos
> determinísticos só produzem ATTACK/ADVANCE). A fração RET+DEF mede o quanto a
> soft-policy de fato dirige o combate.

## Veredito

**O combate é bom e representa bem os arquétipos — não está quebrado.** O
problema do projeto **não** é falta de estocasticidade nas mecânicas; é que o
**desfecho** é robusto ao ruído que já existe. Conserta-se pela formulação do
objetivo (margem por-luta), não por mais ruído.

## Achados

### 1. A soft-policy é bem ativa (hipótese anterior refutada)
RET+DEF agregado: Zoner 55%, Turtle 65%, Grappler 31%, Combo 21%, Rushdown 9%.
A ideia de que "a soft-policy quase nunca dispara" estava **errada** — ela
dispara bastante (cooldowns multi-tick deixam o personagem em range, sem poder
atacar, caindo no ramo estocástico com frequência).

### 2. Determinismo é no desfecho, não nas mecânicas
Apesar do ruído ativo, **KO = 100% nos 10 matchups, zero timeouts**. O ruído da
soft-policy **não flipa o vencedor** — as diferenças de poder entre os canônicos
são decisivas demais. A aleatoriedade existe, mas é fraca demais perto do
desbalanceamento.

### 3. Implicação: A habilita B (e o torna quase desnecessário)
A razão de o ruído não flipar nada é que as lutas são blowouts. Se o objetivo
(A, margem por-luta) empurrar as lutas para **apertadas** (vencedor fecha ~10-20%
HP), o **mesmo ruído que já existe** passará a flipar desfechos → **WR graduado
emerge sozinho**, sem precisar de variância extra. Consequência:

- **A é a alavanca real**, não o B.
- **B (hesitação) deixa de ser correção fundamental e vira realismo/polish.**
  Recomenda-se ε pequeno e avaliar seu efeito *marginal* depois do A — possivelmente
  o A sozinho já entrega gradação suficiente de WR. *(Decisão a revisitar com o
  usuário após medir A.)*

### 4. Os arquétipos são representados bem (achado positivo)
Comportamento distinto e on-concept:

| Arquétipo | ATK | ADV | RET | DEF | leitura |
|---|---|---|---|---|---|
| Rushdown | 19% | 72% | 3% | 6% | rusher puro |
| Combo Master | 7% | 72% | 4% | 17% | fecha distância |
| Grappler | 5% | 64% | 6% | 25% | tanky-agressivo |
| Zoner | 7% | 38% | 39% | 16% | kita (maior RET) |
| Turtle | 4% | 30% | 22% | 43% | muralha (maior DEF) |

DEFEND e RETREAT são usados de forma significativa (não são mecânicas mortas);
os pesos expressam identidade. Espaçamento funciona (Zoner mantém Grappler/Turtle
fora de range 33-43% do tempo). Pacing varia coerentemente (Rushdown mata em ~235
ticks; atrito de Turtle dura ~1100-1220).

### 5. Recovery: funciona, mas é evolutivamente neutro
Stun é impactante (personagens passam 17-36% dos ticks stunados; Rushdown 32%).
Recovery **funciona** (Turtle com recovery 7 fica 0% stunado contra
Zoner/Rushdown). Mas no indivíduo evoluído recovery → 0 em todos (ver
`drift_table`). Explicação provável: como o desfecho é robusto (blowout), resistir
stun **não muda quem ganha** → sem pressão seletiva → drifta pro piso. Pode voltar
a importar quando as lutas ficarem apertadas (A). **Recheco com
`sensitivity_analysis` (agora confiável) após o A.**

## Bugs de combate
Nenhum além do já corrigido (contabilização de `stun_applied`, ver
[10-known-issues.md](10-known-issues.md) B1). As mecânicas se comportam de forma
coerente.
