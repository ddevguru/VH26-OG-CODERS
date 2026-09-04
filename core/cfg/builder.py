import ast
from typing import List, Optional, Tuple, Union
from core.cfg.graph import CFG, CFGBlock, EdgeType


class CFGBuilder:
    """Builds intra-procedural Control Flow Graphs (CFG) with exact exception handling, context manager cleanup, and match/case branching."""

    def __init__(self) -> None:
        self.next_block_id = 0
        self.blocks: List[CFGBlock] = []

    def create_block(self, is_entry: bool = False, is_exit: bool = False, is_exceptional_exit: bool = False) -> CFGBlock:
        block = CFGBlock(
            block_id=self.next_block_id,
            is_entry=is_entry,
            is_exit=is_exit,
            is_exceptional_exit=is_exceptional_exit,
        )
        self.next_block_id += 1
        self.blocks.append(block)
        return block

    def build_cfg(self, func: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> CFG:
        self.next_block_id = 0
        self.blocks = []

        entry_block = self.create_block(is_entry=True)
        exit_block = self.create_block(is_exit=True)
        exceptional_exit_block = self.create_block(is_exceptional_exit=True)

        cfg = CFG(
            method_name=func.name,
            entry_block=entry_block,
            exit_block=exit_block,
            exceptional_exit_block=exceptional_exit_block,
            blocks=self.blocks,
        )

        if not func.body:
            cfg.add_edge(entry_block, exit_block, EdgeType.EXIT)
            return cfg

        current_block = entry_block
        final_block = self._build_statements(
            statements=func.body,
            current_block=current_block,
            cfg=cfg,
            loop_stack=[],
            try_stack=[],
            with_stack=[],
        )

        if final_block and not any(e.edge_type in (EdgeType.EXIT, EdgeType.RETURN) for e in final_block.outgoing):
            cfg.add_edge(final_block, exit_block, EdgeType.EXIT)

        return cfg

    def _build_statements(
        self,
        statements: List[ast.stmt],
        current_block: CFGBlock,
        cfg: CFG,
        loop_stack: List[Tuple[CFGBlock, CFGBlock]],
        try_stack: List[Tuple[List[CFGBlock], Optional[CFGBlock]]],
        with_stack: List[CFGBlock],
    ) -> Optional[CFGBlock]:

        curr = current_block

        for stmt in statements:
            if curr is None:
                curr = self.create_block()

            if isinstance(stmt, ast.If):
                curr = self._build_if_stmt(stmt, curr, cfg, loop_stack, try_stack, with_stack)

            elif isinstance(stmt, (ast.While, ast.For, getattr(ast, "AsyncFor", ast.For))):
                curr = self._build_loop_stmt(stmt, curr, cfg, loop_stack, try_stack, with_stack)

            elif isinstance(stmt, (ast.With, getattr(ast, "AsyncWith", ast.With))):
                curr = self._build_with_stmt(stmt, curr, cfg, loop_stack, try_stack, with_stack)

            elif isinstance(stmt, (ast.Try, getattr(ast, "TryStar", ast.Try))):
                curr = self._build_try_stmt(stmt, curr, cfg, loop_stack, try_stack, with_stack)

            elif isinstance(stmt, getattr(ast, "Match", ast.AST)):
                curr = self._build_match_stmt(stmt, curr, cfg, loop_stack, try_stack, with_stack)

            elif isinstance(stmt, ast.Return):
                curr.add_statement(stmt)
                self._handle_early_exit(curr, cfg.exit_block, cfg, try_stack, with_stack, edge_type=EdgeType.RETURN)
                curr = None

            elif isinstance(stmt, ast.Raise):
                curr.add_statement(stmt)
                self._handle_exception_exit(curr, cfg.exceptional_exit_block, cfg, try_stack, with_stack)
                curr = None

            elif isinstance(stmt, ast.Break):
                curr.add_statement(stmt)
                if loop_stack:
                    _, loop_exit = loop_stack[-1]
                    self._handle_early_exit(curr, loop_exit, cfg, try_stack, with_stack, edge_type=EdgeType.BREAK)
                curr = None

            elif isinstance(stmt, ast.Continue):
                curr.add_statement(stmt)
                if loop_stack:
                    loop_header, _ = loop_stack[-1]
                    self._handle_early_exit(curr, loop_header, cfg, try_stack, with_stack, edge_type=EdgeType.CONTINUE)
                curr = None

            else:
                curr.add_statement(stmt)
                if any(isinstance(node, ast.Call) for node in ast.walk(stmt)):
                    self._handle_exception_exit(curr, cfg.exceptional_exit_block, cfg, try_stack, with_stack)
                    next_block = self.create_block()
                    cfg.add_edge(curr, next_block, EdgeType.NORMAL)
                    curr = next_block

        return curr

    def _build_if_stmt(
        self,
        stmt: ast.If,
        current_block: CFGBlock,
        cfg: CFG,
        loop_stack: List[Tuple[CFGBlock, CFGBlock]],
        try_stack: List[Tuple[List[CFGBlock], Optional[CFGBlock]]],
        with_stack: List[CFGBlock],
    ) -> CFGBlock:
        current_block.add_statement(ast.Expr(value=stmt.test, lineno=getattr(stmt, 'lineno', 1), col_offset=getattr(stmt, 'col_offset', 0)))

        then_block = self.create_block()
        merge_block = self.create_block()

        cfg.add_edge(current_block, then_block, EdgeType.TRUE_BRANCH, label="true")

        then_end = self._build_statements(
            statements=stmt.body,
            current_block=then_block,
            cfg=cfg,
            loop_stack=loop_stack,
            try_stack=try_stack,
            with_stack=with_stack,
        )
        if then_end:
            cfg.add_edge(then_end, merge_block, EdgeType.NORMAL)

        if stmt.orelse:
            else_block = self.create_block()
            cfg.add_edge(current_block, else_block, EdgeType.FALSE_BRANCH, label="false")

            else_end = self._build_statements(
                statements=stmt.orelse,
                current_block=else_block,
                cfg=cfg,
                loop_stack=loop_stack,
                try_stack=try_stack,
                with_stack=with_stack,
            )
            if else_end:
                cfg.add_edge(else_end, merge_block, EdgeType.NORMAL)
        else:
            cfg.add_edge(current_block, merge_block, EdgeType.FALSE_BRANCH, label="false")

        return merge_block

    def _build_loop_stmt(
        self,
        stmt: ast.stmt,
        current_block: CFGBlock,
        cfg: CFG,
        loop_stack: List[Tuple[CFGBlock, CFGBlock]],
        try_stack: List[Tuple[List[CFGBlock], Optional[CFGBlock]]],
        with_stack: List[CFGBlock],
    ) -> CFGBlock:
        header_block = self.create_block()
        body_block = self.create_block()
        exit_block = self.create_block()

        cfg.add_edge(current_block, header_block, EdgeType.NORMAL)

        if isinstance(stmt, ast.While):
            header_block.add_statement(ast.Expr(value=stmt.test, lineno=getattr(stmt, 'lineno', 1), col_offset=getattr(stmt, 'col_offset', 0)))
            body = stmt.body
        else:  # For / AsyncFor
            header_block.add_statement(ast.Expr(value=stmt.iter, lineno=getattr(stmt, 'lineno', 1), col_offset=getattr(stmt, 'col_offset', 0)))  # type: ignore
            body = stmt.body  # type: ignore

        cfg.add_edge(header_block, body_block, EdgeType.TRUE_BRANCH, label="loop_body")

        if stmt.orelse:  # type: ignore
            else_block = self.create_block()
            cfg.add_edge(header_block, else_block, EdgeType.FALSE_BRANCH, label="loop_else")
            else_end = self._build_statements(
                statements=stmt.orelse,  # type: ignore
                current_block=else_block,
                cfg=cfg,
                loop_stack=loop_stack,
                try_stack=try_stack,
                with_stack=with_stack,
            )
            if else_end:
                cfg.add_edge(else_end, exit_block, EdgeType.NORMAL)
        else:
            cfg.add_edge(header_block, exit_block, EdgeType.FALSE_BRANCH, label="loop_exit")

        new_loop_stack = loop_stack + [(header_block, exit_block)]

        body_end = self._build_statements(
            statements=body,
            current_block=body_block,
            cfg=cfg,
            loop_stack=new_loop_stack,
            try_stack=try_stack,
            with_stack=with_stack,
        )

        if body_end:
            cfg.add_edge(body_end, header_block, EdgeType.LOOP_BACK, label="loop_back")

        return exit_block

    def _build_with_stmt(
        self,
        stmt: Union[ast.With, getattr(ast, "AsyncWith", ast.With)],  # type: ignore
        current_block: CFGBlock,
        cfg: CFG,
        loop_stack: List[Tuple[CFGBlock, CFGBlock]],
        try_stack: List[Tuple[List[CFGBlock], Optional[CFGBlock]]],
        with_stack: List[CFGBlock],
    ) -> CFGBlock:
        enter_block = self.create_block()
        with_body_entry = self.create_block()
        exit_context_block = self.create_block()
        merge_block = self.create_block()

        cfg.add_edge(current_block, enter_block, EdgeType.NORMAL)
        enter_block.add_statement(stmt)
        cfg.add_edge(enter_block, with_body_entry, EdgeType.CONTEXT_ENTER)

        exit_context_block.add_statement(stmt)
        cfg.add_edge(exit_context_block, merge_block, EdgeType.CONTEXT_EXIT)

        new_with_stack = with_stack + [exit_context_block]

        body_end = self._build_statements(
            statements=stmt.body,
            current_block=with_body_entry,
            cfg=cfg,
            loop_stack=loop_stack,
            try_stack=try_stack,
            with_stack=new_with_stack,
        )

        if body_end:
            cfg.add_edge(body_end, exit_context_block, EdgeType.NORMAL)

        return merge_block

    def _build_try_stmt(
        self,
        stmt: Union[ast.Try, getattr(ast, "TryStar", ast.Try)],  # type: ignore
        current_block: CFGBlock,
        cfg: CFG,
        loop_stack: List[Tuple[CFGBlock, CFGBlock]],
        try_stack: List[Tuple[List[CFGBlock], Optional[CFGBlock]]],
        with_stack: List[CFGBlock],
    ) -> CFGBlock:
        try_body_entry = self.create_block()
        merge_block = self.create_block()

        cfg.add_edge(current_block, try_body_entry, EdgeType.NORMAL)

        except_entry_blocks: List[CFGBlock] = []
        for handler in stmt.handlers:
            eb = self.create_block()
            except_entry_blocks.append(eb)

        finally_entry_block: Optional[CFGBlock] = None
        if stmt.finalbody:
            finally_entry_block = self.create_block()

        new_try_stack = try_stack + [(except_entry_blocks, finally_entry_block)]

        try_body_end = self._build_statements(
            statements=stmt.body,
            current_block=try_body_entry,
            cfg=cfg,
            loop_stack=loop_stack,
            try_stack=new_try_stack,
            with_stack=with_stack,
        )

        for eb in except_entry_blocks:
            cfg.add_edge(try_body_entry, eb, EdgeType.EXCEPTION)
        if not except_entry_blocks:
            if finally_entry_block:
                cfg.add_edge(try_body_entry, finally_entry_block, EdgeType.EXCEPTION)
            else:
                cfg.add_edge(try_body_entry, cfg.exceptional_exit_block, EdgeType.EXCEPTION)

        # Handle try orelse (executes if try completes without exception)
        if try_body_end:
            if stmt.orelse:
                else_entry = self.create_block()
                cfg.add_edge(try_body_end, else_entry, EdgeType.NORMAL)
                else_end = self._build_statements(
                    statements=stmt.orelse,
                    current_block=else_entry,
                    cfg=cfg,
                    loop_stack=loop_stack,
                    try_stack=try_stack,
                    with_stack=with_stack,
                )
                if else_end:
                    target = finally_entry_block if finally_entry_block else merge_block
                    edge_kind = EdgeType.NORMAL if not finally_entry_block else EdgeType.FINALLY
                    cfg.add_edge(else_end, target, edge_kind)
            else:
                target = finally_entry_block if finally_entry_block else merge_block
                edge_kind = EdgeType.NORMAL if not finally_entry_block else EdgeType.FINALLY
                cfg.add_edge(try_body_end, target, edge_kind)

        for idx, handler in enumerate(stmt.handlers):
            eb_entry = except_entry_blocks[idx]
            eb_end = self._build_statements(
                statements=handler.body,
                current_block=eb_entry,
                cfg=cfg,
                loop_stack=loop_stack,
                try_stack=try_stack,
                with_stack=with_stack,
            )
            if eb_end:
                target = finally_entry_block if finally_entry_block else merge_block
                edge_kind = EdgeType.NORMAL if not finally_entry_block else EdgeType.FINALLY
                cfg.add_edge(eb_end, target, edge_kind)

        if finally_entry_block and stmt.finalbody:
            finally_end = self._build_statements(
                statements=stmt.finalbody,
                current_block=finally_entry_block,
                cfg=cfg,
                loop_stack=loop_stack,
                try_stack=try_stack,
                with_stack=with_stack,
            )
            if finally_end:
                cfg.add_edge(finally_end, merge_block, EdgeType.FINALLY)

        return merge_block

    def _build_match_stmt(
        self,
        stmt: ast.AST,
        current_block: CFGBlock,
        cfg: CFG,
        loop_stack: List[Tuple[CFGBlock, CFGBlock]],
        try_stack: List[Tuple[List[CFGBlock], Optional[CFGBlock]]],
        with_stack: List[CFGBlock],
    ) -> CFGBlock:
        merge_block = self.create_block()
        subject_node = getattr(stmt, "subject", None)
        if subject_node:
            current_block.add_statement(ast.Expr(value=subject_node))

        curr_fallthrough = current_block
        cases = getattr(stmt, "cases", [])

        for case in cases:
            case_entry = self.create_block()
            cfg.add_edge(curr_fallthrough, case_entry, EdgeType.TRUE_BRANCH, label="case_match")
            
            next_fallthrough = self.create_block()
            cfg.add_edge(curr_fallthrough, next_fallthrough, EdgeType.FALSE_BRANCH, label="case_nomatch")
            curr_fallthrough = next_fallthrough

            case_end = self._build_statements(
                statements=getattr(case, "body", []),
                current_block=case_entry,
                cfg=cfg,
                loop_stack=loop_stack,
                try_stack=try_stack,
                with_stack=with_stack,
            )
            if case_end:
                cfg.add_edge(case_end, merge_block, EdgeType.NORMAL)

        cfg.add_edge(curr_fallthrough, merge_block, EdgeType.NORMAL)
        return merge_block

    def _handle_early_exit(
        self,
        source: CFGBlock,
        target_exit: CFGBlock,
        cfg: CFG,
        try_stack: List[Tuple[List[CFGBlock], Optional[CFGBlock]]],
        with_stack: List[CFGBlock],
        edge_type: EdgeType,
    ) -> None:
        curr = source
        # Process context exits in reverse order
        for exit_ctx in reversed(with_stack):
            cfg.add_edge(curr, exit_ctx, EdgeType.CONTEXT_EXIT)
            curr = exit_ctx

        # Process finally blocks in reverse order
        has_finally = False
        for _, finally_block in reversed(try_stack):
            if finally_block:
                cfg.add_edge(curr, finally_block, EdgeType.FINALLY)
                has_finally = True
                break

        if not has_finally:
            cfg.add_edge(curr, target_exit, edge_type)

    def _handle_exception_exit(
        self,
        source: CFGBlock,
        exceptional_exit: CFGBlock,
        cfg: CFG,
        try_stack: List[Tuple[List[CFGBlock], Optional[CFGBlock]]],
        with_stack: List[CFGBlock],
    ) -> None:
        curr = source
        # Process context exits first
        for exit_ctx in reversed(with_stack):
            cfg.add_edge(curr, exit_ctx, EdgeType.CONTEXT_EXIT)
            curr = exit_ctx

        if try_stack:
            except_blocks, finally_block = try_stack[-1]
            if except_blocks:
                for eb in except_blocks:
                    cfg.add_edge(curr, eb, EdgeType.EXCEPTION)
            elif finally_block:
                cfg.add_edge(curr, finally_block, EdgeType.FINALLY)
            else:
                self._handle_exception_exit(curr, exceptional_exit, cfg, try_stack[:-1], with_stack=[])
        else:
            cfg.add_edge(curr, exceptional_exit, EdgeType.RAISE)
