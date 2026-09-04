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

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full architectural documentation.
