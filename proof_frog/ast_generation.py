from typing import Type
from parsing.PrimitiveVisitor import PrimitiveVisitor
from parsing.PrimitiveParser import PrimitiveParser
from parsing.SchemeVisitor import SchemeVisitor
from parsing.SchemeParser import SchemeParser
from parsing.GameVisitor import GameVisitor
from parsing.GameParser import GameParser
import frog_ast


def _binary_operation(
        operator: frog_ast.BinaryOperators, visit: Type[PrimitiveVisitor.visit],
        ctx: Type[PrimitiveParser.ExpressionContext]) -> frog_ast.BinaryOperation:
    return frog_ast.BinaryOperation(
        operator,
        visit(ctx.expression()[0]),
        visit(ctx.expression()[1])
    )


class SharedAST(PrimitiveVisitor, SchemeVisitor):  # type: ignore[misc] # pylint: disable=too-many-public-methods

    def visitParamList(self, ctx: PrimitiveParser.ParamListContext) -> list[frog_ast.Parameter]:
        result = []
        for variable in ctx.variable():
            result.append(frog_ast.Parameter(super().visit(variable.type_()),
                          variable.id_().getText()))
        return result

    def visitUserType(self, ctx: PrimitiveParser.UserTypeContext) -> frog_ast.UserType:
        return frog_ast.UserType([id.getText() for id in ctx.id_()])

    def visitOptionalType(self, ctx: PrimitiveParser.OptionalTypeContext) -> frog_ast.Type:
        the_type: frog_ast.Type = self.visit(ctx.type_())
        the_type.optional = True
        return the_type

    def visitBoolType(self, __: PrimitiveParser.BoolTypeContext) -> frog_ast.Type:
        return frog_ast.Type(frog_ast.BasicTypes.BOOL)

    def visitBitStringType(self, ctx: PrimitiveParser.BitStringTypeContext) -> frog_ast.BitStringType:
        if not ctx.bitstring().integerExpression():
            return frog_ast.BitStringType()
        return frog_ast.BitStringType(self.visit(ctx.bitstring().integerExpression()))

    def visitProductType(self, ctx: PrimitiveParser.ProductTypeContext) -> frog_ast.ProductType:
        return frog_ast.ProductType(list(self.visit(individualType) for individualType in ctx.type_()))

    def visitSetType(self, ctx: PrimitiveParser.SetTypeContext) -> frog_ast.SetType:
        return frog_ast.SetType(self.visit(ctx.set_().type_()) if ctx.set_().type_() else None)

    def visitField(self, ctx: PrimitiveParser.FieldContext) -> frog_ast.Field:
        return frog_ast.Field(
            self.visit(ctx.variable().type_()),
            ctx.variable().id_().getText(),
            self.visit(ctx.expression()) if ctx.expression() else None)

    def visitInitializedField(self, ctx: PrimitiveParser.InitializedFieldContext) -> frog_ast.Field:
        return frog_ast.Field(
            self.visit(ctx.variable().type_()),
            ctx.variable().id_().getText(),
            self.visit(ctx.expression()))

    def visitEqualsExp(self, ctx: PrimitiveParser.EqualsExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.EQUALS, self.visit, ctx)

    def visitNotEqualsExp(self, ctx: PrimitiveParser.NotEqualsExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.NOTEQUALS, self.visit, ctx)

    def visitGtExp(self, ctx: PrimitiveParser.GtExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.GT, self.visit, ctx)

    def visitLtExp(self, ctx: PrimitiveParser.LtExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.LT, self.visit, ctx)

    def visitGeqExp(self, ctx: PrimitiveParser.GeqExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.GEQ, self.visit, ctx)

    def visitLeqExp(self, ctx: PrimitiveParser.LeqExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.LEQ, self.visit, ctx)

    def visitAndExp(self, ctx: PrimitiveParser.AndExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.AND, self.visit, ctx)

    def visitSubsetsExp(self, ctx: PrimitiveParser.SubsetsExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.SUBSETS, self.visit, ctx)

    def visitInExp(self, ctx: PrimitiveParser.InExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.IN, self.visit, ctx)

    def visitOrExp(self, ctx: PrimitiveParser.OrExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.OR, self.visit, ctx)

    def visitUnionExp(self, ctx: PrimitiveParser.UnionExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.UNION, self.visit, ctx)

    def visitSetMinusExp(self, ctx: PrimitiveParser.SetMinusExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.SETMINUS, self.visit, ctx)

    def visitAddExp(self, ctx: PrimitiveParser.AddExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.ADD, self.visit, ctx)

    def visitSubtractExp(self, ctx: PrimitiveParser.SubtractExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.SUBTRACT, self.visit, ctx)

    def visitMultiplyExp(self, ctx: PrimitiveParser.MultiplyExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.MULTIPLY, self.visit, ctx)

    def visitDivideExp(self, ctx: PrimitiveParser.DivideExpContext) -> frog_ast.BinaryOperation:
        return _binary_operation(frog_ast.BinaryOperators.DIVIDE, self.visit, ctx)

    def visitCreateSetExp(self, ctx: PrimitiveParser.CreateSetExpContext) -> frog_ast.Set:
        return frog_ast.Set([self.visit(element) for element in ctx.expression()] if ctx.expression() else [])

    def visitMethod(self, ctx: PrimitiveParser.MethodContext) -> frog_ast.Method:
        statements = [self.visit(statement) for statement in ctx.methodBody().statement()]
        return frog_ast.Method(self.visit(ctx.methodSignature()), statements)

    def visitIntegerExpression(
            self, ctx: PrimitiveParser.IntegerExpressionContext) -> frog_ast.Expression:

        if ctx.INT():
            return frog_ast.Integer(int(ctx.INT().getText()))
        if ctx.lvalue():
            exp: frog_ast.Expression = self.visit(ctx.lvalue())
            return exp

        operator: frog_ast.BinaryOperators
        if ctx.PLUS():
            operator = frog_ast.BinaryOperators.ADD
        elif ctx.SUBTRACT():
            operator = frog_ast.BinaryOperators.SUBTRACT
        elif ctx.TIMES():
            operator = frog_ast.BinaryOperators.MULTIPLY
        elif ctx.DIVIDE():
            operator = frog_ast.BinaryOperators.DIVIDE

        return frog_ast.BinaryOperation(
            operator,
            self.visit(ctx.integerExpression()[0]),
            self.visit(ctx.integerExpression()[1])
        )

    def visitVarDeclWithValueStatement(
            self, ctx: PrimitiveParser.VarDeclWithValueStatementContext) -> frog_ast.Assignment:
        return frog_ast.Assignment(
            self.visit(ctx.type_()),
            self.visit(ctx.lvalue()),
            self.visit(ctx.expression())
        )

    def visitAssignmentStatement(self, ctx: PrimitiveParser.AssignmentStatementContext) -> frog_ast.Assignment:
        return frog_ast.Assignment(
            None,
            self.visit(ctx.lvalue()),
            self.visit(ctx.expression())
        )

    def visitSampleStatement(self, ctx: PrimitiveParser.SampleStatementContext) -> frog_ast.Sample:
        return frog_ast.Sample(
            None,
            self.visit(ctx.lvalue()),
            self.visit(ctx.expression())
        )

    def visitNumericForStatement(self, ctx: PrimitiveParser.NumericForStatementContext) -> frog_ast.NumericFor:
        return frog_ast.NumericFor(
            ctx.id_().getText(),
            self.visit(ctx.expression()[0]),
            self.visit(ctx.expression()[1]),
            self.visit(ctx.block())
        )

    def visitGenericForStatement(self, ctx: PrimitiveParser.GenericForStatementContext) -> frog_ast.GenericFor:
        return frog_ast.GenericFor(
            self.visit(ctx.type_()),
            ctx.id_().getText(),
            self.visit(ctx.expression()),
            self.visit(ctx.block()))

    def visitIntExp(self, ctx: PrimitiveParser.IntExpContext) -> frog_ast.Integer:
        return frog_ast.Integer(int(ctx.INT().getText()))

    def visitBinaryNumExp(self, ctx: PrimitiveParser.BinaryNumExpContext) -> frog_ast.BinaryNum:
        return frog_ast.BinaryNum(int(ctx.BINARYNUM().getText(), 2))

    def visitVarDeclWithSampleStatement(
            self, ctx: PrimitiveParser.VarDeclWithSampleStatementContext) -> frog_ast.Sample:
        return frog_ast.Sample(
            self.visit(ctx.type_()),
            self.visit(ctx.lvalue()),
            self.visit(ctx.expression())
        )

    def visitVarDeclStatement(self, ctx: PrimitiveParser.VarDeclStatementContext) -> frog_ast.VariableDeclaration:
        return frog_ast.VariableDeclaration(
            self.visit(ctx.type_()),
            ctx.id_().getText()
        )

    def visitArrayType(self, ctx: PrimitiveParser.ArrayTypeContext) -> frog_ast.ArrayType:
        return frog_ast.ArrayType(self.visit(ctx.type_()), self.visit(ctx.integerExpression()))

    def visitMapType(self, ctx: PrimitiveParser.MapTypeContext) -> frog_ast.MapType:
        return frog_ast.MapType(self.visit(ctx.type_()[0]), self.visit(ctx.type_()[1]))

    def visitNotExp(self, ctx: PrimitiveParser.NotExpContext) -> frog_ast.UnaryOperation:
        return frog_ast.UnaryOperation(
            frog_ast.UnaryOperators.NOT,
            self.visit(ctx.expression())
        )

    def visitIntType(self, ctx: PrimitiveParser.IntTypeContext) -> frog_ast.Type:
        return frog_ast.Type(frog_ast.BasicTypes.INT)

    def visitSizeExp(self, ctx: PrimitiveParser.SizeExpContext) -> frog_ast.UnaryOperation:
        return frog_ast.UnaryOperation(
            frog_ast.UnaryOperators.SIZE,
            self.visit(ctx.expression())
        )

    def visitNoneExp(self, __: PrimitiveParser.NoneExpContext) -> frog_ast.ASTNone:
        return frog_ast.ASTNone()

    def visitParenExp(self, ctx: PrimitiveParser.ParenExpContext) -> frog_ast.Expression:
        exp: frog_ast.Expression = self.visit(ctx.expression())
        return exp

    def visitLvalue(self, ctx: PrimitiveParser.LvalueExpContext) -> frog_ast.Expression:
        expression: frog_ast.Expression = frog_ast.Variable(ctx.id_()[0].getText())

        i = 1
        while i < ctx.getChildCount():
            if ctx.getChild(i).getText() == '.':
                expression = frog_ast.FieldAccess(expression, ctx.getChild(i+1).getText())
                i += 2
            else:
                index_expression: frog_ast.Expression = self.visit(ctx.getChild(i+1))
                expression = frog_ast.ArrayAccess(expression, index_expression)
                i += 3

        return expression

    def visitCreateTupleExp(self, ctx: PrimitiveParser.CreateTupleExpContext) -> frog_ast.Tuple:
        return frog_ast.Tuple([self.visit(exp) for exp in ctx.expression()])

    def visitReturnStatement(self, ctx: PrimitiveParser.ReturnStatementContext) -> frog_ast.ReturnStatement:
        return frog_ast.ReturnStatement(self.visit(ctx.expression()))

    def visitFunctionCallStatement(
            self, ctx: PrimitiveParser.FunctionCallStatementContext) -> frog_ast.FuncCallStatement:
        return frog_ast.FuncCallStatement(
            self.visit(ctx.expression()),
            self.visit(ctx.argList()) if ctx.argList() else []
        )

    def visitFnCallExp(self, ctx: PrimitiveParser.FnCallExpContext) -> frog_ast.FuncCallExpression:
        return frog_ast.FuncCallExpression(
            self.visit(ctx.expression()),
            self.visit(ctx.argList()) if ctx.argList() else [])

    def visitSliceExp(self, ctx: PrimitiveParser.SliceExpContext) -> frog_ast.Slice:
        return frog_ast.Slice(
            self.visit(ctx.expression()),
            self.visit(ctx.integerExpression()[0]),
            self.visit(ctx.integerExpression()[1]))

    def visitArgList(self, ctx: PrimitiveParser.ArgListContext) -> list[frog_ast.Expression]:
        return [self.visit(exp) for exp in ctx.expression()]

    def visitLvalueExp(self, ctx: PrimitiveParser.LvalueExpContext) -> frog_ast.Expression:
        exp: frog_ast.Expression = self.visit(ctx.lvalue())
        return exp

    def visitMethodSignature(self, ctx: PrimitiveParser.MethodSignatureContext) -> frog_ast.MethodSignature:
        return frog_ast.MethodSignature(
            ctx.id_().getText(),
            self.visit(ctx.type_()),
            [] if not ctx.paramList() else self.visit(ctx.paramList()))

    def visitModuleImport(self, ctx: PrimitiveParser.ModuleImportContext) -> frog_ast.Import:
        return frog_ast.Import(ctx.FILESTRING().getText().strip("'"), ctx.ID().getText() if ctx.ID() else "")

    def visitBlock(self, ctx: PrimitiveParser.BlockContext) -> list[frog_ast.Statement]:
        return [self.visit(statement) for statement in ctx.statement()]

    def visitIfStatement(self, ctx: PrimitiveParser.IfStatementContext) -> frog_ast.IfStatement:
        return frog_ast.IfStatement([self.visit(exp) for exp in ctx.expression()],
                                    [self.visit(block) for block in ctx.block()])

    def visitGame(self, ctx: PrimitiveParser.GameContext) -> frog_ast.Game:
        name = ctx.ID().getText()
        param_list = self.visit(ctx.paramList()) if ctx.paramList() else []
        field_list = []
        if ctx.gameBody().field():
            for field in ctx.gameBody().field():
                field_list.append(self.visit(field))
        methods = []
        if ctx.gameBody().method():
            for method in ctx.gameBody().method():
                methods.append(self.visit(method))

        return frog_ast.Game(name, param_list, field_list, methods)


class PrimitiveASTGenerator(SharedAST, PrimitiveVisitor):  # type: ignore[misc]
    def visitProgram(self, ctx: PrimitiveParser.ProgramContext) -> frog_ast.Primitive:
        name = ctx.ID().getText()
        param_list = [] if not ctx.paramList() else self.visit(ctx.paramList())
        field_list = []
        if ctx.primitiveBody().initializedField():
            for field in ctx.primitiveBody().initializedField():
                field_list.append(self.visit(field))

        method_list = []
        if ctx.primitiveBody().methodSignature():
            for method_signature in ctx.primitiveBody().methodSignature():
                method_list.append(self.visit(method_signature))

        return frog_ast.Primitive(name, param_list, field_list, method_list)


class SchemeASTGenerator(SharedAST, SchemeVisitor):  # type: ignore[misc]
    def visitProgram(self, ctx: SchemeParser.ProgramContext) -> frog_ast.Scheme:
        scheme_ctx = ctx.scheme()

        imports = [self.visit(im) for im in ctx.moduleImport()]

        name = scheme_ctx.ID()[0].getText()
        param_list = [] if not scheme_ctx.paramList() else self.visit(scheme_ctx.paramList())
        primitive_name = scheme_ctx.ID()[1].getText()
        field_list = []
        requirement_list = []
        method_list = []

        if scheme_ctx.schemeBody().field():
            for field in scheme_ctx.schemeBody().field():
                field_list.append(self.visit(field))
        if scheme_ctx.schemeBody().REQUIRES():
            for requirement in scheme_ctx.schemeBody().expression():
                requirement_list.append(self.visit(requirement))
        for method in scheme_ctx.schemeBody().method():
            method_list.append(self.visit(method))

        return frog_ast.Scheme(imports, name, param_list, primitive_name, field_list, requirement_list, method_list)


class GameASTGenerator(SharedAST, GameVisitor):  # type: ignore[misc]
    def visitProgram(self, ctx: GameParser.ProgramContext) -> frog_ast.GameFile:
        imports = [self.visit(im) for im in ctx.moduleImport()]
        game1: frog_ast.Game = self.visit(ctx.game()[0])
        game2: frog_ast.Game = self.visit(ctx.game()[1])
        return frog_ast.GameFile(imports, (game1, game2), ctx.gameExport().ID().getText())
