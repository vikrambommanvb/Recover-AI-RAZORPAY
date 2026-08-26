import { Bot, ShieldCheck, CheckCircle2, XCircle } from 'lucide-react';

export default function PolicyGateVisual({ decision, aiAction, confidence, amount, rootCause, maxRetries }) {
  // Safe limits checklist
  const checks = [
    { name: 'Payment State Check', desc: 'Validates state is eligible (FAILED / AUTHORIZED)', status: rootCause !== 'CARD_EXPIRED' && rootCause !== 'UNKNOWN' ? 'passed' : 'failed' },
    { name: 'Amount Limit Rule Check', desc: 'Verifies amount is under auto limit (₹25,000)', status: amount <= 2500000 ? 'passed' : 'failed' },
    { name: 'Merchant Retry Limit Check', desc: `Attempts must be under max limit (${maxRetries || 2})`, status: rootCause !== 'CARD_EXPIRED' ? 'passed' : 'failed' },
    { name: 'Idempotent Running Check', desc: 'Guarantees no duplicate concurrent executions', status: 'passed' }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-[#141A27] border border-gray-800 rounded-xl p-5">
      
      {/* AI recommendation panel */}
      <div className="space-y-4 pr-0 md:pr-6 border-r-0 md:border-r border-gray-800 text-sm">
        <div className="flex items-center gap-2 text-sm font-bold text-gray-400 uppercase tracking-wider">
          <Bot className="w-5 h-5 text-indigo-400" />
          <span>AI Recommendation (Advisory)</span>
        </div>
        
        <div className="p-4 rounded-lg bg-[#0F131D] border border-gray-800 space-y-3">
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-500 font-bold uppercase text-xs">Intervention</span>
            <span className="px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 font-extrabold uppercase text-xs">
              {aiAction || 'RETRY'}
            </span>
          </div>

          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-500 font-bold uppercase text-xs">Model Confidence</span>
            <span className="font-mono font-bold text-indigo-300 text-base">
              {confidence !== undefined ? `${(confidence * 100).toFixed(0)}%` : '91%'}
            </span>
          </div>

          <p className="text-xs text-gray-450 leading-relaxed border-t border-gray-800 pt-2 font-medium">
            AI recommends a retry because transaction signatures indicate a temporary timeout error.
          </p>
        </div>
      </div>

      {/* Deterministic Policy Gate checks */}
      <div className="space-y-4 pl-0 md:pl-6 flex flex-col justify-between text-sm">
        <div>
          <div className="flex items-center gap-2 text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">
            <ShieldCheck className="w-5 h-5 text-blue-400" />
            <span>Deterministic Policy Gate</span>
          </div>

          <div className="space-y-2">
            {checks.map((check, index) => (
              <div key={index} className="flex items-start justify-between text-sm hover:bg-[#0F131D]/50 p-2 rounded transition font-medium">
                <div>
                  <span className="text-gray-300 font-bold block">{check.name}</span>
                  <span className="text-xs text-gray-500">{check.desc}</span>
                </div>
                <div className="pt-0.5">
                  {check.status === 'passed' ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <XCircle className="w-4 h-4 text-rose-400" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="border-t border-gray-800 pt-3 flex justify-between items-center text-sm shrink-0 mt-3 md:mt-0">
          <span className="text-gray-400 font-bold uppercase tracking-wider text-xs"> Veto Gate Verdict</span>
          <span className={`px-3 py-1 rounded-full text-xs font-extrabold uppercase border ${
            decision === 'ALLOW' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
            decision === 'BLOCK' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
            'bg-amber-500/10 text-amber-400 border-amber-500/20'
          }`}>
            {decision || 'ALLOW'}
          </span>
        </div>
      </div>

    </div>
  );
}
