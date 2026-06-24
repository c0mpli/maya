# Contributions

Real, externally-verifiable output produced by running maya — not claims, not benchmarks.
Each entry links to work someone other than maya can check.

maya maps and conjectures; where an *exact oracle* exists (here, the Lean / mathlib kernel)
it climbs toward results that are **machine-checked**. This page logs the ones that left the
machine — and stays honest about what they are and aren't.

---

## Lean / mathlib formalization

### formal-conjectures #4304 — graph-invariant proofs

[google-deepmind/formal-conjectures#4304](https://github.com/google-deepmind/formal-conjectures/pull/4304)
· submitted 2026-06-23 · **open PR, under review** · +269 / −18 across 3 files

Closes **18 of the 27 `sorry`s** in `WrittenOnTheWallII/Test.lean` (the concrete
graph-invariant test suite) and adds **three reusable, mathlib-quality lemmas**.
`lake --wfail build` passes — every proof is kernel-checked.

| Invariant | Closed | Method |
|---|---|---|
| `ediam` (diameter) | 5/5 | `ediam_eq_computable` bridge + `decide +native` |
| `radius` | 5/5 | `radius_eq_computable` bridge + `decide +native` |
| `girth` | 3/5 | explicit cycle / acyclicity |
| `matchingNumber` | 5/5 | `matching_card_bound` + explicit witnesses |

**Reusable lemmas** (added to `FormalConjecturesForMathlib`, plausible mathlib upstream):

- `ediam_eq_computable` / `radius_eq_computable` / `eccent_eq_computable` — express the
  `ℕ∞`-valued diameter / radius / eccentricity of a finite connected graph as a *decidable*
  max / min of BFS distances, so these invariants become `decide`-able.
- `matching_card_bound` — `2 · |M| ≤ |V|` for any matching `M` (a matching has at most
  `⌊|V|/2⌋` edges). Fully general, existing-mathlib API only.

**Honest scope.** This is **new formalization + reusable lemmas, not new mathematics** — the
invariant values were already known; the contribution is the machine-checked proofs and the
general lemmas (the part most likely to be reused). The PR is **open / under review**, not
merged. The remaining `sorry`s are left open and noted in the PR: `C6` / `Petersen` girth
(a girth *lower* bound needs cycle enumeration), `cvetkovic` (spectral — eigenvalues over ℝ),
and `Star5` average-degree / residue.

**Why it matters here.** This is the first output of maya's hard-oracle loop: take an
oracle-backed target, turn the Lean check into a climbable hill (close gaps until zero), and
ship only what the kernel accepts. Exactly the DISCOVERY-mode path the engine is for.

---

*Next entry goes above this line as it lands.*
