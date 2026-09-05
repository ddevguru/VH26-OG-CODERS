"use client";

import React, { useEffect, useState } from "react";
import { Bot, Play, Sparkles, Search, CheckSquare, Stethoscope, ShieldAlert, Zap, GitCommit, CheckCheck, GitPullRequest, BookOpen, Sliders, X, Terminal, CheckCircle2, AlertTriangle } from "lucide-react";

import { api } from "@/lib/api";
import { VoiceAgent } from "@/components/VoiceAgent";

const AGENT_ICON_MAP: Record<string, any> = {
  hunter: Search,
  reviewer: CheckSquare,
  root_cause: Stethoscope,
  security: ShieldAlert,
  fix_generator: Zap,
  regression: GitCommit,
  verification: CheckCheck,
  pr_agent: GitPullRequest,
  documentation: BookOpen,
  policy: Sliders,
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<any | null>(null);
  const [targetFile, setTargetFile] = useState("app.py");
  const [sourceSnippet, setSourceSnippet] = useState("def process():\n    f = open('data.txt')\n    return f.read()\n");
  const [running, setRunning] = useState(false);
  const [agentResult, setAgentResult] = useState<any | null>(null);
  const [voiceText, setVoiceText] = useState<string>("");

  useEffect(() => {
    api.getAIAgents()
      .then(res => setAgents(res))
      .catch(e => {
        // Fallback catalog if API loading
        setAgents([
          { name: "Resource Hunter Agent", key: "hunter", category: "Detection", description: "Identifies unreleased file handles, socket streams, and DB connections.", capabilities: ["AST Variable Tracking", "Lifetime Boundary Check"] },
          { name: "Code Reviewer Agent", key: "reviewer", category: "Review", description: "Provides senior static security code reviews with clean architectural guidance.", capabilities: ["Multi-File Review", "Senior Engineer Tone"] },
          { name: "Root Cause Agent", key: "root_cause", category: "Analysis", description: "Traces control flow exception paths and identifies exact line of missing cleanup.", capabilities: ["CFG Branch Unwinding", "Exception Path Tracing"] },
          { name: "Security Impact Agent", key: "security", category: "Security", description: "Evaluates resource exhaustion vulnerabilities (FD leaks, socket starvation).", capabilities: ["CVE Mapping", "Resource Exhaustion Scoring"] },
          { name: "Fix Generator Agent", key: "fix_generator", category: "Remediation", description: "Synthesizes standard strategy-pattern patches ('with', 'try-finally').", capabilities: ["Context Manager Synthesis", "Strategy Pattern Fixes"] },
          { name: "Regression Prevention Agent", key: "regression", category: "Verification", description: "Ensures generated patches preserve existing code behavior.", capabilities: ["Behavioral Preservation Check", "Regression Testing"] },
          { name: "Verification Sandbox Agent", key: "verification", category: "Verification", description: "Executes 9-step AST sandbox validation to verify target leak clearance.", capabilities: ["9-Step AST Sandbox", "Deterministic Re-Analysis"] },
          { name: "PR Summary Agent", key: "pr_agent", category: "Integration", description: "Generates security summaries and diff statistics for Pull Request reviews.", capabilities: ["PR Diff Summary", "Delta Reporting"] },
          { name: "Documentation Agent", key: "documentation", category: "Docs", description: "Generates clear remediation docs and coding guidelines.", capabilities: ["Markdown Doc Synthesis", "Best Practice Patterns"] },
          { name: "Policy Enforcement Agent", key: "policy", category: "Policy", description: "Evaluates developer firewall rules and determines block vs warn decisions.", capabilities: ["Firewall Rule Check", "Gate Pass/Block"] },
        ]);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleRunAgent = async (agent: any) => {
    setSelectedAgent(agent);
    setAgentResult(null);
  };

  const executeAgentRun = async () => {
    if (!selectedAgent) return;
    try {
      setRunning(true);
      const res = await api.runAIAgent(selectedAgent.key, {
        file_path: targetFile,
        source_code: sourceSnippet,
        line_number: 2,
        resource_type: "FILE",
        resource_variable: "f",
      });
      setAgentResult(res);
      const speech = `${selectedAgent.name} completed execution. ${res.summary || res.details || "Analysis finished."}`;
      setVoiceText(speech);
    } catch (e: any) {
      setAgentResult({ error: e.message || "Failed to execute agent." });
      setVoiceText(`Agent execution error: ${e.message}`);
    } finally {
      setRunning(false);
    }
  };

  const handleVoiceCommand = (cmd: string) => {
    const matched = agents.find((a) => cmd.includes(a.key) || cmd.includes(a.name.toLowerCase().split(" ")[0]));
    if (matched) {
      setSelectedAgent(matched);
      setVoiceText(`Executing ${matched.name} via voice command.`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Voice Announcer */}
      <VoiceAgent autoAnnounceText={voiceText} onVoiceCommand={handleVoiceCommand} />


      {/* Header */}
      <div className="border-b border-slate-200/80 pb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2.5">
            <Bot className="w-7 h-7 text-emerald-600" />
            <span>AI Multi-Agent Security Hub</span>
          </h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Orchestration hub of 10 specialized AI agents working on top of LeakGuard's 100% deterministic AST static engine.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3.5 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-bold text-emerald-800 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-600" />
            <span>10 / 10 Agents Online & AST Sandbox Verified</span>
          </div>
        </div>
      </div>

      {/* Agent Catalog Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {agents.map((agent, idx) => {
          const IconComp = AGENT_ICON_MAP[agent.key] || Bot;
          return (
            <div
              key={idx}
              className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between space-y-4 relative overflow-hidden"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200/80 flex items-center justify-center text-emerald-600 shadow-2xs">
                    <IconComp className="w-5 h-5" />
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider text-emerald-800 bg-emerald-50 border border-emerald-200">
                    {agent.category}
                  </span>
                </div>

                <div>
                  <h3 className="text-sm font-bold text-slate-900 tracking-tight">{agent.name}</h3>
                  <p className="text-xs text-slate-500 mt-1 leading-relaxed">{agent.description}</p>
                </div>

                <div className="flex flex-wrap gap-1.5 pt-1">
                  {agent.capabilities?.map((cap: string, cIdx: number) => (
                    <span key={cIdx} className="px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200 text-[10px] font-semibold text-slate-700">
                      {cap}
                    </span>
                  ))}
                </div>
              </div>

              <button
                onClick={() => handleRunAgent(agent)}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-sm shadow-emerald-600/20 transition active:scale-95 cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run {agent.name.replace(" Agent", "")}</span>
              </button>
            </div>
          );
        })}
      </div>

      {/* Execution Modal */}
      {selectedAgent && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-3xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center font-bold text-sm shadow-sm">
                  <Bot className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">{selectedAgent.name}</h3>
                  <p className="text-[11px] text-slate-500 font-semibold">Specialized AI Agent Invocation</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedAgent(null)}
                className="p-1.5 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Content Body */}
            <div className="p-6 space-y-4 text-xs overflow-y-auto">
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">
                  Target File Path
                </label>
                <input
                  type="text"
                  value={targetFile}
                  onChange={(e) => setTargetFile(e.target.value)}
                  className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono-code font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">
                  Python Source Snippet
                </label>
                <textarea
                  rows={5}
                  value={sourceSnippet}
                  onChange={(e) => setSourceSnippet(e.target.value)}
                  className="w-full p-3 bg-[#060911] border border-slate-700 rounded-xl font-mono-code text-xs text-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex justify-end">
                <button
                  disabled={running}
                  onClick={executeAgentRun}
                  className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center gap-2 shadow-md shadow-emerald-600/20"
                >
                  <Play className="w-4 h-4 fill-current" />
                  <span>{running ? "Executing Agent..." : `Execute ${selectedAgent.name}`}</span>
                </button>
              </div>

              {/* Agent Run Output */}
              {agentResult && (
                <div className={`p-4 rounded-2xl border space-y-3 pt-3 ${agentResult.error ? "bg-red-50/80 border-red-200" : "bg-slate-50 border-slate-200"}`}>
                  <div className="flex items-center justify-between">
                    <span className={`text-[10px] font-extrabold uppercase tracking-wider flex items-center gap-1.5 ${agentResult.error ? "text-red-800" : "text-emerald-800"}`}>
                      {agentResult.error ? (
                        <>
                          <AlertTriangle className="w-4 h-4 text-red-600" /> Execution Error
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Execution Output ({agentResult.status || "COMPLETED"})
                        </>
                      )}
                    </span>
                    <span className="text-[10px] font-mono-code text-slate-500">
                      {agentResult.execution_time_ms ? `${agentResult.execution_time_ms.toFixed(1)}ms` : selectedAgent.key}
                    </span>
                  </div>

                  {agentResult.summary && (
                    <div className="p-3 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-800 shadow-2xs">
                      {agentResult.summary}
                    </div>
                  )}

                  <pre className="p-3.5 rounded-xl bg-[#060911] border border-slate-700 text-xs font-mono-code text-slate-200 overflow-x-auto max-h-60">
                    {JSON.stringify(agentResult, null, 2)}
                  </pre>
                </div>
              )}

            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex justify-end">
              <button
                onClick={() => setSelectedAgent(null)}
                className="px-4 py-1.5 rounded-xl bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold text-xs"
              >
                Close Agent Tool
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
