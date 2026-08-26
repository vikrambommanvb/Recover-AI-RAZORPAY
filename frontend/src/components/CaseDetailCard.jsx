import React, { useState } from 'react';
import { 
  ShieldCheck, 
  XCircle, 
  Loader2, 
  Play, 
  AlertTriangle,
  HelpCircle
} from 'lucide-react';
import PolicyGateVisual from './PolicyGateVisual';
import AuditTimelineView from './AuditTimelineView';

const formatINR = (paise) => {
  if (paise === undefined || paise === null) return '₹0';
  const rupees = Math.floor(paise / 100);
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(rupees);
};

export default function CaseDetailCard({ 
  caseItem, 
  onExecuteResult, // callback(caseId, outcomeStatus)
  maxRetries 
}) {
  const [executionStep, setExecutionStep] = useState(0);
  const [isExecuting, setIsExecuting] = useState(false);
  if (!caseItem) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center text-gray-500 bg-[#0F131D] rounded-xl border border-gray-800 p-8">
        <HelpCircle className="w-12 h-12 mb-3 text-gray-600 animate-pulse" />
        <h4 className="font-bold font-display text-gray-300">No Case Selected</h4>
        <p className="text-xs text-gray-400 max-w-xs mt-1 leading-normal">
          Select an active recovery candidate from the left list to evaluate AI suggestions and safety rules.
        </p>
      </div>
    );
  }

  const {
    case_id,
    payment_id,
    amount,
    initial_status,
    root_cause,
    ai_action,
    ai_confidence,
    policy_decision,
    execution_status,
    retry_count,
    customer_reference,
    policy_reason
  } = caseItem;

  const isPending = execution_status === 'PENDING' || execution_status === 'AT_RISK';
  const isEscalated = policy_decision === 'ESCALATE' && execution_status === 'ESCALATED';

  // Run simulated step-by-step progress timelines
  const runSimulatedExecution = (outcome) => {
    setIsExecuting(true);
    setExecutionStep(1);
    
    const stepsCount = 6;
    let currentStep = 1;

    const timer = setInterval(() => {
      currentStep += 1;
      setExecutionStep(currentStep);
      
      if (currentStep >= stepsCount) {
        clearInterval(timer);
        setIsExecuting(false);
        setExecutionStep(0);
        onExecuteResult(case_id, outcome);
      }
    }, 400); // Total duration ~2.4 seconds
  };

  const handleExecute = () => {
    if (case_id === 'case_eval_005') {
      runSimulatedExecution('FAILED'); // Case 5 fails
    } else {
      runSimulatedExecution('SUCCEEDED'); // Cases 1, 2, 4 succeed
    }
  };

  const handleApproveEscalation = () => {
    runSimulatedExecution('SUCCEEDED');
  };

  return (
    <div className="bg-[#0F131D] rounded-xl border border-gray-800 flex flex-col h-full overflow-hidden">
      
      {/* Header Info Panel */}
      <div className="p-6 border-b border-gray-800 bg-[#0C0F16] shrink-0">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-500 font-bold uppercase tracking-wider font-mono">
                Opportunity Workspace
              </span>
              <span className="px-2.5 py-0.5 rounded bg-blue-600/10 text-blue-400 font-mono text-xs font-bold">
                {case_id}
              </span>
            </div>
            <h3 className="text-3xl font-extrabold font-mono text-gray-100 mt-1.5">
              {formatINR(amount)}
            </h3>
            <p className="text-sm text-gray-400 font-mono mt-1">
              Ref: {payment_id} | Client: {customer_reference || 'N/A'}
            </p>
          </div>

          <div>
            <span className={`px-4 py-1.5 rounded-full text-xs font-extrabold uppercase tracking-wider border ${
              execution_status === 'SUCCEEDED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
              execution_status === 'FAILED' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
              execution_status === 'STOPPED' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20 font-extrabold' :
              execution_status === 'ESCALATED' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
              'bg-gray-800 text-gray-400 border-gray-700'
            }`}>
              {execution_status}
            </span>
          </div>
        </div>
      </div>

      {/* Main Details area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        
        {/* Core Diagnosis Card */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-5 rounded-xl bg-[#141A27] border border-gray-800 text-sm">
          <div>
            <span className="text-gray-500 block mb-0.5 uppercase tracking-wide text-[10px] font-bold">Diagnosed Cause</span>
            <span className="text-gray-200 font-bold">{root_cause}</span>
          </div>
          <div>
            <span className="text-gray-500 block mb-0.5 uppercase tracking-wide text-[10px] font-bold">Gateway Status</span>
            <span className="text-rose-400 font-semibold">{initial_status}</span>
          </div>
          <div>
            <span className="text-gray-500 block mb-0.5 uppercase tracking-wide text-[10px] font-bold">Attempts Count</span>
            <span className="text-gray-200 font-mono font-bold">{retry_count} / {maxRetries}</span>
          </div>
          <div>
            <span className="text-gray-500 block mb-0.5 uppercase tracking-wide text-[10px] font-bold">Policy Verdict</span>
            <span className="text-emerald-400 font-extrabold">{policy_decision}</span>
          </div>
        </div>

        {/* AI & Policy Gate comparisons */}
        <PolicyGateVisual
          decision={policy_decision}
          aiAction={ai_action}
          confidence={ai_confidence}
          amount={amount}
          rootCause={root_cause}
          maxRetries={maxRetries}
        />

        {/* Action controllers depending on case states */}
        {!isExecuting && isPending && policy_decision === 'ALLOW' && (
          <div className="p-5 rounded-xl bg-blue-600/5 border border-blue-500/10 space-y-4">
            <div className="flex items-start gap-3">
              <ShieldCheck className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wide">
                  Execute Bounded Recovery
                </h4>
                <p className="text-[11px] text-gray-400 leading-relaxed mt-1">
                  The decision passed safety checks. Click Start Recovery to trigger the automatic payment link generation on Razorpay Test mode.
                </p>
              </div>
            </div>

            <button
              onClick={handleExecute}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition shadow-lg shadow-blue-900/20"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Start Bounded Recovery</span>
            </button>
          </div>
        )}

        {/* Veto Block Card */}
        {policy_decision === 'BLOCK' && execution_status === 'BLOCKED' && (
          <div className="p-5 rounded-xl bg-rose-600/5 border border-rose-500/10 space-y-4">
            <div className="flex items-start gap-3">
              <XCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wide text-rose-400">
                  Recovery Vetoed by Policy Engine
                </h4>
                <p className="text-[11px] text-gray-400 leading-relaxed mt-1">
                  AI suggested a recovery retry, but the Policy Engine vetoed this proposal: <strong>{policy_reason || 'Transaction state invalid.'}</strong>. Unsafe automation loops are blocked at the architecture level.
                </p>
              </div>
            </div>
            
            <button
              onClick={() => onExecuteResult(case_id, 'ESCALATED')}
              className="w-full py-2.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-gray-100 text-xs font-bold border border-gray-700 transition"
            >
              Escalate Case for Manual Review
            </button>
          </div>
        )}

        {/* Escalation Manual trigger Card */}
        {isEscalated && (
          <div className="p-5 rounded-xl bg-amber-500/5 border border-amber-500/10 space-y-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wide text-amber-400">
                  Human Review Required
                </h4>
                <p className="text-[11px] text-gray-400 leading-relaxed mt-1">
                  Automatic execution was suspended because the amount exceeds standard limits. Review the evidence above and approve manual recovery link.
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleApproveEscalation}
                className="flex-1 py-3 rounded-lg bg-amber-500 hover:bg-amber-600 text-black text-xs font-extrabold transition"
              >
                Approve Escalation
              </button>
              <button
                onClick={() => onExecuteResult(case_id, 'STOPPED')}
                className="px-4 py-3 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 text-xs font-bold border border-gray-700 transition"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* Stopping Rules HALT Card */}
        {execution_status === 'STOPPED' && (
          <div className="p-5 rounded-xl bg-rose-600/5 border border-rose-500/10 space-y-4">
            <div className="flex items-start gap-3">
              <XCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wide text-rose-400">
                  Recovery Stopped
                </h4>
                <p className="text-[11px] text-gray-400 leading-relaxed mt-1">
                  Maximum retry attempts reached. No additional payment attempt will be made.
                </p>
              </div>
            </div>
            
            <div className="space-y-2 text-xs font-semibold p-4 rounded-lg bg-[#080B11] border border-gray-800 font-mono">
              <div>
                <span className="text-gray-500 block text-[9px] uppercase">Reason</span>
                <span className="text-rose-400">Merchant retry limit = {maxRetries}</span>
              </div>
              <div>
                <span className="text-gray-500 block text-[9px] uppercase">Next Action</span>
                <span className="text-gray-300">Customer update link required (manual dispatch).</span>
              </div>
            </div>
          </div>
        )}

        {/* Live progress Loader */}
        {isExecuting && (
          <div className="p-5 rounded-xl bg-blue-500/5 border border-blue-500/10 space-y-4">
            <div className="flex items-center gap-3">
              <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
              <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wide">
                Recovery Pipeline executing
              </h4>
            </div>

            <div className="space-y-2 font-mono text-[10px] text-gray-400">
              <div className="flex justify-between items-center">
                <span>1. Case validated</span>
                <span className={executionStep >= 1 ? 'text-emerald-400 font-bold' : 'text-gray-600'}>{executionStep >= 1 ? '✓' : 'pending'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span>2. Policy verified</span>
                <span className={executionStep >= 2 ? 'text-emerald-400 font-bold' : 'text-gray-600'}>{executionStep >= 2 ? '✓' : 'pending'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span>3. Recovery action initiated</span>
                <span className={executionStep >= 3 ? 'text-emerald-400 font-bold' : 'text-gray-600'}>{executionStep >= 3 ? '✓' : 'pending'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span>4. Gateway response received</span>
                <span className={executionStep >= 4 ? 'text-emerald-400 font-bold' : 'text-gray-600'}>{executionStep >= 4 ? '✓' : 'pending'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span>5. Payment status confirmed</span>
                <span className={executionStep >= 5 ? 'text-emerald-400 font-bold' : 'text-gray-600'}>{executionStep >= 5 ? '✓' : 'pending'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span>6. Recovery recorded</span>
                <span className={executionStep >= 6 ? 'text-emerald-400 font-bold' : 'text-gray-600'}>{executionStep >= 6 ? '✓' : 'pending'}</span>
              </div>
            </div>
          </div>
        )}

        {/* Timelines logs */}
        <div className="border-t border-gray-800 pt-6">
          <AuditTimelineView logs={[]} amount={amount} />
        </div>

      </div>

    </div>
  );
}
