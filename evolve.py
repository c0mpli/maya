"""
evolve.py — turn maya's verifier into a FITNESS function and close the loop.

FunSearch / AlphaEvolve in miniature: a MAP-Elites population per problem. You write
ONE immutable graded fitness harness; candidates are scored sealed (verifier.py) and
filed into behavior niches so diversity survives (quality-diversity). The cortex
(Claude Code) is the mutator — it reads the elites + the graded feedback and writes
better candidates. maya keeps the books. This is what makes `verify` a HILL to climb
instead of a yes/no GATE.

    import evolve
    evolve.set_fitness("bound-tightness", FITNESS_CODE)  # defines fitness() -> {"score":float,"descriptor":[..]}
    evolve.evaluate("bound-tightness", CANDIDATE_CODE)   # candidate defines solve(); returns graded feedback
    evolve.elites("bound-tightness", k=8)                # diverse parents to mutate
    evolve.best("bound-tightness")                       # the champion so far
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from verifier import run                              # noqa: E402

POOLS = pathlib.Path(os.environ.get("MAYA_POOLS") or (pathlib.Path.home() / ".cache" / "maya" / "pools"))


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower())[:48].strip("-") or "pool"


def _path(p):
    return POOLS / (_slug(p) + ".json")


def _load(p):
    f = _path(p)
    return json.loads(f.read_text()) if f.exists() else {"problem": p, "fitness": None, "archive": {}, "best": None, "history": []}


def _save(p, pool):
    POOLS.mkdir(parents=True, exist_ok=True)
    _path(p).write_text(json.dumps(pool))


def _bucket(desc):
    try:
        return json.dumps([round(float(d), 1) for d in desc])
    except Exception:
        return "[]"


def set_fitness(problem, fitness_code):
    """Register the immutable graded verifier: fitness() -> {'score': float, 'descriptor': [floats]}."""
    pool = _load(problem)
    pool["fitness"] = fitness_code
    _save(problem, pool)
    return True


def evaluate(problem, candidate_code, timeout=30):
    """Score a candidate against the registered fitness, file it into its niche, return graded feedback.
    The candidate defines solve(); the fitness calls it. Failures return what broke, so the cortex can fix it."""
    pool = _load(problem)
    if not pool["fitness"]:
        raise RuntimeError("no fitness set for %r — call set_fitness first" % problem)
    res = run(candidate_code + "\n" + pool["fitness"], entry="fitness", timeout=timeout)
    if not res["ok"] or not isinstance(res["result"], dict) or "score" not in res["result"]:
        return {"ok": False, "score": None, "error": (res["error"] or "fitness returned no score")[:300]}
    out = res["result"]
    score = float(out["score"])
    desc = out.get("descriptor", [0])
    key = _bucket(desc)
    cur = pool["archive"].get(key)
    accepted = cur is None or score > cur["score"]
    if accepted:
        pool["archive"][key] = {"program": candidate_code, "score": score, "descriptor": desc, "detail": out}
    if pool["best"] is None or score > pool["best"]["score"]:
        pool["best"] = {"program": candidate_code, "score": score, "descriptor": desc}
    pool["history"].append(round(score, 5))
    _save(problem, pool)
    return {"ok": True, "score": score, "descriptor": desc, "accepted": accepted,
            "new_niche": cur is None and accepted, "best_score": pool["best"]["score"],
            "niches": len(pool["archive"]), "detail": out}


def elites(problem, k=8):
    """The diverse high-scorers (one per niche) — the cortex's parents to mutate."""
    items = sorted(_load(problem)["archive"].values(), key=lambda e: -e["score"])[:k]
    return [{"program": e["program"], "score": e["score"], "descriptor": e["descriptor"]} for e in items]


def best(problem):
    return _load(problem).get("best")


def status(problem):
    pool = _load(problem)
    return {"problem": problem, "niches": len(pool["archive"]),
            "best_score": (pool["best"] or {}).get("score"), "evaluations": len(pool["history"])}


# ── demo: the loop closes — best score climbs, niches fill ────────────────────
# (the "program" is code; the mutator here is a trivial perturbation standing in
#  for the cortex, which in real maya writes the smarter variants.)
if __name__ == "__main__":
    import random
    random.seed(0)

    FITNESS = '''
def fitness():
    import math
    w = solve()                                  # candidate returns 8 polynomial coefficients
    n = len(w); xs = [i/49.0 for i in range(50)]
    f = lambda x: sum(w[j]*(x**j) for j in range(n))
    mse = sum((f(x) - math.sin(2*math.pi*x))**2 for x in xs)/50.0
    return {"score": -mse, "descriptor": [sum(w)/n, max(w)]}   # hill to climb (0 = perfect), + behavior niche
'''
    cand = lambda v: "def solve():\n    return " + repr([round(x, 4) for x in v]) + "\n"
    def mutate(code):
        v = eval(re.search(r"return (\[.*\])", code).group(1))
        for _ in range(random.randint(1, 3)):
            v[random.randrange(len(v))] += random.gauss(0, 0.4)
        return cand(v)

    P = "demo-approx-sin"
    if _path(P).exists():
        _path(P).unlink()
    set_fitness(P, FITNESS)
    for _ in range(6):
        evaluate(P, cand([random.gauss(0, 1) for _ in range(8)]))   # seed
    print("gen    best_score    niches")
    for gen in range(1, 161):
        evaluate(P, mutate(random.choice(elites(P, 8))["program"]))  # select elite -> mutate -> score
        if gen % 20 == 0:
            print(f"{gen:>4}   {best(P)['score']:>10.4f}   {status(P)['niches']:>5}")
    print("\nverify went from a gate to a HILL: best score climbed to",
          round(best(P)["score"], 5), "(0 = perfect fit)")
    print("final:", status(P))
