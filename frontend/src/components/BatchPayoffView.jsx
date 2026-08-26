import { CheckCircle2, RefreshCw, Award } from 'lucide-react';

export default function BatchPayoffView({ onRestart }) {
  return (
    <div className="min-h-full flex items-center justify-center p-6 bg-[#080B11]">
      <div className="max-w-xl w-full bg-[#0F131D] border border-gray-800 rounded-2xl p-8 space-y-8 shadow-xl shadow-black/40 text-center relative overflow-hidden">
        
        {/* Decorative background logo */}
        <div className="absolute -right-6 -bottom-6 opacity-5">
          <Award className="w-48 h-48 text-emerald-400" />
        </div>

        <div className="space-y-3">
          <div className="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center mx-auto mb-2 border border-emerald-500/20">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-extrabold font-display text-white uppercase tracking-wider">
            Batch Recovery Complete
          </h2>
          <p className="text-gray-400 text-xs max-w-sm mx-auto">
            RecoverAI successfully processed the recovery batch, enforcing all deterministic stopping rules and safety limits.
          </p>
        </div>

        {/* Large payoff Climax Value */}
        <div className="py-6 border-y border-gray-800 space-y-1 relative z-10 bg-[#141A27]/50 rounded-xl border p-4">
          <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">
            Successfully Recovered
          </span>
          <h3 className="text-4xl font-extrabold font-mono text-emerald-400">
            ₹18,400
          </h3>
          <span className="text-[11px] text-gray-400 block font-semibold">
            from ₹58,753 total revenue leakage at risk
          </span>
        </div>

        {/* Detail statistics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-semibold">
          <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800">
            <span className="text-gray-500 block text-[9px] uppercase mb-0.5">Processed</span>
            <span className="text-gray-200 font-mono font-bold">24 Cases</span>
          </div>
          <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800">
            <span className="text-gray-500 block text-[9px] uppercase mb-0.5">Eligible opportunity</span>
            <span className="text-gray-200 font-mono font-bold">₹31,420</span>
          </div>
          <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800">
            <span className="text-gray-500 block text-[9px] uppercase mb-0.5">Conversion rate</span>
            <span className="text-blue-400 font-mono font-bold">58.6%</span>
          </div>
          <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800">
            <span className="text-gray-500 block text-[9px] uppercase mb-0.5">Safety Vetoes</span>
            <span className="text-amber-500 font-mono font-bold">4 Blocked</span>
          </div>
        </div>

        {/* Summary status counts footer */}
        <div className="flex justify-center gap-6 text-[10px] text-gray-500 font-bold uppercase tracking-wider bg-[#0C0F16] py-3 rounded-lg border border-gray-800/60">
          <span>5 Escalated</span>
          <span>7 Stopped by Rules</span>
        </div>

        {/* Action Button */}
        <button
          onClick={onRestart}
          className="w-full flex items-center justify-center gap-2 py-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm transition"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Start New Recovery Run</span>
        </button>

      </div>
    </div>
  );
}
