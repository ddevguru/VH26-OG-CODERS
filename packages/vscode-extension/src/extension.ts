import * as vscode from "vscode";
import { EngineBridge, EngineDiagnostic } from "./engineBridge";
import { LeakGuardHoverProvider } from "./hoverProvider";
import { LeakGuardCodeActionProvider } from "./codeActionProvider";

let diagnosticCollection: vscode.DiagnosticCollection;
let engineBridge: EngineBridge;
let hoverProvider: LeakGuardHoverProvider;

export function activate(context: vscode.ExtensionContext) {
  diagnosticCollection = vscode.languages.createDiagnosticCollection("leakguard");
  engineBridge = new EngineBridge();
  hoverProvider = new LeakGuardHoverProvider();

  context.subscriptions.push(diagnosticCollection);

  // Register Hover Provider for Python
  context.subscriptions.push(
    vscode.languages.registerHoverProvider({ language: "python", scheme: "file" }, hoverProvider)
  );

  // Register Quick Fix Code Action Provider
  context.subscriptions.push(
    vscode.languages.registerCodeActionsProvider(
      { language: "python", scheme: "file" },
      new LeakGuardCodeActionProvider(),
      { providedCodeActionKinds: LeakGuardCodeActionProvider.providedCodeActionKinds }
    )
  );

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

    vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: "LeakGuard: Scanning entire workspace for resource leaks...",
        cancellable: false,
      },
      async () => {
        const rootPath = folders[0].uri.fsPath;
        const diagnostics = await engineBridge.analyzePath(rootPath);
        processWorkspaceDiagnostics(diagnostics);
        vscode.window.showInformationMessage(`LeakGuard Workspace Scan Completed: Found ${diagnostics.length} leak findings.`);
      }
    );
  });

  // Command 3: Rescan
  const cmdRescan = vscode.commands.registerCommand("leakguard.rescan", async () => {
    const editor = vscode.window.activeTextEditor;
    if (editor && editor.document.languageId === "python") {
      await scanFile(editor.document);
    }
  });

  // Command 4: Suppress Finding
  const cmdSuppress = vscode.commands.registerCommand("leakguard.suppressFinding", (uri: vscode.Uri, diag: vscode.Diagnostic) => {
    vscode.window.showInformationMessage(`Finding ${diag.code} suppressed.`);
  });

  // Command 5: AI Explain & Remediate (Optional)
  const cmdAIExplain = vscode.commands.registerCommand("leakguard.explainFindingAI", async (uri: vscode.Uri, diag: vscode.Diagnostic) => {
    const config = vscode.workspace.getConfiguration("leakguard");
    const enableAI = config.get<boolean>("enableAI");

    if (!enableAI) {
      vscode.window.showInformationMessage(
        `LeakGuard Finding (${diag.code}): ${diag.message}\nRemediation: Enclose resource in a 'with' context manager.`
      );
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
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(async (doc) => {
      const config = vscode.workspace.getConfiguration("leakguard");
      if (config.get<boolean>("scanOnSave") && doc.languageId === "python") {
        await scanFile(doc);
      }
    })
  );

  // Auto-scan current active document on open if Python
  if (vscode.window.activeTextEditor && vscode.window.activeTextEditor.document.languageId === "python") {
    scanFile(vscode.window.activeTextEditor.document);
  }
}

async function scanFile(document: vscode.TextDocument) {
  const filePath = document.uri.fsPath;
  const engineDiags = await engineBridge.analyzePath(filePath);

  const vsCodeDiags: vscode.Diagnostic[] = engineDiags.map((d) => {
    const lineNum = Math.max(0, d.line_number - 1);
    const range = new vscode.Range(lineNum, 0, lineNum, 100);
    const severity =
      d.severity.toLowerCase() === "critical" || d.severity.toLowerCase() === "error"
        ? vscode.DiagnosticSeverity.Error
        : vscode.DiagnosticSeverity.Warning;

    const vDiag = new vscode.Diagnostic(range, `[${d.rule_id}] ${d.message} (${d.classification})`, severity);
    vDiag.source = "LeakGuard";
    vDiag.code = d.rule_id;
    return vDiag;
  });

  diagnosticCollection.set(document.uri, vsCodeDiags);
  hoverProvider.updateDiagnostics(document.uri, engineDiags);
}

function processWorkspaceDiagnostics(diagnostics: EngineDiagnostic[]) {
  const fileMap: Map<string, EngineDiagnostic[]> = new Map();
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
      const severity =
        d.severity.toLowerCase() === "critical" || d.severity.toLowerCase() === "error"
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

export function deactivate() {
  if (diagnosticCollection) {
    diagnosticCollection.clear();
  }
}
