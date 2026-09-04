# LeakGuard Sample Repository

This sample repository demonstrates static resource lifetime analysis using LeakGuard across 5 canonical resource patterns:

## Vulnerable Resource Patterns (2 Leaks Detected)
1. `vulnerable/early_return_leak.py`: Resource `f` is acquired via `open()` and left unclosed on an early return branch (`Classification.DEFINITE_LEAK`).
2. `vulnerable/exception_path_leak.py`: Resource `f` is acquired without context manager or try/finally protection before a `raise` statement (`Classification.POTENTIAL_LEAK`).

## Safe Resource Patterns (3 Safe Patterns Verified)
3. `safe/with_statement_safe.py`: Managed via `with open(...) as f:` context manager (`Classification.SAFE`).
4. `safe/try_finally_safe.py`: Cleaned up inside a `finally` block (`Classification.SAFE`).
5. `safe/ownership_transfer_safe.py`: Ownership transferred to caller via `return f` (`Classification.SAFE`).

## Reproducible Scan Command

Run LeakGuard against this sample repository:

```bash
leakguard scan . --format text --fail-on error
```
