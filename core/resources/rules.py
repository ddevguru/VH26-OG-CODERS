import ast
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Union
from core.common.models import ResourceType


@dataclass
class ResourceRule:
    rule_id: str
    category: ResourceType
    acquisition_patterns: Set[str]
    release_methods: Set[str] = field(default_factory=lambda: {"close", "release", "shutdown", "finish", "disconnect"})
    supports_context_manager: bool = True
    auto_release_on_exit: bool = True
    transfer_sinks: Set[str] = field(default_factory=set)
    description: str = ""

    def matches_acquisition(self, func_name: str) -> bool:
        if func_name in self.acquisition_patterns:
            return True
        short_name = func_name.split(".")[-1]
        return short_name in self.acquisition_patterns

    def matches_release(self, method_name: str) -> bool:
        return method_name in self.release_methods


class ResourceRuleRegistry:
    """Extensible plugin registry for built-in and custom Python resource lifecycle rules."""

    def __init__(self) -> None:
        self.rules: Dict[str, ResourceRule] = {}
        self.acquisition_map: Dict[str, ResourceRule] = {}
        self._register_default_rules()

    def register_rule(self, rule: ResourceRule) -> None:
        self.rules[rule.rule_id] = rule
        for pattern in rule.acquisition_patterns:
            self.acquisition_map[pattern] = rule

    def _register_default_rules(self) -> None:
        # FILES & IO
        self.register_rule(
            ResourceRule(
                rule_id="RULE_FILE",
                category=ResourceType.FILE,
                acquisition_patterns={
                    "open",
                    "io.open",
                    "io.FileIO",
                    "io.TextIOWrapper",
                    "io.BufferedWriter",
                    "io.BufferedReader",
                    "io.BytesIO",
                    "io.StringIO",
                    "Path.open",
                    "pathlib.Path.open",
                    "os.open",
                },
                release_methods={"close", "os.close", "detach", "flush"},
                description="Python file, stream, and file-descriptor resources",
            )
        )

        # DATABASE & ORM
        self.register_rule(
            ResourceRule(
                rule_id="RULE_DATABASE",
                category=ResourceType.DATABASE,
                acquisition_patterns={
                    "sqlite3.connect",
                    "psycopg2.connect",
                    "pymysql.connect",
                    "asyncpg.connect",
                    "mariadb.connect",
                    "mysql.connector.connect",
                    "cx_Oracle.connect",
                    "cursor",
                    "conn.cursor",
                    "create_engine",
                    "Engine.connect",
                    "engine.connect",
                    "Session",
                    "sessionmaker",
                    "SessionLocal",
                    "ScopedSession",
                },
                release_methods={"close", "disconnect", "dispose", "remove", "rollback", "commit"},
                description="Database connections, sessions, cursors, and ORM engines",
            )
        )

        # NETWORK & SELECTORS
        self.register_rule(
            ResourceRule(
                rule_id="RULE_NETWORK",
                category=ResourceType.SOCKET,
                acquisition_patterns={
                    "socket.socket",
                    "socket.create_connection",
                    "socket.fromfd",
                    "socket.socketpair",
                    "asyncio.open_connection",
                    "asyncio.start_server",
                    "selectors.DefaultSelector",
                    "selectors.SelectSelector",
                    "selectors.PollSelector",
                    "selectors.KqueueSelector",
                    "selectors.EpollSelector",
                    "DefaultSelector",
                },
                release_methods={"close", "shutdown", "unregister"},
                description="Network socket, selector, and stream connection resources",
            )
        )

        # HTTP CLIENTS
        self.register_rule(
            ResourceRule(
                rule_id="RULE_HTTP",
                category=ResourceType.HTTP,
                acquisition_patterns={
                    "requests.Session",
                    "requests.get",
                    "requests.post",
                    "requests.put",
                    "requests.delete",
                    "httpx.Client",
                    "httpx.AsyncClient",
                    "httpx.get",
                    "httpx.post",
                    "aiohttp.ClientSession",
                    "aiohttp.TCPConnector",
                    "urllib.request.urlopen",
                },
                release_methods={"close", "aclose"},
                description="HTTP client sessions, connectors, and response handles",
            )
        )

        # SUBPROCESS
        self.register_rule(
            ResourceRule(
                rule_id="RULE_SUBPROCESS",
                category=ResourceType.SUBPROCESS,
                acquisition_patterns={"subprocess.Popen", "Popen"},
                release_methods={"terminate", "kill", "wait", "close"},
                description="Subprocess handles",
            )
        )

        # LOCKS & SYNCHRONIZATION
        self.register_rule(
            ResourceRule(
                rule_id="RULE_LOCKS",
                category=ResourceType.LOCK,
                acquisition_patterns={
                    "threading.Lock",
                    "threading.RLock",
                    "threading.Semaphore",
                    "threading.BoundedSemaphore",
                    "asyncio.Lock",
                    "asyncio.Semaphore",
                    "asyncio.BoundedSemaphore",
                    "multiprocessing.Lock",
                },
                release_methods={"release"},
                description="Synchronization locks and semaphores",
            )
        )

        # TEMPORARY FILES & DIRECTORIES
        self.register_rule(
            ResourceRule(
                rule_id="RULE_TEMPORARY",
                category=ResourceType.TEMPFILE,
                acquisition_patterns={
                    "tempfile.NamedTemporaryFile",
                    "tempfile.TemporaryDirectory",
                    "tempfile.SpooledTemporaryFile",
                    "tempfile.mkstemp",
                    "NamedTemporaryFile",
                    "TemporaryDirectory",
                    "SpooledTemporaryFile",
                },
                release_methods={"close", "cleanup"},
                description="Temporary files, directories, and handles",
            )
        )

        # LOGGING HANDLERS
        self.register_rule(
            ResourceRule(
                rule_id="RULE_LOGGING",
                category=ResourceType.CUSTOM,
                acquisition_patterns={
                    "logging.FileHandler",
                    "logging.handlers.RotatingFileHandler",
                    "logging.handlers.TimedRotatingFileHandler",
                    "logging.handlers.SocketHandler",
                    "FileHandler",
                },
                release_methods={"close"},
                description="Logging file and socket handlers",
            )
        )

        # WEB FRAMEWORKS (FastAPI / Flask / Django explicit connection management)
        self.register_rule(
            ResourceRule(
                rule_id="RULE_WEB_FRAMEWORK",
                category=ResourceType.CUSTOM,
                acquisition_patterns={
                    "get_db",
                    "get_db_session",
                    "db_session",
                    "django.db.connection",
                    "django.db.connections",
                    "flask.g.db",
                },
                release_methods={"close", "close_all", "teardown"},
                description="Web framework explicit connection and dependency handles",
            )
        )

        # GENERAL FALLBACK / DEFAULT
        self.register_rule(
            ResourceRule(
                rule_id="RULE_GENERAL",
                category=ResourceType.CUSTOM,
                acquisition_patterns={"create_resource", "acquire_resource"},
                release_methods={"close", "release", "shutdown", "finish", "disconnect", "cleanup"},
                description="General custom resources",
            )
        )

    def match_acquisition(self, func_name: str) -> Optional[ResourceRule]:
        if func_name in self.acquisition_map:
            return self.acquisition_map[func_name]
        
        short_name = func_name.split(".")[-1]
        if short_name in self.acquisition_map:
            return self.acquisition_map[short_name]

        for rule in self.rules.values():
            if rule.matches_acquisition(func_name):
                return rule
        return None

    def match_release(self, method_name: str) -> Optional[ResourceRule]:
        for rule in self.rules.values():
            if rule.matches_release(method_name):
                return rule
        return None

    def load_from_dict(self, config: Dict[str, Any]) -> None:
        """Loads custom resource rules from a dictionary/YAML config structure."""
        custom_rules = config.get("custom_rules", [])
        for r_cfg in custom_rules:
            category_str = r_cfg.get("category", "CUSTOM").upper()
            try:
                cat = ResourceType[category_str]
            except KeyError:
                cat = ResourceType.CUSTOM

            rule = ResourceRule(
                rule_id=r_cfg.get("rule_id", f"CUSTOM_{len(self.rules)+1}"),
                category=cat,
                acquisition_patterns=set(r_cfg.get("acquisition_patterns", [])),
                release_methods=set(r_cfg.get("release_methods", ["close"])),
                supports_context_manager=r_cfg.get("supports_context_manager", True),
                description=r_cfg.get("description", "Custom rule"),
            )
            self.register_rule(rule)
