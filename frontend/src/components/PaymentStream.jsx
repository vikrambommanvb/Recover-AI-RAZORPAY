import React, { useState, useRef } from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  ArrowRight,
  Zap,
  ShieldCheck,
  ShieldAlert,
  Bot
} from 'lucide-react';

const mockStream = [
  { id: 'pay_success_1', amount: 245000, status: 'success', time: '10s ago' },
  { id: 'pay_fail_1', amount: 820000, status: 'failed', time: '8s ago', reason: 'Temporary connection timeout' },
  { id: 'pay_success_2', amount: 125000, status: 'success', time: '7s ago' },
  { id: 'pay_fail_2', amount: 485300, status: 'failed', time: '5s ago', reason: 'Issuer bank decline' },
  { id: 'pay_success_3', amount: 940000, status: 'success', time: '3s ago' },
  { id: 'pay_fail_3', amount: 320000, status: 'failed', time: '1s ago', reason: 'Authentication verification timeout' }
];

const diagnosticsMap = {
  'pay_fail_1': {
    likelyCause: 'Temporary Network Timeout',
    confidence: 94,
    evidence: 'Gateway connection terminated after 5000ms. Response code: TIMEOUT.',
    policyDecision: 'ALLOW',
    action: 'RETRY (using auto cooldown)',
    rules: [
      { name: 'Payment State Validated', passed: true },
      { name: 'Under Automatic Threshold', passed: true },
      { name: 'Cooldown Constraint Met', passed: true },
      { name: 'No Duplicate Active runs', passed: true }
    ]
  },
  'pay_fail_2': {
    likelyCause: 'Issuer Bank Decline / Insufficient Funds',
    confidence: 88,
    evidence: 'Gateway declined response code: INSUFFICIENT_FUNDS.',
    policyDecision: 'ESCALATE',
    action: 'REMIND (Send Link via WhatsApp / SMS)',
    rules: [
      { name: 'Payment State Validated', passed: true },
      { name: 'Under Automatic Threshold', passed: true },
      { name: 'Cooldown Constraint Met', passed: true },
      { name: 'Automatic Run Vetoed', passed: false }
    ]
  },
  'pay_fail_3': {
    likelyCause: 'Authentication Drops / Closed Checkout',
    confidence: 91,
    evidence: 'User abandoned checkout before completing 3D Secure verification.',
    policyDecision: 'ALLOW',
    action: 'RETRY (Soft recovery triggered)',
    rules: [
      { name: 'Payment State Validated', passed: true },
      { name: 'Under Automatic Threshold', passed: true },
      { name: 'Cooldown Constraint Met', passed: true },
      { name: 'No Duplicate Active runs', passed: true }
    ]
  }
};

export default function PaymentStream({ onStartWorkspace }) {
  const [selectedPay, setSelectedPay] = useState(mockStream[1]); // default to pay_fail_1
  const containerRef = useRef(null);

  const diag = diagnosticsMap[selectedPay.id] || diagnosticsMap['pay_fail_1'];

  return (
    <div className="flex flex-col lg:flex-row h-full w-full bg-[#080B11]">
      
      {/* Scrollable Story Panel */}
      <div 
        ref={containerRef}
        className="flex-1 overflow-y-auto p-8 border-r border-[#1F2937] space-y-12 bg-[#090D15]"
      >
        
        {/* Intro Hero Card */}
        <div className="space-y-4">
          <span className="px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 text-xs font-mono font-semibold">
            Stage 1: Revenue Leakage
          </span>
          <h3 className="text-3xl font-extrabold font-display leading-tight text-white">
            Identify the leaks in your payment stream.
          </h3>
          <p className="text-gray-400 text-sm max-w-xl">
            Failed transactions, connection timeouts, and authentication drops siphon away revenue silently. Scroll down and click on any highlighted failed payment to trace how RecoverAI diagnoses and secures it.
          </p>
        </div>

        {/* The Live Payment Feed */}
        <div className="space-y-4">
          <div className="flex justify-between items-center text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
            <span>Gateway Transaction Stream (Click row to inspect)</span>
            <span>Status</span>
          </div>

          <div className="space-y-3">
            {mockStream.map((pay) => {
              const isFailed = pay.status === 'failed';
              const isSelected = selectedPay.id === pay.id;

              return (
                <div 
                  key={pay.id} 
                  onClick={() => isFailed && setSelectedPay(pay)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all duration-300 flex justify-between items-center ${
                    isFailed 
                      ? isSelected
                        ? 'bg-rose-950/40 border-rose-500 text-white shadow-lg shadow-rose-950/20'
                        : 'bg-rose-950/15 border-rose-900/40 text-rose-100 hover:border-rose-700'
                      : 'bg-gray-900/10 border-gray-900 text-gray-500 opacity-40 cursor-not-allowed'
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <span className="font-mono text-xs">{pay.time}</span>
                    <span className={`font-mono font-bold text-sm ${isFailed ? 'text-rose-400 font-extrabold' : 'text-gray-500'}`}>
                      {new Intl.NumberFormat('en-IN', {
                        style: 'currency',
                        currency: 'INR',
                        maximumFractionDigits: 0
                      }).format(pay.amount / 100)}
                    </span>
                    {isFailed && (
                      <span className="text-xs text-rose-400/90 font-medium italic">
                        {pay.reason}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {pay.status === 'success' ? (
                      <span className="text-[10px] uppercase font-bold text-gray-600">Captured</span>
                    ) : (
                      <span className="px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-400 text-[10px] font-extrabold flex items-center gap-1 border border-rose-500/30">
                        <XCircle className="w-3 h-3" />
                        FAILED
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Bounded Scroll Context Trigger */}
        <div className={`p-6 rounded-2xl border transition-all duration-500 bg-blue-500/5 border-blue-500/20 shadow-lg shadow-blue-900/10`}>
          <div className="flex items-start gap-4">
            <div className="p-2.5 rounded-xl bg-blue-600 text-white">
              <Zap className="w-5 h-5" />
            </div>
            <div className="space-y-2">
              <h4 className="font-bold font-display text-gray-200">
                Deterministic Isolation Complete
              </h4>
              <p className="text-xs text-gray-400 leading-relaxed">
                As failures are detected, RecoverAI calculates the aggregate risk and filters out permanent issues. Bounded candidates are instantly isolated for recovery execution.
              </p>
            </div>
          </div>
        </div>

        {/* Empty lower area of the screen: Business KPIs */}
        <div className="border-t border-gray-800 pt-6">
          <div className="bg-[#0C0F16] rounded-xl border border-gray-800 p-5">
            <div className="flex items-center gap-2 text-xs font-bold text-gray-500 uppercase tracking-wider mb-4">
              <Bot className="w-4 h-4 text-blue-400" />
              <span>Simulated Monthly Performance Benchmark</span>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800 text-center">
                <span className="text-[9px] text-gray-500 font-bold block uppercase">Failed Payments</span>
                <span className="text-lg font-extrabold text-gray-200">12</span>
              </div>
              <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800 text-center">
                <span className="text-[9px] text-gray-500 font-bold block uppercase">Revenue at Risk</span>
                <span className="text-lg font-extrabold text-rose-400">₹48,520</span>
              </div>
              <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800 text-center">
                <span className="text-[9px] text-gray-500 font-bold block uppercase">Eligible Recovery</span>
                <span className="text-lg font-extrabold text-blue-400">₹31,200</span>
              </div>
              <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800 text-center">
                <span className="text-[9px] text-gray-500 font-bold block uppercase">Recovered Amount</span>
                <span className="text-lg font-extrabold text-emerald-400 font-bold">₹18,400</span>
              </div>
              <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800 text-center">
                <span className="text-[9px] text-gray-500 font-bold block uppercase">Recovery Rate</span>
                <span className="text-lg font-extrabold text-gray-200">59%</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Side Pipeline Summary Visualizer */}
      <div className="w-full lg:w-96 bg-[#0B0F19] p-8 flex flex-col justify-between overflow-y-auto">
        <div className="space-y-6">
          <div>
            <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">
              Diagnostic Summary
            </span>
            <h4 className="text-lg font-bold font-display text-gray-200 mt-1">
              Active Discovery Feed
            </h4>
          </div>

          {/* At Risk Counters */}
          <div className="p-4 rounded-xl bg-[#0F131D] border border-gray-800 space-y-3">
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-500 font-semibold">Revenue at Risk:</span>
              <span className="font-mono font-bold text-rose-400">₹16,253</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-500 font-semibold">Recoverable:</span>
              <span className="font-mono font-bold text-blue-400">₹13,053</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-500 font-semibold">Excluded:</span>
              <span className="font-mono font-bold text-gray-500">₹3,200</span>
            </div>
          </div>

          {/* AI diagnosis block */}
          <div className="p-4 rounded-xl bg-[#141A27] border border-gray-800 space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-wider">
              <Bot className="w-4 h-4 text-indigo-400" />
              <span>AI Cause Diagnosis</span>
            </div>
            
            <div className="space-y-2 text-xs">
              <div>
                <span className="text-gray-500 block text-[9px] uppercase font-bold">Likely Cause:</span>
                <span className="text-gray-200 font-semibold">{diag.likelyCause}</span>
              </div>
              <div className="flex justify-between">
                <div>
                  <span className="text-gray-500 block text-[9px] uppercase font-bold">Confidence:</span>
                  <span className="text-indigo-400 font-bold">{diag.confidence}%</span>
                </div>
                <div>
                  <span className="text-gray-500 block text-[9px] uppercase font-bold">Decision:</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    diag.policyDecision === 'ALLOW' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
                  }`}>
                    {diag.policyDecision}
                  </span>
                </div>
              </div>
              <div>
                <span className="text-gray-500 block text-[9px] uppercase font-bold">Evidence:</span>
                <p className="text-gray-400 text-[11px] leading-snug">{diag.evidence}</p>
              </div>
            </div>
          </div>

          {/* Deterministic Flow Gate Diagram */}
          <div className="p-4 rounded-xl bg-[#0F131D] border border-gray-800 space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-wider">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Policy Rules Checklist</span>
            </div>
            
            <div className="space-y-2 text-xs">
              {diag.rules.map((rule, idx) => (
                <div key={idx} className="flex justify-between items-center text-[11px]">
                  <span className="text-gray-400">{rule.name}</span>
                  {rule.passed ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
                  )}
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Action Button */}
        <div className="pt-6">
          <button
            onClick={onStartWorkspace}
            className="w-full flex items-center justify-center gap-2 py-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm transition shadow-lg shadow-blue-900/20"
          >
            <span>Review ₹13,053 Bounded Cases</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>

      </div>

    </div>
  );
}
