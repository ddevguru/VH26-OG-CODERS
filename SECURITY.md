# LeakGuard Security Policy & Architecture

## Security Principles & Mandate

LeakGuard is an AST-based static resource lifetime analyzer designed to scan untrusted codebases without executing customer code or compromising host system integrity.

### 1. Absolute Zero Customer Code Execution Guarantee
- **Static Analysis Only**: LeakGuard analyzes source code strictly via standard library `ast.parse()` to produce an Abstract Syntax Tree (AST) and Control-Flow Graph (CFG).
- **No Dynamic Evaluation**: LeakGuard **NEVER** invokes `eval()`, `exec()`, `importlib.import_module()`, `sys.path` injection, or `__import__()` on scanned Python code.
- **No Build Hooks or Setup Scripts**: LeakGuard **NEVER** executes `setup.py`, `pytest` plugins, `poetry` scripts, or customer build hooks during scanning.

### 2. Isolation & Resource Bounds
- **AST Depth Limit**: Maximum recursion depth of 500 (configurable via `max_ast_depth`) prevents stack overflow from deeply nested syntax trees.
- **File Size Limit**: Scanned Python files are bounded by default to 5 MB (`max_file_size_bytes`) to avoid memory allocation spikes.
- **Discovery Capping**: Target directory discovery is capped at 50,000 files (`max_files_limit`) to protect against runaway symlink traversal or zip bombs.
- **Per-File Timeouts**: Analysis per file is bounded (`per_file_timeout_seconds`) to prevent CPU lockup on pathological control flow graphs.

### 3. Path Traversal & Symlink Safety
- All input paths are resolved into canonical absolute paths (`Path.resolve()`).
- Symlink cycles and circular directory loops are detected and ignored during file discovery.
- Path traversal sequences (`../`) in baseline files or SARIF exports are sanitized.

### 4. SaaS Control Plane Security & Data Privacy
- **Metadata Only by Default**: Customer source code is **NEVER** uploaded to the LeakGuard SaaS control plane. Only structured finding metadata (rule ID, line number, resource type, severity, confidence) is transmitted.
- **Tenant Isolation & RBAC**: SaaS APIs enforce JWT Bearer authentication, tenant isolation by organization/repository, and role-based access control (Owner, Admin, Security, Developer, Viewer).

---

## Reporting Vulnerabilities

If you discover a security vulnerability in LeakGuard, please report it privately:

- **Email**: `security@leakguard.io`
- **Response SLA**: Initial triage within 24 hours; fix/advisory within 7 business days.
- Please include reproduction steps, affected versions, and potential impact. Do NOT publish security issues publicly prior to coordinated release.
