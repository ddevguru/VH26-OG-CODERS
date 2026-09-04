from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Union
import json
from pathlib import Path

from core.common.models import Classification, ResourceType, Confidence


@dataclass
class BenchmarkFixture:
    fixture_id: str
    name: str
    category: str  # SAFE, DEFINITE_LEAK, POTENTIAL_LEAK, UNKNOWN
    expected_classification: str
    rule_id: str
    resource_type: str
    expected_confidence: str
    line_number: int
    code: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def generate_benchmark_corpus() -> List[BenchmarkFixture]:
    fixtures: List[BenchmarkFixture] = []

    # =========================================================================
    # 1. SAFE FIXTURES (90 Fixtures)
    # =========================================================================
    safe_base = [
        ("with open('data.txt') as f:\n    data = f.read()\n", "FILE", "with statement file read"),
        ("f = open('data.txt')\nf.close()\n", "FILE", "explicit file close"),
        ("f = open('data.txt')\ntry:\n    data = f.read()\nfinally:\n    f.close()\n", "FILE", "try finally file close"),
        ("f = open('data.txt')\nreturn f\n", "FILE", "returned file ownership transfer"),
        ("self.f = open('data.txt')\n", "FILE", "attribute assignment escape"),
        ("lst.append(open('data.txt'))\n", "FILE", "container append escape"),
        ("async with open_conn() as (r, w):\n    w.write(b'hi')\n", "SOCKET", "async with socket"),
        ("conn = sqlite3.connect('db.sqlite')\nconn.close()\n", "DATABASE", "sqlite3 explicit close"),
        ("s = socket.socket()\ns.close()\n", "SOCKET", "socket explicit close"),
        ("sess = requests.Session()\nsess.close()\n", "HTTP", "requests session explicit close"),
        ("p = subprocess.Popen(['ls'])\np.wait()\n", "SUBPROCESS", "subprocess wait"),
        ("lock = threading.Lock()\nlock.release()\n", "LOCK", "lock release"),
        ("t = tempfile.NamedTemporaryFile()\nt.close()\n", "TEMPFILE", "tempfile explicit close"),
        ("with sqlite3.connect('db.sqlite') as conn:\n    conn.execute('SELECT 1')\n", "DATABASE", "database with context manager"),
        ("with socket.create_connection(('127.0.0.1', 8080)) as s:\n    s.send(b'test')\n", "SOCKET", "socket create_connection with statement"),
        ("with httpx.Client() as client:\n    res = client.get('http://api')\n", "HTTP", "httpx client with statement"),
        ("with tempfile.TemporaryDirectory() as tmp:\n    pass\n", "TEMPFILE", "temporary directory with statement"),
        ("lock = asyncio.Lock()\nasync with lock:\n    pass\n", "LOCK", "asyncio lock async with"),
        ("res = CustomResource()\nres.dispose()\n", "CUSTOM", "custom resource dispose"),
        ("def get_db():\n    db = SessionLocal()\n    try:\n        yield db\n    finally:\n        db.close()\n", "DATABASE", "fastapi yield dependency cleanup"),
    ]

    for idx, (body, res_type, desc) in enumerate(safe_base, 1):
        code = f"def safe_base_{idx}():\n    " + body.replace("\n", "\n    ").rstrip() + "\n"
        fixtures.append(
            BenchmarkFixture(
                fixture_id=f"SAFE_{idx:03d}",
                name=f"safe_{desc.replace(' ', '_')}",
                category="SAFE",
                expected_classification=Classification.SAFE.value,
                rule_id="RULE_LEAK_001",
                resource_type=res_type,
                expected_confidence=Confidence.HIGH.value,
                line_number=2,
                code=code,
            )
        )

    # Generate additional programmatic safe variations up to 90
    for i in range(len(safe_base) + 1, 91):
        r_type = ["FILE", "DATABASE", "SOCKET", "HTTP", "SUBPROCESS", "LOCK", "TEMPFILE"][i % 7]
        code = f"def safe_gen_{i}(val):\n    with open(f'path_{i}.txt') as f_{i}:\n        if val:\n            return f_{i}.read()\n        else:\n            return f_{i}.readline()\n"
        fixtures.append(
            BenchmarkFixture(
                fixture_id=f"SAFE_{i:03d}",
                name=f"safe_generated_branch_{i}",
                category="SAFE",
                expected_classification=Classification.SAFE.value,
                rule_id="RULE_LEAK_001",
                resource_type=r_type,
                expected_confidence=Confidence.HIGH.value,
                line_number=2,
                code=code,
            )
        )

    # =========================================================================
    # 2. DEFINITE_LEAK FIXTURES (90 Fixtures)
    # =========================================================================
    leak_base = [
        ("f = open('data.txt')\nreturn f.read()\n", "FILE", "unclosed file read"),
        ("conn = sqlite3.connect('db.sqlite')\nconn.execute('SELECT 1')\n", "DATABASE", "unclosed database connection"),
        ("s = socket.socket()\ns.connect(('127.0.0.1', 8080))\n", "SOCKET", "unclosed socket"),
        ("sess = requests.Session()\nsess.get('http://api')\n", "HTTP", "unclosed requests session"),
        ("p = subprocess.Popen(['ls'])\n", "SUBPROCESS", "unclosed subprocess Popen"),
        ("t = tempfile.NamedTemporaryFile()\nt.write(b'test')\n", "TEMPFILE", "unclosed tempfile"),
        ("lock = threading.Lock()\nlock.acquire()\n", "LOCK", "unreleased lock acquire"),
        ("r, w = await asyncio.open_connection('127.0.0.1', 8080)\n", "SOCKET", "unclosed open_connection tuple"),
        ("client = httpx.Client()\nres = client.get('http://api')\n", "HTTP", "unclosed httpx client"),
        ("db = SessionLocal()\nres = db.query(User).all()\n", "DATABASE", "unclosed sqlalchemy session"),
        ("f = open('data.txt')\nif True:\n    return None\nf.close()\n", "FILE", "early return before close"),
        ("for i in range(10):\n    f = open(f'file_{i}.txt')\n    data = f.read()\n", "FILE", "unclosed file inside loop"),
        ("if True:\n    f = open('a.txt')\nelse:\n    f = open('b.txt')\n", "FILE", "unclosed files in both branches"),
        ("f = open('a.txt')\ng = f\nreturn g.read()\n", "FILE", "aliased unclosed file"),
        ("res = CustomResource()\nres.process()\n", "CUSTOM", "unclosed custom resource"),
    ]

    for idx, (body, res_type, desc) in enumerate(leak_base, 1):
        code = f"def leak_base_{idx}():\n    " + body.replace("\n", "\n    ").rstrip() + "\n"
        fixtures.append(
            BenchmarkFixture(
                fixture_id=f"DEFINITE_LEAK_{idx:03d}",
                name=f"leak_{desc.replace(' ', '_')}",
                category="DEFINITE_LEAK",
                expected_classification=Classification.DEFINITE_LEAK.value,
                rule_id="RULE_LEAK_001",
                resource_type=res_type,
                expected_confidence=Confidence.HIGH.value,
                line_number=2,
                code=code,
            )
        )

    # Generate additional programmatic definite leak variations up to 90
    for i in range(len(leak_base) + 1, 91):
        r_type = ["FILE", "DATABASE", "SOCKET", "HTTP", "SUBPROCESS", "LOCK", "TEMPFILE"][i % 7]
        code = f"def leak_gen_{i}(cond):\n    f_{i} = open(f'data_{i}.txt')\n    if cond:\n        x = f_{i}.read()\n    else:\n        x = 'default'\n    return x\n"
        fixtures.append(
            BenchmarkFixture(
                fixture_id=f"DEFINITE_LEAK_{i:03d}",
                name=f"leak_generated_{i}",
                category="DEFINITE_LEAK",
                expected_classification=Classification.DEFINITE_LEAK.value,
                rule_id="RULE_LEAK_001",
                resource_type=r_type,
                expected_confidence=Confidence.HIGH.value,
                line_number=2,
                code=code,
            )
        )

    # =========================================================================
    # 3. POTENTIAL_LEAK FIXTURES (80 Fixtures)
    # =========================================================================
    potential_base = [
        ("f = open('data.txt')\ndata = f.read()\nparse(data)\nf.close()\n", "FILE", "unhandled exception before close"),
        ("conn = sqlite3.connect('db.sqlite')\nexecute_query(conn)\nconn.close()\n", "DATABASE", "unhandled exception before db close"),
        ("s = socket.socket()\nsend_payload(s)\ns.close()\n", "SOCKET", "unhandled exception before socket close"),
        ("sess = requests.Session()\nmake_request(sess)\nsess.close()\n", "HTTP", "unhandled exception before session close"),
        ("p = subprocess.Popen(['ls'])\nrun_process(p)\np.kill()\n", "SUBPROCESS", "unhandled exception before subprocess kill"),
        ("f = open('data.txt')\nif cond:\n    f.close()\n", "FILE", "closed on true branch but missing on false branch"),
        ("conn = sqlite3.connect('db.sqlite')\nif valid:\n    conn.close()\n", "DATABASE", "db closed conditionally"),
        ("s = socket.socket()\ntry:\n    s.send(b'data')\n    s.close()\nexcept Exception:\n    pass\n", "SOCKET", "close inside try block but not in finally"),
        ("f = open('a.txt')\ntry:\n    data = f.read()\n    f.close()\nexcept Exception:\n    pass\n", "FILE", "close inside try without finally"),
        ("sess = httpx.Client()\ntry:\n    sess.get('http://api')\n    sess.close()\nexcept Exception:\n    pass\n", "HTTP", "httpx close inside try without finally"),
    ]

    for idx, (body, res_type, desc) in enumerate(potential_base, 1):
        code = f"def potential_base_{idx}(cond):\n    " + body.replace("\n", "\n    ").rstrip() + "\n"
        fixtures.append(
            BenchmarkFixture(
                fixture_id=f"POTENTIAL_LEAK_{idx:03d}",
                name=f"potential_{desc.replace(' ', '_')}",
                category="POTENTIAL_LEAK",
                expected_classification=Classification.POTENTIAL_LEAK.value,
                rule_id="RULE_LEAK_001",
                resource_type=res_type,
                expected_confidence=Confidence.MEDIUM.value,
                line_number=2,
                code=code,
            )
        )

    # Generate additional programmatic potential leak variations up to 80
    for i in range(len(potential_base) + 1, 81):
        r_type = ["FILE", "DATABASE", "SOCKET", "HTTP", "SUBPROCESS", "LOCK", "TEMPFILE"][i % 7]
        code = f"def potential_gen_{i}(flag):\n    f_{i} = open(f'path_{i}.txt')\n    val = f_{i}.read()\n    external_call_{i}(val)\n    if flag:\n        f_{i}.close()\n"
        fixtures.append(
            BenchmarkFixture(
                fixture_id=f"POTENTIAL_LEAK_{i:03d}",
                name=f"potential_generated_{i}",
                category="POTENTIAL_LEAK",
                expected_classification=Classification.POTENTIAL_LEAK.value,
                rule_id="RULE_LEAK_001",
                resource_type=r_type,
                expected_confidence=Confidence.MEDIUM.value,
                line_number=2,
                code=code,
            )
        )

    # =========================================================================
    # 4. UNKNOWN FIXTURES (60 Fixtures)
    # =========================================================================
    unknown_base = [
        ("f = open('data.txt')\nprocess_resource_externally(f)\n", "FILE", "passed to external function"),
        ("conn = sqlite3.connect('db.sqlite')\nregister_connection(conn)\n", "DATABASE", "registered with global manager"),
        ("s = socket.socket()\ncustom_pool.store(s)\n", "SOCKET", "stored in custom connection pool"),
        ("sess = requests.Session()\nconfigure_session(sess)\n", "HTTP", "passed to framework configurator"),
        ("p = subprocess.Popen(['ls'])\nmanage_process(p)\n", "SUBPROCESS", "passed to process manager"),
        ("t = tempfile.NamedTemporaryFile()\nkeep_temp_file(t)\n", "TEMPFILE", "passed to temp file manager"),
        ("f = open('data.txt')\ncallback(f)\n", "FILE", "passed to callback function"),
        ("conn = sqlite3.connect('db.sqlite')\nevent_emitter.emit('conn', conn)\n", "DATABASE", "emitted via event bus"),
        ("s = socket.socket()\nasyncio.create_task(handle_socket(s))\n", "SOCKET", "passed to async task"),
        ("f = open('data.txt')\nThread(target=worker, args=(f,)).start()\n", "FILE", "passed to thread target"),
    ]

    for idx, (body, res_type, desc) in enumerate(unknown_base, 1):
        code = f"def unknown_base_{idx}():\n    " + body.replace("\n", "\n    ").rstrip() + "\n"
        fixtures.append(
            BenchmarkFixture(
                fixture_id=f"UNKNOWN_{idx:03d}",
                name=f"unknown_{desc.replace(' ', '_')}",
                category="UNKNOWN",
                expected_classification=Classification.UNKNOWN.value,
                rule_id="RULE_LEAK_001",
                resource_type=res_type,
                expected_confidence=Confidence.LOW.value,
                line_number=2,
                code=code,
            )
        )

    # Generate additional programmatic unknown variations up to 60
    for i in range(len(unknown_base) + 1, 61):
        r_type = ["FILE", "DATABASE", "SOCKET", "HTTP", "SUBPROCESS", "LOCK", "TEMPFILE"][i % 7]
        code = f"def unknown_gen_{i}():\n    f_{i} = open(f'unk_{i}.txt')\n    external_helper_{i}(f_{i})\n"
        fixtures.append(
            BenchmarkFixture(
                fixture_id=f"UNKNOWN_{i:03d}",
                name=f"unknown_generated_{i}",
                category="UNKNOWN",
                expected_classification=Classification.UNKNOWN.value,
                rule_id="RULE_LEAK_001",
                resource_type=r_type,
                expected_confidence=Confidence.LOW.value,
                line_number=2,
                code=code,
            )
        )

    return fixtures


def save_corpus_to_json(target_path: Union[str, Path] = "benchmarks/corpus/fixtures.json") -> Path:
    fixtures = generate_benchmark_corpus()
    out_path = Path(target_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = [f.to_dict() for f in fixtures]
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return out_path


if __name__ == "__main__":
    path = save_corpus_to_json()
    print(f"Generated {len(generate_benchmark_corpus())} benchmark fixtures at '{path}'.")
