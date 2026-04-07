# GA Character Balancer

> **Work in progress** — this project is still under active development.

An undergraduate thesis (TCC) exploring whether a Genetic Algorithm can achieve competitive balance between 5 distinct fighting game archetypes without destroying their functional identities.

## Overview

The system evolves a set of 5 characters (one per archetype) through a GA, evaluating fitness via full round-robin combat simulations. The core research question: can automated optimization produce balanced matchups while preserving each archetype's unique playstyle?

**Archetypes:** Rushdown, Zoner, Grappler, Turtle, Combo Master

## How it works

- **Simulation layer** — tick-based 1v1 combat with softmax action selection (Attack / Advance / Retreat / Defend)
- **GA layer** — each individual encodes 5 characters (70 genes total); fitness balances win-rate parity, attribute cost, and optional archetype drift penalty

## Running

```bash
py main.py
py main.py --seed 42 --quiet --log-every 5
```

> Requires Python 3. Use `py` on Windows.

## Tests

```bash
py test_base.py
py test_combat.py
py test_fitness.py
py test_operators.py
```
