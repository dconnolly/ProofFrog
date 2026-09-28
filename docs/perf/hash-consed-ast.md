# Hash and copy prototype

## Design

AST equality ignores source locations and provenance. `Game` also ignores its
name, while `Reduction` compares its composition. `Tuple` and `ProductType`
compare equal across classes when their elements match. Any structural hash
used to reject equality must follow these rules.

The AST remains mutable. Transforms assign fields and mutate child lists, and
some copy nodes with `copy.copy` before changing their attributes. Caching a
parent hash after a child changes would make an equality rejection unsound.
This prototype caches hashes only for scalar leaves. Attribute assignment or
deletion clears a leaf's cached hash; source metadata does not. Nodes remain
unhashable as Python dictionary keys because their semantic values can change.
Pickling drops the cache because Python salts string hashes separately in
each worker process.

Inlining now shares statement suffixes while it scans them. Its replacement
transformer creates new nodes along a changed path. Method inlining shallow
copies each block's statement list before editing it, so it no longer needs
to deep copy the whole game on every inlining iteration. The method lookup
dictionary also gets a shallow copy; an invoked method is still deep copied
before substitution.

## Implemented

- Cache scalar leaf structural hashes and reject equality on a hash mismatch.
- Short circuit equality on identity for base AST nodes and custom equality
  classes.
- Share read-only suffixes in `RedundantCopy` and
  `InlineSingleUseVariable`.
- Copy each block before `InlineTransformer` edits its statements, then share
  the unchanged game tree during repeated inlining.

## Left to do

- Cache structural hashes for composite nodes. This needs a way to observe
  descendant mutation, including list edits, or an immutable AST boundary.
- Evaluate hash consing for leaves after their creation and provenance rules
  are settled. The prototype does not intern nodes.
- Audit the remaining deep copies in other transforms before sharing them.

## Measurements

The fixture is the 790-line, nine-oracle pivot game. A copy of its FrogLang
imports lives under `/private/tmp/prooffrog-pivot-fixture` because the CLI
creates a temporary proof next to its input. The source was loaded through
`PYTHONPATH`; the interpreter was the installed pipx Python. The baseline
source was an archive of this branch's original `HEAD`. Both source variants
used the same copied fixture.

| Run | Baseline real (s) | Baseline user (s) | Prototype real (s) | Prototype user (s) |
|---|---:|---:|---:|---:|
| 1 | 47.17 | 36.70 | 50.13 | 37.47 |
| 2 | 143.27 | 48.92 | 39.08 | 34.19 |
| 3 | 146.16 | 48.67 | 37.99 | 32.13 |

The machine shared its CPU with other jobs. Wall time varied widely; the
median user CPU time fell from 48.67 to 34.19 seconds (29.8%). The baseline
run 1 was faster than either later baseline run, so this is a directional
result rather than a stable speedup estimate.

| cProfile counter | Baseline | Prototype |
|---|---:|---:|
| `copy.deepcopy` calls | 32,330,007 | 9,489,354 |
| `copy.deepcopy` cumulative time | 63.067 s | 13.274 s |
| Base AST `__eq__` calls | 1,894,315 | 1,762,401 |
| Base AST `__eq__` self time | 2.318 s | 0.697 s |

Deep copy calls fell 70.6%; base AST equality calls fell 7.0%. The new
`structural_hash` method ran 1,540,150 times. In the baseline profile,
`InlineSingleUseVariable` made 982 direct deep copy calls
costing 22.899 s cumulative; `RedundantCopy` made 414 costing 10.326 s.
Profile elapsed times were affected by concurrent work; call counts are the
more reliable comparison.

The saved canonical outputs, including the final profile output, match byte
for byte. Three KEM proofs
(`KEMPRF_Correctness`, `KEMPRF_INDCPA`, `KEMPRF_INDCCA`) and the Group proof
`GapCDH_implies_GapCDH_NZ` proved with byte-identical CLI output in the
baseline and prototype. `pytest tests -q -x` passed: 2,917 tests passed and
six skipped.
