const vscode = require('vscode');
const { exec } = require('child_process');

let diagnosticCollection;
let statusBarItem;

function activate(context) {
    console.log('🛡️ LeakGuard VS Code Security Extension is active!');
    
    // Create diagnostic collection for squiggly red error underlines
    diagnosticCollection = vscode.languages.createDiagnosticCollection('leakguard');
    
    // Create Status Bar Item in VS Code footer
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'leakguard.scanFile';
    statusBarItem.text = '$(shield) LeakGuard: Active';
    statusBarItem.tooltip = 'Click to run LeakGuard AST Resource Scan';
    statusBarItem.show();

    context.subscriptions.push(diagnosticCollection, statusBarItem);

    // Auto-scan on file save if enabled
    vscode.workspace.onDidSaveTextDocument((document) => {
        const config = vscode.workspace.getConfiguration('leakguard');
        if (document.languageId === 'python' && config.get('enableAutoScan')) {
            runScan(document);
        }
    }, null, context.subscriptions);

    // 1. Scan Active File Command
    let scanCmd = vscode.commands.registerCommand('leakguard.scanFile', function () {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.document.languageId !== 'python') {
            vscode.window.showInformationMessage('LeakGuard: Open a Python file to scan.');
            return;
        }
        runScan(editor.document);
    });

    // 2. Generate & Apply Verified AI Fix Command
    let fixCmd = vscode.commands.registerCommand('leakguard.fixFile', function () {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.document.languageId !== 'python') return;

        const filePath = editor.document.fileName;
        vscode.window.showInformationMessage('🤖 LeakGuard: Generating AI fix & verifying in AST Sandbox...');

        exec(`python -m leakguard fix "${filePath}" --apply`, (error, stdout, stderr) => {
            if (stdout && stdout.includes('VERIFIED FIX')) {
                vscode.window.showInformationMessage('✅ LeakGuard: Patch verified in AST sandbox & applied to file!');
                runScan(editor.document);
            } else if (stdout && stdout.includes('Zero resource leaks')) {
                vscode.window.showInformationMessage('🟢 LeakGuard: File is already safe. No fixes required.');
            } else {
                vscode.window.showWarningMessage(`LeakGuard: Fix verification output: ${stdout || stderr}`);
            }
        });
    });

    // 3. Static What-If Exception Simulator
    let whatIfCmd = vscode.commands.registerCommand('leakguard.whatIf', function () {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        const line = editor.selection.active.line + 1;
        const filePath = editor.document.fileName;

        exec(`python -m leakguard what-if --file "${filePath}" --line ${line}`, (error, stdout, stderr) => {
            const outputChannel = vscode.window.createOutputChannel("LeakGuard What-If Simulator");
            outputChannel.clear();
            outputChannel.appendLine(stdout || stderr);
            outputChannel.show();
        });
    });

    // 4. Inspect Resource Ownership Graph
    let ownershipCmd = vscode.commands.registerCommand('leakguard.ownership', function () {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        const filePath = editor.document.fileName;
        exec(`python -m leakguard ownership "${filePath}"`, (error, stdout, stderr) => {
            const outputChannel = vscode.window.createOutputChannel("LeakGuard Resource Ownership");
            outputChannel.clear();
            outputChannel.appendLine(stdout || stderr);
            outputChannel.show();
        });
    });

    // 5. Compute Risk Score (0-100)
    let riskCmd = vscode.commands.registerCommand('leakguard.riskScore', function () {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        const filePath = editor.document.fileName;
        exec(`python -m leakguard risk "${filePath}"`, (error, stdout, stderr) => {
            vscode.window.showInformationMessage(`🛡️ LeakGuard Risk Score output:\n${stdout.substring(0, 300)}...`);
        });
    });

    // 6. Open Web Dashboard Command
    let dashCmd = vscode.commands.registerCommand('leakguard.openDashboard', function () {
        const config = vscode.workspace.getConfiguration('leakguard');
        const dashUrl = config.get('dashboardUrl') || 'http://localhost:3000';
        vscode.env.openExternal(vscode.Uri.parse(dashUrl));
    });

    // 7. Toggle Voice Audio Announcement
    let voiceCmd = vscode.commands.registerCommand('leakguard.toggleVoice', function () {
        const config = vscode.workspace.getConfiguration('leakguard');
        const current = config.get('voiceAlerts');
        config.update('voiceAlerts', !current, vscode.ConfigurationTarget.Global);
        vscode.window.showInformationMessage(`🎙️ LeakGuard Voice Audio Alerts: ${!current ? 'ENABLED' : 'DISABLED'}`);
    });

    // Code Action Quick Fix Lightbulb Provider
    context.subscriptions.push(
        vscode.languages.registerCodeActionsProvider('python', new LeakGuardCodeActionProvider(), {
            providedCodeActionKinds: [vscode.CodeActionKind.QuickFix]
        })
    );

    context.subscriptions.push(scanCmd, fixCmd, whatIfCmd, ownershipCmd, riskCmd, dashCmd, voiceCmd);
}

function runScan(document) {
    const filePath = document.fileName;
    const config = vscode.workspace.getConfiguration('leakguard');
    const voiceFlag = config.get('voiceAlerts') ? '--voice' : '';

    exec(`python -m leakguard scan "${filePath}" --format json ${voiceFlag}`, (error, stdout, stderr) => {
        try {
            const results = JSON.parse(stdout);
            const diagnostics = [];
            const diagsList = results.diagnostics || [];

            for (const d of diagsList) {
                const line = Math.max(0, (d.location?.start?.line || 1) - 1);
                const range = new vscode.Range(line, 0, line, 100);
                const message = `[LeakGuard ${d.rule_id}] ${d.message} (Resource: ${d.resource_variable})`;
                
                const diag = new vscode.Diagnostic(
                    range,
                    message,
                    d.classification === 'DEFINITE_LEAK' ? vscode.DiagnosticSeverity.Error : vscode.DiagnosticSeverity.Warning
                );
                diag.code = d.rule_id;
                diag.source = 'LeakGuard AST';
                diagnostics.push(diag);
            }

            diagnosticCollection.set(document.uri, diagnostics);

            if (diagnostics.length === 0) {
                statusBarItem.text = '$(check) LeakGuard: Safe';
                statusBarItem.backgroundColor = undefined;
            } else {
                statusBarItem.text = `$(alert) LeakGuard: ${diagnostics.length} Leak(s)`;
                statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
            }
        } catch (e) {
            statusBarItem.text = '$(shield) LeakGuard: Ready';
        }
    });
}

class LeakGuardCodeActionProvider {
    provideCodeActions(document, range, context, token) {
        const actions = [];
        for (const diagnostic of context.diagnostics) {
            if (diagnostic.source === 'LeakGuard AST') {
                const fixAction = new vscode.CodeAction(
                    `🤖 LeakGuard: Apply AST-Verified AI Fix for ${diagnostic.code}`,
                    vscode.CodeActionKind.QuickFix
                );
                fixAction.command = {
                    command: 'leakguard.fixFile',
                    title: 'Apply Fix'
                };
                fixAction.diagnostics = [diagnostic];
                fixAction.isPreferred = true;
                actions.push(fixAction);
            }
        }
        return actions;
    }
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
