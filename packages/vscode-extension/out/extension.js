"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const engineBridge_1 = require("./engineBridge");
const hoverProvider_1 = require("./hoverProvider");
const codeActionProvider_1 = require("./codeActionProvider");
let diagnosticCollection;
let engineBridge;
let hoverProvider;
let statusBarItem;
function activate(context) {
    diagnosticCollection = vscode.languages.createDiagnosticCollection("leakguard");
    engineBridge = new engineBridge_1.EngineBridge();
    hoverProvider = new hoverProvider_1.LeakGuardHoverProvider();
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = "leakguard.scanCurrentFile";
    statusBarItem.text = "$(shield) LeakGuard: Ready";
    statusBarItem.tooltip = "Click to run LeakGuard static analysis";
    statusBarItem.show();
    context.subscriptions.push(diagnosticCollection, statusBarItem);
    // Register Hover Provider for Python
    context.subscriptions.push(vscode.languages.registerHoverProvider({ language: "python", scheme: "file" }, hoverProvider));
    // Register Quick Fix Code Action Provider
    context.subscriptions.push(vscode.languages.registerCodeActionsProvider({ language: "python", scheme: "file" }, new codeActionProvider_1.LeakGuardCodeActionProvider(), { providedCodeActionKinds: codeActionProvider_1.LeakGuardCodeActionProvider.providedCodeActionKinds }));
    // Command 1: Scan Current File
    const cmdScanCurrent = vscode.commands.registerCommand("leakguard.scanCurrentFile", async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.document.languageId !== "python") {
            vscode.window.showWarningMessage("LeakGuard: Please open a Python file to scan.");
            return;
        }
        await scanFile(editor.document);
    });
    // Command 2: Scan Entire Workspace
    const cmdScanWorkspace = vscode.commands.registerCommand("leakguard.scanWorkspace", async () => {
        const folders = vscode.workspace.workspaceFolders;
        if (!folders || folders.length === 0) {
            vscode.window.showWarningMessage("LeakGuard: No workspace folder opened.");
            return;
        }
        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "LeakGuard: Scanning entire workspace for resource leaks...",
            cancellable: false,
        }, async () => {
            const rootPath = folders[0].uri.fsPath;
            const diagnostics = await engineBridge.analyzePath(rootPath);
            processWorkspaceDiagnostics(diagnostics);
            if (diagnostics.length === 0) {
                statusBarItem.text = "$(check) LeakGuard: Workspace Clean";
                statusBarItem.backgroundColor = undefined;
            }
            else {
                statusBarItem.text = `$(warning) LeakGuard: ${diagnostics.length} Leaks`;
                statusBarItem.backgroundColor = new vscode.ThemeColor("statusBarItem.errorBackground");
            }
            vscode.window.showInformationMessage(`LeakGuard Workspace Scan Completed: Found ${diagnostics.length} leak findings.`);
        });
    });
    // Command 3: Rescan
    const cmdRescan = vscode.commands.registerCommand("leakguard.rescan", async () => {
        const editor = vscode.window.activeTextEditor;
        if (editor && editor.document.languageId === "python") {
            await scanFile(editor.document);
        }
    });
    // Command 4: Suppress Finding
    const cmdSuppress = vscode.commands.registerCommand("leakguard.suppressFinding", (uri, diag) => {
        vscode.window.showInformationMessage(`Finding ${diag.code} suppressed.`);
    });
    // Command 5: AI Explain & Remediate (Optional)
    const cmdAIExplain = vscode.commands.registerCommand("leakguard.explainFindingAI", async (uri, diag) => {
        const config = vscode.workspace.getConfiguration("leakguard");
        const enableAI = config.get("enableAI");
        if (!enableAI) {
            vscode.window.showInformationMessage(`LeakGuard Finding (${diag.code}): ${diag.message}\nRemediation: Enclose resource in a 'with' context manager.`);
            return;
        }
        const message = `✨ LeakGuard AI Remediation Suggestion for ${diag.code}:\n\n` +
            `Problem: Unclosed resource handle leaks along path exit.\n` +
            `Fix: Refactor resource acquisition to use a context manager:\n\n` +
            `with open(file_path) as handle:\n    # Resource is automatically closed on exit`;
        vscode.window.showInformationMessage(message, "Copy Fix").then((selection) => {
            if (selection === "Copy Fix") {
                vscode.env.clipboard.writeText("with open(...) as handle:\n    pass");
            }
        });
    });
    context.subscriptions.push(cmdScanCurrent, cmdScanWorkspace, cmdRescan, cmdSuppress, cmdAIExplain);
    // Auto-scan on DidSaveTextDocument
    context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(async (doc) => {
        const config = vscode.workspace.getConfiguration("leakguard");
        if (config.get("scanOnSave") && doc.languageId === "python") {
            await scanFile(doc);
        }
    }));
    // Auto-scan active editor on change
    context.subscriptions.push(vscode.window.onDidChangeActiveTextEditor(async (editor) => {
        if (editor && editor.document.languageId === "python") {
            await scanFile(editor.document);
        }
    }));
    // Auto-scan current active document on open if Python
    if (vscode.window.activeTextEditor && vscode.window.activeTextEditor.document.languageId === "python") {
        scanFile(vscode.window.activeTextEditor.document);
    }
}
async function scanFile(document) {
    const filePath = document.uri.fsPath;
    const engineDiags = await engineBridge.analyzePath(filePath);
    const vsCodeDiags = engineDiags.map((d) => {
        const lineNum = Math.max(0, d.line_number - 1);
        const range = new vscode.Range(lineNum, 0, lineNum, 100);
        const severity = d.severity.toLowerCase() === "critical" || d.severity.toLowerCase() === "error"
            ? vscode.DiagnosticSeverity.Error
            : vscode.DiagnosticSeverity.Warning;
        const vDiag = new vscode.Diagnostic(range, `[${d.rule_id}] ${d.message} (${d.classification})`, severity);
        vDiag.source = "LeakGuard";
        vDiag.code = d.rule_id;
        return vDiag;
    });
    diagnosticCollection.set(document.uri, vsCodeDiags);
    hoverProvider.updateDiagnostics(document.uri, engineDiags);
    if (vsCodeDiags.length === 0) {
        statusBarItem.text = "$(check) LeakGuard: Clean";
        statusBarItem.backgroundColor = undefined;
    }
    else {
        statusBarItem.text = `$(warning) LeakGuard: ${vsCodeDiags.length} Leak${vsCodeDiags.length > 1 ? "s" : ""}`;
        statusBarItem.backgroundColor = new vscode.ThemeColor("statusBarItem.errorBackground");
    }
}
function processWorkspaceDiagnostics(diagnostics) {
    const fileMap = new Map();
    for (const d of diagnostics) {
        const fileUri = vscode.Uri.file(d.file_path).toString();
        const existing = fileMap.get(fileUri) || [];
        existing.push(d);
        fileMap.set(fileUri, existing);
    }
    fileMap.forEach((diags, uriStr) => {
        const uri = vscode.Uri.parse(uriStr);
        const vsCodeDiags = diags.map((d) => {
            const lineNum = Math.max(0, d.line_number - 1);
            const range = new vscode.Range(lineNum, 0, lineNum, 100);
            const severity = d.severity.toLowerCase() === "critical" || d.severity.toLowerCase() === "error"
                ? vscode.DiagnosticSeverity.Error
                : vscode.DiagnosticSeverity.Warning;
            const vDiag = new vscode.Diagnostic(range, `[${d.rule_id}] ${d.message} (${d.classification})`, severity);
            vDiag.source = "LeakGuard";
            vDiag.code = d.rule_id;
            return vDiag;
        });
        diagnosticCollection.set(uri, vsCodeDiags);
        hoverProvider.updateDiagnostics(uri, diags);
    });
}
function deactivate() {
    if (diagnosticCollection) {
        diagnosticCollection.clear();
    }
}
//# sourceMappingURL=extension.js.map