import time
import tracemalloc
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path

from core.analysis.engine import AnalysisEngine
from core.common.models import Classification
from benchmarks.corpus.generator import generate_benchmark_corpus, BenchmarkFixture
from benchmarks.metrics import ConfusionMatrix, AccuracyMetrics, PerformanceStats


@dataclass
class FixtureResult:
    fixture_id: str
    name: str
    category: str
    expected_classification: str
    predicted_classification: str
    matched: bool
    confidence: str
    loc: int
    duration_ms: float


@dataclass
class BenchmarkReport:
    total_fixtures: int
    total_loc: int
    overall_confusion_matrix: Dict[str, int]
    overall_metrics: Dict[str, float]
    category_breakdown: Dict[str, Dict[str, Any]]
    resource_type_breakdown: Dict[str, Dict[str, Any]]
    performance: Dict[str, Any]
    results: List[Dict[str, Any]]


class BenchmarkRunner:
    """Executes LeakGuard analysis against all benchmark corpus fixtures and computes performance & accuracy metrics."""

    def __init__(self) -> None:
        self.engine = AnalysisEngine()

    def _determine_predicted_classification(self, diagnostics) -> str:
        if not diagnostics:
            return Classification.SAFE.value
        classifications = [d.classification.value for d in diagnostics]
        if Classification.DEFINITE_LEAK.value in classifications:
            return Classification.DEFINITE_LEAK.value
        elif Classification.POTENTIAL_LEAK.value in classifications:
            return Classification.POTENTIAL_LEAK.value
        elif Classification.UNKNOWN.value in classifications:
            return Classification.UNKNOWN.value
        return Classification.SAFE.value

    def run_benchmark(self, fixtures: Optional[List[BenchmarkFixture]] = None) -> BenchmarkReport:
        if not fixtures:
            fixtures = generate_benchmark_corpus()

        tracemalloc.start()
        start_time = time.time()

        overall_cm = ConfusionMatrix()
        category_cms: Dict[str, ConfusionMatrix] = {
            "SAFE": ConfusionMatrix(),
            "DEFINITE_LEAK": ConfusionMatrix(),
            "POTENTIAL_LEAK": ConfusionMatrix(),
            "UNKNOWN": ConfusionMatrix(),
        }
        resource_cms: Dict[str, ConfusionMatrix] = {}

        fixture_results: List[FixtureResult] = []
        total_loc = 0

        for fix in fixtures:
            loc = len(fix.code.strip().splitlines())
            total_loc += loc

            t0 = time.time()
            diags = self.engine.analyze_code(fix.code, filename=f"{fix.fixture_id}.py")
            t_elapsed_ms = (time.time() - t0) * 1000.0

            predicted = self._determine_predicted_classification(diags)
            expected = fix.expected_classification

            matched = False
            is_tp = False
            is_tn = False
            is_fp = False
            is_fn = False

            if expected in (Classification.DEFINITE_LEAK.value, Classification.POTENTIAL_LEAK.value):
                if predicted in (Classification.DEFINITE_LEAK.value, Classification.POTENTIAL_LEAK.value):
                    is_tp = True
                    matched = True
                else:
                    is_fn = True
            elif expected == Classification.SAFE.value:
                if predicted == Classification.SAFE.value:
                    is_tn = True
                    matched = True
                else:
                    is_fp = True
            elif expected == Classification.UNKNOWN.value:
                if predicted in (Classification.UNKNOWN.value, Classification.POTENTIAL_LEAK.value, Classification.SAFE.value):
                    is_tn = True
                    matched = True
                else:
                    is_fp = True

            overall_cm.add(is_tp, is_tn, is_fp, is_fn)

            if fix.category in category_cms:
                category_cms[fix.category].add(is_tp, is_tn, is_fp, is_fn)

            if fix.resource_type not in resource_cms:
                resource_cms[fix.resource_type] = ConfusionMatrix()
            resource_cms[fix.resource_type].add(is_tp, is_tn, is_fp, is_fn)

            fixture_results.append(
                FixtureResult(
                    fixture_id=fix.fixture_id,
                    name=fix.name,
                    category=fix.category,
                    expected_classification=expected,
                    predicted_classification=predicted,
                    matched=matched,
                    confidence=fix.expected_confidence,
                    loc=loc,
                    duration_ms=round(t_elapsed_ms, 3),
                )
            )

        duration = time.time() - start_time
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mem_mb = peak_mem / (1024.0 * 1024.0)
        files_per_sec = len(fixtures) / duration if duration > 0 else 0.0
        loc_per_sec = total_loc / duration if duration > 0 else 0.0

        overall_metrics = AccuracyMetrics.compute(overall_cm)

        cat_breakdown: Dict[str, Dict[str, Any]] = {}
        for cat_name, cat_cm in category_cms.items():
            cat_metrics = AccuracyMetrics.compute(cat_cm)
            cat_breakdown[cat_name] = {
                "confusion_matrix": asdict(cat_cm),
                "metrics": asdict(cat_metrics),
            }

        res_breakdown: Dict[str, Dict[str, Any]] = {}
        for res_name, res_cm in resource_cms.items():
            res_metrics = AccuracyMetrics.compute(res_cm)
            res_breakdown[res_name] = {
                "confusion_matrix": asdict(res_cm),
                "metrics": asdict(res_metrics),
            }

        perf_stats = PerformanceStats(
            total_fixtures=len(fixtures),
            total_loc=total_loc,
            duration_seconds=round(duration, 3),
            files_per_sec=round(files_per_sec, 2),
            loc_per_sec=round(loc_per_sec, 2),
            peak_memory_mb=round(peak_mem_mb, 2),
        )

        return BenchmarkReport(
            total_fixtures=len(fixtures),
            total_loc=total_loc,
            overall_confusion_matrix=asdict(overall_cm),
            overall_metrics=asdict(overall_metrics),
            category_breakdown=cat_breakdown,
            resource_type_breakdown=res_breakdown,
            performance=asdict(perf_stats),
            results=[asdict(fr) for fr in fixture_results],
        )
