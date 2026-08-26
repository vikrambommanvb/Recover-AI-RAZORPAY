import React, { useState } from 'react';
import { 
  Search, 
  ChevronLeft, 
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

export default function RecoveryQueue({ cases, selectedCase, onSelectCase }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Filters
  const filteredCases = cases.filter(c => {
    const matchesSearch = 
      (c.case_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (c.payment_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (c.root_cause || '').toLowerCase().includes(searchTerm.toLowerCase());

    if (statusFilter === 'ALL') return matchesSearch;
    if (statusFilter === 'RECOVERED') return matchesSearch && c.execution_status === 'SUCCEEDED';
    if (statusFilter === 'FAILED') return matchesSearch && c.execution_status === 'FAILED';
    if (statusFilter === 'BLOCKED') return matchesSearch && c.policy_decision === 'BLOCK';
    if (statusFilter === 'ESCALATED') return matchesSearch && c.policy_decision === 'ESCALATE';
    return matchesSearch;
  });

  // Paging
  const totalPages = Math.max(1, Math.ceil(filteredCases.length / itemsPerPage));
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedCases = filteredCases.slice(startIndex, startIndex + itemsPerPage);

  const handlePageChange = (direction) => {
    if (direction === 'prev' && currentPage > 1) {
      setCurrentPage(currentPage - 1);
    } else if (direction === 'next' && currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#0F131D] rounded-xl border border-gray-800 overflow-hidden">
      
      {/* Filters Bar */}
      <div className="p-4 border-b border-gray-800 space-y-3 bg-[#0C0F16]">
        
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-3 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search by Case ID, Payment ID, or Root Cause..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full pl-9 pr-4 py-2.5 rounded-lg bg-[#141A27] border border-gray-800 text-xs font-semibold text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none transition"
          />
        </div>

        {/* Tab Filters */}
        <div className="flex gap-1 overflow-x-auto pb-1">
          {['ALL', 'RECOVERED', 'FAILED', 'BLOCKED', 'ESCALATED'].map(status => (
            <button
              key={status}
              onClick={() => {
                setStatusFilter(status);
                setCurrentPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition ${
                statusFilter === status 
                  ? 'bg-blue-600/15 text-blue-400 border border-blue-500/25' 
                  : 'bg-transparent text-gray-400 hover:text-gray-200 border border-transparent'
              }`}
            >
              {status}
            </button>
          ))}
        </div>

      </div>

      {/* Queue Table */}
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-gray-800 text-[10px] text-gray-500 font-bold uppercase tracking-wider bg-[#090C12] sticky top-0 z-10">
              <th className="p-4">Case ID</th>
              <th className="p-4">Amount</th>
              <th className="p-4">Diagnose</th>
              <th className="p-4">AI Recommend</th>
              <th className="p-4">Policy</th>
              <th className="p-4">Verify Result</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800 text-xs font-medium">
            {paginatedCases.length > 0 ? (
              paginatedCases.map((c) => {
                const isSelected = selectedCase?.case_id === c.case_id;
                return (
                  <tr 
                    key={c.case_id}
                    onClick={() => onSelectCase(c)}
                    className={`hover:bg-[#141A27] cursor-pointer transition ${
                      isSelected ? 'bg-blue-600/10 text-blue-400 font-semibold' : ''
                    }`}
                  >
                    <td className="p-4 font-mono text-[11px]">{c.case_id}</td>
                    <td className="p-4 font-mono font-bold">{formatINR(c.amount)}</td>
                    <td className="p-4 text-gray-400">{c.root_cause}</td>
                    <td className="p-4 font-bold text-indigo-400">{c.ai_action}</td>
                    <td className="p-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        c.policy_decision === 'ALLOW' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                        c.policy_decision === 'BLOCK' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : 
                        'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                      }`}>
                        {c.policy_decision}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        c.execution_status === 'SUCCEEDED' ? 'bg-emerald-500/10 text-emerald-400' :
                        c.execution_status === 'FAILED' ? 'bg-rose-500/10 text-rose-400' :
                        c.execution_status === 'ESCALATED' ? 'bg-amber-500/10 text-amber-400' :
                        c.execution_status === 'BLOCKED' ? 'bg-indigo-500/10 text-indigo-400' :
                        'bg-gray-500/10 text-gray-500'
                      }`}>
                        {c.execution_status}
                      </span>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan="6" className="p-12 text-center text-gray-600 font-semibold">
                  No cases matching the selected status filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <div className="p-4 border-t border-gray-800 bg-[#0C0F16] flex justify-between items-center text-xs shrink-0">
        <span className="text-gray-500 font-semibold">
          Page {currentPage} of {totalPages}
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => handlePageChange('prev')}
            disabled={currentPage === 1}
            className="p-1.5 rounded bg-gray-800 border border-gray-700 hover:bg-gray-700 text-gray-300 disabled:opacity-30 disabled:hover:bg-gray-800 transition"
            aria-label="Previous Page"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => handlePageChange('next')}
            disabled={currentPage === totalPages}
            className="p-1.5 rounded bg-gray-800 border border-gray-700 hover:bg-gray-700 text-gray-300 disabled:opacity-30 disabled:hover:bg-gray-800 transition"
            aria-label="Next Page"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

    </div>
  );
}
