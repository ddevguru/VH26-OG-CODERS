# LeakGuard Static Analysis Benchmark Documentation

## Overview

The LeakGuard Benchmark Suite is a rigorous static-analysis evaluation, validation, and regression corpus comprising **320 Python code fixtures** across 4 lifecycle categories:

1. **SAFE**: Resources properly cleaned up via context managers (`with` / `async with`), `try...finally` blocks, explicit `close()` calls, or transferred via return/escape mechanisms.
2. **DEFINITE_LEAK**: Resources acquired via standard or custom calls and left unclosed on all execution paths or early returns.
3. **POTENTIAL_LEAK**: Resources closed during normal execution but left unclosed on unhandled exception branches, or closed conditionally on some execution paths.
4. **UNKNOWN**: Resources passed to third-party callbacks, dynamic handlers, or external framework managers where static ownership cannot be proven.

> [!IMPORTANT]
> **Validation Principles**:
> - **NOT an ML Dataset**: The benchmark is used for deterministic static analysis validation, accuracy evaluation, and regression tracking.
> - **No Benchmark Overfitting**: The analysis engine evaluates standard AST structures, Control Flow Graphs (CFG), and path-sensitive dataflow stores without fixture-specific shortcuts.
> - **Honest Accuracy Reporting**: Reports true empirical statistics without claiming artificial 100% precision or recall.

---

## Statistical Metrics Definitions

### Confusion Matrix Formulas
- **True Positives (TP)**: Leak fixtures (`DEFINITE_LEAK` / `POTENTIAL_LEAK`) correctly identified as leaks.
- **True Negatives (TN)**: Non-leak fixtures (`SAFE` / `UNKNOWN`) correctly classified as safe or unknown.
- **False Positives (FP)**: Safe fixtures incorrectly classified as leaks.
- **False Negatives (FN)**: Leak fixtures missed by analysis and classified as safe.

### Statistical Equations
- **Precision**: $$\text{Precision} = \frac{TP}{TP + FP}$$
- **Recall**: $$\text{Recall} = \frac{TP}{TP + FN}$$
- **F1 Score**: $$\text{F1} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$
- **False Positive Rate (FPR)**: $$\text{FPR} = \frac{FP}{FP + TN}$$
- **False Negative Rate (FNR)**: $$\text{FNR} = \frac{FN}{FN + TP}$$

---

## Execution Command

Run the complete benchmark suite via CLI:

```bash
leakguard benchmark
```

Or via module entrypoint:

```bash
python -m benchmarks.cli
```

Report outputs:
- JSON detailed results: `benchmarks/benchmark_results.json`
- Markdown summary report: `benchmarks/BENCHMARK_REPORT.md`
