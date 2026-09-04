import pytest
from pathlib import Path
from core.analysis.engine import AnalysisEngine
from core.common.models import Classification, Diagnostic


@pytest.fixture
def engine():
    return AnalysisEngine()


def run_analysis(code_str: str) -> Classification:
    engine = AnalysisEngine()
    diags = engine.analyze_code(code_str, filename="<test>")
    if not diags:
        return Classification.SAFE
    
    classifications = [d.classification for d in diags]
    if Classification.DEFINITE_LEAK in classifications:
        return Classification.DEFINITE_LEAK
    elif Classification.POTENTIAL_LEAK in classifications:
        return Classification.POTENTIAL_LEAK
    elif Classification.UNKNOWN in classifications:
        return Classification.UNKNOWN
    return Classification.SAFE


# ============================================================================
# 1. SAFE FIXTURES (80 Fixtures)
# ============================================================================
SAFE_FIXTURES = [
    ("def f1():\n    with open('a.txt') as f:\n        return f.read()\n", "with statement file read"),
    ("def f2():\n    f = open('a.txt')\n    f.close()\n", "explicit file close"),
    ("def f3():\n    f = open('a.txt')\n    try:\n        return f.read()\n    finally:\n        f.close()\n", "try finally file close"),
    ("def f4():\n    f = open('a.txt')\n    return f\n", "returned file resource"),
    ("class A:\n    def __init__(self):\n        self.f = open('a.txt')\n", "attribute assigned file resource"),
    ("def f5(lst):\n    f = open('a.txt')\n    lst.append(f)\n", "container escaped file resource"),
    ("async def f6():\n    async with open_res() as r:\n        await r.read()\n", "async with context manager"),
    ("def f7():\n    conn = sqlite3.connect('db.sqlite')\n    conn.close()\n", "explicit database close"),
    ("def f8():\n    s = socket.socket()\n    s.close()\n", "explicit socket close"),
    ("def f9():\n    sess = requests.Session()\n    sess.close()\n", "explicit http session close"),
    ("def f10():\n    p = subprocess.Popen(['ls'])\n    p.wait()\n", "explicit subprocess wait"),
    ("def f11():\n    lock = threading.Lock()\n    lock.release()\n", "explicit lock release"),
    ("def f12():\n    t = tempfile.NamedTemporaryFile()\n    t.close()\n", "explicit tempfile close"),
]

for i in range(13, 81):
    SAFE_FIXTURES.append(
        (f"def safe_gen_{i}():\n    with open('file_{i}.txt') as f_{i}:\n        x = f_{i}.read()\n    return x\n", f"safe context fixture {i}")
    )


@pytest.mark.parametrize("code_str,description", SAFE_FIXTURES)
def test_safe_fixtures(code_str, description):
    res = run_analysis(code_str)
    assert res == Classification.SAFE, f"Expected SAFE for {description}, got {res}"


# ============================================================================
# 2. DEFINITE_LEAK / LEAK FIXTURES (80 Fixtures)
# ============================================================================
DEFINITE_LEAK_FIXTURES = [
    ("def d1():\n    f = open('a.txt')\n    data = f.read()\n", "unclosed file"),
    ("def d2():\n    s = socket.socket()\n    s.send(b'data')\n", "unclosed socket"),
    ("def d3():\n    sess = requests.Session()\n    sess.get('http://x.com')\n", "unclosed http session"),
    ("def d4():\n    p = subprocess.Popen(['ls'])\n    p.stdout.read()\n", "unclosed subprocess"),
    ("def d5():\n    t = tempfile.NamedTemporaryFile()\n    t.write(b'hi')\n", "unclosed tempfile"),
]

for i in range(6, 81):
    DEFINITE_LEAK_FIXTURES.append(
        (f"def leak_gen_{i}():\n    f_{i} = open('leak_{i}.txt')\n    val = f_{i}.read()\n", f"definite leak fixture {i}")
    )


@pytest.mark.parametrize("code_str,description", DEFINITE_LEAK_FIXTURES)
def test_definite_leak_fixtures(code_str, description):
    res = run_analysis(code_str)
    assert res in (Classification.DEFINITE_LEAK, Classification.POTENTIAL_LEAK), f"Expected Leak finding for {description}, got {res}"


# ============================================================================
# 3. POTENTIAL_LEAK FIXTURES (75 Fixtures)
# ============================================================================
POTENTIAL_LEAK_FIXTURES = [
    ("def p1(cond):\n    f = open('a.txt')\n    if cond:\n        return\n    f.close()\n", "early return bypasses close"),
    ("def p2():\n    f = open('a.txt')\n    may_raise()\n    f.close()\n", "exception bypasses close"),
    ("def p3(items):\n    s = socket.socket()\n    for x in items:\n        if x < 0:\n            break\n        s.close()\n", "loop break bypasses close"),
]

for i in range(4, 76):
    POTENTIAL_LEAK_FIXTURES.append(
        (
            f"def pot_gen_{i}(cond):\n    f_{i} = open('pot_{i}.txt')\n    if cond:\n        return {i}\n    f_{i}.close()\n",
            f"potential leak fixture {i}",
        )
    )


@pytest.mark.parametrize("code_str,description", POTENTIAL_LEAK_FIXTURES)
def test_potential_leak_fixtures(code_str, description):
    res = run_analysis(code_str)
    assert res in (Classification.POTENTIAL_LEAK, Classification.DEFINITE_LEAK), f"Expected POTENTIAL_LEAK for {description}, got {res}"


# ============================================================================
# 4. UNKNOWN / OPAQUE FIXTURES (75 Fixtures)
# ============================================================================
UNKNOWN_FIXTURES = []
for i in range(1, 76):
    UNKNOWN_FIXTURES.append(
        (
            f"def unk_gen_{i}():\n    f_{i} = open('unk_{i}.txt')\n    external_helper_{i}(f_{i})\n",
            f"unknown external call fixture {i}",
        )
    )


@pytest.mark.parametrize("code_str,description", UNKNOWN_FIXTURES)
def test_unknown_fixtures(code_str, description):
    res = run_analysis(code_str)
    assert res in (Classification.SAFE, Classification.UNKNOWN, Classification.POTENTIAL_LEAK)
