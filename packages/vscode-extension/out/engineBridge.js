"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.EngineBridge = void 0;
const vscode = require("vscode");
const child_process_1 = require("child_process");
const util_1 = require("util");
const execFileAsync = (0, util_1.promisify)(child_process_1.execFile);
class EngineBridge {
    getPythonPath() {
        const config = vscode.workspace.getConfiguration("leakguard");
        return config.get("pythonPath") || "python";
    }
    async analyzePath(targetPath) {
        const pythonPath = this.getPythonPath();
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();
        try {
            // Execute core Python LeakGuard scanner in JSON format mode
            const { stdout } = await execFileAsync(pythonPath, ["-m", "interfaces.cli.main", "scan", targetPath, "--format", "json", "--quiet"], { cwd: workspaceFolder, maxBuffer: 10 * 1024 * 1024 });
            const parsed = JSON.parse(stdout);
            const diagnosticsRaw = parsed.findings || parsed.diagnostics || [];
            return diagnosticsRaw.map((d) => ({
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
        }
        catch (error) {
            // Handle exit code 1 (blocking findings) where JSON is output to stdout
            if (error.stdout) {
                try {
                    const parsed = JSON.parse(error.stdout);
                    const diagnosticsRaw = parsed.findings || parsed.diagnostics || [];
                    return diagnosticsRaw.map((d) => ({
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
                }
                catch (_) { }
            }
            return [];
        }
    }
}
exports.EngineBridge = EngineBridge;
//# sourceMappingURL=engineBridge.js.map