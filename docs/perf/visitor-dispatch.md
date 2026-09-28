# Visitor dispatch prototype

Checked 2026-09-27 on branch `perf/visitor-dispatch`. The worktree uses ProofFrog
`b6c73dd7c80324ecac4d79e0cc7b8c642f22e33c` and the examples submodule
`fe33f8fa71a15c3e24421d86194435974546bd10`. Both matched their remote
HEADs when checked. The installed checker reported `0.6.1.dev0 (750f53b)`;
measurements used
`/Users/dconnolly/.local/pipx/venvs/proof-frog/bin/python` with this worktree
on `PYTHONPATH`. `git submodule update --init` could not write the shared Git
metadata outside the sandbox, but `examples` was present at the required pin.

## Design and implementation

`Visitor.visit` now uses one dispatch table per visitor class. Each table maps
AST classes to unbound visit and leave methods, resolving node base classes
through the MRO and then the generic `*_ast_node` hook. A class introduced
after table construction gets a lazy entry. The existing visitor classes have
the same dispatch targets under the old and new lookup rules.

A child-field map covers all 65 built-in AST classes. Visitor and transformer
descent reads only fields that can contain nodes, including optional fields and
tuple-valued fields. Unknown AST subclasses retain the dynamic `vars()` walk.
The copy-on-write transformer already returned unchanged parents by identity;
it now records and sets only fields whose transformed child changed.

`__slots__` remains open. A source search found no production code adding
undeclared AST fields, but `ASTNode.__eq__` deliberately compares instance
`__dict__` key sets, and other walkers still use `vars()`. Slots need a
separate equality and walker change to preserve malformed-node behavior. The
benchmark script now checks the CLI's JSON `success` field so an
error cannot appear as a fast run. A deprecated `typing.Hashable` import was
also replaced with `collections.abc.Hashable` to satisfy the repository's
pylint gate.

## Measurements

The benchmark canonicalizes one side of the 791-line, nine-oracle pivot game.
The CLI writes a temporary proof beside its input, so the source proof tree was
copied to `/private/tmp/visitor-dispatch-bench-proofs` for this sandbox. The
unmodified external tree is read-only here. The CPU was shared with other
jobs; wall times are individual runs, not an isolated speedup estimate.

| Version | Wall times (seconds) | Process user times (seconds) |
| --- | --- | --- |
| Before | 53.39, 61.84, 63.71 | 38.05, 45.49, 45.81 |
| After | 44.54, 32.97, 61.75 | 28.52, 26.14, 29.98 |

Median wall time fell from 61.84 to 44.54 seconds (28%). Median process user
time fell from 45.49 to 28.52 seconds (37%). The wall-time variation is large
because other jobs shared the CPU.

A full cProfile canonicalization was stopped after 392 seconds of wall time
without completing. For comparable visitor counts, the focused profile parsed
the same 791-line game and repeated 40 counting visits and 40 identity
transforms. It visited 120,000 nodes in each version. The table reports
cProfile self time and call counts for this focused workload.

| Function | Before calls / self seconds | After calls / self seconds |
| --- | ---: | ---: |
| `visit_helper` | 120,000 / 0.310 | 120,000 / 0.082 |
| `visit_children` | 576,680 / 0.225 | 143,760 / 0.038 |
| `_cow_transform_child` | 576,680 / 0.237 | 143,760 / 0.041 |
| `_transform_children` | 120,000 / 0.198 | 120,000 / 0.045 |
| `_lookup_visitor_methods` | 120,000 / 0.035 | 70 / <0.001 |

| Builtin | Before calls | After calls |
| --- | ---: | ---: |
| `isinstance` | 6,383,555 | 4,531,915 |
| `getattr` | 1,104,517 | 239,099 |
| `vars` | 245,367 | 5,367 |
| `dict.get` | 2,429,692 | 2,669,741 |

The focused profile's total measured time was 12.636 seconds before and 7.750
seconds after. Parsing and unrelated library calls are included in those totals.

## Validation and limits

The pivot canonical form and CLI output matched byte for byte before and
after. The canonical form's SHA-256 was
`679d0cbaeb281068182bfc2c4c51474e3a78ee6641c0db1110d746472c2ef76b`.
A dynamic traversal of 7,317 nodes from the pivot game and four KEM proofs
found no child field missing from the fixed map. `pytest tests -q -x` passed
with 2,916 tests and 6 skips. The four KEM proofs and
`DDH_implies_CDH.proof` succeeded with byte-identical CLI output before and
after. `make lint` passed (black, mypy, pylint, and TypeScript). The
map-reindex tests passed after the `Hashable` import change (23 tests).

## Fix

The review found that 1,000 calls to `referenced_variables_in_order` left
1,000 visitor tables and 65,000 dispatch entries in this branch. The helper
defined its visitor class on every call. Four other production helpers also
defined visitor classes inside functions. All five visitor classes now live at
module scope.

The visitor cache now holds at most 128 class tables. The transformer lookup
caches hold at most 4,096 method entries and 128 fallback entries. Cached
methods use weak references so a method that closes over its class cannot
keep that class alive through the cache value. A callable that cannot be
weakly referenced is resolved without caching. After 1,000 and 2,000 calls
to `referenced_variables_in_order`, the cache held one table with 65 entries
both times. A regression test also creates transient visitor and transformer
classes and checks that evicted classes can be collected.

Two runs of `bench/pivot_inline_bench.sh` on the shared CPU gave these times:

| Version | Wall times (seconds) | Process user times (seconds) |
| --- | --- | --- |
| Before fix | 22.44, 22.32 | 21.17, 20.96 |
| After fix | 24.34, 22.46 | 22.70, 20.87 |

The second post-fix run matched the baseline range. The first took about two
seconds longer; the shared CPU limits what two samples can establish.
The pivot CLI returned success, and its JSON output matched the pre-fix output
byte for byte (SHA-256
`9c53aa91fc2bfd0c00401deb37ca3a81e231127372dee8ed6452b5ce84776ca2`).
`pytest tests -q -x` passed with 2,918 tests and 6 skips. `make lint` passed.
