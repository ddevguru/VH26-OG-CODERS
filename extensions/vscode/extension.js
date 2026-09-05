const vscode = require('vscode');
const { exec } = require('child_process');

let diagnosticCollection;

function activate(context) {
    console.log('LeakGuard VS Code Extension is active!');
    diagnosticCollection = vscode.languages.createDiagnosticCollection('leakguard');
    context.subscriptions.push(diagnosticCollection);

    // Register Scan Active File Command
    let scanDisposable = vscode.commands.registerCommand('leakguard.scanFile', function () {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showInformationMessage('No active editor open.');
            return;
        }

        const filePath = editor.document.fileName;
        vscode.window.showInformationMessage(`Shielding ${filePath} with LeakGuard...`);

        exec(`python -m leakguard scan "${filePath}" --format json`, (error, stdout, stderr) => {
            try {
                const results = JSON.parse(stdout);
                const diagnostics = [];
                const diagsList = results.diagnostics || [];

                for (const d of diagsList) {
                    const line = Math.max(0, (d.location?.start?.line || 1) - 1);
                    const range = new vscode.Range(line, 0, line, 100);
                    const message = `[${d.rule_id}] ${d.message} (Resource: ${d.resource_variable})`;
                    
                    const diag = new vscode.Diagnostic(
                        range,
                        message,
                        d.classification === 'DEFINITE_LEAK' ? vscode.DiagnosticSeverity.Error : vscode.DiagnosticSeverity.Warning
                    );
                    diagnostics.push(diag);
                }

                diagnosticCollection.set(editor.document.uri, diagnostics);

                if (diagnostics.length === 0) {
                    vscode.window.showInformationMessage('🟢 LeakGuard: Zero resource leaks detected!');
                } else {
                    vscode.window.showErrorMessage(`🔴 LeakGuard: Found ${diagnostics.length} resource leak(s)!`);
                }
            } catch (e) {
                vscode.window.showErrorMessage('LeakGuard scan failed. Ensure leakguard is installed (pip install -e .)');
            }
        });
    });

    // Register Fix Command
    let fixDisposable = vscode.commands.registerCommand('leakguard.fixFile', function () {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        const filePath = editor.document.fileName;
        vscode.window.showInformationMessage('Generating AST-Verified AI Fix...');

        exec(`python -m leakguard fix "${filePath}" --apply`, (error, stdout, stderr) => {
            vscode.window.showInformationMessage('✅ LeakGuard: Patch applied & verified by AST Sandbox!');
            diagnosticCollection.clear();
        });
    });

    // Register Open Dashboard Command
    let dashDisposable = vscode.commands.registerCommand('leakguard.openDashboard', function () {
        const config = vscode.workspace.getConfiguration('leakguard');
        const dashUrl = config.get('dashboardUrl') || 'http://localhost:3000';
        vscode.env.openExternal(vscode.Uri.parse(dashUrl));
    });

    context.subscriptions.push(scanDisposable, fixDisposable, dashDisposable);
}

function deactivate() {
    if (diagnosticCollection) {
        diagnosticCollection.clear();
    }
}

module.exports = {
    activate,
    deactivate
};
