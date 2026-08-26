import React from 'react';
import { 
  HelpCircle,
  ShieldCheck,
  RotateCw,
  Play
} from 'lucide-react';
import PolicyGate from './PolicyGate';
import AuditTrail from './AuditTrail';

const formatINR = (paise) => {
  if (paise === undefined || paise === null) return '₹0';
  const rupees = Math.floor(paise / 100);
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(rupees);
};

export default function RecoveryCaseDetail({ 
  selectedCase, 
  auditLogs,
  onExecuteCase,
  onVerifyCase,
  onStopCase,
  actionLoading 
}) {
  if (!selectedCase) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center text-gray-500 bg-[#0F131D] rounded-xl border border-gray-800 p-8">
        <HelpCircle className="w-12 h-12 mb-3 text-gray-600" />
        <h4 className="font-bold font-display text-gray-300">No Case Selected</h4>
        <p className="text-xs text-gray-400 max-w-xs mt-1">
          Select an active case from the queue to view details, evaluate safety rules, and trigger verification checks.
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
    max_attempts
  } = selectedCase;

  const isPending = execution_status === 'PENDING' || execution_status === 'AT_RISK';
  const isEscalated = policy_decision === 'ESCALATE' && execution_status === 'ESCALATED';
  const isRunnable = isPending || isEscalated;

  return (
    <div className="bg-[#0F131D] rounded-xl border border-gray-800 flex flex-col h-full overflow-hidden">
      
      {/* Header Panel */}
      <div className="p-6 border-b border-gray-800 bg-[#0C0F16] shrink-0">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider font-mono">
                Case File
              </span>
              <span className="px-2 py-0.5 rounded bg-blue-600/10 text-blue-400 font-mono text-[10px] font-bold">
                {case_id}
              </span>
            </div>
            <h3 className="text-xl font-extrabold font-display text-gray-100 mt-1">
              {formatINR(amount)}
            </h3>
            <p className="text-xs text-gray-500 font-mono mt-0.5">
              Original Payment Ref: {payment_id}
            </p>
          </div>

          <div className="flex gap-2">
            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
              execution_status === 'SUCCEEDED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
              execution_status === 'FAILED' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
              execution_status === 'ESCALATED' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
              'bg-gray-800 text-gray-400 border border-gray-700'
            }`}>
              {execution_status}
            </span>
          </div>
        </div>
      </div>

      {/* Scrollable details panel */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        
        {/* Core Diagnosis Card */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 rounded-xl bg-[#141A27] border border-gray-800 text-xs">
          <div>
            <span className="text-gray-500 block mb-0.5 uppercase tracking-wide text-[9px] font-bold">Diagnosed Cause</span>
            <span className="text-gray-200 font-semibold">{root_cause}</span>
          </div>
          <div>
            <span className="text-gray-500 block mb-0.5 uppercase tracking-wide text-[9px] font-bold">Gateway Status</span>
            <span className="text-rose-400 font-semibold">{initial_status}</span>
          </div>
          <div>
            <span className="text-gray-500 block mb-0.5 uppercase tracking-wide text-[9px] font-bold">Attempts Count</span>
            <span className="text-gray-200 font-mono font-semibold">{retry_count} / {max_attempts || 3}</span>
          </div>
          <div>
            <span className="text-gray-500 block mb-0.5 uppercase tracking-wide text-[9px] font-bold">Policy Verdict</span>
            <span className="text-emerald-400 font-semibold font-bold">{policy_decision}</span>
          </div>
        </div>

        {/* Advisory and Policy Engine details */}
        <PolicyGate 
          decision={policy_decision}
          aiAction={ai_action}
          confidence={ai_confidence}
          amount={amount}
          rootCause={root_cause}
        />

        {/* Action Panel for runnable cases */}
        {isRunnable && (
          <div className="p-5 rounded-xl bg-blue-600/5 border border-blue-500/10 space-y-4">
            <div className="flex items-start gap-3">
              <ShieldCheck className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wide">
                  Execute Bounded Recovery
                </h4>
                <p className="text-[11px] text-gray-400 leading-relaxed mt-1">
                  The decision passed safety checks. Click Execute to initiate the checkout link generation on Razorpay Test mode, followed by verification status checks.
                </p>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button
                onClick={() => onExecuteCase(case_id)}
                disabled={actionLoading || policy_decision === 'BLOCK'}
                className="flex-1 flex items-center justify-center gap-2 py-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition disabled:opacity-50"
              >
                {actionLoading ? (
                  <>
                    <RotateCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Executing order checkout...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    <span>Confirm & Execute Recovery</span>
                  </>
                )}
              </button>
              
              <button
                onClick={() => onStopCase(case_id)}
                disabled={actionLoading}
                className="px-4 py-3 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-gray-200 text-xs font-semibold border border-gray-700 transition"
              >
                Dismiss Case
              </button>
            </div>
          </div>
        )}

        {/* Manual Verification verification checks */}
        {execution_status === 'VERIFICATION_REQUIRED' && (
          <div className="p-5 rounded-xl bg-amber-500/5 border border-amber-500/10 space-y-4">
            <div className="flex items-start gap-3">
              <RotateCw className="w-5 h-5 text-amber-400 shrink-0 mt-0.5 animate-spin" />
              <div>
                <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wide">
                  Awaiting Verification Check
                </h4>
                <p className="text-[11px] text-gray-400 leading-relaxed mt-1">
                  The payment attempt order was sent to Razorpay. Run verification to retrieve the final gateway status and captured amount.
                </p>
              </div>
            </div>

            <button
              onClick={() => onVerifyCase(case_id)}
              disabled={actionLoading}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-lg bg-amber-500 hover:bg-amber-600 text-black text-xs font-extrabold transition disabled:opacity-50"
            >
              {actionLoading ? (
                <>
                  <RotateCw className="w-3.5 h-3.5 animate-spin text-black" />
                  <span>Checking gateway status...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-3.5 h-3.5 text-black" />
                  <span>Verify Recovery Outcome</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* Historical Logs timeline */}
        <div className="border-t border-gray-800 pt-6">
          <AuditTrail auditLogs={auditLogs} />
        </div>

      </div>

    </div>
  );
}
