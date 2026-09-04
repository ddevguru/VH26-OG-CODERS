from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from core.common.models import Span


@dataclass
class ASTNode:
    span: Span


@dataclass
class Parameter(ASTNode):
    name: str
    default_value: Optional['Expression'] = None


@dataclass
class Expression(ASTNode):
    pass


@dataclass
class Statement(ASTNode):
    pass


@dataclass
class BlockStmt(Statement):
    statements: List[Statement] = field(default_factory=list)


@dataclass
class FunctionDeclaration(ASTNode):
    name: str
    parameters: List[Parameter] = field(default_factory=list)
    body: Optional[BlockStmt] = None
    is_async: bool = False


@dataclass
class ClassDeclaration(ASTNode):
    name: str
    methods: List[FunctionDeclaration] = field(default_factory=list)


@dataclass
class Module(ASTNode):
    statements: List[Statement] = field(default_factory=list)
    functions: List[FunctionDeclaration] = field(default_factory=list)
    classes: List[ClassDeclaration] = field(default_factory=list)


# --- Statements ---

@dataclass
class ExpressionStmt(Statement):
    expression: Expression


@dataclass
class AssignmentStmt(Statement):
    target: Expression
    value: Expression


@dataclass
class IfStmt(Statement):
    condition: Expression
    then_branch: Statement
    elif_branches: List[Tuple[Expression, Statement]] = field(default_factory=list)
    else_branch: Optional[Statement] = None


@dataclass
class WhileStmt(Statement):
    condition: Expression
    body: Statement


@dataclass
class ForStmt(Statement):
    target: Expression
    iterable: Expression
    body: Statement


@dataclass
class WithItem(ASTNode):
    context_expr: Expression
    optional_vars: Optional[Expression] = None


@dataclass
class WithStmt(Statement):
    items: List[WithItem] = field(default_factory=list)
    body: BlockStmt = field(default_factory=lambda: BlockStmt(span=None))  # type: ignore
    is_async: bool = False


@dataclass
class ExceptHandler(ASTNode):
    type_name: Optional[str]
    var_name: Optional[str]
    body: BlockStmt


@dataclass
class TryStmt(Statement):
    body: BlockStmt
    handlers: List[ExceptHandler] = field(default_factory=list)
    else_block: Optional[BlockStmt] = None
    finally_block: Optional[BlockStmt] = None


@dataclass
class ReturnStmt(Statement):
    expression: Optional[Expression] = None


@dataclass
class RaiseStmt(Statement):
    expression: Optional[Expression] = None


@dataclass
class BreakStmt(Statement):
    pass


@dataclass
class ContinueStmt(Statement):
    pass


# --- Expressions ---

@dataclass
class LiteralExpr(Expression):
    value: str
    literal_type: str


@dataclass
class IdentifierExpr(Expression):
    name: str


@dataclass
class AttributeAccessExpr(Expression):
    object_expr: Expression
    attribute_name: str


@dataclass
class CallExpr(Expression):
    function: Expression
    arguments: List[Expression] = field(default_factory=list)


@dataclass
class BinaryExpr(Expression):
    left: Expression
    operator: str
    right: Expression


@dataclass
class UnknownExpr(Expression):
    raw_text: str
