import * as vscode from "vscode";
import { EngineDiagnostic } from "./engineBridge";

export class LeakGuardHoverProvider implements vscode.HoverProvider {
  private diagnosticsMap: Map<string, EngineDiagnostic[]> = new Map();

  public updateDiagnostics(uri: vscode.Uri, diagnostics: EngineDiagnostic[]) {
    this.diagnosticsMap.set(uri.toString(), diagnostics);
  }

  public provideHover(
    document: vscode.TextDocument,
    position: vscode.Position,
    token: vscode.CancellationToken
  ): vscode.ProviderResult<vscode.Hover> {
    const fileDiags = this.diagnosticsMap.get(document.uri.toString()) || [];
    const lineDiags = fileDiags.filter((d) => d.line_number === position.line + 1);

    if (lineDiags.length === 0) return null;

    const hoverMarkdown = new vscode.MarkdownString();
    hoverMarkdown.isTrusted = true;

    lineDiags.forEach((diag, idx) => {
      if (idx > 0) hoverMarkdown.appendMarkdown("\n---\n");

      hoverMarkdown.appendMarkdown(`### 🛡️ LeakGuard Resource Leak (${diag.rule_id})\n`);
      hoverMarkdown.appendMarkdown(`**Severity**: \`${diag.severity.toUpperCase()}\` | **Confidence**: \`${diag.confidence.toUpperCase()}\` | **Classification**: \`${diag.classification}\`\n\n`);
      hoverMarkdown.appendMarkdown(`**Resource Lifecycle Path**:\n`);
      hoverMarkdown.appendMarkdown(`> Resource handle acquired at line ${diag.line_number} is unclosed along path exit.\n\n`);
      hoverMarkdown.appendMarkdown(`**Why**: ${diag.reason}\n\n`);
      hoverMarkdown.appendMarkdown(`**Remediation**:\n\`\`\`python\n# Recommended Fix:\n${diag.remediation}\n\`\`\`\n`);
    });

    return new vscode.Hover(hoverMarkdown);
  }
}
