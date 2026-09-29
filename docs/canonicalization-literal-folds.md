# Literal condition folds

## Symptom

Inlining a protocol scheme's `Send`/`Recv` on literal states leaves conditions that are compile-time constants.
The canonical form kept three shapes:

```
if (!(false)) { ... } else { ... }
if (0 >= 1) { ... } else { ... }
if (None == [[1, true, x, None, y, 1], [a, b]]) { return None; }
```

`BranchElimination` removes a branch only when its condition is the literal `true` or `false`.
No pass reduced these three shapes to a literal.
Two games that differed only in such dead branches failed to canonicalize together.
The hop then failed with "Branch not eliminated: no condition is a compile-time constant".

## Change

A new core pass, `FoldLiteralConditions` (`proof_frog/transforms/control_flow.py`), rewrites these expressions anywhere in a game:

| Input | Result |
|---|---|
| `!true`, `!false` | `false`, `true` |
| `a < b`, `a > b`, `a <= b`, `a >= b` with integer literals `a`, `b` | the literal truth value |
| `a == b`, `a != b` with boolean literals `a`, `b` | the literal truth value |
| `a == a`, `a != a` with integer literal `a` | `true`, `false` |
| `None == L`, `L == None` | `false` |
| `None != L`, `L != None` | `true` |

`L` must be a tuple, set, integer, boolean, `0b...`, or `0^n`/`1^n` literal.
`L` must contain no call, map/array index, or slice.

The pass runs just before `BranchElimination` in `CORE_PIPELINE`.
`BranchElimination` then drops the dead branches in the same iteration.

The pass does not fold:

- `None` against a variable, a call, or any other non-literal expression.
  Deciding those needs types; `DeadNullGuardElimination` owns them.
- `==`/`!=` on distinct integer literals, such as `0 == 1`.
- A literal whose evaluation makes a call or indexes a value.

## Soundness

Each rewrite replaces an expression with a literal of the same value on every execution.

- **Negation.** `!true` is `false` and `!false` is `true` in every Boolean model.
- **Integer order.** The type checker accepts `<`, `>`, `<=`, `>=` only on `Int` operands.
  It rejects them on `ModInt<q>`, so no ordered literal comes from a modular slot.
  Two `Int` literals compare as Python integers, so the pass uses Python's comparison.
- **Integer equality.** An `Int` literal may flow into a `ModInt<q>` slot (the type checker accepts the coercion) and later be inlined into an equality.
  Mod `q`, distinct literals can be equal (`5 == 0` in `ModInt<5>`).
  Equal literals are equal under any modulus, so the pass folds only that case.
- **Boolean equality.** `Bool` has exactly the two literal values.
- **None versus a literal.** A tuple, set, integer, boolean, or bitstring literal evaluates to a value of a non-optional type.
  A tuple literal is non-`None` even when a component is `None`.
  So `None == L` is always false.
  Folding also drops the evaluation of `L`.
  `L` makes no call and indexes nothing, so that evaluation has no effect.
  `RemoveEmptyIf` uses the same effect-free test.

No fold reads a type map, a variable's definition, or a call's return type.
Each decision rests on the syntax of the literal operands.

## Tests

- `tests/unit/transforms/test_fold_literal_conditions.py`
  - Each fold, both operand orders for `None`, nested folds.
  - Non-folds: non-literal operands, `0 == 1`, `None == v`, `None == F.f(x)`, `None == x + y`, `None == M[k]`, literals containing a call, index, or slice, and `None == None`.
  - The fold followed by `BranchElimination` removes all three dead-branch shapes.
- `tests/integration/test_fold_literal_conditions.py`, through `ProofEngine.check_equivalent`:
  - A game guarded by the three shapes and one with none are accepted as equivalent.
    Upstream `main` rejects this pair.
  - Literal conditions that select the other branch are rejected.
  - `[x, b] != None` guarding a `return None` is rejected against the unguarded game.
  - `None == y` with `y` an `Int?` argument is not folded; the pair is rejected.
  - `Bool? v` set to `None` or `false` on every path: `v != true` folds, and the game equals one that returns the first branch.
    Upstream `main` rejects this pair.
  - The same guard on a `Bool?` argument is not folded; the pair is rejected.
- `tests/unit/typechecking/test_modint_type_checking.py`: `<`, `>`, `<=`, `>=` on `ModInt<q>` fail type checking, against a `ModInt<q>` or an `Int` literal.

The motivating toy (`ToyUnfold.proof`, an eight-step unfold of a KEM+AEAD protocol) failed steps 1 and 8.
With this pass all eight steps pass.
