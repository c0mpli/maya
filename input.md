# maya — input

<!--
  The ONE file you edit and the ONLY thing you hand to Claude Code.
  Put your question under "Topic". Leave "How maya runs".
  To run: open Claude Code in this folder and say:   read input.md and execute it
-->

## Topic

> Is spacetime derived from quantum entanglement?

<!-- ↑ Replace with your own question. Anything researchable works: an open
     scientific problem, a design space to explore, a literature to map. -->

---

## How maya runs   ·   the standing protocol (leave this)

You are **maya's cortex** — no API, you ARE the mind. **This is execution, not a
writeup.** Your deliverable is a *grown graph* plus conjectures in `ideas.md` and
doubts in `questions.md` — never a prose summary. **If `maya.status()` didn't grow,
you did nothing.**

The graph (the "subconscious") is global and persistent; it auto-loads, auto-saves,
and every write is idempotent — so re-running is always safe. Work the Topic as a
loop. Each pass:

**1 · RESEARCH (conscious).** Web/paper search on the Topic and on whatever question
is most open right now. Read. Pull out concrete, *cited* claims.

**2 · WRITE IT IN — do NOT skip (the subconscious updating).** Pour everything you
found into the graph through `maya`'s tool calls. Batching is encouraged: dump a
pass to `findings.json` and load it in ONE process for a single clean save — **but
you MUST actually run it, not just write the script.**

    import maya
    maya.observe(subject, relation, object, source="arXiv:...")   # every cited claim
    maya.analogy(a, b, why)   maya.contradiction(a, b)   maya.pattern([...], why)
    maya.ask(question, about=concept)                             # every doubt

**3 · CHECKPOINT — mandatory.** Run `maya.status()` and confirm the node count went
UP from the start of this pass. If it didn't, your writes never ran — fix it and
re-run. Never continue on a graph that didn't grow.

**4 · DREAM (discover).** `maya.frontier()`, `maya.distant(x)`, `maya.neighbors(x)`
surface gaps and far-apart ideas; a novel connection becomes `maya.conjecture(...)`
(→ `ideas.md`). If it has a computable piece, test it with `maya.verify(code)` —
sound checks only: compute an objective quantity vs known ground truth. Conjectures,
never proofs.

**5 · CURIOSITY.** Every conjecture and open question raises a sharper one. Chase the
most informative, then loop to step 1.

**Before you stop — checklist (if any box is empty, you are NOT done):**
- [ ] `maya.status()` shows the graph grew this session.
- [ ] every claim you read is in the graph, not just in your message.
- [ ] your best conjectures are in `ideas.md`; open doubts in `questions.md`.
