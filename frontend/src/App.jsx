import React, { useState, useEffect } from 'react';
import AppShell from './components/AppShell';
import RecoverLanding from './components/RecoverLanding';
import DiscoveryLoading from './components/DiscoveryLoading';
import WorkspaceView from './components/WorkspaceView';
import PolicyCenter from './components/PolicyCenter';
import SafetySandboxView from './components/SafetySandboxView';
import BatchPayoffView from './components/BatchPayoffView';

const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';

const initialCasesDataset = [
  {
    case_id: 'case_eval_001',
    payment_id: 'pay_fail_001',
    amount: 820000,
    initial_status: 'failed',
    root_cause: 'TIMEOUT',
    ai_action: 'RETRY',
    ai_confidence: 0.94,
    policy_decision: 'ALLOW',
    execution_status: 'PENDING',
    retry_count: 0,
    customer_reference: 'Cardholder A',
    recommended_action: 'Retry payment immediately',
    policy_reason: '',
    stopping_rule: ''
  },
  {
    case_id: 'case_eval_002',
    payment_id: 'pay_fail_002',
    amount: 485300,
    initial_status: 'failed',
    root_cause: 'TIMEOUT',
    ai_action: 'RETRY',
    ai_confidence: 0.91,
    policy_decision: 'ALLOW',
    execution_status: 'PENDING',
    retry_count: 0,
    customer_reference: 'Cardholder B',
    recommended_action: 'Retry payment after 30m cooldown',
    policy_reason: '',
    stopping_rule: ''
  },
  {
    case_id: 'case_eval_003',
    payment_id: 'pay_fail_003',
    amount: 320000,
    initial_status: 'failed',
    root_cause: 'CARD_EXPIRED',
    ai_action: 'RETRY',
    ai_confidence: 0.91,
    policy_decision: 'BLOCK',
    execution_status: 'BLOCKED',
    retry_count: 2,
    customer_reference: 'Cardholder C',
    recommended_action: 'Retry payment',
    policy_reason: 'Maximum retry limit reached (Attempts: 2).',
    stopping_rule: 'MAX_RETRIES_REACHED'
  },
  {
    case_id: 'case_eval_004',
    payment_id: 'pay_fail_004',
    amount: 534700,
    initial_status: 'failed',
    root_cause: 'INSUFFICIENT_FUNDS',
    ai_action: 'REMIND',
    ai_confidence: 0.91,
    policy_decision: 'ALLOW',
    execution_status: 'PENDING',
    retry_count: 0,
    customer_reference: 'Cardholder D',
    recommended_action: 'Send reminder WhatsApp link',
    policy_reason: '',
    stopping_rule: ''
  },
  {
    case_id: 'case_eval_005',
    payment_id: 'pay_fail_005',
    amount: 1200000,
    initial_status: 'failed',
    root_cause: 'TIMEOUT',
    ai_action: 'REMIND',
    ai_confidence: 0.91,
    policy_decision: 'ALLOW',
    execution_status: 'PENDING',
    retry_count: 0,
    customer_reference: 'Cardholder E',
    recommended_action: 'Send checkout reminder link',
    policy_reason: '',
    stopping_rule: ''
  },
  {
    case_id: 'case_eval_006',
    payment_id: 'pay_fail_006',
    amount: 2515300,
    initial_status: 'failed',
    root_cause: 'HIGH_VALUE',
    ai_action: 'RETRY',
    ai_confidence: 0.89,
    policy_decision: 'ESCALATE',
    execution_status: 'ESCALATED',
    retry_count: 0,
    customer_reference: 'Cardholder F',
    recommended_action: 'Retry payment',
    policy_reason: 'Amount exceeds automatic threshold of ₹25,000.',
    stopping_rule: ''
  }
];

export default function App() {
  const [activeTab, setActiveTab] = useState('discover'); // 'discover', 'sandbox', 'policies'
  const [workflowState, setWorkflowState] = useState('home'); // 'home', 'discovery', 'workspace', 'outcome'
  const [maxRetries, setMaxRetries] = useState(2);
  const [cases, setCases] = useState(initialCasesDataset);
  const [health, setHealth] = useState(null);

  const fetchHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch (e) {
      console.error("Health check failed", e);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const handleUpdateRetries = (newLimit) => {
    setMaxRetries(newLimit);
    
    // Dynamically adjust Case 003 status depending on retry limits
    setCases(prev => prev.map(c => {
      if (c.case_id === 'case_eval_003') {
        if (newLimit === 3) {
          return {
            ...c,
            policy_decision: 'ALLOW',
            execution_status: 'PENDING',
            policy_reason: ''
          };
        } else {
          return {
            ...c,
            policy_decision: 'BLOCK',
            execution_status: 'BLOCKED',
            policy_reason: 'Maximum retry limit reached (Attempts: 2).'
          };
        }
      }
      return c;
    }));
  };

  const handleExecuteResult = (caseId, outcome) => {
    setCases(prev => prev.map(c => {
      if (c.case_id === caseId) {
        return {
          ...c,
          execution_status: outcome,
          retry_count: outcome === 'SUCCEEDED' ? c.retry_count : c.retry_count + 1
        };
      }
      return c;
    }));
  };

  const handleRestart = () => {
    setCases(initialCasesDataset);
    setMaxRetries(2);
    setWorkflowState('home');
    setActiveTab('discover');
  };

  return (
    <AppShell
      activeTab={activeTab}
      setActiveTab={(tab) => {
        setActiveTab(tab);
        // If clicking discover, return to correct journey step
        if (tab === 'discover' && workflowState === 'outcome') {
          setWorkflowState('outcome');
        } else if (tab === 'discover') {
          setWorkflowState(workflowState === 'home' ? 'home' : workflowState);
        }
      }}
      health={health}
      evaluationId="eval_session_2026_demo"
      isRunning={false}
      onReloadDefault={fetchHealth}
    >
      
      {/* Tab: Discover (The central recovery campaign journey) */}
      {activeTab === 'discover' && (
        <>
          {workflowState === 'home' && (
            <RecoverLanding 
              onLoadBatch={() => setWorkflowState('discovery')} 
            />
          )}
          
          {workflowState === 'discovery' && (
            <DiscoveryLoading 
              onFinishDiscovery={() => setWorkflowState('workspace')} 
            />
          )}
          
          {workflowState === 'workspace' && (
            <WorkspaceView 
              cases={cases}
              onExecuteResult={handleExecuteResult}
              onFinishBatch={() => setWorkflowState('outcome')}
              maxRetries={maxRetries}
            />
          )}
          
          {workflowState === 'outcome' && (
            <BatchPayoffView 
              onRestart={handleRestart} 
            />
          )}
        </>
      )}

      {/* Tab: Safety Sandbox */}
      {activeTab === 'sandbox' && (
        <div className="p-8 overflow-y-auto h-full bg-[#080B11]">
          <SafetySandboxView />
        </div>
      )}

      {/* Tab: Policies Center */}
      {activeTab === 'policies' && (
        <div className="p-8 overflow-y-auto h-full bg-[#080B11]">
          <PolicyCenter 
            maxRetries={maxRetries}
            onUpdateRetries={handleUpdateRetries}
          />
        </div>
      )}

    </AppShell>
  );
}
