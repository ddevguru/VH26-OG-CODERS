from typing import List, Union
from pathlib import Path

from core.common.models import Diagnostic, ScanResult
from presentation.terminal.formatter import TerminalFormatter
from presentation.sarif.exporter import SarifExporter
from presentation.json.exporter import JsonExporter


class ReportingEngine:
    """Reporting Facade orchestrating terminal output, JSON export, and SARIF 2.1.0 generation."""

    def __init__(self) -> None:
        self.terminal_formatter = TerminalFormatter()
        self.sarif_exporter = SarifExporter()
        self.json_exporter = JsonExporter()

    def report_terminal(self, diagnostics: List[Diagnostic]) -> None:
        self.terminal_formatter.print_diagnostics(diagnostics)

    def export_sarif(self, diagnostics: List[Diagnostic], output_path: Union[str, Path]) -> None:
        self.sarif_exporter.write_sarif_file(diagnostics, output_path)

    def export_json(self, diagnostics: List[Diagnostic], output_path: Union[str, Path]) -> None:
        self.json_exporter.write_json_file(diagnostics, output_path)
