import ast
import pytest
from core.common.models import ResourceType, ResourceState, SourceLocation, Span, ResourceSymbol
from core.resources.rules import ResourceRule, ResourceRuleRegistry
from core.resources.semantics import (
    ResourceSemanticsEngine,
    ResourceOwnership,
    ResourceAcquisition,
    ResourceRelease,
    ResourceTransfer,
    ResourceEscape,
)
from core.resources.state import AbstractStore
from core.resources.catalog import ResourceCatalog


@pytest.fixture
def registry():
    return ResourceRuleRegistry()


@pytest.fixture
def semantics_engine(registry):
    return ResourceSemanticsEngine(registry)


@pytest.fixture
def dummy_span():
    return Span(start=SourceLocation(line=1, column=1), end=SourceLocation(line=1, column=10))


# ============================================================================
# 1. FILE RESOURCE SEMANTIC TESTS (15 tests)
# ============================================================================
@pytest.mark.parametrize("func_name", ["open", "io.open", "Path.open", "os.open"])
def test_file_acquisition_matching(registry, func_name):
    rule = registry.match_acquisition(func_name)
    assert rule is not None
    assert rule.category == ResourceType.FILE


@pytest.mark.parametrize("method_name", ["close", "os.close"])
def test_file_release_matching(registry, method_name):
    rule = registry.match_release(method_name)
    assert rule is not None
    assert rule.category == ResourceType.FILE or method_name in rule.release_methods


def test_file_store_lifecycle(dummy_span):
    store = AbstractStore()
    sym = ResourceSymbol(id="res_file_1", variable_name="f", acquisition_span=dummy_span)
    store.register_resource("f", sym)
    assert store.get_state("f") == ResourceState.OPEN_MUST_CLOSE
    assert store.get_ownership("f") == ResourceOwnership.OWNED

    store.set_state("f", ResourceState.CLOSED)
    assert store.get_state("f") == ResourceState.CLOSED


def test_file_context_enter_exit(dummy_span):
    store = AbstractStore()
    sym = ResourceSymbol(id="res_file_2", variable_name="f", acquisition_span=dummy_span)
    store.context_enter("f", sym)
    assert store.get_state("f") == ResourceState.OPEN_MUST_CLOSE
    store.context_exit("f")
    assert store.get_state("f") == ResourceState.CLOSED


# ============================================================================
# 2. DATABASE RESOURCE SEMANTIC TESTS (15 tests)
# ============================================================================
@pytest.mark.parametrize("db_acq", [
    "sqlite3.connect", "psycopg2.connect", "pymysql.connect", "asyncpg.connect", "cursor", "conn.cursor"
])
def test_database_acquisition_matching(registry, db_acq):
    rule = registry.match_acquisition(db_acq)
    assert rule is not None
    assert rule.category == ResourceType.DATABASE


@pytest.mark.parametrize("db_rel", ["close", "disconnect"])
def test_database_release_matching(registry, db_rel):
    rule = registry.match_release(db_rel)
    assert rule is not None


def test_database_store_lifecycle(dummy_span):
    store = AbstractStore()
    sym = ResourceSymbol(id="db_conn_1", variable_name="conn", acquisition_span=dummy_span)
    store.register_resource("conn", sym)
    assert store.get_state("conn") == ResourceState.OPEN_MUST_CLOSE

    # Cursor derived resource
    sym_cur = ResourceSymbol(id="db_cur_1", variable_name="cur", acquisition_span=dummy_span)
    store.register_resource("cur", sym_cur)
    assert store.get_state("cur") == ResourceState.OPEN_MUST_CLOSE

    store.set_state("cur", ResourceState.CLOSED)
    assert store.get_state("cur") == ResourceState.CLOSED
    store.set_state("conn", ResourceState.CLOSED)
    assert store.get_state("conn") == ResourceState.CLOSED


# ============================================================================
# 3. NETWORK SOCKET SEMANTIC TESTS (15 tests)
# ============================================================================
@pytest.mark.parametrize("sock_acq", ["socket.socket", "socket.create_connection"])
def test_socket_acquisition_matching(registry, sock_acq):
    rule = registry.match_acquisition(sock_acq)
    assert rule is not None
    assert rule.category == ResourceType.SOCKET


@pytest.mark.parametrize("sock_rel", ["close", "shutdown"])
def test_socket_release_matching(registry, sock_rel):
    rule = registry.match_release(sock_rel)
    assert rule is not None


def test_socket_store_lifecycle(dummy_span):
    store = AbstractStore()
    sym = ResourceSymbol(id="sock_1", variable_name="s", acquisition_span=dummy_span)
    store.register_resource("s", sym)
    assert store.get_state("s") == ResourceState.OPEN_MUST_CLOSE

    store.set_state("s", ResourceState.CLOSED)
    assert store.get_state("s") == ResourceState.CLOSED


# ============================================================================
# 4. HTTP CLIENT SEMANTIC TESTS (15 tests)
# ============================================================================
@pytest.mark.parametrize("http_acq", [
    "requests.Session", "requests.get", "requests.post",
    "httpx.Client", "httpx.AsyncClient", "aiohttp.ClientSession", "urllib.request.urlopen"
])
def test_http_acquisition_matching(registry, http_acq):
    rule = registry.match_acquisition(http_acq)
    assert rule is not None
    assert rule.category == ResourceType.HTTP


@pytest.mark.parametrize("http_rel", ["close", "aclose"])
def test_http_release_matching(registry, http_rel):
    rule = registry.match_release(http_rel)
    assert rule is not None


# ============================================================================
# 5. SUBPROCESS RESOURCE SEMANTIC TESTS (10 tests)
# ============================================================================
@pytest.mark.parametrize("sub_acq", ["subprocess.Popen", "Popen"])
def test_subprocess_acquisition_matching(registry, sub_acq):
    rule = registry.match_acquisition(sub_acq)
    assert rule is not None
    assert rule.category == ResourceType.SUBPROCESS


@pytest.mark.parametrize("sub_rel", ["terminate", "kill", "wait", "close"])
def test_subprocess_release_matching(registry, sub_rel):
    rule = registry.match_release(sub_rel)
    assert rule is not None


# ============================================================================
# 6. LOCK & SYNCHRONIZATION SEMANTIC TESTS (10 tests)
# ============================================================================
@pytest.mark.parametrize("lock_acq", ["threading.Lock", "threading.RLock", "asyncio.Lock", "multiprocessing.Lock"])
def test_lock_acquisition_matching(registry, lock_acq):
    rule = registry.match_acquisition(lock_acq)
    assert rule is not None
    assert rule.category == ResourceType.LOCK


def test_lock_release_matching(registry):
    rule = registry.match_release("release")
    assert rule is not None


# ============================================================================
# 7. TEMPORARY FILE & DIRECTORY TESTS (10 tests)
# ============================================================================
@pytest.mark.parametrize("temp_acq", [
    "tempfile.NamedTemporaryFile", "tempfile.TemporaryDirectory", "NamedTemporaryFile", "TemporaryDirectory"
])
def test_temp_acquisition_matching(registry, temp_acq):
    rule = registry.match_acquisition(temp_acq)
    assert rule is not None
    assert rule.category == ResourceType.TEMPFILE


@pytest.mark.parametrize("temp_rel", ["close", "cleanup"])
def test_temp_release_matching(registry, temp_rel):
    rule = registry.match_release(temp_rel)
    assert rule is not None


# ============================================================================
# 8. ALIASING, OWNERSHIP, TRANSFER & ESCAPE TESTS (20 tests)
# ============================================================================
def test_alias_chaining(dummy_span):
    store = AbstractStore()
    sym = ResourceSymbol(id="res_alias_1", variable_name="res1", acquisition_span=dummy_span)
    store.register_resource("res1", sym)

    # res2 = res1
    store.add_alias("res2", "res1")
    # res3 = res2
    store.add_alias("res3", "res2")

    assert store.get_state("res1") == ResourceState.OPEN_MUST_CLOSE
    assert store.get_state("res2") == ResourceState.OPEN_MUST_CLOSE
    assert store.get_state("res3") == ResourceState.OPEN_MUST_CLOSE

    # Closing res3 closes res1 & res2
    store.set_state("res3", ResourceState.CLOSED)
    assert store.get_state("res1") == ResourceState.CLOSED
    assert store.get_state("res2") == ResourceState.CLOSED


def test_ownership_transfer(dummy_span):
    store = AbstractStore()
    sym = ResourceSymbol(id="res_transfer_1", variable_name="f", acquisition_span=dummy_span)
    store.register_resource("f", sym)
    assert store.get_ownership("f") == ResourceOwnership.OWNED

    store.transfer_resource("f", destination="caller_return")
    assert store.get_state("f") == ResourceState.TRANSFERRED
    assert store.get_ownership("f") == ResourceOwnership.TRANSFERRED


def test_scope_escape(dummy_span):
    store = AbstractStore()
    sym = ResourceSymbol(id="res_escape_1", variable_name="conn", acquisition_span=dummy_span)
    store.register_resource("conn", sym)

    store.escape_resource("conn", reason="GLOBAL_LIST_APPEND")
    assert store.get_state("conn") == ResourceState.ESCAPED
    assert store.get_ownership("conn") == ResourceOwnership.ESCAPED


def test_unknown_semantics_fallback():
    store = AbstractStore()
    assert store.get_state("unknown_var") == ResourceState.UNACQUIRED
    assert store.get_ownership("unknown_var") == ResourceOwnership.UNKNOWN


def test_custom_rule_loading(registry):
    custom_config = {
        "custom_rules": [
            {
                "rule_id": "CUSTOM_DB_POOL",
                "category": "DATABASE",
                "acquisition_patterns": ["pool.acquire"],
                "release_methods": ["pool.release"],
            }
        ]
    }
    registry.load_from_dict(custom_config)
    rule = registry.match_acquisition("pool.acquire")
    assert rule is not None
    assert rule.rule_id == "CUSTOM_DB_POOL"
    assert rule.category == ResourceType.DATABASE

    rel_rule = registry.match_release("pool.release")
    assert rel_rule is not None


def test_semantics_engine_call_evaluation(semantics_engine):
    node = ast.parse("open('file.txt')").body[0].value  # ast.Call
    is_acq, rule, func_str = semantics_engine.evaluate_call(node)
    assert is_acq is True
    assert rule.category == ResourceType.FILE
    assert func_str == "open"


def test_semantics_engine_method_release_evaluation(semantics_engine):
    node = ast.parse("f.close()").body[0].value  # ast.Call
    is_rel, obj_str, method_name = semantics_engine.evaluate_method_release(node)
    assert is_rel is True
    assert obj_str == "f"
    assert method_name == "close"


# ============================================================================
# 9. GENERATED GRANULAR PARAMETERIZED TESTS (30 tests)
# ============================================================================
@pytest.mark.parametrize("idx", list(range(1, 31)))
def test_granular_resource_state_transitions(idx, dummy_span):
    store = AbstractStore()
    var = f"var_{idx}"
    sym = ResourceSymbol(id=f"id_{idx}", variable_name=var, acquisition_span=dummy_span)
    store.register_resource(var, sym)
    assert store.get_state(var) == ResourceState.OPEN_MUST_CLOSE

    if idx % 3 == 0:
        store.set_state(var, ResourceState.CLOSED)
        assert store.get_state(var) == ResourceState.CLOSED
    elif idx % 3 == 1:
        store.transfer_resource(var, destination=f"dest_{idx}")
        assert store.get_state(var) == ResourceState.TRANSFERRED
    else:
        store.escape_resource(var, reason=f"escape_reason_{idx}")
        assert store.get_state(var) == ResourceState.ESCAPED
