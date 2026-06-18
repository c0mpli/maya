# maya

**An autonomous discovery engine you drive with Claude Code.**

You write a question in `input.md` and say **“read input.md and execute it.”** From
there Claude Code is the *cortex*: it researches the question on the web, pours
everything it observes into one persistent associative memory (a self-organizing
“subconscious”), surfaces novel cross-domain conjectures, and verifies the checkable
ones in a sealed playground. It maps and conjectures — it never claims to have
proved anything.

---

## Run it

1. Install [Claude Code](https://claude.com/claude-code), and Python 3.9+ with `numpy`.
2. Open Claude Code in this folder.
3. Put your question under `## Topic` in `input.md`.
4. Say: **read input.md and execute it**

Watch `ideas.md` (conjectures) and `questions.md` (open doubts) fill in. The graph
itself persists in `~/.cache/maya/graph/` — and it’s **global**: every question you
ever ask feeds one shared, cross-domain memory, which is where the surprising bridges
come from.

---

## The whole system

| file | role |
| --- | --- |
| `input.md` | your question + the standing protocol — the only file you edit |
| `maya.py` | the tool calls — the whole interface |
| `memory.py` | the global associative graph (the subconscious) |
| `verifier.py` | the sealed playground for self-written checks |
| `ideas.md` | conjectures, for human review |
| `questions.md` | open doubts (add your own to steer it) |
| `architecture.md` | how and why it works |

Three code files. The cognition is the agent; the skeleton is small and readable.

---

## How it works

Claude Code runs a loop — **observe → associate → doubt → dream → verify → curiosity** —
recording everything through `maya`’s tool calls:

- **observe** a cited claim → it becomes concepts + a weighted, Hebbian-reinforced edge.
- **associate** the links you see → analogies, patterns, contradictions (kept, never deleted).
- **ask** a doubt → it jumps to the top of the frontier and gets chased first.
- **dream** at the frontier → novel connections become conjectures in `ideas.md`.
- **verify** a checkable piece → write code, run it sealed (no network, time/memory limits).

The memory is an 8-layer typed graph with a vector index and spreading activation.
Every write is **idempotent** (re-running reinforces, never duplicates), so the loop
is safe to repeat. See [`architecture.md`](architecture.md) for the full design.

---

## Philosophy

Inspired by Karpathy’s [autoresearch](https://github.com/karpathy/autoresearch):
instructions + an agent that reads them and loops, with the heavy machinery in a
tiny, fixed substrate. maya’s rule is **simple skeleton, rich cognition.**

And it stays honest: maya maps and conjectures — leads you can chase, with the
checkable pieces verified by sound checks against independent ground truth. It never
claims certainty.
