"""
maya — the tool calls.

Claude Code is the cortex; these are the things it does to keep the subconscious
(the memory graph in memory.py) alive. Import and call them — the graph auto-loads
for input.md's topic and auto-saves on exit. The whole interface is right here.

    import maya
    maya.observe("Ryu-Takayanagi", "computes", "entanglement entropy", source="arXiv:hep-th/0603001")
    maya.analogy("entanglement", "spacetime connectivity", "disentangling pulls geometry apart")
    print(maya.frontier())                          # open questions / contradictions / thin spots
    print(maya.distant("entanglement entropy"))     # far-apart ideas -> surprising bridges
    maya.conjecture(title="...", claim="...", why="...", test="...", sources=["arXiv:..."])  # -> ideas.md

    # turn verify into a HILL and climb it (FunSearch loop; see evolve.py / fitness_templates.py):
    maya.fitness("problem", FITNESS_CODE)           # register one graded check: fitness()->{score, descriptor}
    maya.evaluate("problem", CANDIDATE_CODE)        # score a candidate; files it into a behavior niche
    maya.elites("problem"); maya.champion("problem")  # parents to mutate; the best so far
    maya.surprising("entanglement")                 # novelty: distant-but-reachable links (anti-association)
    maya.duel("conj A", "conj B", "conj A"); maya.by_taste()   # Elo: which conjecture is more fruitful
"""
from __future__ import annotations

import atexit
import os
import pathlib
import re

from memory import Memory, QUESTION

ROOT = pathlib.Path(__file__).resolve().parent
_M = None
_STORE = None
_dirty = False


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower())[:40].strip("-") or "topic"


def topic():
    # the topic is the first markdown blockquote (">") line in input.md
    for ln in (ROOT / "input.md").read_text().splitlines():
        s = ln.strip()
        if s.startswith(">") and len(s) > 1:
            return s.lstrip(">").strip()
    return "untitled"


def _g():
    global _M, _STORE
    if _M is None:
        # one global cross-domain graph by default; set MAYA_STORE to run an isolated / parallel graph
        _STORE = pathlib.Path(os.environ.get("MAYA_STORE") or (pathlib.Path.home() / ".cache" / "maya" / "graph"))
        _M = Memory.open(_STORE)
        if topic()[:60].strip().lower() not in _M._by_name:
            _M.concept(topic()[:60], topic())      # the topic is just the current focus, not a silo
            _touch()
    return _M


def _touch():
    global _dirty
    _dirty = True


@atexit.register
def _flush():
    if _M is not None and _dirty:
        _M.save(_STORE)


# ── OBSERVE — pour cited claims into the subconscious (this is "learning") ────
def observe(subject, relation, obj, source=None, note=None):
    m = _g()
    a = m.concept(subject, support=[source] if source else None)
    b = m.concept(obj)
    m.relate(a, b, relation.replace(" ", "_"))
    m.hebbian(a, b, 0.3)
    m.add_episode(note or f"{subject} {relation} {obj}" + (f"  [{source}]" if source else ""), concepts=[a, b])
    _touch()
    return f"{subject} -{relation}-> {obj}"


def concept(name, description="", source=None):
    _g().concept(name, description, [source] if source else None)
    _touch()
    return name


def relate(a, b, relation="relates to"):
    m = _g()
    x, y = m.concept(a), m.concept(b)
    m.relate(x, y, relation.replace(" ", "_"))
    m.hebbian(x, y, 0.3)
    _touch()


# ── ASSOCIATE — the links YOU see (you are the semantics, not the embeddings) ──
def analogy(a, b, why=""):
    m = _g()
    m.add_analogy(a, b, mapping=[[a, b, why]], members=[m.concept(a), m.concept(b)])
    _touch()


def pattern(members, description):
    m = _g()
    m.add_pattern(description, supporting=[m.concept(x) for x in members])
    _touch()


def contradiction(a, b):
    _g().add_contradiction(a, b)
    _touch()


# ── EXPLORE the graph ─────────────────────────────────────────────────────────
def frontier(k=12):
    m = _g()
    return [m.nodes[i].name for i in m.frontier(k)]


def neighbors(name, k=10):
    m = _g()
    nid = m._by_name.get(name.strip().lower())
    if not nid:
        return []
    es = m.out.get(nid, []) + m.inc.get(nid, [])
    return [(m.nodes[e.dst if e.src == nid else e.src].name, e.kind) for e in es][:k]


def distant(name, k=5):
    m = _g()
    q = m._by_name.get(name.strip().lower()) or name
    return [m.nodes[i].name for i, _ in m.find_distant(q, k=k)]


def status():
    st = _g().stats()
    print(st)
    return st


# ── DREAM — surface a conjecture (never a proof) -> ideas.md ──────────────────
def conjecture(title, claim, why, test="", sources=None):
    m = _g()
    is_new = ("emergent:" + " ".join(title.lower().split())) not in m._by_key
    m.emerge(title, f"{claim}  |  why: {why}", status="idea")      # conjectures live in the graph too
    if is_new:                                  # idempotent: only append a genuinely new conjecture
        block = (f"\n## {title}\n- **claim:** {claim}\n- **why it surfaced:** {why}\n"
                 f"- **how it could be tested:** {test or '(open)'}\n"
                 f"- **sources:** {', '.join(sources or []) or '(cite)'}\n- **status:** new\n")
        with open(ROOT / "ideas.md", "a") as f:
            f.write(block)
        _touch()
    return title


# ── DOUBT — the explicit curiosity channel (ask / list open / resolve) ────────
def ask(question, about=None):
    """Record a doubt / something to understand more deeply. The sharpest frontier."""
    m = _g()
    is_new = ("question:" + " ".join(question.lower().split())) not in m._by_key
    m.add_question(question, about=(m.concept(about) if about else None))
    if is_new:                                  # idempotent: only log a genuinely new doubt
        with open(ROOT / "questions.md", "a") as f:
            f.write(f"- [ ] {question}" + (f"  · about {about}" if about else "") + "\n")
        _touch()
    return question


def questions(k=12):
    m = _g()
    return [n.description for n in m.nodes.values()
            if n.kind == QUESTION and not n.data.get("resolved")][:k]


def resolve(question, answer):
    m = _g()
    key = (question or "").strip().lower()
    for nid, n in m.nodes.items():
        if n.kind == QUESTION and not n.data.get("resolved") and n.description.strip().lower() == key:
            m.answer_question(nid, answer)
            with open(ROOT / "questions.md", "a") as f:
                f.write(f"- [x] {n.description}  ->  {answer}\n")
            _touch()
            return True
    return False


# ── VERIFY — the playground: run any check you write (verifier.py) ────────────
def verify(check_code, entry="check", timeout=30):
    """Run AI-written verification code, sealed (no net, time/mem limits). The code
    defines check() returning a JSON-able result. Soundness is YOURS: compute an
    objective quantity vs known ground truth — a check that returns True proves nothing."""
    import verifier
    return verifier.run(check_code, entry=entry, timeout=timeout)


# ── EVOLVE — turn verify into a FITNESS and climb it (FunSearch loop, evolve.py) ─
def fitness(problem, fitness_code):
    """Register the immutable graded verifier for a problem: fitness() -> {score, descriptor}."""
    import evolve
    return evolve.set_fitness(problem, fitness_code)


def evaluate(problem, candidate_code, timeout=30):
    """Score a candidate up the hill and file it into its behavior niche; returns graded feedback.
    The candidate defines solve(); the registered fitness grades it. This is the loop the cortex drives:
    elites() -> mutate -> evaluate() -> repeat."""
    import evolve
    return evolve.evaluate(problem, candidate_code, timeout=timeout)


def elites(problem, k=8):
    """The diverse high-scorers (one per behavior niche) — your parents to mutate (quality-diversity)."""
    import evolve
    return evolve.elites(problem, k)


def champion(problem):
    """The single best candidate so far."""
    import evolve
    return evolve.best(problem)


def evolve_status(problem):
    """Pool status: niches filled, best score, evaluations."""
    import evolve
    return evolve.status(problem)


# ── SYNTHESIS — pour verifier-labeled elites back into the subconscious ───────
def ingest_elites(problem, k=6):
    """Manufacture data: file the pool's best verified candidates into the graph as ideas,
    so the loop's discoveries feed the memory (your own AlphaProof-style data factory)."""
    import evolve
    m = _g()
    n = 0
    for e in evolve.elites(problem, k):
        m.emerge(f"{problem} · {round(e['score'], 4)}",
                 f"evolved candidate (niche {e['descriptor']}, score {e['score']}):\n{e['program'][:200]}",
                 status="idea", score=e["score"])
        n += 1
    _touch()
    return n


# ── SURPRISE — invert the ranking toward novelty (distant but reachable) ──────
def surprising(name, k=8):
    """Plausible-but-low-probability long-range links: far in meaning, yet connected.
    The anti-association frontier — stepping-stones to novelty, not progress toward an objective."""
    m = _g()
    q = m._by_name.get(name.strip().lower()) or name
    out = []
    for nid, sim in m.find_distant(q, k=80, kinds=["concept", "emergent"]):
        deg = len(m.out.get(nid, [])) + len(m.inc.get(nid, []))
        if deg > 0:                                   # connected = plausible, not isolated noise
            out.append((m.nodes[nid].name, round(float(sim), 3), deg))
    out.sort(key=lambda t: (t[1], -t[2]))             # most distant first, then most connected
    return [n for n, _, _ in out[:k]]


# ── TASTE — Elo duels on conjectures ("which is more fruitful?") ──────────────
def _resolve(ref):
    m = _g()
    if ref in m.nodes:
        return ref
    key = (ref or "").strip().lower()
    if key in m._by_name:
        return m._by_name[key]
    for nid, n in m.nodes.items():                    # resolve conjectures / any node by name
        if n.name.strip().lower() == key:
            return nid
    return None


def duel(a, b, winner):
    """Record one pairwise taste judgment; update Elo on the two nodes. winner = a or b (name/id)."""
    m = _g()
    ia, ib = _resolve(a), _resolve(b)
    if not ia or not ib:
        return None
    ra = m.nodes[ia].data.get("elo", 1200.0)
    rb = m.nodes[ib].data.get("elo", 1200.0)
    ea = 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))
    sa = 1.0 if (winner in (a, ia) or str(winner).strip().lower() == "a") else 0.0
    K = 24.0
    m.nodes[ia].data["elo"] = round(ra + K * (sa - ea), 1)
    m.nodes[ib].data["elo"] = round(rb + K * ((1 - sa) - (1 - ea)), 1)
    _touch()
    return {a: m.nodes[ia].data["elo"], b: m.nodes[ib].data["elo"]}


def by_taste(k=12, kind="emergent"):
    """Conjectures ranked by Elo — where to spend compute (taste, not just novelty or association)."""
    m = _g()
    items = [(n.name, n.data.get("elo", 1200.0)) for n in m.nodes.values() if n.kind == kind]
    items.sort(key=lambda t: -t[1])
    return items[:k]
