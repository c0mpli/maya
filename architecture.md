# maya — Architecture

> An autonomous discovery engine. **Claude Code is the cortex**: it researches a
> question on the web, pours what it observes into one persistent associative
> memory (a self-organizing "subconscious"), surfaces novel conjectures, and
> verifies the checkable ones. One instruction file. One global graph. One
> playground. No API.

---

## 1. What it is

You write a question in `input.md` and tell Claude Code: **"read input.md and
execute it."** From there Claude Code *is* the mind — it searches the web, reads,
and reflexively feeds everything it observes into a graph (the subconscious), lets
associations and contradictions accumulate, and writes the conjectures that
surface to `ideas.md`. Where a conjecture has a computable piece, it writes a
check and runs it in the playground.

maya is not an app you launch; it's a substrate the agent drives through tool
calls. The whole system is three small code files: `maya.py` (the tool calls),
`memory.py` (the graph), `verifier.py` (the playground).

---

## 2. North star: autoresearch

We keep the discipline of Karpathy's autoresearch — instructions + an agent that
reads them and loops, with the heavy machinery in a fixed substrate:

| autoresearch | maya |
| --- | --- |
| `program.md` (instructions) | `input.md` (instructions + the question) |
| the agent reads it and loops | Claude Code reads it and loops |
| `train.py` — the artifact it builds | the **memory graph** — the artifact it builds |
| `prepare.py` — the fixed substrate | `memory.py` + `verifier.py` — the fixed substrate |

> The rule, still: **simple skeleton, rich cognition.** The cognition is the
> agent; the skeleton is three files.

---

## 3. Claude Code is the cortex — both minds at once

Earlier maya ran its own loops and called an LLM API. Now the agent *is* the
cognition, so it plays both minds, the way a person does:

- **Conscious** — deliberate web research: search, read, extract cited claims.
- **Subconscious** — the persistent graph. The agent feeds it *reflexively*
  (everything observed goes in) and it reorganizes — like a brain updating from
  what it sees without being told to. "Automatic" means the `input.md` protocol
  makes feeding-and-associating a reflex, and the graph's own structure
  (activation, frontier) surfaces what to think about next.

No API, no orchestrator, no background loops — Claude Code is all of it.

---

## 4. One global graph — cross-domain by design

The memory is a **single, persistent, global graph** (`~/.cache/maya/graph/`),
not one-per-topic. Everything maya has ever read — across every question — lives
in one associative memory, so a concept from one domain can bridge to another.
That cross-domain reach is the source of the best analogies and surprises; siloing
per topic would throw it away. The topic in `input.md` is just the current
**focus** (a seed concept), never a partition.

---

## 5. Memory — the layers (`memory.py`)

Rich model, simple substrate: typed nodes + typed weighted edges + a numpy vector
index + spreading activation + JSON/npy snapshots.

| layer | what it is |
| --- | --- |
| **concept** | an idea (+ embedding, citations) |
| **relationship** | a typed, weighted edge (Hebbian-reinforced) |
| **hyperedge** | an n-ary association |
| **episode** | a timestamped observation, linked to concepts |
| **pattern** | recurring structure — a building block |
| **analogy** | a cross-domain mapping |
| **contradiction** | clashing claims — kept, never deleted |
| **emergent** | a system-made result (status: idea / discovery) |
| **question** | an open doubt — the explicit curiosity signal |

`frontier()` ranks the research edge: **open questions first**, then
contradictions, then thinly-connected concepts.

---

## 6. The loop (`input.md` drives this)

```
OBSERVE → ASSOCIATE → DOUBT → DREAM → VERIFY → CURIOSITY → (back to OBSERVE)
```

- **OBSERVE** (conscious) — web/paper search → `maya.observe(subj, rel, obj, source=)`
  pours each cited claim into the graph. Reflexive: everything read goes in.
- **ASSOCIATE** (you are the semantics) — `maya.analogy`, `maya.pattern`,
  `maya.contradiction`: the links the agent sees, recorded the way a mind settles.
- **DOUBT** (curiosity) — `maya.ask(q, about=)` records what to understand more
  deeply; `maya.questions()` lists open ones; `maya.resolve(q, answer)` closes them.
- **DREAM** (discover) — `maya.frontier()`, `maya.distant(name)`, `maya.neighbors(name)`
  surface gaps and far-apart ideas; a novel connection becomes
  `maya.conjecture(...)` → `ideas.md` (conjectures, never proofs).
- **VERIFY** (when checkable) — `maya.verify(code)` runs a self-written check.
- **CURIOSITY** — every conjecture and doubt raises a sharper question; chase the
  most informative one and loop.

---

## 7. The tool calls (`maya.py` — the whole interface)

- **learn:** `observe` · `concept` · `relate`
- **associate:** `analogy` · `pattern` · `contradiction`
- **doubt:** `ask` · `questions` · `resolve`
- **explore:** `frontier` · `neighbors` · `distant` · `status`
- **dream / verify:** `conjecture` (→ `ideas.md`) · `verify` (→ the playground)

The graph auto-loads and auto-saves; the agent never manages files.

---

## 8. The playground (`verifier.py`)

One file. The AI writes any check it wants and runs it **sealed**: a separate
process, no network, wall-clock + CPU + memory limits, nothing persisted. The
check computes something and returns a JSON-able result (numpy values are
auto-converted).

**Soundness is the caller's job.** A check only means something if it computes an
*objective* quantity and compares it to *independent* ground truth (a known value,
a provable inequality, a closed-form result) — and could actually fail. A check
that returns `True` verifies nothing. This is the reward-hacking guard, now on the
agent: be your own adversary; write checks that can fail.

This is what lets maya do real work on a "soft" question. It can't prove
"spacetime is derived from entanglement," but it *can* verify checkable pieces — a
Bell state's entanglement entropy equals ln 2; a tensor-network code reproduces an
area law; an inequality holds — and a passed, sound check turns a conjecture into
something you can stand behind.

---

## 9. Grounding & honesty

- **Web = the novelty oracle** — "has anyone already shown this?"
- **The verifier = the correctness oracle** — "does this actually hold?"
- A conjecture in `ideas.md` is a **lead, not a proof**. One backed by a passed,
  sound check is stronger. maya maps and conjectures; it never claims to have
  proved the big question.

---

## 10. File layout

```
maya/
  input.md      # the question + the standing protocol   (the only thing you edit)
  maya.py       # the tool calls                           (the whole interface)
  memory.py     # the global associative graph             (the subconscious)
  verifier.py   # the sealed playground                     (self-written checks)
  ideas.md      # conjectures, for human review
  questions.md  # open doubts — you can add your own to steer the dig
  log.md        # narrative trail
  ~/.cache/maya/graph/    # the persisted global graph (durable; lives outside the repo)
```

---

## 11. How to run it

Open Claude Code in this folder and say:

> **read input.md and execute it**

It researches, builds the shared graph, surfaces conjectures into `ideas.md`, asks
and resolves doubts in `questions.md`, and verifies the checkable pieces in the
playground — for any question you put under `## Topic`.
