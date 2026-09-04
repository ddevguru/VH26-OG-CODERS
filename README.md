# LEAKGUARD

**AST-Based Static Resource Leak Detection for Python**

LeakGuard is a commercial-grade, deterministic static analysis platform designed to detect Python resource leaks (unclosed files, database connections, sockets, HTTP sessions, subprocesses, locks, and temp files) across realistic execution paths before code reaches production.

## Key Principles
- **100% Offline & Deterministic**: Built using standard library Python `ast` and intra-procedural path-sensitive dataflow analysis.
- **Zero Source Execution**: Analyzes code statically without executing target source files.
- **No Regex Logic**: Uses formal AST visitors and control-flow graphs for analysis decisions.
- **Enterprise Ready**: Full SARIF 2.1.0 report generation, pre-commit hooks, GitHub Actions CI integration, and Rich terminal output.

## Installation

```bash
pip install -e .
```

## Usage

### CLI Scan
```bash
leakguard scan ./examples/vulnerable
```

### Live Developer Watch & Resource Radar
```bash
leakguard watch .
```
Options:
- `--debounce 300`: Debounce rapid saves (ms, default 300)
- `--quiet`: Suppress live status updates
- `--verbose`: Show detailed debug logs
- `--json`: Output machine-readable JSON live event streams
- `--no-color`: Disable Rich terminal formatting

### AI Code Review & Multi-Agent System
```bash
leakguard review . --mode detailed
leakguard explain --finding LEAK_001
leakguard fix --file services/database.py --finding LEAK_001
leakguard verify --patch candidate.patch
```
Options:
- `--mode [concise|detailed|security|senior-engineer|developer-friendly]`: Review mode
- `--commit <sha>`: Review specific Git commit
- `--pr <number>`: Review Pull Request
- `--json`: Output machine-readable JSON review stream

### SARIF Export for GitHub Security / Code Scanning
```bash
leakguard scan ./examples/vulnerable --format sarif --out results.sarif
```

### Pre-commit Integration
Add to your `.pre-commit-config.yaml`:
```yaml
  - repo: local
    hooks:
      - id: leakguard
        name: LeakGuard Resource Leak Checker
        entry: leakguard scan
        language: python
        types: [python]
```

## AI Code Review & Multi-Agent Architecture

LeakGuard extends deterministic AST static analysis with an AI Orchestration and Verification layer:
- **Sole Source of Truth**: The deterministic AST/CFG dataflow solver holds 100% authority over leak detection. AI never decides whether code is safe vs leaking.
- **Multi-Agent Orchestration**: Specialized agents (Resource Hunter, Code Reviewer, Root Cause, Security Impact, Fix Generator, Regression, Verification, PR, Documentation, Policy).
- **Authoritative Isolated Verification**: Candidate AI patches are **never trusted automatically**. Every fix candidate is applied in an isolated workspace and re-analyzed by the deterministic LeakGuard engine. Only patches that clear the original leak without introducing new findings receive the `VERIFIED_FIX` status.
- **LangFuse Tracing**: Per-tenant (`org_id`) and per-user (`user_id`) execution tracing, token metrics, and timeline logging.
- **Multi-Provider Support**: Supports local **Ollama** models, **OpenAI** API format, and `MockLLMProvider` for offline testing.
- **Secret Redaction**: Automatically sanitizes API keys, passwords, bearer tokens, AWS credentials, and connection strings before prompt execution.

## Live Developer Experience (`leakguard watch`)

LeakGuard includes a real-time terminal watcher and Live Resource Radar:
- **Zero Execution Security**: Monitors `.py` file changes and runs intra-procedural static analysis without running customer code.
- **Debounced Scans**: Coalesces rapid keystrokes/saves into a single analysis run.
- **Incomplete Syntax Tolerance**: Gracefully handles incomplete syntax while typing without crashing.
- **Resource Lifecycle Radar**: Visualizes resource acquisition, transfer, release, and exception paths in terminal.
- **Live Finding Identity Tracking**: Dynamically reports `NEW LEAK`, `LEAK RESOLVED`, and classification shifts (`POTENTIAL` -> `DEFINITE` -> `SAFE`).

### Leak Firewall & PR Leak Diff
```bash
leakguard firewall .                               # Evaluate developer policies (PASS / BLOCK)
leakguard pr-diff --before target_v1 --after target_v2 --pr 42 # Compare Before vs After leak findings
```

### Phase 16 Advanced Features
```bash
leakguard risk .                                   # Bounded 0-100 deterministic risk scoring
leakguard ownership .                              # Resource Ownership Graph visualizer
leakguard what-if --file database.py --line 42     # Static hypothetical exception simulation
leakguard fix --file app.py --strategy context-manager # Strategy pattern AI auto fixer & verification
```

## Advanced Intelligence & Resource Risk System (Phase 16)

- **Deterministic Risk Scoring (0–100)**: Evaluates resource category weights (`DATABASE`=85, `SOCKET`=80, `FILE`=50), classification severity, exposure multipliers, and control-flow path complexity. **Zero LLM dependencies** ensure 100% reproducible security scoring.
- **Resource Ownership Graph**: Constructs a serializable AST/CFG-backed graph exposing scope ownership (`OWNS`), acquisition (`CREATES`), derivative handles (`conn` → `cursor`), transfers, escapes, and leak paths.
- **What-If Static Exception Simulator**: Simulates stack unwinding and exception paths statically without executing customer code. Reports cleanup status (`GUARANTEED` vs `UNGUARANTEED`) and affected resource state across execution paths.
- **Strategy Pattern AI Auto Fixer**: Generates candidate cleanup patches using standard strategy patterns (`ContextManagerStrategy`, `TryFinallyStrategy`, `CloseInsertionStrategy`, `ExceptionSafeCleanupStrategy`, `AsyncCleanupStrategy`) and verifies patches in isolated temporary workspaces before marking `VERIFIED_FIX`.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full architectural documentation.
