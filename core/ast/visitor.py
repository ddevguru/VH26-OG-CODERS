import ast
from typing import List, Tuple, Optional, Any
from core.common.models import SourceLocation, Span
from core.scopes.scope_manager import ScopeManager, ScopeType, Scope
from core.symbols.table import Symbol, SymbolTable


class AstFunctionCollector(ast.NodeVisitor):
    """Walks a Python stdlib ast.AST module and collects all function definitions (functions & methods)."""

    def __init__(self) -> None:
        self.functions: List[Tuple[ast.AST, str]] = []  # List of (ast.FunctionDef/AsyncFunctionDef, scope_name)
        self.current_scope: List[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        scope = ".".join(self.current_scope) if self.current_scope else "global"
        self.functions.append((node, scope))
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        scope = ".".join(self.current_scope) if self.current_scope else "global"
        self.functions.append((node, scope))
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()


class LeakGuardAstVisitor(ast.NodeVisitor):
    """Comprehensive AST visitor tracking scope hierarchy, symbol bindings, references, reads, writes, and aliases."""

    def __init__(self, scope_manager: Optional[ScopeManager] = None) -> None:
        self.scope_manager = scope_manager or ScopeManager()
        self.functions: List[Tuple[ast.AST, str]] = []
        self.classes: List[Tuple[ast.ClassDef, str]] = []
        self.imports: List[Tuple[str, Optional[str], Span]] = []

    @staticmethod
    def get_span(node: ast.AST) -> Span:
        line = getattr(node, "lineno", 1)
        col = getattr(node, "col_offset", 0) + 1
        end_line = getattr(node, "end_lineno", line)
        end_col = getattr(node, "end_col_offset", col - 1) + 1
        return Span(
            start=SourceLocation(line=line, column=col),
            end=SourceLocation(line=end_line, column=end_col)
        )

    def visit_Module(self, node: ast.Module) -> None:
        # Module root
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        span = self.get_span(node)
        scope_name = node.name
        self.classes.append((node, self.scope_manager.current_scope.fully_qualified_name))
        
        # Decorators evaluation (in outer scope)
        for dec in node.decorator_list:
            self.visit(dec)

        # Base classes evaluation (in outer scope)
        for base in node.bases:
            self.visit(base)
        for kw in node.keywords:
            self.visit(kw.value)

        # Declare class name in parent scope
        sym = Symbol(
            name=node.name,
            scope_name=self.scope_manager.current_scope.fully_qualified_name,
            declaration_span=span,
        )
        self.scope_manager.current_scope.symbol_table.insert(sym)

        # Push CLASS scope
        self.scope_manager.push_scope(scope_name, ScopeType.CLASS)
        for stmt in node.body:
            self.visit(stmt)
        self.scope_manager.pop_scope()

    def _visit_function(self, node: ast.AST, is_async: bool) -> None:
        func_name = getattr(node, "name", "<function>")
        span = self.get_span(node)
        
        # Decorators evaluation (in outer scope)
        for dec in getattr(node, "decorator_list", []):
            self.visit(dec)

        # Function defaults evaluation (in outer scope)
        args_node: ast.arguments = getattr(node, "args")
        for default in args_node.defaults:
            if default:
                self.visit(default)
        for kw_default in args_node.kw_defaults:
            if kw_default:
                self.visit(kw_default)

        # Declare function symbol in current scope
        sym = Symbol(
            name=func_name,
            scope_name=self.scope_manager.current_scope.fully_qualified_name,
            declaration_span=span,
        )
        self.scope_manager.current_scope.symbol_table.insert(sym)
        self.functions.append((node, self.scope_manager.current_scope.fully_qualified_name))

        # Push Function scope
        stype = ScopeType.ASYNC_FUNCTION if is_async else ScopeType.FUNCTION
        self.scope_manager.push_scope(func_name, stype)

        # Process function parameters in function scope
        all_args: List[ast.arg] = args_node.args + args_node.kwonlyargs
        if args_node.vararg:
            all_args.append(args_node.vararg)
        if args_node.kwarg:
            all_args.append(args_node.kwarg)

        for arg in all_args:
            arg_span = self.get_span(arg)
            annotation_str = ast.unparse(arg.annotation) if getattr(arg, "annotation", None) else None
            param_sym = Symbol(
                name=arg.arg,
                scope_name=self.scope_manager.current_scope.fully_qualified_name,
                type_annotation=annotation_str,
                declaration_span=arg_span,
            )
            self.scope_manager.current_scope.symbol_table.insert(param_sym)
            self.scope_manager.declare_variable(arg.arg)

        # Visit function body statements
        for stmt in getattr(node, "body", []):
            self.visit(stmt)

        self.scope_manager.pop_scope()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node, is_async=True)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        span = self.get_span(node)
        self.scope_manager.push_scope("<lambda>", ScopeType.LAMBDA)
        
        # Process arguments
        for arg in node.args.args + node.args.kwonlyargs:
            arg_span = self.get_span(arg)
            param_sym = Symbol(
                name=arg.arg,
                scope_name=self.scope_manager.current_scope.fully_qualified_name,
                declaration_span=arg_span,
            )
            self.scope_manager.current_scope.symbol_table.insert(param_sym)
            self.scope_manager.declare_variable(arg.arg)

        self.visit(node.body)
        self.scope_manager.pop_scope()

    def visit_Global(self, node: ast.Global) -> None:
        for name in node.names:
            self.scope_manager.declare_global(name)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        for name in node.names:
            self.scope_manager.declare_nonlocal(name)

    def visit_Import(self, node: ast.Import) -> None:
        span = self.get_span(node)
        for alias in node.names:
            bound_name = alias.asname or alias.name.split('.')[0]
            sym = Symbol(
                name=bound_name,
                scope_name=self.scope_manager.current_scope.fully_qualified_name,
                declaration_span=span,
            )
            self.scope_manager.current_scope.symbol_table.insert(sym)
            self.imports.append((alias.name, alias.asname, span))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        span = self.get_span(node)
        module_name = node.module or ""
        for alias in node.names:
            bound_name = alias.asname or alias.name
            sym = Symbol(
                name=bound_name,
                scope_name=self.scope_manager.current_scope.fully_qualified_name,
                declaration_span=span,
            )
            self.scope_manager.current_scope.symbol_table.insert(sym)
            full_imp = f"{module_name}.{alias.name}" if module_name else alias.name
            self.imports.append((full_imp, alias.asname, span))

    def visit_Assign(self, node: ast.Assign) -> None:
        span = self.get_span(node)
        self.visit(node.value)

        # Alias tracking if assigning a simple variable to another variable (a = b)
        rhs_name = node.value.id if isinstance(node.value, ast.Name) else None

        for target in node.targets:
            self._handle_target(target, span, rhs_name)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        span = self.get_span(node)
        if node.value:
            self.visit(node.value)
        rhs_name = node.value.id if isinstance(node.value, ast.Name) else None
        annotation_str = ast.unparse(node.annotation) if node.annotation else None
        self._handle_target(node.target, span, rhs_name, type_annotation=annotation_str)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        span = self.get_span(node)
        self.visit(node.value)
        if isinstance(node.target, ast.Name):
            var_name = node.target.id
            self.scope_manager.current_scope.symbol_table.add_read(var_name, span)
            self.scope_manager.current_scope.symbol_table.add_write(var_name, span)
        else:
            self.visit(node.target)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        # Walrus operator :=
        span = self.get_span(node)
        self.visit(node.value)
        rhs_name = node.value.id if isinstance(node.value, ast.Name) else None
        self._handle_target(node.target, span, rhs_name)

    def _handle_target(self, target: ast.AST, span: Span, rhs_name: Optional[str] = None, type_annotation: Optional[str] = None) -> None:
        if isinstance(target, ast.Name):
            var_name = target.id
            self.scope_manager.declare_variable(var_name)
            sym = Symbol(
                name=var_name,
                scope_name=self.scope_manager.current_scope.fully_qualified_name,
                type_annotation=type_annotation,
                declaration_span=span,
            )
            self.scope_manager.current_scope.symbol_table.insert(sym)
            self.scope_manager.current_scope.symbol_table.add_assignment(var_name, span)
            self.scope_manager.current_scope.symbol_table.add_write(var_name, span)
            if rhs_name:
                self.scope_manager.current_scope.symbol_table.add_alias(var_name, rhs_name)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._handle_target(elt, span, rhs_name=None, type_annotation=type_annotation)
        elif isinstance(target, ast.Attribute):
            self.visit(target.value)
        elif isinstance(target, ast.Subscript):
            self.visit(target.value)
            self.visit(target.slice)

    def visit_Name(self, node: ast.Name) -> None:
        span = self.get_span(node)
        var_name = node.id
        if isinstance(node.ctx, ast.Load):
            self.scope_manager.current_scope.symbol_table.add_read(var_name, span)
            # Check outer scopes if not in current scope symbol table
            sym = self.scope_manager.resolve_symbol(var_name)
            if sym and sym.scope_name != self.scope_manager.current_scope.fully_qualified_name:
                # Upward scope read reference
                pass
        elif isinstance(node.ctx, (ast.Store, ast.Param)):
            self.scope_manager.declare_variable(var_name)
            self.scope_manager.current_scope.symbol_table.add_assignment(var_name, span)
            self.scope_manager.current_scope.symbol_table.add_write(var_name, span)

    def _visit_comprehension(self, generators: List[ast.comprehension], elt_or_val: List[ast.AST]) -> None:
        self.scope_manager.push_scope("<comprehension>", ScopeType.COMPREHENSION)
        for gen in generators:
            self.visit(gen.iter)
            span = self.get_span(gen.target)
            self._handle_target(gen.target, span)
            for if_clause in gen.ifs:
                self.visit(if_clause)
        for item in elt_or_val:
            self.visit(item)
        self.scope_manager.pop_scope()

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node.generators, [node.elt])

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node.generators, [node.elt])

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension(node.generators, [node.key, node.value])

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension(node.generators, [node.elt])

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                span = self.get_span(item.optional_vars)
                self._handle_target(item.optional_vars, span)
        for stmt in node.body:
            self.visit(stmt)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                span = self.get_span(item.optional_vars)
                self._handle_target(item.optional_vars, span)
        for stmt in node.body:
            self.visit(stmt)

    def visit_For(self, node: ast.For) -> None:
        span = self.get_span(node.target)
        self.visit(node.iter)
        self._handle_target(node.target, span)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        span = self.get_span(node.target)
        self.visit(node.iter)
        self._handle_target(node.target, span)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_Match(self, node: ast.Match) -> None:
        # Python 3.10+ match statement
        self.visit(node.subject)
        for case in node.cases:
            if case.guard:
                self.visit(case.guard)
            for stmt in case.body:
                self.visit(stmt)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type:
            self.visit(node.type)
        if node.name:
            span = self.get_span(node)
            self._handle_target(ast.Name(id=node.name, ctx=ast.Store()), span)
        for stmt in node.body:
            self.visit(stmt)
