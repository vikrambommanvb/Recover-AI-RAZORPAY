import React, { useState } from 'react';
import { ShieldAlert, Play, Loader2 } from 'lucide-react';

const sandboxScenarios = [
  {
    id: 'unknown',
    title: 'Unknown Gateway State Check',
    desc: 'AI recommends RETRY, but gateway state is UNKNOWN. Policy engine vetoes to avoid double captured charges.',
    ai: 'RETRY (94% confidence)',
    policy: 'BLOCK (VETO)',
    reason: 'Payment status is UNKNOWN.',
    result: '❌ Execution Denied (Safe Guardrail)'
  },
  {
    id: 'timeout',
    title: 'Gateway Connection Timeout',
    desc: 'AI suggests RETRY, policy allows it. Gateway API timeout occurs. System handles error cleanly with ₹0 counted.',
    ai: 'RETRY (91% confidence)',
    policy: 'ALLOW',
    reason: 'Gateway connection timed out after 5000ms.',
    result: '⚠️ FAILED (Attempt gracefully saved with zero value)'
  },
  {
    id: 'duplicate',
    title: 'Duplicate Attempt Check',
    desc: 'AI recommends RETRY. Policy engine flags active concurrent attempts for same payment, preventing duplicates.',
    ai: 'RETRY (88% confidence)',
    policy: 'BLOCK (VETO)',
    reason: 'An active retry execution thread is already running.',
    result: '❌ Deduplicated (Execution Blocked)'
  },
  {
    id: 'max_retries',
    title: 'Max Retries Stopped Rule',
    desc: 'Retry attempts reach merchant limit. System halts automated interventions and requests customer update.',
    ai: 'RETRY (91% confidence)',
    policy: 'BLOCK (VETO)',
    reason: 'Attempts limit exceeded (Max limit = 2).',
    result: '🛑 STOPPED (Enforced Stopping Rule)'
  },
  {
    id: 'high_value',
    title: 'High Value Threshold Escalate',
    desc: 'Invoice exceeds auto threshold limit. System suspends automatic link triggers and prompts manager manual approval.',
    ai: 'RETRY (89% confidence)',
    policy: 'ESCALATE',
    reason: 'Amount exceeds automatic threshold (Limit = ₹25,000).',
    result: '👤 ESCALATED (Manual Approval Required)'
  }
];

export default function SafetySandboxView() {
  const [activeScenario, setActiveScenario] = useState(null);
  const [loadingId, setLoadingId] = useState(null);

  const handleSimulate = (scenarioId) => {
    setLoadingId(scenarioId);
    setActiveScenario(null);
    setTimeout(() => {
      setLoadingId(null);
      setActiveScenario(scenarioId);
    }, 800);
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      
      {/* Intro Info Banner */}
      <div className="p-5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-400 flex items-start gap-4">
        <ShieldAlert className="w-5 h-5 shrink-0 mt-0.5" />
        <div>
          <h4 className="font-bold text-sm mb-1 uppercase tracking-wide">
            Interactive Safety Sandbox
          </h4>
          <p className="leading-relaxed font-semibold">
            Test how RecoverAI guardrails react to edge conditions. AI recommenders propose actions, while the deterministic policy checks enforce bounds and block unsafe executions.
          </p>
        </div>
      </div>

      {/* Grid of Simulation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {sandboxScenarios.map((scen) => {
          const isSimulating = loadingId === scen.id;
          const isShowingResult = activeScenario === scen.id;

          return (
            <div key={scen.id} className="p-5 bg-[#0F131D] border border-gray-800 rounded-xl flex flex-col justify-between space-y-4">
              <div className="space-y-2">
                <h4 className="font-bold font-display text-gray-200 text-sm leading-tight">
                  {scen.title}
                </h4>
                <p className="text-xs text-gray-400 leading-relaxed">
                  {scen.desc}
                </p>
              </div>

              <div className="space-y-4">
                {/* Trigger Button */}
                <button
                  onClick={() => handleSimulate(scen.id)}
                  disabled={loadingId !== null}
                  className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 text-xs font-bold transition disabled:opacity-40"
                >
                  {isSimulating ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Simulating...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5 text-blue-400" />
                      <span>Simulate scenario</span>
                    </>
                  )}
                </button>

                {/* Simulation Output Card */}
                {isShowingResult && (
                  <div className="p-4 rounded-lg bg-[#080B11] border border-gray-800 font-mono text-xs space-y-2.5 animate-fade-in">
                    <div>
                      <span className="text-gray-500 block text-[9px] uppercase font-bold">AI suggestion</span>
                      <span className="text-indigo-400 font-bold">{scen.ai}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block text-[9px] uppercase font-bold">Policy Verdict</span>
                      <span className={`font-bold ${
                        scen.policy.includes('BLOCK') ? 'text-rose-400' :
                        scen.policy.includes('ALLOW') ? 'text-emerald-400' : 'text-amber-400'
                      }`}>{scen.policy}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block text-[9px] uppercase font-bold">Trigger Reason</span>
                      <span className="text-gray-300 font-semibold">{scen.reason}</span>
                    </div>
                    <div className="border-t border-gray-800 pt-2 mt-2">
                      <span className="text-gray-500 block text-[9px] uppercase font-bold">Outcome</span>
                      <span className="font-semibold block">{scen.result}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
}
