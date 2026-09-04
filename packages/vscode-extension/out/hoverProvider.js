"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.LeakGuardHoverProvider = void 0;
const vscode = require("vscode");
class LeakGuardHoverProvider {
    constructor() {
        this.diagnosticsMap = new Map();
    }
    updateDiagnostics(uri, diagnostics) {
        this.diagnosticsMap.set(uri.toString(), diagnostics);
    }
    provideHover(document, position, token) {
        const fileDiags = this.diagnosticsMap.get(document.uri.toString()) || [];
        const lineDiags = fileDiags.filter((d) => d.line_number === position.line + 1);
        if (lineDiags.length === 0)
            return null;
        const hoverMarkdown = new vscode.MarkdownString();
        hoverMarkdown.isTrusted = true;
        lineDiags.forEach((diag, idx) => {
            if (idx > 0)
                hoverMarkdown.appendMarkdown("\n---\n");
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
exports.LeakGuardHoverProvider = LeakGuardHoverProvider;
//# sourceMappingURL=hoverProvider.js.map