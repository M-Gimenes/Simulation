import json, statistics as st
from collections import defaultdict
from src.engine.individual import Individual
from src.engine.character import Character
from src.engine import fitness as F
from src.engine.archetypes import ARCHETYPES, ARCHETYPE_ORDER
g=json.load(open('results/multi_run/multi_run_ga.json'));n=json.load(open('results/multi_run/multi_run_nsga2.json'))
c0=json.load(open('results/controls/multi_run_ga_drift0_dom1.json'))
def sc(r): return r['dominance_penalty']+r['drift_penalty']
print("seed  GA(dom,drift,sum)   NSGA-so(dom,drift,sum)  better")
wins=0
for a,b in zip(g['per_seed'],n['per_seed']):
    s=b['representatives']['scalar_optimum']
    w='NSGA' if sc(s)<sc(a) else 'GA'; wins+= w=='NSGA'
    print(a['seed'],f"{a['dominance_penalty']:.4f} {a['drift_penalty']:.4f} {sc(a):.4f} | {s['dominance_penalty']:.4f} {s['drift_penalty']:.4f} {sc(s):.4f}",w)
print("NSGA scalar_optimum beats GA on GA's own scalar objective:",wins,"/20")
# cycle edges
names={aid:ARCHETYPES[aid].name for aid in ARCHETYPE_ORDER}
edges=[(names[w],names[l]) for w in ARCHETYPE_ORDER for l in ARCHETYPES[w].beats]
def wr_of(m,x,y):
    k=f"{x} vs {y}"
    return m[k]['wr'] if k in m else 1-m[f"{y} vs {x}"]['wr']
for lab,runs in [('GA',[r for r in g['per_seed']]),('NSGA-so',[r['representatives']['scalar_optimum'] for r in n['per_seed']]),('ctrl λ0',c0['per_seed'])]:
    print(f"\n== {lab}: WR do vencedor canonico por aresta (media, #seeds >0.5, #hard)")
    tot=[]
    for w,l in edges:
        v=[wr_of(r['matchups'],w,l) for r in runs]
        print(f"  {w:>12} > {l:<12} {st.mean(v):.3f} ±{st.stdev(v):.3f}  kept {sum(x>0.5 for x in v):2d}/20  hard {sum(abs(x-.5)>.15 for x in v)}")
    tot=[sum(wr_of(r['matchups'],w,l)>0.5 for w,l in edges) for r in runs]
    print("  arestas mantidas por seed: media",st.mean(tot),"min",min(tot),"max",max(tot))
# per-character deviation
for lab,runs in [('GA',g['per_seed']),('NSGA-so',[r['representatives']['scalar_optimum'] for r in n['per_seed']]),('ctrl λ0',c0['per_seed'])]:
    dv=defaultdict(list)
    for r in runs:
        for aid,genes in zip(ARCHETYPE_ORDER,r['genes']):
            ch=Character(ARCHETYPES[aid],list(genes[:8]),list(genes[8:]))
            dv[names[aid]].append(F._archetype_deviation(ch))
    print(f"\n== {lab} desvio por personagem (media ± dp)")
    for k,v in dv.items(): print(f"  {k:12} {st.mean(v):.3f} ± {st.stdev(v):.3f}")
