import React from 'react';
import { 
  Bot, 
  ShieldCheck, 
  CheckCircle2, 
  XCircle, 
  AlertOctagon
} from 'lucide-react';

export default function PolicyGate({ decision, aiAction, confidence, amount, rootCause }) {
  // Mock list of deterministic safety checks performed by PolicyEngine
  const checks = [
    { name: 'Payment State Verifier Checks', desc: 'Validates state is failed or authorized', status: rootCause !== 'UNKNOWN' ? 'passed' : 'failed' },
    { name: 'Amount Threshold Rule Check', desc: 'Validates amount is under 15,000 paise for auto-run', status: amount < 1500000 ? 'passed' : 'escalated' },
    { name: 'Retry Limit Cooldown Check', desc: 'Enforces max attempts limits', status: 'passed' },
    { name: 'Idempotent Duplicate Check', desc: 'Guarantees single recovery execute instance', status: 'passed' }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 fintech-panel p-5 border border-gray-800 rounded-xl bg-[#0F131D]">
      
      {/* AI recommendation panel */}
      <div className="space-y-4 pr-0 md:pr-4 border-r-0 md:border-r border-gray-800">
        <div className="flex items-center gap-2 text-xs font-bold text-gray-500 uppercase tracking-wider">
          <Bot className="w-4 h-4 text-indigo-400" />
          <span>AI Advisory Recommendation</span>
        </div>
        
        <div className="p-4 rounded-lg bg-[#141A27] border border-gray-800 space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Suggested action</span>
            <span className="px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 text-xs font-bold uppercase">
              {aiAction || 'RETRY'}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Confidence index</span>
            <span className="font-mono font-bold text-sm text-indigo-300">
              {confidence !== undefined ? `${(confidence * 100).toFixed(0)}%` : '91%'}
            </span>
          </div>

          <div className="text-[11px] text-gray-400 leading-relaxed border-t border-gray-800 pt-2">
            AI recommends a bounded retry because a recoverable error was classified. Note that AI suggestions are advisory and hold no direct financial execution authorization.
          </div>
        </div>
      </div>

      {/* Policy Engine Checks */}
      <div className="space-y-4 pl-0 md:pl-4">
        <div className="flex items-center gap-2 text-xs font-bold text-gray-500 uppercase tracking-wider">
          <ShieldCheck className="w-4 h-4 text-blue-400" />
          <span>Deterministic Safety Gate</span>
        </div>

        <div className="space-y-2">
          {checks.map((check, index) => (
            <div key={index} className="flex items-start justify-between text-xs p-2 rounded hover:bg-[#141A27] transition">
              <div>
                <span className="text-gray-300 font-semibold block">{check.name}</span>
                <span className="text-[9px] text-gray-500">{check.desc}</span>
              </div>
              <div className="pt-0.5">
                {check.status === 'passed' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                {check.status === 'failed' && <XCircle className="w-3.5 h-3.5 text-rose-400" />}
                {check.status === 'escalated' && <AlertOctagon className="w-3.5 h-3.5 text-amber-400" />}
              </div>
            </div>
          ))}
        </div>

        <div className="border-t border-gray-800 pt-3 flex justify-between items-center">
          <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Verdict</span>
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-extrabold uppercase tracking-wider border ${
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
