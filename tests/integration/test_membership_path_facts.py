"""Membership path facts in GuardConditionSimplification.

After ``if (x in S) { ...; return ...; }``, or inside a branch on ``x in S``,
a later test ``x in S`` folds to its known value until a write to ``x`` or
``S``.
Positive pairs need the fold (upstream rejects them); negative pairs are
inequivalent and must stay rejected.
"""

from __future__ import annotations

import pytest
from sympy import Symbol

from proof_frog import frog_parser
from proof_frog.proof_engine import ProofEngine


def _engine() -> ProofEngine:
    prim = frog_parser.parse_primitive_file("""
        Primitive P(Int n) {
            BitString<n> Draw(BitString<n> x);
            deterministic BitString<n> Eval(BitString<n> x);
        }
        """)
    engine = ProofEngine()
    engine.variables["n"] = Symbol("n", positive=True, integer=True)
    engine.proof_namespace["P"] = prim
    engine.proof_namespace["PP"] = prim
    return engine


def _game(name: str, body: str) -> str:
    return f"""
        Game {name}(P PP, Int q) {{
            Set<BitString<n>> S;
            Set<BitString<n>> T;
            Map<BitString<n>, BitString<n>> M;
            [Set<BitString<n>>, Int] U;
            Int count;
            Void Initialize() {{
                count = 0;
            }}
            Void Add(BitString<n> a) {{
                S = S union a;
                M[a] = a;
                U = [U[0] union a, U[1]];
            }}
            Void AddT(BitString<n> a) {{
                T = T union a;
            }}
            BitString<n>? Query(BitString<n> a, BitString<n> b, Bool c) {{
                {body}
            }}
        }}
        """


def _equivalent(left: str, right: str) -> bool:
    result = _engine().check_equivalent(
        frog_parser.parse_game(_game("Left", left)),
        frog_parser.parse_game(_game("Right", right)),
    )
    return bool(result.valid)


def test_early_return_fact_folds_later_test() -> None:
    left = """
        if (a in S) {
            return None;
        }
        if (count >= q) {
            return b;
        }
        count = count + 1;
        if (a in S) {
            return a;
        }
        return PP.Eval(a);
    """
    right = """
        if (a in S) {
            return None;
        }
        if (count >= q) {
            return b;
        }
        count = count + 1;
        return PP.Eval(a);
    """
    assert _equivalent(left, right)


def test_early_return_fact_folds_nested_if_else() -> None:
    """The inlined-oracle shape: the nested test has an else branch."""
    left = """
        if (a in S) {
            return None;
        }
        BitString<n>? v;
        if (count >= q) {
            v = None;
        } else {
            count = count + 1;
            if (a in S) {
                v = a;
            } else {
                v = PP.Eval(a);
            }
        }
        return v;
    """
    right = """
        if (a in S) {
            return None;
        }
        if (count >= q) {
            return None;
        }
        count = count + 1;
        return PP.Eval(a);
    """
    assert _equivalent(left, right)


def test_negated_early_return_fact_folds_to_true() -> None:
    left = """
        if (!(a in S)) {
            return None;
        }
        count = count + 1;
        if (a in S) {
            return a;
        }
        return b;
    """
    right = """
        if (!(a in S)) {
            return None;
        }
        count = count + 1;
        return a;
    """
    assert _equivalent(left, right)


def test_taken_branch_fact_holds_until_write() -> None:
    """A write to S after the nested test does not block the fold."""
    left = """
        if (a in S) {
            count = count + 1;
            BitString<n> r;
            if (a in S) {
                r = a;
            } else {
                r = b;
            }
            S = S union b;
            return r;
        }
        return None;
    """
    right = """
        if (a in S) {
            count = count + 1;
            S = S union b;
            return a;
        }
        return None;
    """
    assert _equivalent(left, right)


def test_map_membership_fact_folds() -> None:
    left = """
        if (a in M) {
            return M[a];
        }
        if (count >= q) {
            return b;
        }
        count = count + 1;
        if (a in M) {
            return b;
        }
        return a;
    """
    right = """
        if (a in M) {
            return M[a];
        }
        if (count >= q) {
            return b;
        }
        count = count + 1;
        return a;
    """
    assert _equivalent(left, right)


def _drop_pair(write: str, test: str = "a in S") -> tuple[str, str]:
    """Left re-tests after *write*; right drops the re-test as if it folded."""
    left = f"""
        if (a in S) {{
            return None;
        }}
        {write}
        if ({test}) {{
            return a;
        }}
        return b;
    """
    right = f"""
        if (a in S) {{
            return None;
        }}
        {write}
        return b;
    """
    return left, right


# Soundness: each right side is NOT equivalent to its left side.
_NEGATIVE = {
    "plain_write_to_set": _drop_pair("S = S union b;"),
    "write_in_nested_branch": _drop_pair("if (c) { S = S union b; }"),
    "write_in_loop": _drop_pair("for (Int i = 0 to 2) { S = S union b; }"),
    "uniq_growth": _drop_pair(
        "BitString<n> y <-uniq[S] BitString<n>; count = count + 1;"
    ),
    "x_reassigned": _drop_pair("a = b;"),
    "different_x": _drop_pair("count = count + 1;", "b in S"),
    "different_set": _drop_pair("count = count + 1;", "a in T"),
    "map_fact_vs_set_test": (
        """
        if (a in M) {
            return None;
        }
        count = count + 1;
        if (a in S) {
            return a;
        }
        return b;
        """,
        """
        if (a in M) {
            return None;
        }
        count = count + 1;
        return b;
        """,
    ),
    "map_element_write": (
        """
        if (a in M) {
            return None;
        }
        M[b] = a;
        if (a in M) {
            return a;
        }
        return b;
        """,
        """
        if (a in M) {
            return None;
        }
        M[b] = a;
        return b;
        """,
    ),
    "tuple_element_write": (
        """
        if (a in U[0]) {
            return None;
        }
        U[0] = U[0] union b;
        if (a in U[0]) {
            return a;
        }
        return b;
        """,
        """
        if (a in U[0]) {
            return None;
        }
        U[0] = U[0] union b;
        return b;
        """,
    ),
    "taken_branch_write_before_test": (
        """
        if (a in S) {
            return None;
        } else {
            S = S union b;
            if (a in S) {
                return a;
            }
            return b;
        }
        """,
        """
        if (a in S) {
            return None;
        }
        S = S union b;
        return b;
        """,
    ),
    "nondeterministic_element": (
        """
        if (PP.Draw(a) in S) {
            return None;
        }
        if (PP.Draw(a) in S) {
            return a;
        }
        return b;
        """,
        """
        if (PP.Draw(a) in S) {
            return None;
        }
        return b;
        """,
    ),
}


@pytest.mark.parametrize("name", sorted(_NEGATIVE))
def test_inequivalent_membership_retests_stay_rejected(name: str) -> None:
    left, right = _NEGATIVE[name]
    assert not _equivalent(left, right)
