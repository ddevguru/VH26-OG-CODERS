import * as vscode from "vscode";
import { execFile } from "child_process";
import { promisify } from "util";

const execFileAsync = promisify(execFile);

export interface DiagnosticLocation {
  start_line: number;
  start_column?: number;
  end_line?: number;
  end_column?: number;
}

export interface EngineDiagnostic {
  rule_id: string;
  file_path: string;
  line_number: number;
  severity: string;
  confidence: string;
  classification: string;
  message: string;
  reason: string;
  remediation?: string;
  fingerprint: string;
}

export class EngineBridge {
  private getPythonPath(): string {
    const config = vscode.workspace.getConfiguration("leakguard");
    return config.get<string>("pythonPath") || "python";
  }

  async analyzePath(targetPath: string): Promise<EngineDiagnostic[]> {
    const pythonPath = this.getPythonPath();
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();

    try {
      // Execute core Python LeakGuard scanner in JSON format mode
      const { stdout } = await execFileAsync(
        pythonPath,
        ["-m", "interfaces.cli.main", "scan", targetPath, "--format", "json", "--quiet"],
        { cwd: workspaceFolder, maxBuffer: 10 * 1024 * 1024 }
      );

      const parsed = JSON.parse(stdout);
      const diagnosticsRaw = parsed.findings || parsed.diagnostics || [];

      return diagnosticsRaw.map((d: any) => ({
        rule_id: d.rule_id || "LG-FILE-001",
        file_path: d.file_path || targetPath,
        line_number: d.location?.start?.line || d.location?.start_line || 1,
        severity: d.severity || "error",
        confidence: d.confidence || "high",
        classification: d.classification || "DEFINITE_LEAK",
        message: d.message || d.reason || "Unclosed resource handle",
        reason: d.reason || d.message || "Resource handle opened without matching release call",
        remediation: d.remediation || "Enclose resource initialization inside a context manager ('with' or 'async with').",
        fingerprint: d.fingerprint || `${d.rule_id}:${d.file_path}:${d.location?.start?.line || 1}`,
      }));
    } catch (error: any) {
      // Handle exit code 1 (blocking findings) where JSON is output to stdout
      if (error.stdout) {
        try {
          const parsed = JSON.parse(error.stdout);
          const diagnosticsRaw = parsed.findings || parsed.diagnostics || [];
          return diagnosticsRaw.map((d: any) => ({
            rule_id: d.rule_id || "LG-FILE-001",
            file_path: d.file_path || targetPath,
            line_number: d.location?.start?.line || d.location?.start_line || 1,
            severity: d.severity || "error",
            confidence: d.confidence || "high",
            classification: d.classification || "DEFINITE_LEAK",
            message: d.message || d.reason || "Unclosed resource handle",
            reason: d.reason || d.message || "Resource handle opened without matching release call",
            remediation: d.remediation || "Enclose resource initialization inside a context manager ('with' or 'async with').",
            fingerprint: d.fingerprint || `${d.rule_id}:${d.file_path}:${d.location?.start?.line || 1}`,
          }));
        } catch (_) {}
      }
      return [];
    }
  }
}
