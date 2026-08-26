import React, { useState, useEffect } from 'react';
import { Layers, ArrowRight, Loader2 } from 'lucide-react';

export default function DiscoveryLoading({ onFinishDiscovery }) {
  const [progress, setProgress] = useState(0);
  const [finished, setFinished] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setFinished(true);
          return 100;
        }
        return prev + 10;
      });
    }, 150);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-full flex items-center justify-center p-6 bg-[#080B11]">
      <div className="max-w-md w-full bg-[#0F131D] border border-gray-800 rounded-2xl p-8 space-y-8 shadow-xl shadow-black/40">
        
        {!finished ? (
          /* Loading State */
          <div className="space-y-6 text-center py-6">
            <Loader2 className="w-10 h-10 text-blue-500 animate-spin mx-auto" />
            <div className="space-y-2">
              <h3 className="text-base font-bold font-display text-gray-200">
                Analyzing 48 revenue events...
              </h3>
              <p className="text-xs text-gray-500 max-w-xs mx-auto">
                RecoverAI is isolating payment failures, parsing root causes, and evaluating merchant policy constraints.
              </p>
            </div>
            
            {/* Progress Bar */}
            <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
              <div 
                style={{ width: `${progress}%` }} 
                className="h-full bg-blue-500 rounded-full transition-all duration-150"
              ></div>
            </div>
            <span className="text-xs font-mono font-bold text-gray-500">{progress}%</span>
          </div>
        ) : (
          /* Results Briefing State */
          <div className="space-y-6 animate-fade-in">
            <div className="flex items-center gap-2.5 pb-4 border-b border-gray-800">
              <Layers className="w-5 h-5 text-blue-400" />
              <h3 className="text-lg font-bold font-display text-gray-200">
                Discovery Run Complete
              </h3>
            </div>

            <p className="text-xs text-gray-400 leading-relaxed">
              RecoverAI isolated 17 recovery opportunities from the failure batch of 48 events. Permanent declines and invalid payments were excluded.
            </p>

            {/* Results Grid */}
            <div className="grid grid-cols-2 gap-4 text-xs font-semibold">
              <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800">
                <span className="text-gray-500 block text-[9px] uppercase mb-0.5">Events Analyzed</span>
                <span className="text-gray-200 font-mono font-bold">48</span>
              </div>
              <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800">
                <span className="text-gray-500 block text-[9px] uppercase mb-0.5">Potential Leakage</span>
                <span className="text-rose-400 font-mono font-bold">₹58,753</span>
              </div>
              <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800">
                <span className="text-gray-500 block text-[9px] uppercase mb-0.5">Recoverable Opportunities</span>
                <span className="text-blue-400 font-mono font-bold">17</span>
              </div>
              <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800">
                <span className="text-gray-500 block text-[9px] uppercase mb-0.5">Blocked by Policy</span>
                <span className="text-amber-500 font-mono font-bold">4</span>
              </div>
            </div>

            {/* Review Opportunities Button */}
            <button
              onClick={onFinishDiscovery}
              className="w-full flex items-center justify-center gap-2 py-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm transition"
            >
              <span>Review Recovery Opportunities</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
