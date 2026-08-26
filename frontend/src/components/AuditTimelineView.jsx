import React from 'react';
import { Clock, Zap, Bot, ShieldCheck, CheckCircle2, XCircle } from 'lucide-react';

export default function AuditTimelineView({ logs }) {
  // Static fallback timeline
  const displayLogs = (logs && logs.length > 0) ? logs : [
    { time: '10:42:01', type: 'PAYMENT_FAILED', desc: 'Raw gateway transaction failure detected.' },
    { time: '10:42:02', type: 'RISK_DETECTED', desc: 'Isolated candidate as recoverable revenue risk.' },
    { time: '10:42:02', type: 'AI_DIAGNOSIS', desc: 'AI parsed timeout error and recommended retry (94% confidence).' },
    { time: '10:42:03', type: 'POLICY_CHECKED', desc: 'Policy Engine approved execution constraints.' },
    { time: '10:42:03', type: 'RECOVERY_INITIATED', desc: 'Awaiting operator manual launch authorization.' }
  ];

  const getIcon = (type) => {
    switch (type) {
      case 'PAYMENT_FAILED':
      case 'RISK_DETECTED':
        return <Zap className="w-3.5 h-3.5 text-blue-400" />;
      case 'AI_DIAGNOSIS':
        return <Bot className="w-3.5 h-3.5 text-indigo-400" />;
      case 'POLICY_CHECKED':
        return <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />;
      case 'RECOVERY_INITIATED':
      case 'RECOVERY_SUCCESS':
      case 'RECOVERED':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
      case 'RECOVERY_STOPPED':
      case 'RECOVERY_FAILED':
        return <XCircle className="w-3.5 h-3.5 text-rose-400" />;
      default:
        return <Clock className="w-3.5 h-3.5 text-gray-400" />;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
        <Clock className="w-4 h-4 text-blue-400" />
        <span>Operations Trace Log</span>
      </div>

      <div className="space-y-4 relative border-l border-gray-800 pl-4 ml-2">
        {displayLogs.map((log, index) => (
          <div key={index} className="relative animate-fade-in text-xs">
            <div className="absolute -left-6.5 top-0.5 bg-[#0F131D] rounded-full p-0.5 ring-4 ring-[#080B11]">
              {getIcon(log.type || log.action_type || log.event_type)}
            </div>
            
            <div className="space-y-0.5">
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-gray-400 font-bold uppercase tracking-wider">
                  {log.type || log.action_type || log.event_type}
                </span>
                <span className="text-gray-500 font-mono">
                  {log.time || new Date(log.created_at || log.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <p className="text-gray-300 leading-relaxed">
                {log.desc || log.description || log.details}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
