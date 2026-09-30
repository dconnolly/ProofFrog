"""IfSplitBranchAssignment on nested if-else leaves.

An inlined oracle with early returns assigns its result slot in every leaf
of a nested if-else, then tests the slot.
Splitting the tail into every leaf turns that into direct early returns.
Positive pairs need the nested split (upstream rejects them); negative pairs
are inequivalent and must stay rejected.
"""

from __future__ import annotations

import pytest
from sympy import Symbol

from proof_frog import frog_parser
from proof_frog.proof_engine import ProofEngine


def _engine() -> ProofEngine:
    prim = frog_parser.parse_primitive_file("""
        Primitive P(Int n) {
            Int Draw(Int x);
            deterministic Int Eval(Int x);
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
            Int count;
            Int Initialize() {{
                count = 0;
                return 0;
            }}
            Int Query(Int a, Int b) {{
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


# The inlined shape: a result slot assigned in every nested leaf, then tested.
_NESTED = """
    Int v;
    if (count >= q) {
        v = 0;
    } else {
        count = count + 1;
        if (a == b) {
            v = 1;
        } else {
            v = PP.Eval(a);
        }
    }
    if (v == 0) {
        return 7;
    }
    return v;
"""

_EARLY = """
    if (count >= q) {
        return 7;
    }
    count = count + 1;
    if (a == b) {
        return 1;
    }
    if (PP.Eval(a) == 0) {
        return 7;
    }
    return PP.Eval(a);
"""


def test_nested_leaves_fold_into_early_returns() -> None:
    assert _equivalent(_NESTED, _EARLY)


def test_three_level_nesting_folds() -> None:
    left = """
        Int v;
        if (count >= q) {
            v = 0;
        } else {
            count = count + 1;
            if (a == b) {
                v = 1;
            } else {
                if (a < b) {
                    v = 2;
                } else {
                    v = PP.Eval(b);
                }
            }
        }
        return v + 1;
    """
    right = """
        if (count >= q) {
            return 1;
        }
        count = count + 1;
        if (a == b) {
            return 2;
        }
        if (a < b) {
            return 3;
        }
        return PP.Eval(b) + 1;
    """
    assert _equivalent(left, right)


def test_nondeterministic_leaf_used_once_folds() -> None:
    left = """
        Int v;
        if (count >= q) {
            v = 0;
        } else {
            count = count + 1;
            if (a == b) {
                v = 1;
            } else {
                v = PP.Draw(a);
            }
        }
        return v;
    """
    right = """
        if (count >= q) {
            return 0;
        }
        count = count + 1;
        if (a == b) {
            return 1;
        }
        return PP.Draw(a);
    """
    assert _equivalent(left, right)


# Soundness: each right side is NOT equivalent to its left side.
_NEGATIVE = {
    # One leaf value differs from the early-return form.
    "different_leaf_value": (
        _NESTED,
        _EARLY.replace("return 1;", "return 2;"),
    ),
    # A leaf that does not assign keeps v's earlier value (3), not 1.
    "leaf_does_not_assign": (
        """
        Int v = 3;
        if (count >= q) {
            v = 0;
        } else {
            count = count + 1;
            if (a == b) {
                count = count + 1;
            } else {
                v = PP.Eval(a);
            }
        }
        return v;
        """,
        """
        if (count >= q) {
            return 0;
        }
        count = count + 1;
        if (a == b) {
            count = count + 1;
            return 1;
        }
        return PP.Eval(a);
        """,
    ),
    # A leaf that assigns another variable leaves v at 3.
    "leaf_assigns_other_variable": (
        """
        Int v = 3;
        Int w = 3;
        if (count >= q) {
            v = 0;
        } else {
            count = count + 1;
            if (a == b) {
                w = 1;
            } else {
                v = PP.Eval(a);
            }
        }
        return v + w;
        """,
        """
        if (count >= q) {
            return 3;
        }
        count = count + 1;
        if (a == b) {
            return 2;
        }
        return PP.Eval(a) + 3;
        """,
    ),
    # The tail writes count, which a leaf value reads, before testing v.
    "tail_writes_leaf_free_variable": (
        """
        Int v;
        if (count >= q) {
            v = 0;
        } else {
            if (a == b) {
                v = count;
            } else {
                v = PP.Eval(a);
            }
        }
        count = count + 1;
        if (v == 0) {
            return 7;
        }
        return v;
        """,
        """
        if (count >= q) {
            count = count + 1;
            return 7;
        }
        if (a == b) {
            count = count + 1;
            if (count == 0) {
                return 7;
            }
            return count;
        }
        count = count + 1;
        if (PP.Eval(a) == 0) {
            return 7;
        }
        return PP.Eval(a);
        """,
    ),
    # The tail writes v between the leaves and the test.
    "tail_writes_slot": (
        """
        Int v;
        if (count >= q) {
            v = 0;
        } else {
            count = count + 1;
            if (a == b) {
                v = 1;
            } else {
                v = PP.Eval(a);
            }
        }
        v = v + 1;
        if (v == 1) {
            return 7;
        }
        return v;
        """,
        """
        if (count >= q) {
            return 1;
        }
        count = count + 1;
        if (a == b) {
            return 1;
        }
        if (PP.Eval(a) == 1) {
            return 7;
        }
        return PP.Eval(a);
        """,
    ),
    # A non-deterministic leaf value read twice: substitution would draw twice.
    "nondeterministic_leaf_read_twice": (
        """
        Int v;
        if (count >= q) {
            v = 0;
        } else {
            count = count + 1;
            if (a == b) {
                v = 1;
            } else {
                v = PP.Draw(a);
            }
        }
        return v - v;
        """,
        """
        if (count >= q) {
            return 0;
        }
        count = count + 1;
        if (a == b) {
            return 0;
        }
        return PP.Draw(a) - PP.Draw(a);
        """,
    ),
}


@pytest.mark.parametrize("name", sorted(_NEGATIVE))
def test_inequivalent_nested_shapes_stay_rejected(name: str) -> None:
    left, right = _NEGATIVE[name]
    assert not _equivalent(left, right)
