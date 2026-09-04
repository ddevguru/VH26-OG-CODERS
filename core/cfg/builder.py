import ast
from typing import List, Optional, Tuple, Union
from core.cfg.graph import CFG, CFGBlock, EdgeType


class CFGBuilder:
    """Builds an intra-procedural Control Flow Graph (CFG) from Python stdlib ast.FunctionDef / ast.AsyncFunctionDef."""

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
            cfg.add_edge(entry_block, exit_block, EdgeType.NORMAL)
            return cfg

        current_block = entry_block
        final_block = self._build_statements(
            statements=func.body,
            current_block=current_block,
            cfg=cfg,
            loop_stack=[],
            try_stack=[],
        )

        if final_block and not final_block.outgoing:
            cfg.add_edge(final_block, exit_block, EdgeType.NORMAL)

        return cfg

    def _build_statements(
        self,
        statements: List[ast.stmt],
        current_block: CFGBlock,
        cfg: CFG,
        loop_stack: List[Tuple[CFGBlock, CFGBlock]],
        try_stack: List[Tuple[List[CFGBlock], Optional[CFGBlock]]],
    ) -> Optional[CFGBlock]:

        curr = current_block

        for stmt in statements:
            if curr is None:
                curr = self.create_block()

            if isinstance(stmt, ast.If):
                curr = self._build_if_stmt(stmt, curr, cfg, loop_stack, try_stack)

            elif isinstance(stmt, (ast.While, ast.For, getattr(ast, "AsyncFor", ast.For))):
                curr = self._build_loop_stmt(stmt, curr, cfg, loop_stack, try_stack)

            elif isinstance(stmt, (ast.With, getattr(ast, "AsyncWith", ast.With))):
                curr = self._build_with_stmt(stmt, curr, cfg, loop_stack, try_stack)

            elif isinstance(stmt, (ast.Try, getattr(ast, "TryStar", ast.Try))):
                curr = self._build_try_stmt(stmt, curr, cfg, loop_stack, try_stack)

            elif isinstance(stmt, ast.Return):
                curr.add_statement(stmt)
                self._link_exit_with_finally(curr, cfg.exit_block, cfg, try_stack, EdgeType.RETURN)
                curr = None

            elif isinstance(stmt, ast.Raise):
                curr.add_statement(stmt)
                self._link_exception_with_finally(curr, cfg.exceptional_exit_block, cfg, try_stack)
                curr = None

            elif isinstance(stmt, ast.Break):
                curr.add_statement(stmt)
                if loop_stack:
                    _, loop_exit = loop_stack[-1]
                    cfg.add_edge(curr, loop_exit, EdgeType.NORMAL, label="break")
                curr = None

            elif isinstance(stmt, ast.Continue):
                curr.add_statement(stmt)
                if loop_stack:
                    loop_header, _ = loop_stack[-1]
                    cfg.add_edge(curr, loop_header, EdgeType.NORMAL, label="continue")
                curr = None

            else:
                curr.add_statement(stmt)

        return curr

    def _build_if_stmt(
        self,
        stmt: ast.If,
        current_block: CFGBlock,
        cfg: CFG,
        loop_stack: List[Tuple[CFGBlock, CFGBlock]],
        try_stack: List[Tuple[List[CFGBlock], Optional[CFGBlock]]],
    ) -> CFGBlock:
        current_block.add_statement(ast.Expr(value=stmt.test, lineno=getattr(stmt, 'lineno', 1), col_offset=getattr(stmt, 'col_offset', 0)))

        then_block = self.create_block()
        merge_block = self.create_block()

        cfg.add_edge(current_block, then_block, EdgeType.COND_TRUE)

        then_end = self._build_statements(
            statements=stmt.body,
            current_block=then_block,
            cfg=cfg,
            loop_stack=loop_stack,
            try_stack=try_stack,
        )
        if then_end:
            cfg.add_edge(then_end, merge_block, EdgeType.NORMAL)

        if stmt.orelse:
            else_block = self.create_block()
            cfg.add_edge(current_block, else_block, EdgeType.COND_FALSE)

            else_end = self._build_statements(
                statements=stmt.orelse,
                current_block=else_block,
                cfg=cfg,
                loop_stack=loop_stack,
                try_stack=try_stack,
            )
            if else_end:
                cfg.add_edge(else_end, merge_block, EdgeType.NORMAL)
        else:
            cfg.add_edge(current_block, merge_block, EdgeType.COND_FALSE)

        return merge_block

    def _build_loop_stmt(
        self,
        stmt: ast.stmt,
        current_block: CFGBlock,
        cfg: CFG,
        loop_stack: List[Tuple[CFGBlock, CFGBlock]],
        try_stack: List[Tuple[List[CFGBlock], Optional[CFGBlock]]],
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

        cfg.add_edge(header_block, body_block, EdgeType.COND_TRUE)
        cfg.add_edge(header_block, exit_block, EdgeType.COND_FALSE)

        new_loop_stack = loop_stack + [(header_block, exit_block)]

        body_end = self._build_statements(
            statements=body,
            current_block=body_block,
            cfg=cfg,
            loop_stack=new_loop_stack,
            try_stack=try_stack,
        )

        if body_end:
            cfg.add_edge(body_end, header_block, EdgeType.NORMAL, label="loop_back")

        return exit_block

    def _build_with_stmt(
        self,
        stmt: Union[ast.With, getattr(ast, "AsyncWith", ast.With)],  # type: ignore
        current_block: CFGBlock,
        cfg: CFG,
        loop_stack: List[Tuple[CFGBlock, CFGBlock]],
        try_stack: List[Tuple[List[CFGBlock], Optional[CFGBlock]]],
    ) -> CFGBlock:
        current_block.add_statement(stmt)

        with_body_entry = self.create_block()
        merge_block = self.create_block()

        cfg.add_edge(current_block, with_body_entry, EdgeType.NORMAL)

        body_end = self._build_statements(
            statements=stmt.body,
            current_block=with_body_entry,
            cfg=cfg,
            loop_stack=loop_stack,
            try_stack=try_stack,
        )

        if body_end:
            cfg.add_edge(body_end, merge_block, EdgeType.NORMAL)

        merge_block.add_statement(stmt)  # Auto-exit context manager marker
        return merge_block

    def _build_try_stmt(
        self,
        stmt: Union[ast.Try, getattr(ast, "TryStar", ast.Try)],  # type: ignore
        current_block: CFGBlock,
        cfg: CFG,
        loop_stack: List[Tuple[CFGBlock, CFGBlock]],
        try_stack: List[Tuple[List[CFGBlock], Optional[CFGBlock]]],
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
        )

        for eb in except_entry_blocks:
            cfg.add_edge(try_body_entry, eb, EdgeType.EXCEPTIONAL)
        if not except_entry_blocks:
            if finally_entry_block:
                cfg.add_edge(try_body_entry, finally_entry_block, EdgeType.EXCEPTIONAL)
            else:
                cfg.add_edge(try_body_entry, cfg.exceptional_exit_block, EdgeType.EXCEPTIONAL)

        if try_body_end:
            if finally_entry_block:
                cfg.add_edge(try_body_end, finally_entry_block, EdgeType.NORMAL)
            else:
                cfg.add_edge(try_body_end, merge_block, EdgeType.NORMAL)

        for idx, handler in enumerate(stmt.handlers):
            eb_entry = except_entry_blocks[idx]
            eb_end = self._build_statements(
                statements=handler.body,
                current_block=eb_entry,
                cfg=cfg,
                loop_stack=loop_stack,
                try_stack=try_stack,
            )
            if eb_end:
                if finally_entry_block:
                    cfg.add_edge(eb_end, finally_entry_block, EdgeType.NORMAL)
                else:
                    cfg.add_edge(eb_end, merge_block, EdgeType.NORMAL)

        if finally_entry_block and stmt.finalbody:
            finally_end = self._build_statements(
                statements=stmt.finalbody,
                current_block=finally_entry_block,
                cfg=cfg,
                loop_stack=loop_stack,
                try_stack=try_stack,
            )
            if finally_end:
                cfg.add_edge(finally_end, merge_block, EdgeType.FINALLY_EXIT)

        return merge_block

    def _link_exit_with_finally(
        self,
        source: CFGBlock,
        target_exit: CFGBlock,
        cfg: CFG,
        try_stack: List[Tuple[List[CFGBlock], Optional[CFGBlock]]],
        edge_type: EdgeType,
    ) -> None:
        curr = source
        for _, finally_block in reversed(try_stack):
            if finally_block:
                cfg.add_edge(curr, finally_block, EdgeType.FINALLY_ENTRY)
                curr = finally_block
        cfg.add_edge(curr, target_exit, edge_type)

    def _link_exception_with_finally(
        self,
        source: CFGBlock,
        exceptional_exit: CFGBlock,
        cfg: CFG,
        try_stack: List[Tuple[List[CFGBlock], Optional[CFGBlock]]],
    ) -> None:
        if not try_stack:
            cfg.add_edge(source, exceptional_exit, EdgeType.EXCEPTIONAL)
            return

        except_blocks, finally_block = try_stack[-1]
        if except_blocks:
            for eb in except_blocks:
                cfg.add_edge(source, eb, EdgeType.EXCEPTIONAL)
        elif finally_block:
            cfg.add_edge(source, finally_block, EdgeType.EXCEPTIONAL)
        else:
            self._link_exception_with_finally(source, exceptional_exit, cfg, try_stack[:-1])
