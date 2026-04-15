"""
Visualizador web de combate.

Uso:
    py web_viewer.py                  # abre no browser na porta 8080
    py web_viewer.py --port 9000

Acesse http://localhost:8080 no browser.
Ctrl+C para encerrar.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(__file__))

from archetypes import ARCHETYPES, ARCHETYPE_ORDER, ArchetypeID, ARCHETYPE_ALIASES
from character import Character
from combat import Action, FighterState, _choose_action, _resolve_attack
from config import FIELD_SIZE, INITIAL_DISTANCE, MAX_TICKS
from individual import Individual


# ─────────────────────────────────────────────────────────────────────────────
# Aliases para selecionar arquétipos via URL
# ─────────────────────────────────────────────────────────────────────────────

ALIASES = ARCHETYPE_ALIASES

ARCHETYPE_COLORS = {
    ArchetypeID.RUSHDOWN:     "#ef4444",
    ArchetypeID.ZONER:        "#22d3ee",
    ArchetypeID.COMBO_MASTER: "#a855f7",
    ArchetypeID.GRAPPLER:     "#eab308",
    ArchetypeID.TURTLE:       "#22c55e",
}


# ─────────────────────────────────────────────────────────────────────────────
# Gravação do combate
# ─────────────────────────────────────────────────────────────────────────────

def record_combat(char_a: Character, char_b: Character) -> dict:
    """Roda o combate e retorna todos os dados tick a tick como dict JSON-serializável."""

    fighters = [
        FighterState(character=char_a, hp=char_a.hp),
        FighterState(character=char_b, hp=char_b.hp),
    ]
    pos = [
        (FIELD_SIZE - INITIAL_DISTANCE) / 2.0,
        (FIELD_SIZE + INITIAL_DISTANCE) / 2.0,
    ]

    ticks = []
    winner_idx = 0
    ko = False
    end_tick = MAX_TICKS

    for tick in range(MAX_TICKS):
        if not fighters[0].is_alive or not fighters[1].is_alive:
            end_tick = tick
            ko = True
            break

        # Fase 1: ações
        actions: List[Optional[int]] = []
        for i in range(2):
            if fighters[i].is_stunned:
                actions.append(None)
            else:
                distance = abs(pos[1] - pos[0])
                actions.append(_choose_action(fighters[i], fighters[1 - i], distance, pos[i]))

        # Fase 2: movimento
        distance = abs(pos[1] - pos[0])
        for i in range(2):
            if actions[i] not in (Action.ADVANCE, Action.RETREAT):
                continue
            speed = fighters[i].character.speed
            direction = 1.0 if pos[i] < pos[1 - i] else -1.0
            if actions[i] == Action.ADVANCE:
                pos[i] = max(0.0, min(FIELD_SIZE, pos[i] + direction * speed))
            else:
                pos[i] = max(0.0, min(FIELD_SIZE, pos[i] - direction * speed))

        # Fase 3: ataques
        distance = abs(pos[1] - pos[0])
        defending = [a == Action.DEFEND for a in actions]
        tick_events = []

        pre_stun = [f.stun_remaining for f in fighters]
        pre_cd   = [f.cooldown_remaining for f in fighters]

        for att_idx in range(2):
            if actions[att_idx] != Action.ATTACK:
                continue
            if not fighters[att_idx].attack_ready:
                continue

            def_idx = 1 - att_idx
            hp_before_pct = fighters[def_idx].hp_pct

            dmg, stun, kb = _resolve_attack(
                attacker=fighters[att_idx].character,
                defender_state=fighters[def_idx],
                defender_is_defending=defending[def_idx],
                distance=distance,
            )

            if dmg > 0:
                fighters[def_idx].hp = max(0.0, fighters[def_idx].hp - dmg)
                if stun > fighters[def_idx].stun_remaining:
                    fighters[def_idx].stun_remaining = stun
                kb_dir = 1.0 if pos[def_idx] >= pos[att_idx] else -1.0
                pos[def_idx] = max(0.0, min(FIELD_SIZE, pos[def_idx] + kb_dir * kb))

                tick_events.append({
                    "attacker_idx": att_idx,
                    "damage": round(dmg, 1),
                    "stun": stun,
                    "knockback": round(kb, 1),
                    "ko": not fighters[def_idx].is_alive,
                    "hp_before": round(hp_before_pct, 3),
                    "hp_after": round(fighters[def_idx].hp_pct, 3),
                })

                # Cooldown só é setado em hit — ataque fora de range não desperdiça cooldown
                fighters[att_idx].cooldown_remaining = round(
                    fighters[att_idx].character.attack_cooldown
                )

        # Fase 4: decrementar apenas timers não recém-setados
        for i, f in enumerate(fighters):
            if f.stun_remaining <= pre_stun[i]:
                f.stun_remaining = max(0, f.stun_remaining - 1)
            if f.cooldown_remaining <= pre_cd[i]:
                f.cooldown_remaining = max(0, f.cooldown_remaining - 1)

        def _action_name(a) -> str:
            if a is None:
                return "STUNNED"
            return {Action.ATTACK: "ATTACK", Action.ADVANCE: "ADVANCE",
                    Action.RETREAT: "RETREAT", Action.DEFEND: "DEFEND"}.get(a, "?")

        ticks.append({
            "tick": tick,
            "hp_a": round(fighters[0].hp, 1),
            "hp_b": round(fighters[1].hp, 1),
            "hp_pct_a": round(fighters[0].hp_pct, 4),
            "hp_pct_b": round(fighters[1].hp_pct, 4),
            "pos_a": round(pos[0], 2),
            "pos_b": round(pos[1], 2),
            "action_a": _action_name(actions[0]),
            "action_b": _action_name(actions[1]),
            "cd_a": fighters[0].cooldown_remaining,
            "cd_b": fighters[1].cooldown_remaining,
            "stun_a": fighters[0].stun_remaining,
            "stun_b": fighters[1].stun_remaining,
            "events": tick_events,
        })

    # Vencedor
    if not fighters[0].is_alive and not fighters[1].is_alive:
        winner_idx = 0 if fighters[0].hp_pct >= fighters[1].hp_pct else 1
    elif not fighters[0].is_alive:
        winner_idx = 1
    elif not fighters[1].is_alive:
        winner_idx = 0
    else:
        winner_idx = 0 if fighters[0].hp_pct >= fighters[1].hp_pct else 1

    def _char_info(char: Character) -> dict:
        return {
            "name": char.name,
            "archetype": char.archetype.id.name,
            "color": ARCHETYPE_COLORS.get(char.archetype.id, "#ffffff"),
            "hp_max": char.hp,
            "damage": round(char.damage, 1),
            "attack_cooldown": round(char.attack_cooldown, 1),
            "range": round(char.range_, 1),
            "speed": round(char.speed, 1),
            "defense": round(char.defense, 2),
            "stun": round(char.stun, 1),
            "knockback": round(char.knockback, 1),
            "recovery": round(char.recovery, 2),
        }

    return {
        "char_a": _char_info(char_a),
        "char_b": _char_info(char_b),
        "ticks": ticks,
        "winner_idx": winner_idx,
        "winner_name": [char_a.name, char_b.name][winner_idx],
        "ko": ko,
        "total_ticks": end_tick,
        "field_size": FIELD_SIZE,
    }


# ─────────────────────────────────────────────────────────────────────────────
# HTML (inline, sem dependências externas)
# ─────────────────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Simulation Viewer</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0f1117; --surface: #1a1d27; --border: #2a2d3e;
    --text: #e2e8f0; --dim: #64748b; --accent: #6366f1;
    --green: #22c55e; --yellow: #eab308; --red: #ef4444;
    --radius: 8px; --font: 'Segoe UI', system-ui, sans-serif;
  }
  body { background: var(--bg); color: var(--text); font-family: var(--font);
         min-height: 100vh; display: flex; flex-direction: column; }

  /* ── Header */
  header { background: var(--surface); border-bottom: 1px solid var(--border);
           padding: 12px 24px; display: flex; align-items: center; gap: 16px; }
  header h1 { font-size: 1rem; font-weight: 600; color: var(--accent); letter-spacing: .05em; }

  /* ── Selector bar */
  .selector { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  select, button {
    background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius);
    color: var(--text); font-size: .85rem; padding: 6px 12px; cursor: pointer;
    transition: border-color .15s;
  }
  select:hover, button:hover { border-color: var(--accent); }
  button.primary {
    background: var(--accent); border-color: var(--accent); font-weight: 600;
    padding: 6px 20px;
  }
  button.primary:hover { background: #818cf8; }
  .vs-label { color: var(--dim); font-size: .8rem; }

  /* ── Layout */
  .main { flex: 1; display: grid; grid-template-columns: 1fr 340px;
          gap: 16px; padding: 16px; }
  .left  { display: flex; flex-direction: column; gap: 12px; }
  .right { display: flex; flex-direction: column; gap: 12px; }
  .card  { background: var(--surface); border: 1px solid var(--border);
           border-radius: var(--radius); padding: 14px; }
  .card-title { font-size: .7rem; font-weight: 600; color: var(--dim);
                text-transform: uppercase; letter-spacing: .1em; margin-bottom: 10px; }

  /* ── HP bars */
  .hp-section { display: flex; flex-direction: column; gap: 10px; }
  .hp-row { display: flex; flex-direction: column; gap: 4px; }
  .hp-label { display: flex; justify-content: space-between; font-size: .82rem; }
  .hp-name  { font-weight: 700; }
  .hp-value { color: var(--dim); font-variant-numeric: tabular-nums; }
  .hp-track { height: 14px; background: #1e2130; border-radius: 4px; overflow: hidden; }
  .hp-fill  { height: 100%; border-radius: 4px; transition: width .1s linear; }

  /* ── Arena */
  #arena-canvas { width: 100%; height: 100px; display: block;
                  border-radius: var(--radius); background: #0a0c12;
                  border: 1px solid var(--border); }

  /* ── Action badges */
  .actions { display: flex; justify-content: space-between; }
  .action-badge {
    display: flex; flex-direction: column; align-items: center; gap: 4px;
    flex: 1; padding: 8px; border-radius: var(--radius); border: 1px solid var(--border);
  }
  .action-badge:first-child { margin-right: 8px; }
  .action-name { font-size: .8rem; font-weight: 700; }
  .action-meta { font-size: .7rem; color: var(--dim); }

  /* ── Controls */
  .controls { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .controls button { padding: 5px 14px; font-size: .8rem; }
  #tick-slider { flex: 1; min-width: 120px; accent-color: var(--accent); }
  .tick-info { font-size: .78rem; color: var(--dim); white-space: nowrap; }
  .speed-label { font-size: .78rem; color: var(--dim); }
  #speed-select { padding: 4px 8px; font-size: .78rem; }

  /* ── Stats table */
  .stats-table { width: 100%; border-collapse: collapse; font-size: .78rem; }
  .stats-table th { color: var(--dim); font-weight: 500; padding: 3px 6px;
                    text-align: left; border-bottom: 1px solid var(--border); }
  .stats-table td { padding: 3px 6px; font-variant-numeric: tabular-nums; }
  .stats-table td.v { text-align: right; color: var(--text); }

  /* ── Combat log */
  #log-list { list-style: none; max-height: 320px; overflow-y: auto;
              display: flex; flex-direction: column-reverse; }
  #log-list li { font-size: .75rem; padding: 4px 6px; border-bottom: 1px solid var(--border);
                 display: flex; gap: 6px; align-items: baseline; }
  .log-tick  { color: var(--dim); min-width: 36px; font-variant-numeric: tabular-nums; }
  .log-atk   { font-weight: 600; min-width: 80px; }
  .log-dmg   { color: var(--red); font-weight: 700; }
  .log-stun  { color: #a855f7; }
  .log-ko    { color: var(--red); font-weight: 700; }

  /* ── Winner banner */
  #winner-banner {
    display: none; position: fixed; inset: 0; background: rgba(0,0,0,.75);
    align-items: center; justify-content: center; z-index: 100;
  }
  #winner-banner.show { display: flex; }
  .banner-box {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 32px 48px; text-align: center;
  }
  .banner-box h2 { font-size: 1.6rem; margin-bottom: 8px; }
  .banner-box p  { color: var(--dim); margin-bottom: 20px; }
  .banner-box button { padding: 8px 24px; }

  /* ── Loading */
  #loading { display: none; align-items: center; justify-content: center;
             gap: 8px; font-size: .85rem; color: var(--dim); }
  #loading.show { display: flex; }
  .spinner { width: 16px; height: 16px; border: 2px solid var(--border);
             border-top-color: var(--accent); border-radius: 50%;
             animation: spin .6s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>

<header>
  <h1>⚔ SIMULATION VIEWER</h1>
  <div class="selector">
    <select id="sel-a"></select>
    <span class="vs-label">vs</span>
    <select id="sel-b"></select>
    <button class="primary" onclick="runCombat()">Simular</button>
    <div id="loading"><div class="spinner"></div> simulando…</div>
  </div>
</header>

<div class="main">
  <div class="left">

    <!-- HP -->
    <div class="card">
      <div class="card-title">HP</div>
      <div class="hp-section">
        <div class="hp-row">
          <div class="hp-label">
            <span class="hp-name" id="name-a">—</span>
            <span class="hp-value" id="hp-val-a">—</span>
          </div>
          <div class="hp-track"><div class="hp-fill" id="hp-bar-a" style="width:100%"></div></div>
        </div>
        <div class="hp-row">
          <div class="hp-label">
            <span class="hp-name" id="name-b">—</span>
            <span class="hp-value" id="hp-val-b">—</span>
          </div>
          <div class="hp-track"><div class="hp-fill" id="hp-bar-b" style="width:100%"></div></div>
        </div>
      </div>
    </div>

    <!-- Arena -->
    <div class="card">
      <div class="card-title">Arena</div>
      <canvas id="arena-canvas" height="80"></canvas>
      <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:.7rem;color:var(--dim)">
        <span id="dist-label">Distância: —</span>
        <span id="pos-label">—</span>
      </div>
    </div>

    <!-- Actions -->
    <div class="card">
      <div class="card-title">Ações</div>
      <div class="actions">
        <div class="action-badge" id="badge-a">
          <div class="action-name" id="act-name-a">—</div>
          <div class="action-meta" id="act-meta-a">—</div>
        </div>
        <div class="action-badge" id="badge-b">
          <div class="action-name" id="act-name-b">—</div>
          <div class="action-meta" id="act-meta-b">—</div>
        </div>
      </div>
    </div>

    <!-- Controls -->
    <div class="card controls">
      <button id="btn-prev" onclick="stepBy(-1)">◀</button>
      <button id="btn-play" onclick="togglePlay()">▶ Play</button>
      <button id="btn-next" onclick="stepBy(1)">▶</button>
      <input id="tick-slider" type="range" min="0" value="0" oninput="seekTo(+this.value)">
      <span class="tick-info" id="tick-info">tick 0 / 0</span>
      <span class="speed-label">Vel:</span>
      <select id="speed-select" onchange="updateSpeed()">
        <option value="200">0.5×</option>
        <option value="100" selected>1×</option>
        <option value="50">2×</option>
        <option value="20">5×</option>
        <option value="5">20×</option>
        <option value="0">Máx</option>
      </select>
    </div>

  </div>
  <div class="right">

    <!-- Stats -->
    <div class="card">
      <div class="card-title">Atributos</div>
      <table class="stats-table">
        <thead>
          <tr>
            <th>Atributo</th>
            <th id="th-a" class="v">—</th>
            <th id="th-b" class="v">—</th>
          </tr>
        </thead>
        <tbody id="stats-tbody"></tbody>
      </table>
    </div>

    <!-- Log -->
    <div class="card" style="flex:1">
      <div class="card-title">Log de combate</div>
      <ul id="log-list"><li style="color:var(--dim);font-size:.75rem">Selecione um matchup e clique Simular.</li></ul>
    </div>

  </div>
</div>

<!-- Winner banner -->
<div id="winner-banner" onclick="this.classList.remove('show')">
  <div class="banner-box" onclick="event.stopPropagation()">
    <h2 id="winner-title">—</h2>
    <p id="winner-sub">—</p>
    <button onclick="document.getElementById('winner-banner').classList.remove('show')">Fechar</button>
  </div>
</div>

<script>
// ── State
let data = null;
let currentTick = 0;
let playing = false;
let playTimer = null;
let playInterval = 100;

// ── Canvas
const canvas = document.getElementById('arena-canvas');
const ctx    = canvas.getContext('2d');

// ── Populate selectors
const ARCHETYPES = [
  { key: 'zoner',    label: 'Zoner' },
  { key: 'rushdown', label: 'Rushdown' },
  { key: 'combo',    label: 'Combo Master' },
  { key: 'grappler', label: 'Grappler' },
  { key: 'turtle',   label: 'Turtle' },
];
['sel-a','sel-b'].forEach((id, i) => {
  const sel = document.getElementById(id);
  ARCHETYPES.forEach((a, j) => {
    const opt = document.createElement('option');
    opt.value = a.key; opt.textContent = a.label;
    if (i === 0 && j === 1) opt.selected = true;
    if (i === 1 && j === 3) opt.selected = true;
    sel.appendChild(opt);
  });
});

// ── Action colors
const ACT_COLORS = {
  ATTACK:  '#ef4444', ADVANCE: '#eab308',
  RETREAT: '#60a5fa', DEFEND:  '#22c55e', STUNNED: '#a855f7',
};
const ACT_ICONS = {
  ATTACK: '⚔ ATAQUE', ADVANCE: '→ AVANÇA', RETREAT: '← RECUA',
  DEFEND: '🛡 DEFESA', STUNNED: '✦ STUNNED',
};

// ── Run combat
async function runCombat() {
  stopPlay();
  const a = document.getElementById('sel-a').value;
  const b = document.getElementById('sel-b').value;
  document.getElementById('loading').classList.add('show');
  try {
    const res = await fetch(`/api/combat?a=${a}&b=${b}`);
    data = await res.json();
  } finally {
    document.getElementById('loading').classList.remove('show');
  }

  // Setup UI
  const slider = document.getElementById('tick-slider');
  slider.max   = data.ticks.length - 1;
  slider.value = 0;

  document.getElementById('th-a').textContent = data.char_a.name;
  document.getElementById('th-b').textContent = data.char_b.name;
  document.getElementById('th-a').style.color = data.char_a.color;
  document.getElementById('th-b').style.color = data.char_b.color;

  // Stats table
  const attrs = [
    ['HP máx',        'hp_max',          v => v.toFixed(0)],
    ['Dano',          'damage',          v => v.toFixed(1)],
    ['Cooldown (t)',   'attack_cooldown', v => v.toFixed(1)],
    ['Range',         'range',           v => v.toFixed(1)],
    ['Velocidade',    'speed',           v => v.toFixed(1)],
    ['Defesa',        'defense',         v => (v*100).toFixed(0)+'%'],
    ['Stun',          'stun',            v => v.toFixed(1)],
    ['Knockback',     'knockback',       v => v.toFixed(1)],
    ['Recovery',      'recovery',        v => (v*100).toFixed(0)+'%'],
  ];
  const tbody = document.getElementById('stats-tbody');
  tbody.innerHTML = '';
  attrs.forEach(([label, key, fmt]) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td style="color:var(--dim)">${label}</td>
                    <td class="v" style="color:${data.char_a.color}">${fmt(data.char_a[key])}</td>
                    <td class="v" style="color:${data.char_b.color}">${fmt(data.char_b[key])}</td>`;
    tbody.appendChild(tr);
  });

  // Clear log
  document.getElementById('log-list').innerHTML = '';

  seekTo(0);
}

// ── Render tick
function renderTick(idx) {
  if (!data || idx < 0 || idx >= data.ticks.length) return;
  currentTick = idx;
  const t = data.ticks[idx];
  document.getElementById('tick-slider').value = idx;
  document.getElementById('tick-info').textContent = `tick ${t.tick} / ${data.total_ticks}`;

  // HP
  const hpPctA = t.hp_pct_a, hpPctB = t.hp_pct_b;
  setHp('a', data.char_a, t.hp_a, hpPctA);
  setHp('b', data.char_b, t.hp_b, hpPctB);

  // Arena
  drawArena(t.pos_a, t.pos_b, data.char_a, data.char_b, data.field_size);
  const dist = Math.abs(t.pos_b - t.pos_a).toFixed(1);
  document.getElementById('dist-label').textContent = `Distância: ${dist}`;
  document.getElementById('pos-label').textContent  =
    `${data.char_a.name.slice(0,2).toUpperCase()}: ${t.pos_a.toFixed(1)}  ${data.char_b.name.slice(0,2).toUpperCase()}: ${t.pos_b.toFixed(1)}`;

  // Actions
  setAction('a', t.action_a, t.cd_a, t.stun_a, data.char_a.color);
  setAction('b', t.action_b, t.cd_b, t.stun_b, data.char_b.color);

  // Log events from this tick
  t.events.forEach(ev => appendLog(t.tick, ev, data));
}

function setHp(side, char, hp, pct) {
  document.getElementById(`name-${side}`).textContent = char.name;
  document.getElementById(`name-${side}`).style.color  = char.color;
  document.getElementById(`hp-val-${side}`).textContent =
    `${hp.toFixed(0)} / ${char.hp_max.toFixed(0)}  (${(pct*100).toFixed(1)}%)`;
  const bar = document.getElementById(`hp-bar-${side}`);
  bar.style.width = `${(pct * 100).toFixed(2)}%`;
  bar.style.background = pct > 0.6 ? '#22c55e' : pct > 0.3 ? '#eab308' : '#ef4444';
}

function setAction(side, action, cd, stun, charColor) {
  const badge = document.getElementById(`badge-${side}`);
  const col   = ACT_COLORS[action] || '#fff';
  badge.style.borderColor = col + '66';
  badge.style.background  = col + '11';
  document.getElementById(`act-name-${side}`).textContent = ACT_ICONS[action] || action;
  document.getElementById(`act-name-${side}`).style.color = col;
  const meta = stun > 0
    ? `stunned ${stun}t`
    : cd > 0 ? `cooldown ${cd}t` : 'pronto';
  document.getElementById(`act-meta-${side}`).textContent = meta;
}

function appendLog(tick, ev, d) {
  const list    = document.getElementById('log-list');
  const atkChar = ev.attacker_idx === 0 ? d.char_a : d.char_b;
  const defChar = ev.attacker_idx === 0 ? d.char_b : d.char_a;
  const li = document.createElement('li');
  const stunStr = ev.stun > 0 ? ` <span class="log-stun">stun×${ev.stun}</span>` : '';
  const koStr   = ev.ko       ? ` <span class="log-ko">KO!</span>` : '';
  li.innerHTML =
    `<span class="log-tick">t${String(tick).padStart(4,'0')}</span>` +
    `<span class="log-atk" style="color:${atkChar.color}">${atkChar.name}</span>` +
    `→ <span class="log-dmg">-${ev.damage}hp</span>` +
    ` <span style="color:var(--dim)">${defChar.name}: ${(ev.hp_before*100).toFixed(0)}%→${(ev.hp_after*100).toFixed(0)}%</span>` +
    stunStr + koStr;
  list.insertBefore(li, list.firstChild);
}

// ── Arena canvas
function drawArena(posA, posB, charA, charB, fieldSize) {
  const W = canvas.clientWidth, H = canvas.height;
  canvas.width = W;
  ctx.clearRect(0, 0, W, H);

  // Background
  ctx.fillStyle = '#0a0c12';
  ctx.fillRect(0, 0, W, H);

  // Ground line
  const groundY = H * 0.72;
  ctx.strokeStyle = '#2a2d3e';
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(0, groundY); ctx.lineTo(W, groundY); ctx.stroke();

  // Zone markers (25% and 75% = range zones)
  const toX = p => (p / fieldSize) * W;
  ctx.strokeStyle = '#1e2130';
  ctx.setLineDash([4, 4]);
  [25, 50, 75].forEach(p => {
    const x = toX(p);
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
  });
  ctx.setLineDash([]);

  // Connecting line between fighters
  const xA = toX(posA), xB = toX(posB);
  ctx.strokeStyle = '#2a2d3e';
  ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(xA, groundY); ctx.lineTo(xB, groundY); ctx.stroke();

  // Fighters
  drawFighter(xA, groundY, charA, 'A');
  drawFighter(xB, groundY, charB, 'B');
}

function drawFighter(x, y, char, label) {
  const R = 14;
  ctx.beginPath();
  ctx.arc(x, y - R, R, 0, Math.PI * 2);
  ctx.fillStyle = char.color + '33';
  ctx.fill();
  ctx.strokeStyle = char.color;
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.fillStyle = char.color;
  ctx.font = 'bold 9px monospace';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(char.name.slice(0, 2).toUpperCase(), x, y - R);

  ctx.fillStyle = '#64748b';
  ctx.font = '8px sans-serif';
  ctx.fillText(char.name.slice(0, 6), x, y + 8);
}

// ── Playback
function seekTo(idx) { renderTick(idx); }
function stepBy(d)   { seekTo(Math.max(0, Math.min(data ? data.ticks.length - 1 : 0, currentTick + d))); }

function togglePlay() {
  if (!data) return;
  playing ? stopPlay() : startPlay();
}

function startPlay() {
  playing = true;
  document.getElementById('btn-play').textContent = '⏸ Pause';
  scheduleNext();
}

function stopPlay() {
  playing = false;
  document.getElementById('btn-play').textContent = '▶ Play';
  clearTimeout(playTimer);
}

function scheduleNext() {
  if (!playing) return;
  const delay = parseInt(document.getElementById('speed-select').value);
  if (delay === 0) {
    // Max speed: render all immediately
    while (currentTick < data.ticks.length - 1) renderTick(currentTick + 1);
    stopPlay();
    showWinner();
    return;
  }
  playTimer = setTimeout(() => {
    if (currentTick >= data.ticks.length - 1) {
      stopPlay();
      showWinner();
      return;
    }
    renderTick(currentTick + 1);
    scheduleNext();
  }, delay);
}

function updateSpeed() {
  if (playing) { stopPlay(); startPlay(); }
}

function showWinner() {
  if (!data) return;
  const wchar = data.winner_idx === 0 ? data.char_a : data.char_b;
  document.getElementById('winner-title').textContent = `🏆 ${data.winner_name}`;
  document.getElementById('winner-title').style.color = wchar.color;
  document.getElementById('winner-sub').textContent =
    data.ko
      ? `Vitória por K.O. em ${data.total_ticks} ticks`
      : `Vitória por HP% após ${data.total_ticks} ticks`;
  document.getElementById('winner-banner').classList.add('show');
}
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# HTTP Server
# ─────────────────────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # silencia logs do servidor

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self._send(200, "text/html; charset=utf-8", HTML.encode())

        elif parsed.path == "/api/archetypes":
            payload = [
                {"key": k, "name": ARCHETYPES[v].name}
                for k, v in ALIASES.items()
            ]
            self._send(200, "application/json", json.dumps(payload).encode())

        elif parsed.path == "/api/combat":
            qs = parse_qs(parsed.query)
            key_a = qs.get("a", ["rushdown"])[0]
            key_b = qs.get("b", ["grappler"])[0]
            id_a = ALIASES.get(key_a)
            id_b = ALIASES.get(key_b)
            if id_a is None or id_b is None:
                self._send(400, "text/plain", b"Arquetipo invalido")
                return
            result = record_combat(self.server.chars[id_a], self.server.chars[id_b])
            self._send(200, "application/json", json.dumps(result).encode())

        else:
            self._send(404, "text/plain", b"Not found")

    def _send(self, code: int, ctype: str, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Visualizador web de combate")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--evolved", action="store_true",
                        help="Usa o melhor indivíduo salvo em results.json (default: canônico)")
    args = parser.parse_args()

    if args.evolved:
        ind = Individual.from_results()
        print("  Usando indivíduo evoluído (results.json)")
    else:
        ind = Individual.from_canonical()
        print("  Usando indivíduo canônico")

    url = f"http://localhost:{args.port}"
    print(f"  Servidor rodando em {url}")
    print(f"  Ctrl+C para encerrar\n")
    webbrowser.open(url)

    server = HTTPServer(("localhost", args.port), Handler)
    server.chars = {c.archetype.id: c for c in ind.characters}
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Encerrado.")


if __name__ == "__main__":
    main()
