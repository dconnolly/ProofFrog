"""Visitor dispatch and structural child traversal regressions."""

from proof_frog import frog_ast, visitors


class _GameNames(visitors.Visitor[list[str]]):
    def __init__(self) -> None:
        self.names: list[str] = []

    def result(self) -> list[str]:
        return self.names

    def visit_game(self, node: frog_ast.Game) -> None:
        self.names.append(node.name)


class _VariableNames(visitors.Visitor[list[str]]):
    def __init__(self) -> None:
        self.names: list[str] = []

    def result(self) -> list[str]:
        return self.names

    def visit_variable(self, node: frog_ast.Variable) -> None:
        self.names.append(node.name)


def test_dispatch_falls_back_to_node_base_class() -> None:
    reduction = frog_ast.Reduction(
        ("R", [], [], []),
        frog_ast.ParameterizedGame("G", []),
        frog_ast.ParameterizedGame("A", []),
    )
    assert _GameNames().visit(reduction) == ["R"]


def test_visitor_descends_through_optional_and_tuple_children() -> None:
    first = frog_ast.Game(("First", [], [], []))
    second = frog_ast.Game(("Second", [], [], []))
    game_file = frog_ast.GameFile([], (first, second), "Pair")
    assert _GameNames().visit(game_file) == ["First", "Second"]

    field = frog_ast.Field(frog_ast.IntType(), "f", None)
    assert _VariableNames().visit(field) == []
    field.value = frog_ast.Variable("x")
    assert _VariableNames().visit(field) == ["x"]


def test_custom_node_keeps_dynamic_children() -> None:
    class Extension(frog_ast.ASTNode):
        def __init__(self) -> None:
            super().__init__()
            self.child = frog_ast.Variable("x")

    node = Extension()
    assert _VariableNames().visit(node) == ["x"]
    transformed = visitors.ReplaceTransformer(
        node.child, frog_ast.Variable("y")
    ).transform(node)
    assert transformed is not node
    assert transformed.child.name == "y"
