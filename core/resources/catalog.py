import ast
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple


@dataclass
class ResourceSpec:
    type_name: str
    acquisition_functions: Set[str] = field(default_factory=set)
    release_methods: Set[str] = field(default_factory=lambda: {"close", "finish", "disconnect", "release"})


class ResourceCatalog:
    """Catalog of tracked Python closeable resources and acquisition/release specifications for stdlib ast.AST."""

    KNOWN_RESOURCE_FUNCTIONS: Set[str] = {
        "open",
        "connect",
        "socket",
        "Session",
        "urlopen",
        "NamedTemporaryFile",
        "TemporaryDirectory",
        "Client",
        "AsyncClient",
        "ClientSession",
        "Lock",
        "RLock",
        "Popen",
    }

    ACQUISITION_FULL_NAMES: Set[str] = {
        "open",
        "io.open",
        "Path.open",
        "sqlite3.connect",
        "psycopg2.connect",
        "pymysql.connect",
        "asyncpg.connect",
        "socket.socket",
        "socket.create_connection",
        "requests.Session",
        "requests.get",
        "requests.post",
        "aiohttp.ClientSession",
        "httpx.Client",
        "httpx.AsyncClient",
        "urllib.request.urlopen",
        "tempfile.NamedTemporaryFile",
        "tempfile.TemporaryDirectory",
        "subprocess.Popen",
        "threading.Lock",
        "threading.RLock",
        "asyncio.Lock",
    }

    RELEASE_METHODS: Set[str] = {"close", "finish", "disconnect", "release"}

    def __init__(self, custom_specs: Optional[List[ResourceSpec]] = None) -> None:
        self.specs: Dict[str, ResourceSpec] = {}
        self._load_default_specs()
        if custom_specs:
            for spec in custom_specs:
                self.specs[spec.type_name] = spec

    def _load_default_specs(self) -> None:
        for rfunc in self.ACQUISITION_FULL_NAMES:
            self.specs[rfunc] = ResourceSpec(
                type_name=rfunc,
                acquisition_functions={rfunc},
                release_methods=self.RELEASE_METHODS,
            )

    def is_acquisition_expr(self, expr: Optional[ast.AST]) -> Tuple[bool, Optional[str]]:
        if expr is None or not isinstance(expr, ast.Call):
            return False, None

        func_str = self._call_func_to_string(expr.func)
        if not func_str:
            return False, None

        short_name = func_str.split(".")[-1]
        if func_str in self.ACQUISITION_FULL_NAMES or short_name in self.KNOWN_RESOURCE_FUNCTIONS:
            return True, func_str

        return False, None

    def is_release_invocation(self, expr: Optional[ast.AST]) -> Tuple[bool, Optional[str], Optional[str]]:
        """Returns (is_release, target_var_name, release_method_name)"""
        if expr is None:
            return False, None, None

        call_expr: Optional[ast.Call] = None
        if isinstance(expr, ast.Expr) and isinstance(expr.value, ast.Call):
            call_expr = expr.value
        elif isinstance(expr, ast.Call):
            call_expr = expr

        if call_expr and isinstance(call_expr.func, ast.Attribute):
            attr_name = call_expr.func.attr
            if attr_name in self.RELEASE_METHODS:
                target_var = self._call_func_to_string(call_expr.func.value)
                if target_var:
                    return True, target_var, attr_name

        return False, None, None

    def _call_func_to_string(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            obj = self._call_func_to_string(node.value)
            return f"{obj}.{node.attr}" if obj else node.attr
        return ""
