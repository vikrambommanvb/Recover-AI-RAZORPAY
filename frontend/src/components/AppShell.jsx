import React from 'react';
import {
  TrendingUp,
  ShieldAlert,
  Server,
  RotateCw
} from 'lucide-react';

export default function AppShell({ 
  activeTab, 
  setActiveTab, 
  health, 
  evaluationId, 
  isRunning, 
  onReloadDefault, 
  children 
}) {
  return (
    <div className="flex h-screen bg-[#090D16] text-gray-100 font-sans overflow-hidden">
      
      {/* SIDEBAR NAVIGATION */}
      <aside className="w-72 bg-[#0F131F] border-r border-[#1F293D] flex flex-col justify-between shrink-0">
        <div>
          {/* Logo Header */}
          <div className="p-6 border-b border-[#1F293D]">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gray-800 border border-gray-700 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-gray-200" />
              </div>
              <div>
                <h1 className="text-xl font-extrabold font-display text-white">
                  RecoverAI
                </h1>
                <span className="text-xs text-gray-500 font-mono tracking-wider uppercase font-bold">
                  Operations Workspace
                </span>
              </div>
            </div>
          </div>
          
          {/* Main Navigation Items */}
          <nav className="p-5 space-y-2">
            <button
              onClick={() => setActiveTab('discover')}
              className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-base font-semibold transition-all ${
                activeTab === 'discover'
                  ? 'bg-blue-600/10 text-blue-400 border-l-4 border-blue-500'
                  : 'text-gray-400 hover:bg-[#151B27] hover:text-gray-200'
              }`}
            >
              <TrendingUp className="w-5 h-5" />
              <span>Recover Revenue</span>
            </button>

            <button
              onClick={() => setActiveTab('sandbox')}
              className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-base font-semibold transition-all ${
                activeTab === 'sandbox'
                  ? 'bg-blue-600/10 text-blue-400 border-l-4 border-blue-500'
                  : 'text-gray-400 hover:bg-[#151B27] hover:text-gray-200'
              }`}
            >
              <ShieldAlert className="w-5 h-5" />
              <span>Safety Sandbox</span>
            </button>
            
            <button
              onClick={() => setActiveTab('policies')}
              className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-base font-semibold transition-all ${
                activeTab === 'policies'
                  ? 'bg-blue-600/10 text-blue-400 border-l-4 border-blue-500'
                  : 'text-gray-400 hover:bg-[#151B27] hover:text-gray-200'
              }`}
            >
              <Server className="w-5 h-5" />
              <span>Recovery Policies</span>
            </button>
          </nav>
        </div>

        {/* System Config & Heartbeat status */}
        <div className="p-6 border-t border-[#1F293D] bg-[#0A0D15]">
          <div className="flex items-center gap-2 mb-3 text-xs font-bold text-gray-400 uppercase tracking-wider">
            <Server className="w-4 h-4 text-gray-400" />
            <span>Health & Diagnostics</span>
          </div>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">FastAPI status:</span>
              <span className={`${
                health && health.status === 'ok' ? 'text-emerald-400' : 'text-amber-400'
              } font-bold flex items-center gap-1.5`}>
                <span className={`w-2 h-2 rounded-full ${
                  health && health.status === 'ok' ? 'bg-emerald-400 animate-ping' : 'bg-amber-400'
                }`}></span>
                {health ? (health.status === 'ok' ? 'Connected' : 'Demo Mode') : 'Simulation Mode'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Gateway Key:</span>
              <span className="text-blue-400 font-bold font-mono text-xs">
                rzp_test_...
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">MongoDB state:</span>
              <span className={`${
                health && health.database === 'healthy' ? 'text-emerald-400' : 'text-amber-400'
              } font-bold`}>
                {health && health.database === 'healthy' ? 'Connected' : 'Simulation Mode'}
              </span>
            </div>
            <div className="pt-2 border-t border-gray-800 flex flex-col gap-1.5">
              <span className="text-xs text-amber-500 font-bold uppercase tracking-wider block">
                Razorpay Test Mode
              </span>
              <span className="text-[11px] text-gray-500 font-mono leading-normal block">
                Synthetic test data loaded. No live transactions are processed.
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* MAIN CONTAINER */}
      <main className="flex-1 flex flex-col overflow-hidden bg-[#080B11]">
        
        {/* TOP HEADER */}
        <header className="h-20 border-b border-[#1F293D] bg-[#0F131F] px-10 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-extrabold font-display text-gray-100 uppercase tracking-wider">
              {activeTab === 'discover' && "Revenue Recovery Workspace"}
              {activeTab === 'sandbox' && "Interactive Safety Sandbox"}
              {activeTab === 'policies' && "Merchant Bounded Policies"}
            </h2>
            {evaluationId && (
              <span className="px-2.5 py-1 rounded bg-blue-600/10 text-blue-400 text-xs font-mono font-bold">
                Live Recovery Session
              </span>
            )}
          </div>
          
          <button 
            onClick={onReloadDefault}
            disabled={isRunning}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-bold border border-gray-700 transition"
          >
            <RotateCw className={`w-4 h-4 ${isRunning ? 'animate-spin' : ''}`} />
            <span>Sync Live Metrics</span>
          </button>
        </header>

        {/* CONTAINER VIEWPORT */}
        <div className="flex-1 overflow-hidden relative">
          {children}
        </div>
      </main>

    </div>
  );
}
