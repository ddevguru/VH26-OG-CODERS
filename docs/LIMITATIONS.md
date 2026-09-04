# LeakGuard Static Analysis Known Limitations

## Overview
LeakGuard is a 100% static, offline, deterministic resource-lifetime analysis engine for Python repositories. To guarantee safety and prevent execution of untrusted customer code, LeakGuard operates purely on ASTs, Control Flow Graphs (CFG), and path-sensitive dataflow stores.

---

## Technical Limitations & Boundaries

### 1. Inter-procedural Call Boundaries
- **Current Behavior**: Intra-procedural analysis per function/method block.
- **Limitation**: When a resource object is passed into an un-analyzed external helper function (e.g. `helper(f)`), LeakGuard conservatively treats the resource as transferred/escaped (`TRANSFERRED` / `UNKNOWN`) to avoid false positives. If the helper fails to close it, LeakGuard will not flag a `DEFINITE_LEAK` unless custom rules configure `helper` as a non-releasing sink.

### 2. Dynamic Code Execution & Reflection
- **Limitation**: Python constructs utilizing dynamic evaluation (`eval()`, `exec()`, `importlib.import_module()`, `globals()`, `locals()`, `getattr()`, or dynamic `__dict__` manipulation) cannot be analyzed statically.
- **Handling**: Dynamic calls are safely ignored without raising runtime parser errors.

### 3. Indirect Container & Complex Collection Aliasing
- **Limitation**: Storing resources inside nested collections (e.g., `list_of_files[0][key] = f`) tracks container reference escaping (`ESCAPED`), but element-level lifecycle tracking inside complex dynamic collections is unproven.
- **Classification**: Classified conservatively as `UNKNOWN` or `TRANSFERRED`.

### 4. Custom Third-Party Cleanup Signatures
- **Limitation**: Third-party proprietary libraries that use non-standard cleanup method names (e.g. `res.dispose_handle()`) without registering a rule in `.leakguard.yml` will not be recognized as cleanup calls.
- **Remediation**: Users can define custom rule packs in `.leakguard.yml` under `custom_rules`.

### 5. Multiprocessing & Asynchronous Queue IPC
- **Limitation**: Passing a file descriptor or socket handle across multiprocessing queues or IPC pipes is tracked as `TRANSFERRED`/`ESCAPED`. LeakGuard does not simulate remote process lifecycles across process boundaries.

---

## Soundness & Completeness Statement
Static analysis of Turing-complete dynamic programming languages like Python is subject to Rice's Theorem. LeakGuard prioritizes precision and developer trust by enforcing conservative classification rules:
- **No False Positives on Returned Resources**: Returning a resource transfers ownership to the caller.
- **No False Positives on Context Managers**: `with` and `async with` blocks guarantee context exit cleanup.
- **Conservative Fallback**: Unproven ownership states result in `UNKNOWN` or `POTENTIAL_LEAK` rather than false `DEFINITE_LEAK` warnings.
