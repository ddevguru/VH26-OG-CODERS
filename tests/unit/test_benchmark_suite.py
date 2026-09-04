import json
import pytest
from pathlib import Path

from benchmarks.corpus.generator import generate_benchmark_corpus, save_corpus_to_json
from benchmarks.metrics import ConfusionMatrix, AccuracyMetrics
from benchmarks.runner import BenchmarkRunner
from benchmarks.report import BenchmarkReportExporter


def test_benchmark_corpus_generator_fixture_count():
    fixtures = generate_benchmark_corpus()
    assert len(fixtures) >= 300, f"Expected at least 300 fixtures, got {len(fixtures)}"


def test_benchmark_corpus_categories():
    fixtures = generate_benchmark_corpus()
    categories = {f.category for f in fixtures}
    assert "SAFE" in categories
    assert "DEFINITE_LEAK" in categories
    assert "POTENTIAL_LEAK" in categories
    assert "UNKNOWN" in categories

    resource_types = {f.resource_type for f in fixtures}
    assert "FILE" in resource_types
    assert "DATABASE" in resource_types
    assert "SOCKET" in resource_types
    assert "HTTP" in resource_types


def test_confusion_matrix_metrics_calculation():
    cm = ConfusionMatrix(tp=90, tn=80, fp=10, fn=5)
    metrics = AccuracyMetrics.compute(cm)

    assert metrics.precision == round(90 / 100, 4)
    assert metrics.recall == round(90 / 95, 4)
    assert metrics.false_positive_rate == round(10 / 90, 4)
    assert metrics.false_negative_rate == round(5 / 95, 4)


def test_benchmark_runner_execution():
    runner = BenchmarkRunner()
    # Test on a small subset of fixtures
    corpus = generate_benchmark_corpus()[:10]
    report = runner.run_benchmark(corpus)

    assert report.total_fixtures == 10
    assert "precision" in report.overall_metrics
    assert report.performance["files_per_sec"] >= 0.0


def test_benchmark_report_exporter(tmp_path: Path):
    runner = BenchmarkRunner()
    corpus = generate_benchmark_corpus()[:5]
    report = runner.run_benchmark(corpus)

    json_file = tmp_path / "benchmark_results.json"
    md_file = tmp_path / "BENCHMARK_REPORT.md"

    exporter = BenchmarkReportExporter()
    exporter.write_json_results(report, json_file)
    exporter.write_markdown_report(report, md_file)

    assert json_file.exists()
    assert md_file.exists()

    data = json.loads(json_file.read_text(encoding="utf-8"))
    assert data["total_fixtures"] == 5
    assert "overall_metrics" in data
