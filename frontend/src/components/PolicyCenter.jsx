import { Sliders, Info } from 'lucide-react';

export default function PolicyCenter({ maxRetries, onUpdateRetries }) {
  const policies = [
    { name: 'Max Automated Recovery Limit', value: '₹25,000', desc: 'Transactions exceeding this threshold escalate to manual review.' },
    { name: 'Unknown Gateway State Action', value: 'BLOCK', desc: 'Vetoes recovery if payment status cannot be verified.' },
    { name: 'Duplicate Payment Rule', value: 'BLOCK', desc: 'Idempotency checks reject duplicate retry triggers.' },
    { name: 'Expired Card Failure Handling', value: 'CUSTOMER ACTION', desc: 'Requests payment method update instead of triggering retries.' }
  ];

  return (
    <div className="space-y-6 max-w-2xl mx-auto bg-[#0F131D] border border-gray-800 rounded-xl p-6">
      
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-gray-800 pb-4">
        <Sliders className="w-5 h-5 text-blue-400" />
        <div>
          <h3 className="text-base font-bold font-display text-gray-200">
            Deterministic Recovery Policies
          </h3>
          <span className="text-[10px] text-gray-500 font-mono">
            Adjust limits to verify deterministic rules compliance.
          </span>
        </div>
      </div>

      {/* Editor Block */}
      <div className="p-4 rounded-lg bg-[#141A27] border border-gray-800 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-xs font-bold text-gray-200 block">Maximum Retry Attempts</span>
            <span className="text-[10px] text-gray-500">Number of allowed retry events before stopping.</span>
          </div>
          
          <div className="flex gap-2">
            {[2, 3].map(val => (
              <button
                key={val}
                onClick={() => onUpdateRetries(val)}
                className={`px-3 py-1.5 rounded font-mono font-bold text-xs transition ${
                  maxRetries === val 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-850 hover:bg-gray-800 text-gray-400 border border-gray-800'
                }`}
              >
                {val} Attempts
              </button>
            ))}
          </div>
        </div>

        <div className="p-3 bg-blue-500/5 rounded border border-blue-500/10 text-[11px] text-blue-400 flex gap-2">
          <Info className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            Changing this policy dynamically updates the stopping rules. Active cases exceeding {maxRetries} attempts will stop immediately.
          </span>
        </div>
      </div>

      {/* Static Policies List */}
      <div className="space-y-3">
        <span className="text-[9px] text-gray-500 font-bold uppercase tracking-wider block">
          Default Guardrail Regulations
        </span>

        <div className="space-y-2">
          {policies.map((p, idx) => (
            <div key={idx} className="flex justify-between items-center p-3 rounded-lg bg-[#141A27]/50 border border-gray-800/80 text-xs">
              <div>
                <span className="text-gray-300 font-bold block">{p.name}</span>
                <span className="text-[10px] text-gray-500 leading-normal">{p.desc}</span>
              </div>
              <span className="px-2.5 py-1 rounded bg-[#0F131D] text-gray-300 font-mono font-bold text-[10px] border border-gray-800">
                {p.value}
              </span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
