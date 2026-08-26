import React, { useState } from 'react';
import { 
  Bot, 
  ChevronRight
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

export default function CopilotPanel({ activeTab, selectedCase, queueCount }) {
  const [showSection, setShowSection] = useState(null);

  const getContextInfo = () => {
    if (activeTab === 'discover') {
      return {
        state: 'DISCOVERY_FEED',
        message: 'I am tracking the real time gateway transaction feed. Scroll down to see failed payments isolated as revenue risk candidates.',
        tips: ['How is risk isolated?', 'What are permanent failures?']
      };
    }

    if (!selectedCase) {
      return {
        state: 'QUEUE_PREVIEW',
        message: `I found ${queueCount || 0} potentially recoverable payments. Select a case from the queue to start the diagnosis flow.`,
        tips: ['What constitutes a case?', 'How does AI recommend actions?']
      };
    }

    const { 
      case_id, 
      amount, 
      root_cause, 
      ai_action, 
      ai_confidence, 
      policy_decision, 
      execution_status,
      stop_reason,
      escalation_reason
    } = selectedCase;

    if (execution_status === 'SUCCEEDED') {
      return {
        state: 'RECOVERY_SUCCEEDED',
        message: `Success. Captured state verified on Razorpay Test Mode gateway. ${formatINR(amount)} added to recovered revenue metrics.`,
        tips: ['View captured webhook logs', 'Show audit trail details']
      };
    }

    if (execution_status === 'FAILED') {
      return {
        state: 'RECOVERY_FAILED',
        message: `Recovery stopped: ${stop_reason || 'payment verification failed on the gateway'}. The system recorded ₹0 recovered.`,
        tips: ['Why did verification fail?', 'Inspect retry timeline']
      };
    }

    if (policy_decision === 'BLOCK') {
      return {
        state: 'SAFETY_BLOCK',
        message: `AI suggested ${ai_action || 'RETRY'}, but the Deterministic Policy Engine blocked the execution. Reason: ${stop_reason || 'Payment status check failed.'}`,
        tips: ['Show guardrail rules', 'Why is AI overridden?']
      };
    }

    if (policy_decision === 'ESCALATE') {
      return {
        state: 'HUMAN_ESCALATION',
        message: `Human Review Required. Case ${case_id} is escalated because: ${escalation_reason || 'amount exceeds auto run limit'}.`,
        tips: ['Approve this action manually', 'Stop future runs']
      };
    }

    if (execution_status === 'VERIFICATION_REQUIRED') {
      return {
        state: 'AWAITING_VERIFICATION',
        message: 'Order created in test mode. Awaiting verification of the payment state from Razorpay.',
        tips: ['How is status verified?', 'Gateway connection details']
      };
    }

    return {
      state: 'EVALUATION_ACTIVE',
      message: `AI diagnosed cause as ${root_cause || 'temporary timeout'} and recommends a RETRY with ${(ai_confidence * 100).toFixed(0)}% confidence. Safety check verdict is ALLOW.`,
      tips: ['Show evidence logs', 'Show safety engine checks']
    };
  };

  const context = getContextInfo();

  return (
    <div className="bg-[#0F131D] rounded-xl border border-gray-800 p-5 flex flex-col justify-between h-full bg-gradient-to-b from-[#0F131D] to-[#0A0D15]">
      
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-800 pb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-blue-600/10 text-blue-400">
              <Bot className="w-4 h-4 animate-bounce" />
            </div>
            <span className="text-xs font-bold uppercase tracking-wider text-gray-200">
              RecoverAI Copilot
            </span>
          </div>
          <span className="px-2 py-0.5 rounded bg-gray-800 text-gray-500 font-mono text-[9px] font-bold">
            {context.state}
          </span>
        </div>

        {/* Message */}
        <div className="space-y-3">
          <p className="text-xs text-gray-300 leading-relaxed font-medium">
            {context.message}
          </p>
        </div>

        {/* Context Accordion / Sub explanations */}
        {showSection && (
          <div className="p-3 bg-[#141A27] rounded-lg border border-gray-800 text-[11px] text-gray-400 leading-normal animate-fade-in">
            {showSection === 'How is risk isolated?' && 'Risk is isolated by verifying if the transaction amount is positive, has a unique case identifier, and matches FAILED or AUTHORIZED gateway states.'}
            {showSection === 'What are permanent failures?' && 'Permanent failures include invalid cards or expired checkouts. RecoverAI policy rules veto automation for these cases, saving processing costs.'}
            {showSection === 'What constitutes a case?' && 'A recovery case maps one unique payment failure. It holds the gateway metadata, classified cause, policy gate checks, and audit history.'}
            {showSection === 'How does AI recommend actions?' && 'AI maps error descriptions to classifications (e.g. BANK_DECLINE) and recommends interventions based on the probability of recovery.'}
            {showSection === 'Show guardrail rules' && 'Safety checks require: payment ID must exist, amount must be positive, attempts must be under limit, and payment state must be eligible.'}
            {showSection === 'Why is AI overridden?' && 'If the AI recommends a retry but the payment status is unknown, the policy engine blocks the request to prevent double-captures.'}
            {showSection === 'Show evidence logs' && 'Evidence is gathered from payment payloads, status attributes, and root cause descriptions returned by the gateway API.'}
            {showSection === 'Show safety engine checks' && 'Deterministic checks: Verified payment ID, verified retry count <= 3, verified amount under threshold.'}
            {showSection === 'How is status verified?' && 'Status is verified by querying the Razorpay API payments endpoint for the corresponding ID and checking if captured is true.'}
            {showSection === 'View captured webhook logs' && 'The webhook event log stores event type details (payment.captured) and unique payload IDs for traceability.'}
            {showSection === 'Show audit trail details' && 'The audit trail registers payment detection, classification, AI suggestions, policy checks, execution status, and outcomes.'}
            {showSection === 'Approve this action manually' && 'Merchant operator can override the ESCALATE block to execute bounded checkout links manually.'}
          </div>
        )}
      </div>

      {/* Suggested Actions/Questions */}
      <div className="pt-4 border-t border-gray-800 space-y-2 shrink-0">
        <span className="text-[9px] text-gray-500 font-bold uppercase tracking-wider block mb-1">
          Ask Copilot
        </span>
        <div className="flex flex-col gap-1.5">
          {context.tips.map((tip, idx) => (
            <button
              key={idx}
              onClick={() => setShowSection(showSection === tip ? null : tip)}
              className="flex items-center justify-between p-2 rounded-lg bg-[#141A27] hover:bg-gray-800 text-left text-[10px] text-gray-400 hover:text-gray-200 transition font-semibold"
            >
              <span>{tip}</span>
              <ChevronRight className="w-3 h-3 text-gray-600" />
            </button>
          ))}
        </div>
      </div>

    </div>
  );
}
