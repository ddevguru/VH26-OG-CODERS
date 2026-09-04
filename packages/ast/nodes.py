from dataclasses import dataclass, field
from typing import List, Optional
from packages.common.models import Span


@dataclass
class ASTNode:
    span: Span


# --- Declarations ---

@dataclass
class Parameter(ASTNode):
    type_name: str
    name: str


@dataclass
class Expression(ASTNode):
    pass


@dataclass
class Statement(ASTNode):
    pass


@dataclass
class MethodDeclaration(ASTNode):
    name: str
    return_type: str
    parameters: List[Parameter] = field(default_factory=list)
    body: Optional['BlockStmt'] = None
    throws_types: List[str] = field(default_factory=list)


@dataclass
class ClassDeclaration(ASTNode):
    name: str
    methods: List[MethodDeclaration] = field(default_factory=list)


@dataclass
class CompilationUnit(ASTNode):
    package_name: Optional[str] = None
    imports: List[str] = field(default_factory=list)
    types: List[ClassDeclaration] = field(default_factory=list)


# --- Statements ---

@dataclass
class BlockStmt(Statement):
    statements: List[Statement] = field(default_factory=list)


@dataclass
class ExpressionStmt(Statement):
    expression: Expression


@dataclass
class LocalVarDeclStmt(Statement):
    type_name: str
    var_name: str
    initializer: Optional[Expression] = None


@dataclass
class IfStmt(Statement):
    condition: Expression
    then_branch: Statement
    else_branch: Optional[Statement] = None


@dataclass
class WhileStmt(Statement):
    condition: Expression
    body: Statement


@dataclass
class ForStmt(Statement):
    init: Optional[ASTNode] = None
    condition: Optional[Expression] = None
    update: Optional[ASTNode] = None
    body: Optional[Statement] = None


@dataclass
class EnhancedForStmt(Statement):
    var_type: str
    var_name: str
    iterable: Expression
    body: Statement


@dataclass
class CatchClause(ASTNode):
    param_type: str
    param_name: str
    body: BlockStmt


@dataclass
class TryStmt(Statement):
    body: BlockStmt
    catch_clauses: List[CatchClause] = field(default_factory=list)
    finally_block: Optional[BlockStmt] = None


@dataclass
class TryWithResourcesStmt(Statement):
    resources: List[LocalVarDeclStmt] = field(default_factory=list)
    body: BlockStmt = field(default_factory=lambda: BlockStmt(span=None))  # type: ignore
    catch_clauses: List[CatchClause] = field(default_factory=list)
    finally_block: Optional[BlockStmt] = None


@dataclass
class ReturnStmt(Statement):
    expression: Optional[Expression] = None


@dataclass
class ThrowStmt(Statement):
    expression: Expression


@dataclass
class BreakStmt(Statement):
    label: Optional[str] = None


@dataclass
class ContinueStmt(Statement):
    label: Optional[str] = None


# --- Expressions ---

@dataclass
class LiteralExpr(Expression):
    value: str
    literal_type: str


@dataclass
class IdentifierExpr(Expression):
    name: str


@dataclass
class MemberAccessExpr(Expression):
    object_expr: Expression
    member_name: str


@dataclass
class MethodInvocationExpr(Expression):
    target: Optional[Expression]
    method_name: str
    arguments: List[Expression] = field(default_factory=list)


@dataclass
class ObjectCreationExpr(Expression):
    type_name: str
    arguments: List[Expression] = field(default_factory=list)


@dataclass
class AssignmentExpr(Expression):
    target: Expression
    value: Expression
    operator: str = "="


@dataclass
class BinaryExpr(Expression):
    left: Expression
    operator: str
    right: Expression


@dataclass
class CastExpr(Expression):
    target_type: str
    expression: Expression


@dataclass
class UnknownExpr(Expression):
    raw_text: str
