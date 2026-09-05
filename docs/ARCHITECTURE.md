# LeakGuard Architecture Documentation

> 📖 **Deep-Dive Technical Specification**: See [TECHNICAL_ARCHITECTURE.md](file:///c:/LeakGaurd/docs/TECHNICAL_ARCHITECTURE.md) for full code mapping, AI agent implementations, AST dataflow equations, database schemas, and CLI command source code locations.

## Overview
LeakGuard is a static analysis platform implemented in Python (3.11+) designed to analyze Python repositories for resource lifecycle issues (unclosed files, database connections, sockets, HTTP sessions, subprocesses, locks, temp files, and custom resources) across control flow execution paths without running untrusted source code.

---

## Architectural Principles

1. **Deterministic Static Analysis**: Uses Python's standard library `ast` parser. Code is parsed into an Abstract Syntax Tree (AST), transformed into an Intra-procedural Control Flow Graph (CFG), and evaluated using path-sensitive dataflow analysis.
2. **Zero Code Execution**: LeakGuard never executes target Python source code. All analysis occurs purely on abstract syntax graphs.
3. **No Regex Analysis**: LeakGuard does not rely on regular expression string matching for core security decisions.
4. **Structured Security Diagnostics**: All findings conform to SARIF 2.1.0 schemas and structured Pydantic models.

---

## Core Component Pipeline

```
  +-----------------------+
  |  Target Python Source |
  +-----------+-----------+
              |
              v
   [ 1. Python AST Parser ]   --> Safe stdlib ast.parse() with depth/span checks
              |
              v
  [ 2. AST Visitor & Collect] --> AST Scope & Function identification
              |
              v
  [ 3. CFG Builder Engine  ]  --> Construct basic blocks & control flow edges
              |
              v
 [ 4. Path Dataflow Analysis ] --> Intra-procedural path-sensitive analysis
              |
              v
 [ 5. Resource State Store  ] --> Track lifecycle (UNACQUIRED -> OPEN_MUST_CLOSE -> CLOSED/LEAKED)
              |
              v
 [ 6. Rule & Diagnostic Engine] -> Generate findings & SARIF/Rich reports
```

---

## Domain Model Taxonomy

| Model Class | Category | Purpose |
|---|---|---|
| `ResourceType` | Common | Enum representing supported resource types (`FILE`, `DATABASE`, `SOCKET`, `HTTP`, `SUBPROCESS`, `LOCK`, `TEMPFILE`, `CUSTOM`) |
| `ResourceIdentity` | Common | Symbol representation tracking acquisition location, variable name, and scope |
| `ResourceAcquisition` | Common | Event recorded when a resource is instantiated (e.g. `open()`, `sqlite3.connect()`) |
| `ResourceRelease` | Common | Event recorded when a resource cleanup method is invoked (e.g. `close()`, `__exit__`) |
| `ResourceState` | Common | Finite state machine values (`UNACQUIRED`, `OPEN_MUST_CLOSE`, `CLOSED`, `TRANSFERRED`, `MAYBE_LEAKED`, `LEAKED`, `ESCAPED`, `UNKNOWN`) |
| `OwnershipState` | Common | Ownership tracking enum (`OWNED`, `BORROWED`, `TRANSFERRED`, `ESCAPED`, `UNKNOWN`) |
| `ControlFlowNode` | CFG | Node representing a basic block of AST statements |
| `ControlFlowEdge` | CFG | Directed edge between control flow nodes (`NORMAL`, `TRUE_BRANCH`, `FALSE_BRANCH`, `EXCEPTIONAL`, `FINALLY`) |
| `Diagnostic` | Reporting | Structured finding containing diagnostic metadata, execution path, location, and remediation |
| `Finding` | Reporting | Serializable container linking finding ID, diagnostic details, and fingerprint |
| `ScanResult` | Reporting | Aggregate results of a repository scan including metrics, findings, and policy pass status |
| `Policy` | Configuration | User policy defining thresholds for CI failure |
| `RuleDefinition` | Rules | Rule metadata and catalog matching rules |

---

## Package Hierarchy

- `core/parser`: Safe python AST parsing with line/column span extraction.
- `core/ast`: Visitor pattern abstractions for function, scope, and variable tracking.
- `core/cfg`: Intra-procedural control flow graph generation for conditional branches, loops, `try/except/finally`, and context managers (`with` / `async with`).
- `core/scopes`: Lexical and functional scope hierarchy tracking.
- `core/symbols`: Symbol table management for variable lookups.
- `core/resources`: Resource catalog defining acquisition/release signatures and resource state lattice tracking.
- `core/ownership`: Ownership transfer tracking (e.g. return statements, object attribute assignment).
- `core/dataflow`: Path-sensitive worklist dataflow solver.
- `core/analysis`: Engine orchestrator linking parser, CFG, analyzer, and reporting.
- `core/rules`: Static analysis rule definitions.
- `core/diagnostics`: Builder for structured diagnostic findings.
- `core/reporting`: Console (Rich UI), JSON, and SARIF 2.1.0 output formatting.
- `core/watch`: Live watch subsystem (`Watcher`, `EventDebouncer`, `WatchState`, `LiveRadarRenderer`).

- `interfaces/cli`: Command-line interface built with `typer` (`leakguard scan <path>`, `leakguard watch <path>`).
- `interfaces/ci`: GitHub Actions wrapper and SARIF exporter.
- `interfaces/precommit`: Pre-commit hook implementation.
- `interfaces/api`: Programmatic Python API client for embedding LeakGuard into tools/workflows.

---

## Watch Subsystem (`leakguard watch`)

The live watch subsystem provides incremental static analysis with zero customer code execution:

```
  FileSystem Event (File Modified/Created/Deleted)
                   │
                   ▼
         [ FileWatcher Engine ]  (Watchdog API with Polling Fallback)
                   │
                   ▼
        [ EventDebouncer Queue ]  (Coalesces edits within 300ms window)
                   │
                   ▼
         [ Analysis Engine ]     (Performs incremental file scan & AST parse)
                   │
                   ├──> SyntaxError -> [ WatchState: Incomplete Syntax ]
                   │
                   └──> Valid AST -> [ WatchState: Update Findings & Diffs ]
                                             │
                                             ▼
                                  [ LiveRadarRenderer UI ]
                                (Displays Status, Radar & Lifecycle Diagrams)
```

1. **Safety & Zero Code Execution**: Pure AST/CFG parsing without importing or executing any code.
2. **Debouncing**: `EventDebouncer` prevents duplicate analysis when IDEs issue multiple file write operations within milliseconds.
3. **Syntax Error Resilience**: Captures `SyntaxError` cleanly, indicating `Syntax Incomplete` in the terminal UI without interrupting the watch thread.
4. **Stable Finding Identity**: Tracks findings across file edits using deterministic identity keys (`file::func::res_var::line::rule`).

---

## Verification & Quality Assurance

- **Unit & Integration Tests**: `pytest` suite testing parser, AST collector, CFG builder, dataflow analyzer, watcher subsystem, and regression examples.
- **Coverage**: Configured with `pytest-cov`.
- **Linting & Formatting**: Configured with `ruff`.
- **Type Checking**: Configured with `mypy`.
