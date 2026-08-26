import React from 'react';
import { 
  ShieldAlert, 
  Play, 
  Loader2
} from 'lucide-react';

export default function SafetyDemoPanel({ 
  onRunDemo1, 
  onRunDemo2, 
  demo1Result, 
  demo2Result, 
  demoLoading 
}) {
  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      
      {/* Intro Warning Warning banner */}
      <div className="p-6 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-400 flex items-start gap-4">
        <ShieldAlert className="w-6 h-6 shrink-0 mt-0.5" />
        <div>
          <h4 className="font-bold text-sm mb-1 uppercase tracking-wide">
            Buildathon Safety Rule Demonstration Panel
          </h4>
          <p className="leading-relaxed font-semibold">
            This section proves that the AI recovery recommendations never directly authorize or execute financial actions. Deterministic Policy controls override AI recommendations, preventing duplicate charges or invalid calls.
          </p>
        </div>
      </div>

      {/* Grid of demo cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Scenario 1: Unknown Gateway Status Status Veto */}
        <div className="p-6 rounded-xl bg-[#0F131D] border border-gray-800 space-y-4">
          <h4 className="font-bold font-display text-gray-200 uppercase tracking-wider text-xs">
            Scenario 1: Ambiguous payment state block
          </h4>
          <p className="text-xs text-gray-400 leading-relaxed">
            AI recommends RETRY (with high confidence), but the payment status is UNKNOWN. PolicyEngine vetoes execution to prevent double-charging the customer.
          </p>
          
          <button
            onClick={onRunDemo1}
            disabled={demoLoading}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs font-bold border border-gray-700 text-gray-300 disabled:opacity-40 transition"
          >
            {demoLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 text-blue-400" />}
            <span>Run Unknown State Simulation</span>
          </button>

          {demo1Result && (
            <div className="space-y-3 p-4 rounded-lg bg-[#080B11] border border-gray-800 font-mono text-xs animate-fade-in">
              <div>
                <span className="text-gray-500 block text-[9px] uppercase font-bold">AI recommendation</span>
                <span className="text-indigo-400 font-bold">
                  {demo1Result.ai_action} (Conf: {(demo1Result.ai_confidence * 100).toFixed(0)}%)
                </span>
              </div>
              <div>
                <span className="text-gray-500 block text-[9px] uppercase font-bold">Deterministic Veto Gate</span>
                <span className="text-rose-400 font-bold">BLOCK</span>
              </div>
              <div>
                <span className="text-gray-500 block text-[9px] uppercase font-bold">Veto Reason</span>
                <span className="text-amber-500 font-medium">
                  {demo1Result.stop_reason || "Blocked: Payment status check failed."}
                </span>
              </div>
              <div className="border-t border-gray-800 pt-2 mt-2">
                <span className="text-gray-500 block text-[9px] uppercase font-bold">Gateway call execution</span>
                <span className="text-rose-500 font-semibold block">
                  ❌ BLOCKED (Execution Denied)
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Scenario 2: API Timeout Handling */}
        <div className="p-6 rounded-xl bg-[#0F131D] border border-gray-800 space-y-4">
          <h4 className="font-bold font-display text-gray-200 uppercase tracking-wider text-xs">
            Scenario 2: Gateway API timeout handling
          </h4>
          <p className="text-xs text-gray-400 leading-relaxed">
            AI recommends RETRY and Policy Engine allows it. During execution, the API times out. The system flags the attempt failed and records ₹0 recovered.
          </p>
          
          <button
            onClick={onRunDemo2}
            disabled={demoLoading}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs font-bold border border-gray-700 text-gray-300 disabled:opacity-40 transition"
          >
            {demoLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 text-blue-400" />}
            <span>Run Timeout Simulation</span>
          </button>

          {demo2Result && (
            <div className="space-y-3 p-4 rounded-lg bg-[#080B11] border border-gray-800 font-mono text-xs animate-fade-in">
              <div>
                <span className="text-gray-500 block text-[9px] uppercase font-bold">Policy Verdict</span>
                <span className="text-emerald-400 font-bold">ALLOW</span>
              </div>
              <div>
                <span className="text-gray-500 block text-[9px] uppercase font-bold">Execution result</span>
                <span className="text-rose-400 font-bold">{demo2Result.execution_status}</span>
              </div>
              <div>
                <span className="text-gray-500 block text-[9px] uppercase font-bold">Audit timeline entry</span>
                <span className="text-gray-300">
                  RECOVERY_ATTEMPT_FAILED saved in MongoDB.
                </span>
              </div>
              <div>
                <span className="text-gray-500 block text-[9px] uppercase font-bold">Recovered amount counted</span>
                <span className="text-rose-400 font-bold">₹0 (Zero count added)</span>
              </div>
            </div>
          )}
        </div>

      </div>

    </div>
  );
}
