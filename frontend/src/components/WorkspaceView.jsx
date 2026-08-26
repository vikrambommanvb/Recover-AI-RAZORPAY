import React, { useState } from 'react';
import { Bot, ArrowRight } from 'lucide-react';
import CaseDetailCard from './CaseDetailCard';

const formatINR = (paise) => {
  if (paise === undefined || paise === null) return '₹0';
  const rupees = Math.floor(paise / 100);
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(rupees);
};

export default function WorkspaceView({ 
  cases, 
  onExecuteResult, // callback(caseId, outcomeStatus)
  onFinishBatch, 
  maxRetries 
}) {
  const [selectedCaseId, setSelectedCaseId] = useState('case_eval_001');

  const selectedCase = cases.find(c => c.case_id === selectedCaseId);

  // Check if all core cases are resolved (not in PENDING/AT_RISK state)
  const isBatchResolved = cases.every(c => c.execution_status !== 'PENDING' && c.execution_status !== 'AT_RISK');

  return (
    <div className="flex h-full w-full bg-[#080B11]">
      
      {/* 1. Left Sidebar: Case List */}
      <aside className="w-96 border-r border-gray-800 bg-[#090D15] flex flex-col justify-between shrink-0 h-full overflow-hidden">
        <div className="p-5 border-b border-gray-800 shrink-0">
          <div className="flex justify-between items-center text-sm font-bold text-gray-400 uppercase tracking-wider mb-2">
            <span>Discovery Batch Queue</span>
            <span className="px-2 py-0.5 rounded bg-[#141A27] text-gray-300 font-mono text-xs font-bold">
              {cases.length} cases
            </span>
          </div>
        </div>

        {/* Case List Scroll Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {cases.map((c) => {
            const isSelected = selectedCaseId === c.case_id;
            
            return (
              <div
                key={c.case_id}
                onClick={() => setSelectedCaseId(c.case_id)}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  isSelected 
                    ? 'bg-blue-950/20 border-blue-500 shadow-md shadow-blue-950/10' 
                    : 'bg-[#0F131D]/80 border-gray-800/80 hover:border-gray-700'
                }`}
              >
                <div className="flex justify-between items-center text-sm font-semibold">
                  <span className="font-mono text-gray-300 font-bold">{c.case_id}</span>
                  <span className={`px-2 py-0.5 rounded-[4px] text-[10px] font-extrabold uppercase ${
                    c.execution_status === 'SUCCEEDED' ? 'bg-emerald-500/10 text-emerald-400 font-bold' :
                    c.execution_status === 'FAILED' ? 'bg-rose-500/10 text-rose-400 font-bold' :
                    c.execution_status === 'STOPPED' ? 'bg-rose-500/10 text-rose-400 font-extrabold' :
                    c.execution_status === 'ESCALATED' ? 'bg-amber-500/10 text-amber-400 font-bold' :
                    'bg-gray-800 text-gray-400'
                  }`}>
                    {c.execution_status}
                  </span>
                </div>
                
                <div className="flex justify-between items-baseline mt-3">
                  <span className="text-base font-extrabold font-mono text-gray-100">
                    {formatINR(c.amount)}
                  </span>
                  <span className="text-xs text-gray-400 italic max-w-[150px] truncate">
                    {c.root_cause}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Completion Panel in bottom left sidebar */}
        <div className="p-4 border-t border-gray-800 bg-[#0C0F16] shrink-0">
          {isBatchResolved ? (
            <button
              onClick={onFinishBatch}
              className="w-full flex items-center justify-center gap-2 py-3.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-sm transition animate-pulse"
            >
              <span>View Climax metrics payoff</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <div className="text-center text-xs text-gray-400 font-bold uppercase tracking-wider py-3 bg-[#141A27]/50 rounded border border-gray-800/40">
              ⚡ Resolve queue to view outcome
            </div>
          )}
        </div>
      </aside>

      {/* 2. Middle Panel: Case details workspace */}
      <main className="flex-1 overflow-hidden h-full p-6 bg-[#080B11]">
        <CaseDetailCard
          caseItem={selectedCase}
          onExecuteResult={onExecuteResult}
          maxRetries={maxRetries}
        />
      </main>

      {/* 3. Right Sidebar: Context Copilot & Strategy */}
      <aside className="w-96 border-l border-gray-800 bg-[#090D15] flex flex-col justify-between shrink-0 h-full overflow-hidden">
        
        {/* Campaign Strategy Config Box */}
        <div className="p-6 border-b border-gray-800 space-y-4 shrink-0">
          <div className="flex items-center gap-2 text-sm font-bold text-gray-400 uppercase tracking-wider">
            <Bot className="w-5 h-5 text-indigo-400" />
            <span>Active Strategy Profile</span>
          </div>

          <div className="space-y-4 text-sm bg-[#0F131D] p-5 rounded-xl border border-gray-800">
            <div>
              <span className="text-gray-500 block text-xs uppercase font-bold">Campaign Strategy</span>
              <span className="text-gray-300 font-bold">Adaptive Bounded Retry</span>
            </div>
            <div>
              <span className="text-gray-500 block text-xs uppercase font-bold">Safe Cooldown Limit</span>
              <span className="text-gray-300 font-bold">30 Minutes</span>
            </div>
            <div>
              <span className="text-gray-500 block text-xs uppercase font-bold">Stopping Criteria</span>
              <span className="text-gray-300 font-bold">Max Retries Reach ({maxRetries})</span>
            </div>
          </div>
        </div>

        {/* Dynamic Context Copilot Panel */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <span className="text-xs text-gray-400 font-bold uppercase tracking-wider block">
            Contextual Advisor
          </span>

          {selectedCase ? (
            <div className="space-y-4 text-sm leading-relaxed text-gray-400 font-medium">
              <div className="p-5 rounded-xl bg-[#141A27] border border-gray-850/60 space-y-2">
                <span className="text-indigo-400 font-bold block text-xs uppercase tracking-wider">AI Context Diagnosis</span>
                {selectedCase.case_id === 'case_eval_001' && (
                  <p>Timeout failure was isolated on standard card payment stream. AI confirms no duplicate authorization block is present.</p>
                )}
                {selectedCase.case_id === 'case_eval_002' && (
                  <p>Gateway connection timeout error. Bounded retries satisfy the 30-minute cooldown rule constraints.</p>
                )}
                {selectedCase.case_id === 'case_eval_003' && (
                  <p>Card expired event. AI recommending payment method update link request, as direct payment retries will fail.</p>
                )}
                {selectedCase.case_id === 'case_eval_004' && (
                  <p>Subscription failed on insufficient funds trigger. Notification scheduled to query customer checkout updates.</p>
                )}
                {selectedCase.case_id === 'case_eval_005' && (
                  <p>Checkout abandoned. AI scheduled soft reminder dispatch but simulation will fail if customer ignores checkout links.</p>
                )}
                {selectedCase.case_id === 'case_eval_006' && (
                  <p>Amount ₹25,153 exceeds manual automation threshold limits. Detailing human review checks to avoid unauthorized run trials.</p>
                )}
              </div>

              <div className="p-5 rounded-xl bg-[#0F131D] border border-gray-850/60 space-y-1">
                <span className="text-emerald-400 font-bold block text-xs uppercase tracking-wider">Safety Constraints</span>
                <p>The policy engine forces a strict separator: AI suggests retry schedules, but the deterministic rule engine verifies merchant parameters before executing Razorpay links.</p>
              </div>
            </div>
          ) : (
            <p className="text-xs text-gray-500">Select a case details panel to load dynamic copilot assistant.</p>
          )}
        </div>

      </aside>

    </div>
  );
}
