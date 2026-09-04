from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class ConfusionMatrix:
    tp: int = 0
    tn: int = 0
    fp: int = 0
    fn: int = 0

    def add(self, is_tp: bool, is_tn: bool, is_fp: bool, is_fn: bool) -> None:
        if is_tp:
            self.tp += 1
        if is_tn:
            self.tn += 1
        if is_fp:
            self.fp += 1
        if is_fn:
            self.fn += 1


@dataclass
class AccuracyMetrics:
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0

    @classmethod
    def compute(cls, cm: ConfusionMatrix) -> 'AccuracyMetrics':
        tp, tn, fp, fn = cm.tp, cm.tn, cm.fp, cm.fn

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

        return cls(
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
            false_positive_rate=round(fpr, 4),
            false_negative_rate=round(fnr, 4),
        )


@dataclass
class PerformanceStats:
    total_fixtures: int = 0
    total_loc: int = 0
    duration_seconds: float = 0.0
    files_per_sec: float = 0.0
    loc_per_sec: float = 0.0
    peak_memory_mb: float = 0.0
