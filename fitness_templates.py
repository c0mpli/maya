"""
fitness_templates.py — graded fitness functions for math & physics, ready for evolve.

A fitness is the immutable graded verifier: it defines `fitness()`, which calls the
candidate's `solve()` and returns {"score": float (higher = better), "descriptor": [..]}.
Register one, then let the cortex mutate candidates up the hill:

    import evolve, fitness_templates as F
    evolve.set_fitness("pi-cf", F.MATH_PRECISION)      # or write your own
    evolve.evaluate("pi-cf", "def solve(): return [3,7,15,1]")
    evolve.elites("pi-cf"); evolve.best("pi-cf")

These are PATTERNS — edit the marked lines for your problem. The score must be
continuous (a hill), and computed against INDEPENDENT ground truth (precision,
a known value, a provable margin) so it can't be gamed.
"""

# ── MATH · precision (Ramanujan-machine flavor) ───────────────────────────────
# Candidate returns the parameters of an approximation; score = digits of agreement
# with a target constant, at high precision. (The demo below uses continued-fraction
# terms approximating pi.) Swap the target / construction for your conjecture.
MATH_PRECISION = '''
def fitness():
    import mpmath as mp
    mp.mp.dps = 50
    a = solve()                                  # continued-fraction terms [a0, a1, ...]
    if not a: return {"score": -1.0, "descriptor": [0, 0]}
    val = mp.mpf(a[-1])
    for t in reversed(a[:-1]):
        val = mp.mpf(t) + 1/val
    err = abs(val - mp.pi)                        # <-- edit: your target constant
    digits = float(-mp.log10(err)) if err > 0 else 45.0
    return {"score": min(digits, 45.0), "descriptor": [len(a), int(a[-1])]}
'''

# ── MATH · inequality margin (entropy-cone / Diophantine flavor) ──────────────
# Candidate returns coefficients of a claimed inequality sum(c_i * q_i) >= 0.
# Fitness = the worst (min) margin over a battery of instances. >0 ⇒ holds (and you
# climb toward TIGHT-but-true, the facets); <0 ⇒ a counterexample was found.
MATH_INEQUALITY = '''
def fitness():
    import numpy as np
    c = solve()                                  # coefficients
    rng = np.random.default_rng(0)
    worst = 1e9
    for _ in range(300):
        q = rng.random(len(c))                   # <-- edit: real quantities (entropies, etc.)
        worst = min(worst, float(np.dot(c, q)))
    # reward holding (worst>=0) and tightness (worst near 0); punish triviality
    return {"score": -abs(worst) if worst >= 0 else worst, "descriptor": [round(float(np.mean(c)),1), len(c)]}
'''

# ── PHYSICS · residual vs known/reference ─────────────────────────────────────
# Candidate returns a model's predictions; score = -error against reference data or a
# known result. The honest, general physics hill: closer to nature = higher.
PHYSICS_RESIDUAL = '''
def fitness():
    import numpy as np
    pred = np.asarray(solve(), float)
    ref  = np.array([__YOUR_REFERENCE_DATA__])   # <-- edit: known values / measured data
    err  = float(np.sqrt(np.mean((pred - ref)**2)))
    return {"score": -err, "descriptor": [round(float(pred.mean()),2), round(float(pred.std()),2)]}
'''

# ── PHYSICS · emergent-geometry smoothness (the report's suggestion) ──────────
# Candidate returns an N×N mutual-information matrix (or build it from a state).
# Fitness = how smoothly it embeds into a low-dimensional manifold (MDS stress).
# A continuous "how geometric is this state" signal — verify becomes a hill.
PHYSICS_EMBEDDING = '''
def fitness():
    import numpy as np
    from sklearn.manifold import MDS
    M = np.asarray(solve(), float)               # mutual-information matrix, N x N
    N = M.shape[0]
    d = M.max() - M                              # distance ~ (less MI = farther)
    np.fill_diagonal(d, 0.0)
    best = None
    for dim in (1, 2, 3):                        # prefer the lowest dim that fits well
        emb = MDS(n_components=dim, dissimilarity="precomputed", random_state=0, normalized_stress="auto")
        emb.fit(d)
        s = emb.stress_                          # lower stress = smoother embedding
        if best is None or s < best[1]: best = (dim, s)
    return {"score": -float(best[1]), "descriptor": [best[0], round(float(M.mean()),2)]}
'''


# ── demo: a REAL math hill — discover rational approximations to pi ───────────
if __name__ == "__main__":
    import random, re
    import evolve
    random.seed(1)
    P = "demo-pi-continued-fraction"
    if evolve._path(P).exists():
        evolve._path(P).unlink()
    evolve.set_fitness(P, MATH_PRECISION)

    cand = lambda a: "def solve():\n    return " + repr([int(x) for x in a]) + "\n"
    def mutate(code):
        a = eval(re.search(r"return (\[.*\])", code).group(1))[:]
        r = random.random()
        if r < 0.6 and a:
            i = random.randrange(len(a)); a[i] = max(1, a[i] + random.choice([-2, -1, 1, 2, 3]))
        elif r < 0.85:
            a.append(random.randint(1, 16))
        elif len(a) > 1:
            a.pop()
        return cand(a or [3])

    for s in ([3], [3, 7], [random.randint(1, 9)], [random.randint(1, 9), random.randint(1, 9)]):
        evolve.evaluate(P, cand(s))
    print("gen   best_digits   niches   champion")
    for gen in range(1, 221):
        evolve.evaluate(P, mutate(random.choice(evolve.elites(P, 10))["program"]))
        if gen % 40 == 0:
            b = evolve.best(P); terms = eval(re.search(r"return (\[.*\])", b["program"]).group(1))
            print(f"{gen:>4}   {b['score']:>10.2f}   {evolve.status(P)['niches']:>5}   {terms}")
    b = evolve.best(P); terms = eval(re.search(r"return (\[.*\])", b["program"]).group(1))
    print("\nbest:", round(b["score"], 2), "digits of pi from continued fraction", terms)
