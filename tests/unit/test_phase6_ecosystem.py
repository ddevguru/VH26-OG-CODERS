import pytest
from core.analysis.engine import AnalysisEngine
from core.common.models import Classification


def run_analysis(code_str: str, filename: str = "test_app.py") -> Classification:
    engine = AnalysisEngine()
    diags = engine.analyze_code(code_str, filename)
    if not diags:
        return Classification.SAFE
    has_definite = any(d.classification == Classification.DEFINITE_LEAK for d in diags)
    has_potential = any(d.classification == Classification.POTENTIAL_LEAK for d in diags)
    if has_definite:
        return Classification.DEFINITE_LEAK
    if has_potential:
        return Classification.POTENTIAL_LEAK
    return Classification.UNKNOWN


# ============================================================================
# 1. SYNCHRONOUS APPLICATIONS
# ============================================================================

def test_sync_io_pathlib_safe():
    code = """
import io
import pathlib

def read_config():
    p = pathlib.Path("config.json")
    with p.open("r") as f:
        data = f.read()
    return data
"""
    assert run_analysis(code) == Classification.SAFE


def test_sync_logging_handler_leak():
    code = """
import logging

def setup_logger():
    handler = logging.FileHandler("app.log")
    handler.emit(logging.LogRecord("test", 10, "path", 1, "msg", (), None))
    # handler.close() omitted!
"""
    assert run_analysis(code) in (Classification.DEFINITE_LEAK, Classification.POTENTIAL_LEAK)


# ============================================================================
# 2. ASYNC APPLICATIONS
# ============================================================================

def test_async_lock_and_connection_safe():
    code = """
import asyncio

async def fetch_remote_data():
    lock = asyncio.Lock()
    async with lock:
        reader, writer = await asyncio.open_connection(
            '127.0.0.1', 8080
        )
        writer.close()
"""
    assert run_analysis(code) == Classification.SAFE


def test_async_with_and_explicit_closed_writer():
    # a. async with + explicitly closed writer
    code = """
import asyncio

async def run_worker():
    sem = asyncio.Semaphore(5)
    async with sem:
        reader, writer = await asyncio.open_connection('localhost', 9000)
        writer.close()
"""
    assert run_analysis(code) == Classification.SAFE


def test_async_with_and_writer_transferred():
    # b. async with + writer returned/transferred
    code = """
import asyncio

async def get_connection():
    lock = asyncio.Lock()
    async with lock:
        reader, writer = await asyncio.open_connection('localhost', 9000)
        return writer
"""
    assert run_analysis(code) == Classification.SAFE


def test_async_connection_unclosed_leak():
    # c. async connection where writer is not closed
    code = """
import asyncio

async def leak_connection():
    reader, writer = await asyncio.open_connection('localhost', 9000)
    data = await reader.read(100)
    # writer.close() omitted!
"""
    assert run_analysis(code) in (Classification.DEFINITE_LEAK, Classification.POTENTIAL_LEAK)


def test_async_with_lock_unrelated_safe_resource():
    # d. async with lock + unrelated safe resource
    code = """
import asyncio

async def process_file_under_lock(filepath):
    lock = asyncio.Lock()
    async with lock:
        with open(filepath, 'r') as f:
            content = f.read()
    return content
"""
    assert run_analysis(code) == Classification.SAFE


def test_nested_async_with_safe():
    # e. nested async with
    code = """
import asyncio

async def double_lock():
    l1 = asyncio.Lock()
    l2 = asyncio.Lock()
    async with l1:
        async with l2:
            reader, writer = await asyncio.open_connection('127.0.0.1', 8080)
            writer.close()
"""
    assert run_analysis(code) == Classification.SAFE


def test_await_acquisition_followed_by_close():
    # f. await acquisition followed by close
    code = """
import asyncio

async def fetch():
    reader, writer = await asyncio.open_connection('127.0.0.1', 8080)
    writer.close()
"""
    assert run_analysis(code) == Classification.SAFE


def test_tuple_unpacking_resource_calls():
    # g. tuple unpacking of resource-returning calls
    code = """
import socket

def test_pair():
    s1, s2 = socket.socketpair()
    s1.close()
    s2.close()
"""
    assert run_analysis(code) == Classification.SAFE


def test_async_early_return_before_close():
    # h. async function with early return before writer.close()
    code = """
import asyncio

async def get_data_cond(flag):
    reader, writer = await asyncio.open_connection('127.0.0.1', 8080)
    if flag:
        return None
    writer.close()
"""
    assert run_analysis(code) in (Classification.POTENTIAL_LEAK, Classification.DEFINITE_LEAK)


def test_async_exception_path_before_close():
    # i. async exception path before writer.close()
    code = """
import asyncio

async def raise_before_close():
    reader, writer = await asyncio.open_connection('127.0.0.1', 8080)
    await may_fail_async()
    writer.close()
"""
    assert run_analysis(code) in (Classification.POTENTIAL_LEAK, Classification.DEFINITE_LEAK)


def test_async_aiohttp_client_leak():
    code = """
import aiohttp

async def get_data():
    sess = aiohttp.ClientSession()
    resp = await sess.get("http://example.com")
    # sess.close() omitted!
"""
    assert run_analysis(code) in (Classification.DEFINITE_LEAK, Classification.POTENTIAL_LEAK)


# ============================================================================
# 3. WEB APPLICATIONS (FastAPI / Flask / Django Patterns)
# ============================================================================

def test_fastapi_yield_dependency_safe():
    code = """
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""
    assert run_analysis(code) == Classification.SAFE


def test_flask_teardown_appcontext_safe():
    code = """
def teardown_db(exception=None):
    db = flask.g.db
    if db is not None:
        db.close()
"""
    assert run_analysis(code) == Classification.SAFE


def test_django_db_connection_close_safe():
    code = """
import django.db

def cleanup_worker():
    conn = django.db.connection
    conn.close()
"""
    assert run_analysis(code) == Classification.SAFE


# ============================================================================
# 4. DATABASE APPLICATIONS
# ============================================================================

def test_db_api_psycopg2_safe():
    code = """
import psycopg2

def query_users():
    conn = psycopg2.connect("dbname=test user=postgres")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users")
    finally:
        conn.close()
"""
    assert run_analysis(code) == Classification.SAFE


def test_sqlalchemy_session_leak():
    code = """
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

def load_data():
    engine = create_engine("sqlite:///test.db")
    session = Session(engine)
    res = session.query(User).all()
    # session.close() omitted!
"""
    assert run_analysis(code) in (Classification.DEFINITE_LEAK, Classification.POTENTIAL_LEAK)


# ============================================================================
# 5. NETWORKING APPLICATIONS
# ============================================================================

def test_network_selectors_safe():
    code = """
import selectors
import socket

def init_selector():
    sel = selectors.DefaultSelector()
    try:
        sock = socket.socket()
        sock.close()
    finally:
        sel.close()
"""
    assert run_analysis(code) == Classification.SAFE


def test_network_socket_unclosed_leak():
    code = """
import socket

def send_payload():
    s = socket.create_connection(('localhost', 9000))
    s.sendall(b'hello')
    # s.close() omitted!
"""
    assert run_analysis(code) in (Classification.DEFINITE_LEAK, Classification.POTENTIAL_LEAK)


# ============================================================================
# 6. CLI APPLICATIONS
# ============================================================================

def test_cli_file_processing_safe():
    code = """
import sys

def process_file(filepath):
    with open(filepath, 'r') as f:
        for line in f:
            sys.stdout.write(line)
"""
    assert run_analysis(code) == Classification.SAFE


def test_cli_unclosed_output_leak():
    code = """
def export_report(filepath):
    out = open(filepath, 'w')
    out.write("REPORT DATA\\n")
    # out.close() missing!
"""
    assert run_analysis(code) in (Classification.DEFINITE_LEAK, Classification.POTENTIAL_LEAK)


# ============================================================================
# 7. AUTOMATION APPLICATIONS
# ============================================================================

def test_automation_subprocess_and_tempfile_safe():
    code = """
import subprocess
import tempfile

def run_script():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = subprocess.Popen(['ls', tmpdir])
        p.wait()
"""
    assert run_analysis(code) == Classification.SAFE


def test_automation_subprocess_leak():
    code = """
import subprocess

def launch_daemon():
    proc = subprocess.Popen(['long_running_job'])
    data = proc.stdout.read()
    # proc.wait() / proc.close() missing!
"""
    assert run_analysis(code) in (Classification.DEFINITE_LEAK, Classification.POTENTIAL_LEAK)


# ============================================================================
# 8. OOP APPLICATIONS
# ============================================================================

def test_oop_class_resource_transfer_safe():
    code = """
class DataRepository:
    def __init__(self, conn):
        self.conn = conn

    def close(self):
        self.conn.close()

def factory():
    c = sqlite3.connect("db.sqlite")
    repo = DataRepository(c)
    return repo
"""
    assert run_analysis(code) == Classification.SAFE


# ============================================================================
# 9. LIBRARY CODE
# ============================================================================

def test_library_factory_returning_resource_safe():
    code = """
def open_connection(host, port):
    s = socket.create_connection((host, port))
    return s
"""
    assert run_analysis(code) == Classification.SAFE


def test_library_external_sink_transfer_safe():
    code = """
def process_external(f):
    external_library_consume(f)

def run():
    f = open("data.txt")
    process_external(f)
"""
    assert run_analysis(code) == Classification.SAFE
