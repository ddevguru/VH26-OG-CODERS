# LeakGuard STRIDE Threat Model

This document outlines the threat modeling analysis for LeakGuard following the **STRIDE** methodology (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege).

---

## 1. System Overview & Trust Boundaries

```
[ Scanned Repo / Codebase ] (UNTRUSTED)
           │
           ▼
   ┌──────────────────────────────────────────────┐
   │ LeakGuard Core Engine                        │
   │  - AST Parser (stdlib ast.parse)              │
   │  - CFG & Dataflow Builder                    │
   │  - Resource Semantics Evaluator              │
   └──────────────────────────────────────────────┘
           │                                 │
           ▼                                 ▼
┌──────────────────────┐          ┌──────────────────────┐
│ CLI / SARIF Reports  │          │ SaaS Control Plane   │
│ (Local Console/Disk) │          │ (Metadata Sync API)  │
└──────────────────────┘          └──────────────────────┘
```

**Trust Boundaries**:
1. **Boundary A (Host / Scanned Input)**: Scanned Python files, `.leakguard.yml` configs, baseline JSON files, and SARIF inputs are strictly **UNTRUSTED**.
2. **Boundary B (Engine Internal)**: AST parser and CFG builder operate within the local user process environment with restricted execution permissions.
3. **Boundary C (Network / SaaS API)**: HTTPS REST API endpoints connecting CLI scanner and Web Dashboard with the SaaS Control Plane.

---

## 2. STRIDE Analysis

| Threat Category | Threat Description | Attack Vector | Impact | Mitigation Status |
| :--- | :--- | :--- | :--- | :--- |
| **Spoofing** | Rogue scanner sending fake scan results to SaaS Control Plane | Forged API token or hijacked tenant headers | Unauthorized scan ingestion / telemetry pollution | **Mitigated**: JWT authentication with organization signature and tenant claim checks in SaaS API. |
| **Tampering** | Malicious source code attempting code execution via build hooks | Scanned repository contains malicious `setup.py` or dynamic imports | Arbitrary code execution on host machine | **Mitigated**: Zero code execution model. No `import`, `eval()`, `exec()`, or script execution. |
| **Repudiation** | User denies altering policy thresholds or baseline suppressions | Deletion or modification of suppression rules | Unaudited security posture changes | **Mitigated**: Immutable `AuditEvent` logging for all baseline and policy mutations in SaaS backend. |
| **Information Disclosure** | Leakage of customer proprietary source code to cloud SaaS | Cloud scan payload containing raw source snippets | Exposure of confidential IP | **Mitigated**: Local-first scan architecture. Only structured metadata (Rule ID, line, severity) is synced. |
| **Denial of Service** | Resource exhaustion attack (CPU/Memory/Stack) | Deeply nested syntax tree, huge files, or infinite symlinks | Scanner lockup, crash, or memory overflow | **Mitigated**: `max_ast_depth=500`, `max_file_size_bytes=5MB`, `max_files_limit=50,000`, per-file timeouts. |
| **Elevation of Privilege** | Path traversal escaping workspace root | File paths containing `../../etc/passwd` in SARIF or baseline | File overwrites or unauthorized file reads | **Mitigated**: Canonical path resolution (`Path.resolve()`) and path boundary verification. |

---

## 3. Threat Vector Specifics & Security Guarantees

### A. Untrusted Python Source Files
- **Threat**: Code containing malicious constructs such as `os.system()`, `subprocess.Popen()`, `exec()`, or `sys.exit()`.
- **Guarantee**: `ast.parse()` parses source tokens into an AST without evaluating expressions or running module top-level scope. `sys.exit()` in customer source code does not terminate LeakGuard.

### B. Pathological Syntactic Complexity
- **Threat**: Syntax bombs (e.g. 1,000 nested `if` statements or parentheses) designed to trigger Python stack overflow (`RecursionError`).
- **Guarantee**: `PythonAstParser._verify_depth()` inspects tree depth dynamically, raising a `ParserSecurityError` before stack overflow occurs.

### C. Subprocess Safety
- **Threat**: Shell injection via `git status` commands during `--changed-only` scans.
- **Guarantee**: All subprocess invocations pass command arguments as explicit lists (`["git", "status", "--porcelain"]`) with `shell=False` and a strict 10-second timeout.
