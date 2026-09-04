import sys
from pathlib import Path

from benchmarks.runner import BenchmarkRunner
from benchmarks.report import BenchmarkReportExporter


def run_benchmark_suite() -> int:
    print("Starting LeakGuard Benchmark Suite (320+ Fixtures)...")
    runner = BenchmarkRunner()
    report = runner.run_benchmark()

    exporter = BenchmarkReportExporter()
    json_path = exporter.write_json_results(report)
    md_path = exporter.write_markdown_report(report)

    m = report.overall_metrics
    p = report.performance

    print(f"\n=======================================================")
    print(f" LEAKGUARD BENCHMARK RESULTS ({report.total_fixtures} FIXTURES, {report.total_loc} LOC)")
    print(f"=======================================================")
    print(f" Precision           : {m['precision'] * 100:.2f}%")
    print(f" Recall              : {m['recall'] * 100:.2f}%")
    print(f" F1 Score            : {m['f1_score'] * 100:.2f}%")
    print(f" False Positive Rate : {m['false_positive_rate'] * 100:.2f}%")
    print(f" False Negative Rate : {m['false_negative_rate'] * 100:.2f}%")
    print(f"-------------------------------------------------------")
    print(f" Scan Duration       : {p['duration_seconds']}s")
    print(f" Throughput          : {p['files_per_sec']} files/sec ({p['loc_per_sec']} LOC/sec)")
    print(f" Peak Memory Usage   : {p['peak_memory_mb']} MB")
    print(f"-------------------------------------------------------")
    print(f" Reports written to  : '{json_path}' & '{md_path}'")
    print(f"=======================================================\n")

    return 0


if __name__ == "__main__":
    sys.exit(run_benchmark_suite())
