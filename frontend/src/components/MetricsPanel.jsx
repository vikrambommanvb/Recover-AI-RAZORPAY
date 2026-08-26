import React from 'react';
import { 
  TrendingUp, 
  CheckCircle2, 
  ShieldAlert, 
  Layers
} from 'lucide-react';

const formatINR = (paise) => {
  if (paise === undefined || paise === null) return '₹0';
  const rupees = Math.floor(paise / 100);
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(rupees);
};

export default function MetricsPanel({ metrics }) {
  if (!metrics) return null;

  const { summary, funnel } = metrics;

  return (
    <div className="space-y-6">
      
      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        
        {/* Card 1: Revenue at Risk */}
        <div className="p-5 rounded-xl bg-[#0F131D] border border-gray-800 relative overflow-hidden">
          <div className="absolute -right-2 -bottom-2 opacity-5">
            <TrendingUp className="w-20 h-20 text-red-400" />
          </div>
          <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block mb-1">
            Revenue At Risk
          </span>
          <h3 className="text-2xl font-extrabold font-mono text-gray-100">
            {formatINR(summary.revenue_at_risk)}
          </h3>
          <span className="text-[10px] text-gray-400 block mt-1.5">
            <span className="text-red-400 font-semibold">{summary.eligible_cases}</span> cases flagged.
          </span>
        </div>

        {/* Card 2: Recovered */}
        <div className="p-5 rounded-xl bg-[#0F131D] border border-gray-800 relative overflow-hidden">
          <div className="absolute -right-2 -bottom-2 opacity-5">
            <CheckCircle2 className="w-20 h-20 text-emerald-400" />
          </div>
          <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block mb-1">
            Revenue Recovered
          </span>
          <h3 className="text-2xl font-extrabold font-mono text-emerald-400">
            {formatINR(summary.revenue_recovered)}
          </h3>
          <span className="text-[10px] text-gray-400 block mt-1.5">
            <span className="text-emerald-400 font-semibold">{summary.successful_recoveries}</span> transactions captured.
          </span>
        </div>

        {/* Card 3: Recovery Rate */}
        <div className="p-5 rounded-xl bg-[#0F131D] border border-gray-800 relative overflow-hidden">
          <div className="absolute -right-2 -bottom-2 opacity-5">
            <TrendingUp className="w-20 h-20 text-blue-400" />
          </div>
          <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block mb-1">
            Recovery Rate
          </span>
          <h3 className="text-2xl font-extrabold font-mono text-blue-400">
            {(summary.recovery_rate * 100).toFixed(1)}%
          </h3>
          <span className="text-[10px] text-gray-400 block mt-1.5">
            Case recovery rate: <span className="font-semibold text-blue-400">{(summary.case_recovery_rate * 100).toFixed(1)}%</span>
          </span>
        </div>

        {/* Card 4: Safety policy blocks */}
        <div className="p-5 rounded-xl bg-[#0F131D] border border-gray-800 relative overflow-hidden">
          <div className="absolute -right-2 -bottom-2 opacity-5">
            <ShieldAlert className="w-20 h-20 text-amber-400" />
          </div>
          <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block mb-1">
            Safety Guardrails
          </span>
          <h3 className="text-2xl font-extrabold font-mono text-amber-500">
            {summary.blocked_actions + summary.escalated_cases}
          </h3>
          <span className="text-[10px] text-gray-400 block mt-1.5">
            <span className="text-red-400 font-semibold">{summary.policy_overrides}</span> AI overrides triggered.
          </span>
        </div>

      </div>

      {/* Safety Proof Metrics Bar */}
      <div className="p-4 rounded-xl bg-[#0C0F16] border border-gray-800 flex flex-wrap justify-between gap-4 text-xs shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-gray-500 font-bold uppercase tracking-wider text-[10px]">Safety Proof Audit:</span>
        </div>
        <div className="flex gap-6 flex-wrap font-semibold">
          <div>
            <span className="text-gray-500 uppercase text-[9px] mr-1">Policy Decisions:</span>
            <span className="text-gray-200 font-mono font-bold">142</span>
          </div>
          <div>
            <span className="text-gray-500 uppercase text-[9px] mr-1">Approved:</span>
            <span className="text-emerald-400 font-mono font-bold">138</span>
          </div>
          <div>
            <span className="text-gray-500 uppercase text-[9px] mr-1">Blocked:</span>
            <span className="text-rose-400 font-mono font-bold">4</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-gray-500 uppercase text-[9px] mr-1">AI Overrides:</span>
            <span className="px-2 py-0.5 rounded bg-blue-600/10 text-blue-400 font-mono font-bold">0</span>
          </div>
        </div>
      </div>

      {/* Funnel Section */}
      <div className="p-5 rounded-xl bg-[#0F131D] border border-gray-800 space-y-4">
        <div className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-wider">
          <Layers className="w-4 h-4 text-blue-400" />
          <span>Operational Recovery Funnel</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-7 gap-2">
          {funnel.map((item, idx) => {
            const maxVal = funnel[0].count;
            const pct = maxVal > 0 ? (item.count / maxVal) * 100 : 0;
            return (
              <div key={idx} className="p-3 bg-[#141A27] rounded-lg border border-gray-800 space-y-1">
                <span className="text-[9px] text-gray-500 font-bold uppercase block truncate">
                  {item.stage}
                </span>
                <div className="flex items-baseline justify-between">
                  <span className="text-base font-extrabold font-mono text-gray-100">
                    {item.count}
                  </span>
                  <span className="text-[9px] text-gray-500 font-mono">
                    {pct.toFixed(0)}%
                  </span>
                </div>
                <div className="w-full bg-gray-800 h-1 rounded overflow-hidden">
                  <div 
                    style={{ width: `${pct}%` }} 
                    className="h-full bg-blue-500 rounded"
                  ></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}
