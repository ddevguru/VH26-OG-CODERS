# LEAKGUARD

**AST-Based Static Resource Leak Detection for CI/CD**

LeakGuard is a deterministic static analysis engine designed to catch Java resource leaks (unclosed streams, database connections, readers/writers, sockets, and auto-closeable resources) before they hit production.

## Features
- **Deterministic AST & Control-Flow Analysis**: Built on `tree-sitter-java` and path-sensitive dataflow analysis.
- **Precision Flow Engine**: Accurate handling of early returns, `try/catch/finally`, `try-with-resources`, and exception paths.
- **CI/CD Native**: SARIF 2.1.0 output support, configurable severity thresholds, GitHub Action integration, and pre-commit hooks.
- **Zero AI Core**: 100% deterministic code analysis without hallucination or LLM non-determinism.

## Installation
```bash
pip install -e .
```

## Quick Start
```bash
leakguard scan ./examples/vulnerable --threshold high --format sarif --out results.sarif
```
