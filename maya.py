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
"""
from __future__ import annotations

import atexit
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
        _STORE = pathlib.Path.home() / ".cache" / "maya" / "graph"   # ONE global graph — cross-domain memory, like a brain
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
