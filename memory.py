"""
maya / memory — the self-organizing associative graph.

Eight layers (concepts, relationships, hyperedges, episodes, patterns, analogies,
contradictions, emergent concepts) over one substrate: typed nodes, typed weighted
edges, a numpy vector index, live spreading activation, and JSON snapshots.

Rich model, simple substrate (architecture.md §5). The cognition layer (real
embeddings, LLM) lives in cognition.py; Memory just holds an `embed` callable so
it can vectorize concepts — defaulting to a deterministic hash embedder so this
module runs and tests with no external services.
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import random
import time
from dataclasses import asdict, dataclass, field
from typing import Callable, Optional

import numpy as np

# ── the eight layers (architecture §5); RELATION is edges, not nodes ──────────
CONCEPT = "concept"
HYPEREDGE = "hyperedge"
EPISODE = "episode"
PATTERN = "pattern"
ANALOGY = "analogy"
CONTRADICTION = "contradiction"
EMERGENT = "emergent"
QUESTION = "question"

EMBED_DIM = 256


def _norm(s):
    """Normalize text to a stable content key (lowercase, collapsed whitespace)."""
    return " ".join((s or "").lower().split())


def hash_embed(text: str, dim: int = EMBED_DIM) -> np.ndarray:
    """Deterministic, offline stand-in for a real embedding model. Hashes word +
    character-trigram features into a normalized bag-of-features vector. Not
    semantic — just enough to exercise the index and activation machinery until
    cognition.py supplies a real model."""
    vec = np.zeros(dim, dtype=np.float32)
    text = (text or "").lower()
    grams = text.split() + [text[i:i + 3] for i in range(max(0, len(text) - 2))]
    for g in grams:
        h = int(hashlib.md5(g.encode("utf-8")).hexdigest(), 16)
        vec[h % dim] += 1.0
    n = float(np.linalg.norm(vec))
    return vec / n if n > 0 else vec


def _default_embed(text: str, dim: int = EMBED_DIM) -> np.ndarray:
    """Use a real semantic embedder if one is configured (see maya_embed.py), else fall back to the
    deterministic offline hash_embed. This makes recall/analogy/distant *semantic* the moment you plug
    in a model — and keeps maya fully working offline until then. Model-agnostic by design."""
    try:
        import maya_embed
        if maya_embed.available():
            return maya_embed.embed(text, dim)
    except Exception:
        pass
    return hash_embed(text, dim)


@dataclass
class Node:
    id: str
    kind: str                                       # one of the layer names above
    name: str
    description: str = ""
    data: dict = field(default_factory=dict)        # layer-specific payload
    support: list = field(default_factory=list)     # citations / sources
    members: list = field(default_factory=list)     # hyperedge / analogy member ids
    parents: list = field(default_factory=list)     # provenance (emergent concepts)
    status: Optional[str] = None                    # emergent: discovery | idea | refuted
    weight: float = 1.0                             # salience / confidence
    created: float = 0.0


@dataclass
class Edge:
    src: str
    dst: str
    kind: str = "relates_to"
    weight: float = 1.0


class Memory:
    def __init__(self, embed: Optional[Callable[[str], np.ndarray]] = None,
                 dim: int = EMBED_DIM, seed: int = 0):
        self.embed = embed or _default_embed
        self.dim = dim
        self.nodes = {}                 # id -> Node
        self.out = {}                   # src -> [Edge]
        self.inc = {}                   # dst -> [Edge]
        self._edge_idx = {}             # (src, dst, kind) -> Edge
        self._emb = np.zeros((0, dim), dtype=np.float32)
        self._rows = []                 # row -> node id
        self._row_of = {}               # node id -> row
        self.activation = {}            # node id -> float (last spread)
        self._by_name = {}              # concept name (lower) -> id, for find-or-create
        self._by_key = {}               # "kind:contentkey" -> id, for idempotent writes
        self._rng = random.Random(seed)
        self._counter = 0

    # ── construction ─────────────────────────────────────────────────────────
    def _new_id(self, kind: str) -> str:
        self._counter += 1
        return f"{kind[:4]}_{self._counter}"

    def _set_embedding(self, nid: str, vec: np.ndarray) -> None:
        row = self._row_of.get(nid)
        if row is None:
            self._row_of[nid] = len(self._rows)
            self._rows.append(nid)
            self._emb = np.vstack([self._emb, vec[None, :].astype(np.float32)])
        else:
            self._emb[row] = vec

    def _add(self, kind: str, name: str, description: str = "",
             embedding: Optional[np.ndarray] = None, dedup: Optional[str] = None, **kw) -> str:
        if dedup is not None:
            seen = self._by_key.get(kind + ":" + dedup)
            if seen is not None:                      # re-encountered -> reinforce, don't duplicate
                self.nodes[seen].weight += 0.15
                return seen
        nid = self._new_id(kind)
        node = Node(id=nid, kind=kind, name=name, description=description, created=time.time(), **kw)
        self.nodes[nid] = node
        if dedup is not None:
            node.data["_key"] = dedup
            self._by_key[kind + ":" + dedup] = nid
        if embedding is None:
            embedding = self.embed(f"{name}: {description}" if description else name)
        self._set_embedding(nid, np.asarray(embedding, dtype=np.float32))
        self.out.setdefault(nid, [])
        self.inc.setdefault(nid, [])
        return nid

    def add_concept(self, name, description="", support=None, embedding=None) -> str:
        nid = self._add(CONCEPT, name, description, embedding=embedding, support=support or [])
        self._by_name.setdefault(name.strip().lower(), nid)
        return nid

    def concept(self, name, description="", support=None) -> str:
        """Find-or-create a concept by name (case-insensitive) — keeps the graph deduped."""
        nid = self._by_name.get(name.strip().lower())
        if nid is None:
            return self.add_concept(name, description, support)
        node = self.nodes[nid]
        if description and not node.description:
            node.description = description
        if support:
            node.support.extend(support)
        return nid

    def add_episode(self, observation, concepts=None) -> str:
        nid = self._add(EPISODE, name=observation[:60], description=observation, dedup=_norm(observation))
        for c in (concepts or []):
            self.relate(nid, c, "mentions", 0.5)
        return nid

    def add_contradiction(self, a, b, about=None) -> str:
        return self._add(CONTRADICTION, name="contradiction", description=f"{a}  <->  {b}",
                         data={"a": a, "b": b}, members=list(about or []),
                         dedup="~".join(sorted([_norm(a), _norm(b)])))

    def add_hyperedge(self, members, description="") -> str:
        return self._add(HYPEREDGE, name="hyperedge", description=description, members=list(members),
                         dedup="~".join(sorted(str(m) for m in members)))

    def add_analogy(self, source, target, mapping, members=None) -> str:
        return self._add(ANALOGY, name=f"{source}~{target}", description=f"{source} <-> {target}",
                         data={"mapping": mapping}, members=list(members or []),
                         dedup="~".join(sorted([_norm(source), _norm(target)])))

    def add_pattern(self, description, supporting=None) -> str:
        return self._add(PATTERN, name="pattern", description=description, members=list(supporting or []),
                         dedup=_norm(description))

    def emerge(self, name, description, parents=None, status="idea", score=None) -> str:
        return self._add(EMERGENT, name, description, parents=list(parents or []),
                         status=status, data={"score": score}, dedup=_norm(name))

    def add_question(self, text, about=None) -> str:
        """An open doubt / question — the explicit curiosity signal (architecture §4)."""
        return self._add(QUESTION, name=text[:60], description=text,
                         members=[about] if about else [], data={"resolved": False},
                         dedup=_norm(text))

    def answer_question(self, qid, answer) -> None:
        if qid in self.nodes:
            self.nodes[qid].data["resolved"] = True
            ep = self.add_episode(answer, concepts=[qid])
            self.relate(qid, ep, "answered_by", 1.0)

    # ── edges, Hebbian wiring, credit assignment ──────────────────────────────
    def relate(self, src, dst, kind="relates_to", weight=1.0) -> None:
        e = self._edge_idx.get((src, dst, kind))
        if e is None:
            e = Edge(src, dst, kind, weight)
            self._edge_idx[(src, dst, kind)] = e
            self.out.setdefault(src, []).append(e)
            self.inc.setdefault(dst, []).append(e)
        else:
            e.weight = weight

    def hebbian(self, a, b, delta=0.1, kind="co_occurs") -> None:
        """Concepts that fire together wire together — strengthen both directions."""
        for s, d in ((a, b), (b, a)):
            e = self._edge_idx.get((s, d, kind))
            if e is None:
                self.relate(s, d, kind, weight=max(0.0, delta))
            else:
                e.weight += delta

    def credit(self, node_ids, delta) -> None:
        """Reinforce (+) or weaken (-) a lineage by what it produced (architecture §12)."""
        ids = set(node_ids)
        for nid in ids:
            if nid in self.nodes:
                self.nodes[nid].weight = max(0.0, self.nodes[nid].weight + delta)
        for e in self._edge_idx.values():
            if e.src in ids and e.dst in ids:
                e.weight = max(0.0, e.weight + delta)

    # ── vector search ─────────────────────────────────────────────────────────
    def _vec_of(self, query) -> np.ndarray:
        if isinstance(query, str) and query in self.nodes:
            return self._emb[self._row_of[query]]
        if isinstance(query, str):
            return self.embed(query)
        return np.asarray(query, dtype=np.float32)

    def _cos(self, vec: np.ndarray) -> np.ndarray:
        if not self._rows:
            return np.zeros(0, dtype=np.float32)
        v = np.asarray(vec, dtype=np.float32)
        nv = float(np.linalg.norm(v))
        if nv == 0:
            return np.zeros(len(self._rows), dtype=np.float32)
        return (self._emb @ v) / (np.linalg.norm(self._emb, axis=1) * nv + 1e-9)

    def _search(self, query, k, kinds, exclude, most):
        if not self._rows:
            return []
        sims = self._cos(self._vec_of(query))
        order = np.argsort(sims)
        order = order[::-1] if most else order
        exclude = set(exclude or [])
        if isinstance(query, str) and query in self.nodes:
            exclude.add(query)
        out = []
        for row in order:
            nid = self._rows[int(row)]
            if nid in exclude or (kinds and self.nodes[nid].kind not in kinds):
                continue
            out.append((nid, float(sims[int(row)])))
            if len(out) >= k:
                break
        return out

    def find_similar(self, query, k=8, kinds=None, exclude=None):
        return self._search(query, k, kinds, exclude, most=True)

    def find_distant(self, query, k=8, kinds=None, exclude=None):
        """The exploration primitive — least-similar concepts (architecture §10)."""
        return self._search(query, k, kinds, exclude, most=False)

    # ── activation dynamics (the "thinking") ──────────────────────────────────
    def spread(self, seeds, steps=3, decay=0.6, explore_bonus=0.3):
        """Spread activation from seeds; WEAK links get an exploration bonus so the
        search wanders instead of only exploiting strong edges (architecture §4)."""
        act = {n: 1.0 for n in seeds if n in self.nodes}
        for _ in range(steps):
            nxt = dict(act)
            for nid, a in act.items():
                if a < 1e-3:
                    continue
                for e in self.out.get(nid, []):
                    bonus = explore_bonus / (1.0 + e.weight)     # thinner edge, bigger nudge
                    nxt[e.dst] = nxt.get(e.dst, 0.0) + a * decay * (e.weight + bonus)
            m = max(nxt.values()) if nxt else 1.0
            m = m or 1.0
            act = {n: v / m for n, v in nxt.items() if v / m > 1e-3}
        self.activation = act
        return act

    def random_walk(self, start=None, length=20, n=50):
        """n random walks; returns visit counts. Occasional teleport = serendipity."""
        counts = {}
        ids = list(self.nodes)
        if not ids:
            return counts
        for _ in range(n):
            cur = start if (start in self.nodes) else self._rng.choice(ids)
            for _ in range(length):
                counts[cur] = counts.get(cur, 0) + 1
                nbrs = self.out.get(cur, [])
                if not nbrs or self._rng.random() < 0.15:
                    cur = self._rng.choice(ids)
                else:
                    cur = self._rng.choices([e.dst for e in nbrs],
                                            weights=[max(1e-6, e.weight) for e in nbrs], k=1)[0]
        return counts

    def frontier(self, k=12):
        """The research edge: open questions, contradictions, thin concepts (architecture §4)."""
        scored = []
        for nid, node in self.nodes.items():
            if node.kind == QUESTION and not node.data.get("resolved"):
                scored.append((nid, 3.0))          # open doubts are the sharpest edge
            elif node.kind == CONTRADICTION:
                scored.append((nid, 2.0))
            elif node.kind in (CONCEPT, EMERGENT):
                degree = len(self.out.get(nid, [])) + len(self.inc.get(nid, []))
                scored.append((nid, 1.0 / (1.0 + degree + len(node.support))))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [nid for nid, _ in scored[:k]]

    # ── snapshot (concurrency: dream on a frozen view, architecture §7) ───────
    def snapshot(self) -> "Memory":
        snap = Memory(embed=self.embed, dim=self.dim)
        snap.nodes = {k: copy.copy(v) for k, v in self.nodes.items()}
        snap.out = {k: list(v) for k, v in self.out.items()}
        snap.inc = {k: list(v) for k, v in self.inc.items()}
        snap._edge_idx = dict(self._edge_idx)
        snap._emb = self._emb.copy()
        snap._rows = list(self._rows)
        snap._row_of = dict(self._row_of)
        snap._by_name = dict(self._by_name)
        snap._by_key = dict(self._by_key)
        snap._counter = self._counter
        return snap

    # ── persistence (human-readable graph + npy vectors) ──────────────────────
    def save(self, path) -> None:
        p = pathlib.Path(path)
        p.mkdir(parents=True, exist_ok=True)
        p.joinpath("graph.json").write_text(json.dumps({
            "nodes": [asdict(n) for n in self.nodes.values()],
            "edges": [asdict(e) for e in self._edge_idx.values()],
            "rows": self._rows,
        }, indent=2))
        np.save(str(p / "embeddings.npy"), self._emb)

    @classmethod
    def load(cls, path, embed=None) -> "Memory":
        p = pathlib.Path(path)
        g = json.loads((p / "graph.json").read_text())
        m = cls(embed=embed)
        m._emb = np.load(str(p / "embeddings.npy"))
        m._rows = list(g["rows"])
        m._row_of = {nid: i for i, nid in enumerate(m._rows)}
        for nd in g["nodes"]:
            m.nodes[nd["id"]] = Node(**nd)
            m.out.setdefault(nd["id"], [])
            m.inc.setdefault(nd["id"], [])
            if nd["kind"] == CONCEPT:
                m._by_name.setdefault(nd["name"].strip().lower(), nd["id"])
            k = (nd.get("data") or {}).get("_key")
            if k is not None:
                m._by_key[nd["kind"] + ":" + k] = nd["id"]
        for ed in g["edges"]:
            e = Edge(**ed)
            m._edge_idx[(e.src, e.dst, e.kind)] = e
            m.out.setdefault(e.src, []).append(e)
            m.inc.setdefault(e.dst, []).append(e)
        m._counter = len(m.nodes)
        return m

    @classmethod
    def open(cls, path, embed=None) -> "Memory":
        """Load the store if it exists, else start fresh (agent-mode convenience)."""
        return cls.load(path, embed=embed) if (pathlib.Path(path) / "graph.json").exists() else cls(embed=embed)

    def stats(self) -> dict:
        from collections import Counter
        kinds = Counter(n.kind for n in self.nodes.values())
        return {"nodes": len(self.nodes), "edges": len(self._edge_idx), **dict(kinds)}


# ── smoke test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import tempfile

    m = Memory()
    ai = m.add_concept("bin packing", "pack items into the fewest bins")
    ff = m.add_concept("first-fit", "place each item in the first bin that fits")
    bf = m.add_concept("best-fit", "place each item in the tightest bin that fits")
    nn = m.add_concept("neural network", "layers of weighted units trained by backprop")
    m.relate(ai, ff, "has_heuristic")
    m.relate(ai, bf, "has_heuristic")
    m.hebbian(ff, bf, 0.5)
    m.add_episode("first-fit and best-fit both leave gaps on adversarial inputs", [ff, bf])
    m.add_contradiction("FFD is near-optimal in practice", "FFD is far from optimal on hard instances", about=[ff])

    print("stats        :", m.stats())
    print("similar(bin) :", [(m.nodes[i].name, round(s, 2)) for i, s in m.find_similar(ai, k=3)])
    print("distant(bin) :", [m.nodes[i].name for i, _ in m.find_distant(ai, k=1)])
    act = m.spread([ai], steps=2)
    print("activation   :", sorted([(m.nodes[i].name, round(a, 2)) for i, a in act.items()],
                                    key=lambda x: -x[1])[:4])
    print("frontier     :", [m.nodes[i].name for i in m.frontier(k=3)])

    snap = m.snapshot()
    snap.add_concept("scratch", "only in the snapshot")
    print("snapshot iso :", f"live={len(m.nodes)}  snapshot={len(snap.nodes)}")

    d = tempfile.mkdtemp()
    m.save(d)
    print("reload       :", Memory.load(d).stats())
