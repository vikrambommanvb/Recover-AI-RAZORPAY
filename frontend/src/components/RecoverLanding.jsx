import { TrendingUp, Zap } from 'lucide-react';

export default function RecoverLanding({ onLoadBatch }) {
  return (
    <div className="min-h-full flex items-center justify-center p-6 bg-[#080B11]">
      <div className="max-w-md w-full bg-[#0F131D] border border-gray-800 rounded-2xl p-8 space-y-8 shadow-xl shadow-black/40">
        
        {/* Brand Header */}
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gray-800 border border-gray-700 flex items-center justify-center">
            <TrendingUp className="w-6 h-6 text-gray-200" />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold font-display text-white">RecoverAI</h1>
            <span className="text-xs text-gray-500 font-mono tracking-wider uppercase font-bold">
              Fintech Operations Workspace
            </span>
          </div>
        </div>

        {/* Headline */}
        <div className="space-y-3">
          <h2 className="text-xl font-bold font-display text-gray-200">
            Recover lost revenue.
          </h2>
          <p className="text-gray-400 text-sm leading-relaxed font-medium">
            RecoverAI finds revenue leakage, determines the safest recovery path, and executes bounded recovery workflows. Import transaction failure datasets to isolate and recover leaking revenue.
          </p>
        </div>

        {/* Primary CTA */}
        <button
          onClick={onLoadBatch}
          className="w-full flex items-center justify-center gap-3 py-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm transition"
        >
          <Zap className="w-4 h-4 text-white" />
          <span>Load Demo Recovery Batch</span>
        </button>

        {/* Previous Run Context */}
        <div className="pt-6 border-t border-gray-800 space-y-4 text-xs font-semibold">
          <span className="text-xs text-gray-500 font-bold uppercase tracking-wider block">
            Previous Session Summary
          </span>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800">
              <span className="text-xs text-gray-500 block uppercase font-bold">Recovered</span>
              <span className="text-base font-extrabold text-emerald-400 font-mono">₹18,400</span>
            </div>
            <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800">
              <span className="text-xs text-gray-500 block uppercase font-bold">Processed</span>
              <span className="text-base font-extrabold text-gray-200 font-mono">24</span>
            </div>
            <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800">
              <span className="text-xs text-gray-500 block uppercase font-bold">Conversion</span>
              <span className="text-base font-extrabold text-blue-400 font-mono">58.6%</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
