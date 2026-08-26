import React from 'react';
import { 
  Clock, 
  CheckCircle2, 
  XCircle, 
  Bot, 
  ShieldCheck, 
  Zap 
} from 'lucide-react';

const DEFAULT_MOCK_LOGS = [
  { timestamp: '2026-08-26T20:41:00.000Z', event_type: 'PAYMENT_DETECTION', description: 'Original failed transaction detected on Gateway API.' },
  { timestamp: '2026-08-26T20:41:01.000Z', event_type: 'RISK_DETECTED', description: 'Revenue risk isolated. Case flagged as recoverable.' },
  { timestamp: '2026-08-26T20:41:02.000Z', event_type: 'AI_RECOMMENDATION', description: 'AI Agent evaluated transaction metadata and suggested RETRY.' },
  { timestamp: '2026-08-26T20:41:03.000Z', event_type: 'POLICY_EVALUATION', description: 'Deterministic Policy Engine checked limits and approved ALLOW.' },
  { timestamp: '2026-08-26T20:41:04.000Z', event_type: 'RECOVERY_INITIALIZED', description: 'Case registered and ready for execution.' }
];

export default function AuditTrail({ auditLogs }) {
  const displayLogs = (auditLogs && auditLogs.length > 0) ? auditLogs : DEFAULT_MOCK_LOGS;

  const getIcon = (type) => {
    switch (type) {
      case 'PAYMENT_DETECTION':
      case 'RISK_DETECTED':
        return <Zap className="w-3.5 h-3.5 text-blue-400" />;
      case 'AI_RECOMMENDATION':
        return <Bot className="w-3.5 h-3.5 text-indigo-400" />;
      case 'POLICY_EVALUATION':
        return <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />;
      case 'RECOVERY_ATTEMPT_SUCCESS':
      case 'RECOVERY_VERIFIED':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
      case 'RECOVERY_ATTEMPT_FAILED':
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
        <span>Operational Audit timeline</span>
      </div>

      <div className="space-y-4 relative border-l border-gray-800 pl-4 ml-2">
        {displayLogs.map((log, index) => (
          <div key={log.id || index} className="relative animate-fade-in">
            {/* Timeline node icon */}
            <div className="absolute -left-6.5 top-0.5 bg-[#0F131D] rounded-full p-0.5 ring-4 ring-[#080B11]">
              {getIcon(log.action_type || log.event_type)}
            </div>
            
            <div className="space-y-0.5">
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-gray-400 font-bold uppercase tracking-wider">
                  {log.action_type || log.event_type}
                </span>
                <span className="text-gray-500 font-mono">
                  {new Date(log.created_at || log.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <p className="text-xs text-gray-300 leading-relaxed">
                {log.description || log.details}
              </p>
              {log.metadata && Object.keys(log.metadata).length > 0 && (
                <div className="p-2 bg-[#141A27]/60 border border-gray-800 rounded font-mono text-[9px] text-gray-400 mt-1 max-w-full overflow-x-auto">
                  {JSON.stringify(log.metadata, null, 2)}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
