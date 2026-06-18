# maya

**An autonomous discovery engine that gives an AI agent a *subconscious*.**

You ask a question in `input.md` and tell your AI agent **“read input.md and execute it.”**

The AI is the **conscious** mind: it researches your question on the web,
deliberately. But everything it reads pours into a persistent **subconscious** — one
associative memory that keeps accumulating across *every* question you ever ask,
links ideas between distant domains, and lets new conjectures surface from those
connections, the way a human mind makes sense of things in the background. maya maps
and conjectures, and verifies the checkable pieces in a sealed playground — it never
claims to have proved anything.

---

## Run it

1. Install an AI coding agent — [Claude Code](https://claude.com/claude-code) or [Codex](https://github.com/openai/codex) — and Python 3.9+ with `numpy`.
2. Open the agent in this folder.
3. Put your question under `## Topic` in `input.md`.
4. Say: **read input.md and execute it**

Watch `ideas.md` (conjectures) and `questions.md` (open doubts) fill in. The
subconscious itself persists in `~/.cache/maya/graph/` — and it’s **global**: every
question you ever ask feeds one shared, cross-domain memory, which is where the
surprising bridges come from.

---

## The whole system

| file | role |
| --- | --- |
| `input.md` | your question + the standing protocol — the only file you edit |
| `maya.py` | the tool calls — the whole interface |
| `memory.py` | the global associative graph — the **subconscious** |
| `verifier.py` | the sealed playground for self-written checks |
| `ideas.md` | conjectures, for human review |
| `questions.md` | open doubts (add your own to steer it) |
| `architecture.md` | how and why it works |

Three code files. The cognition is the agent; the skeleton is small and readable.

---

## How it works

Point a capable coding agent at it — [Claude Code](https://claude.com/claude-code)
or [Codex](https://github.com/openai/codex). The agent runs the **conscious** loop
(researching) that constantly feeds the **subconscious** (the graph) — **observe →
associate → doubt → dream → verify → curiosity** — all through `maya`’s tool calls:

- **observe** a cited claim → it becomes concepts + a weighted, Hebbian-reinforced edge.
- **associate** the links you see → analogies, patterns, contradictions (kept, never deleted).
- **ask** a doubt → it jumps to the top of the frontier and gets chased first.
- **dream** at the frontier → novel connections become conjectures in `ideas.md`.
- **verify** a checkable piece → write code, run it sealed (no network, time/memory limits).

The subconscious is an 8-layer typed graph with a vector index and spreading
activation. Every write is **idempotent** (re-running reinforces, never duplicates),
so the loop is safe to repeat. See [`architecture.md`](architecture.md) for the full design.

---

## Philosophy

Inspired by Karpathy’s [autoresearch](https://github.com/karpathy/autoresearch):
instructions + an agent that reads them and loops, with the heavy machinery in a
tiny, fixed substrate. maya’s rule is **simple skeleton, rich cognition.**

And it stays honest: maya maps and conjectures — leads you can chase, with the
checkable pieces verified by sound checks against independent ground truth. It never
claims certainty.

---

## License

[MIT](LICENSE) © 2026 c0mpli
