import json
from pathlib import Path
from typing import Union, Dict, Any

from benchmarks.runner import BenchmarkReport


class BenchmarkReportExporter:
    """Exports benchmark execution results to JSON artifacts and human-readable Markdown reports."""

    def write_json_results(self, report: BenchmarkReport, output_path: Union[str, Path] = "benchmarks/benchmark_results.json") -> Path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "total_fixtures": report.total_fixtures,
            "total_loc": report.total_loc,
            "overall_confusion_matrix": report.overall_confusion_matrix,
            "overall_metrics": report.overall_metrics,
            "category_breakdown": report.category_breakdown,
            "resource_type_breakdown": report.resource_type_breakdown,
            "performance": report.performance,
            "results": report.results,
        }
        out_p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return out_p

    def write_markdown_report(self, report: BenchmarkReport, output_path: Union[str, Path] = "benchmarks/BENCHMARK_REPORT.md") -> Path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        m = report.overall_metrics
        cm = report.overall_confusion_matrix
        p = report.performance

        md_content = f"""# LeakGuard Static Analysis Benchmark Report

## Executive Summary

- **Total Corpus Fixtures**: {report.total_fixtures}
- **Total Lines of Code (LOC)**: {report.total_loc}
- **Scan Duration**: {p['duration_seconds']} seconds
- **Throughput**: {p['files_per_sec']} files/sec ({p['loc_per_sec']} LOC/sec)
- **Peak Memory Usage**: {p['peak_memory_mb']} MB

---

## Statistical Accuracy & Confusion Matrix

### Overall Metrics
| Metric | Value | Description |
| :--- | :--- | :--- |
| **Precision** | `{m['precision'] * 100:.2f}%` | True Positives / (True Positives + False Positives) |
| **Recall** | `{m['recall'] * 100:.2f}%` | True Positives / (True Positives + False Negatives) |
| **F1 Score** | `{m['f1_score'] * 100:.2f}%` | Harmonic mean of Precision and Recall |
| **False-Positive Rate (FPR)** | `{m['false_positive_rate'] * 100:.2f}%` | False Positives / (False Positives + True Negatives) |
| **False-Negative Rate (FNR)** | `{m['false_negative_rate'] * 100:.2f}%` | False Negatives / (False Negatives + True Positives) |

### Global Confusion Matrix
- **True Positives (TP)**: `{cm['tp']}`
- **True Negatives (TN)**: `{cm['tn']}`
- **False Positives (FP)**: `{cm['fp']}`
- **False Negatives (FN)**: `{cm['fn']}`

---

## Category Breakdown

| Category | Fixture Count | Precision | Recall | F1 Score |
| :--- | :--- | :--- | :--- | :--- |
"""
        for cat, data in report.category_breakdown.items():
            cm_c = data['metrics']
            md_content += f"| **{cat}** | `{data['confusion_matrix']['tp'] + data['confusion_matrix']['tn'] + data['confusion_matrix']['fp'] + data['confusion_matrix']['fn']}` | `{cm_c['precision'] * 100:.1f}%` | `{cm_c['recall'] * 100:.1f}%` | `{cm_c['f1_score'] * 100:.1f}%` |\n"

        md_content += """
---

## Resource Type Breakdown

| Resource Type | TP | TN | FP | FN | Precision | Recall |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
"""
        for res, data in report.resource_type_breakdown.items():
            cm_r = data['confusion_matrix']
            met_r = data['metrics']
            md_content += f"| **{res}** | `{cm_r['tp']}` | `{cm_r['tn']}` | `{cm_r['fp']}` | `{cm_r['fn']}` | `{met_r['precision'] * 100:.1f}%` | `{met_r['recall'] * 100:.1f}%` |\n"

        md_content += """
---

## Methodology & Safety Principles

1. **No ML Training / Overfitting**: LeakGuard uses a pure AST, CFG, and path-sensitive dataflow analysis engine. The benchmark corpus is used for regression verification and empirical accuracy measurement.
2. **Conservative Leak Classification**: Unprovable ownership transfers or complex dynamic callbacks fallback to `UNKNOWN` or `POTENTIAL_LEAK` rather than triggering ungrounded `DEFINITE_LEAK` alerts.
"""
        out_p.write_text(md_content, encoding="utf-8")
        return out_p
