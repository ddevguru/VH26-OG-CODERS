# LeakGuard Static Analysis Benchmark Report

## Executive Summary

- **Total Corpus Fixtures**: 320
- **Total Lines of Code (LOC)**: 1710
- **Scan Duration**: 1.239 seconds
- **Throughput**: 258.26 files/sec (1380.06 LOC/sec)
- **Peak Memory Usage**: 0.28 MB

---

## Statistical Accuracy & Confusion Matrix

### Overall Metrics
| Metric | Value | Description |
| :--- | :--- | :--- |
| **Precision** | `98.82%` | True Positives / (True Positives + False Positives) |
| **Recall** | `98.24%` | True Positives / (True Positives + False Negatives) |
| **F1 Score** | `98.53%` | Harmonic mean of Precision and Recall |
| **False-Positive Rate (FPR)** | `1.33%` | False Positives / (False Positives + True Negatives) |
| **False-Negative Rate (FNR)** | `1.76%` | False Negatives / (False Negatives + True Positives) |

### Global Confusion Matrix
- **True Positives (TP)**: `167`
- **True Negatives (TN)**: `148`
- **False Positives (FP)**: `2`
- **False Negatives (FN)**: `3`

---

## Category Breakdown

| Category | Fixture Count | Precision | Recall | F1 Score |
| :--- | :--- | :--- | :--- | :--- |
| **SAFE** | `90` | `0.0%` | `0.0%` | `0.0%` |
| **DEFINITE_LEAK** | `90` | `100.0%` | `96.7%` | `98.3%` |
| **POTENTIAL_LEAK** | `80` | `100.0%` | `100.0%` | `100.0%` |
| **UNKNOWN** | `60` | `0.0%` | `0.0%` | `0.0%` |

---

## Resource Type Breakdown

| Resource Type | TP | TN | FP | FN | Precision | Recall |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FILE** | `26` | `25` | `1` | `2` | `96.3%` | `92.9%` |
| **SOCKET** | `25` | `21` | `1` | `0` | `96.2%` | `100.0%` |
| **DATABASE** | `24` | `22` | `0` | `0` | `100.0%` | `100.0%` |
| **HTTP** | `25` | `20` | `0` | `0` | `100.0%` | `100.0%` |
| **SUBPROCESS** | `23` | `20` | `0` | `0` | `100.0%` | `100.0%` |
| **LOCK** | `22` | `19` | `0` | `0` | `100.0%` | `100.0%` |
| **TEMPFILE** | `22` | `20` | `0` | `0` | `100.0%` | `100.0%` |
| **CUSTOM** | `0` | `1` | `0` | `1` | `0.0%` | `0.0%` |

---

## Methodology & Safety Principles

1. **No ML Training / Overfitting**: LeakGuard uses a pure AST, CFG, and path-sensitive dataflow analysis engine. The benchmark corpus is used for regression verification and empirical accuracy measurement.
2. **Conservative Leak Classification**: Unprovable ownership transfers or complex dynamic callbacks fallback to `UNKNOWN` or `POTENTIAL_LEAK` rather than triggering ungrounded `DEFINITE_LEAK` alerts.
