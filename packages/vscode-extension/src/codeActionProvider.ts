import * as vscode from "vscode";

export class LeakGuardCodeActionProvider implements vscode.CodeActionProvider {
  public static readonly providedCodeActionKinds = [
    vscode.CodeActionKind.QuickFix,
  ];

  public provideCodeActions(
    document: vscode.TextDocument,
    range: vscode.Range | vscode.Selection,
    context: vscode.CodeActionContext,
    token: vscode.CancellationToken
  ): vscode.ProviderResult<(vscode.Command | vscode.CodeAction)[]> {
    const actions: vscode.CodeAction[] = [];

    // Filter diagnostics owned by LeakGuard
    const leakGuardDiags = context.diagnostics.filter(
      (d) => d.source === "LeakGuard"
    );

    for (const diag of leakGuardDiags) {
      // Action 1: Suppress Finding (Inline Comment)
      const suppressAction = new vscode.CodeAction(
        `Suppress finding (${diag.code || "LeakGuard"})`,
        vscode.CodeActionKind.QuickFix
      );
      suppressAction.diagnostics = [diag];
      suppressAction.isPreferred = true;
      suppressAction.edit = new vscode.WorkspaceEdit();

      const line = document.lineAt(diag.range.start.line);
      suppressAction.edit.insert(
        document.uri,
        line.range.end,
        "  # leakguard: ignore"
      );
      actions.push(suppressAction);

      // Action 2: Optional AI Explanation & Remediation
      const aiAction = new vscode.CodeAction(
        `✨ AI Explain & Remediate (${diag.code || "LeakGuard"})`,
        vscode.CodeActionKind.QuickFix
      );
      aiAction.command = {
        command: "leakguard.explainFindingAI",
        title: "AI Explain & Remediate",
        arguments: [document.uri, diag],
      };
      actions.push(aiAction);
    }

    return actions;
  }
}
