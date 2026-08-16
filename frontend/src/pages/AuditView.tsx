import React, { useEffect, useState } from 'react';
import { fetchAuditLogs } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { FileText, RefreshCw, AlertCircle, LogIn, Clock } from 'lucide-react';

export const AuditView: React.FC = () => {
  const { logout } = useAuth();
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isAuthError, setIsAuthError] = useState<boolean>(false);

  useEffect(() => {
    loadLogs();
  }, []);

  const loadLogs = async () => {
    setLoading(true);
    setError(null);
    setIsAuthError(false);
    try {
      const data = await fetchAuditLogs(100);
      setLogs(data);
    } catch (err: any) {
      console.error('Failed to load prediction audit records:', err);
      if (err?.status === 401 || err?.message === 'UNAUTHORIZED') {
        setIsAuthError(true);
      } else {
        setError(err?.message || 'Unable to load prediction audit records.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-700" />
            <h1 className="text-xl font-bold font-display text-[#12213A]">Prediction Audit Log</h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Prediction history and decision trace
          </p>
        </div>

        <button
          onClick={loadLogs}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-[#12213A] text-xs font-semibold rounded-lg border border-slate-200 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* 401 Session Expired State */}
      {isAuthError && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 text-center space-y-3">
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-amber-100 text-amber-800">
            <AlertCircle className="w-5 h-5" />
          </div>
          <h3 className="text-sm font-bold text-amber-900">Authentication Session Expired</h3>
          <p className="text-xs text-amber-700 max-w-md mx-auto">
            Your session token is missing, invalid, or expired. Please sign in again to view prediction audit records.
          </p>
          <div>
            <button
              onClick={logout}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-amber-800 hover:bg-amber-900 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
            >
              <LogIn className="w-4 h-4" />
              <span>Sign in again</span>
            </button>
          </div>
        </div>
      )}

      {/* General Error State */}
      {!isAuthError && error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center space-y-3">
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-red-100 text-red-800">
            <AlertCircle className="w-5 h-5" />
          </div>
          <h3 className="text-sm font-bold text-red-900">Unable to load prediction audit records.</h3>
          <p className="text-xs text-red-700 max-w-md mx-auto">{error}</p>
          <div>
            <button
              onClick={loadLogs}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-red-700 hover:bg-red-800 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        </div>
      )}

      {/* Main Audit Table View */}
      {!isAuthError && !error && (
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-50 text-slate-500 border-b border-slate-200 font-mono">
                  <th className="p-3">Prediction ID</th>
                  <th className="p-3">Patient ID</th>
                  <th className="p-3">Probability</th>
                  <th className="p-3">Risk Tier</th>
                  <th className="p-3">Threshold</th>
                  <th className="p-3">Model Version</th>
                  <th className="p-3">Drivers / Actions</th>
                  <th className="p-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {loading ? (
                  [...Array(5)].map((_, i) => (
                    <tr key={i} className="animate-pulse">
                      <td className="p-3"><div className="h-4 bg-slate-100 rounded w-12"></div></td>
                      <td className="p-3"><div className="h-4 bg-slate-100 rounded w-28"></div></td>
                      <td className="p-3"><div className="h-4 bg-slate-100 rounded w-16"></div></td>
                      <td className="p-3"><div className="h-4 bg-slate-100 rounded w-20"></div></td>
                      <td className="p-3"><div className="h-4 bg-slate-100 rounded w-16"></div></td>
                      <td className="p-3"><div className="h-4 bg-slate-100 rounded w-24"></div></td>
                      <td className="p-3"><div className="h-4 bg-slate-100 rounded w-28"></div></td>
                      <td className="p-3"><div className="h-4 bg-slate-100 rounded w-32"></div></td>
                    </tr>
                  ))
                ) : logs.length > 0 ? (
                  logs.map((log) => {
                    const probPct = typeof log.probability === 'number' ? (log.probability * 100).toFixed(1) : 'N/A';
                    const threshPct = typeof log.operating_threshold === 'number' ? (log.operating_threshold * 100).toFixed(1) : '25.6';
                    
                    return (
                      <tr key={log.id} className="hover:bg-slate-50 transition-colors">
                        <td className="p-3 font-bold text-slate-700">#{log.id}</td>
                        <td className="p-3 font-bold text-[#12213A]">
                          {log.patient_reference || `PT-${log.id}`}
                        </td>
                        <td className="p-3 font-bold text-[#12213A]">{probPct}%</td>
                        <td className="p-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                              log.risk_tier === 'High Risk'
                                ? 'bg-red-100 text-red-800 border border-red-200'
                                : log.risk_tier === 'Elevated Risk'
                                ? 'bg-amber-100 text-amber-800 border border-amber-200'
                                : log.risk_tier === 'Moderate Risk'
                                ? 'bg-blue-100 text-blue-800 border border-blue-200'
                                : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                            }`}
                          >
                            {log.risk_tier || 'Minimal Risk'}
                          </span>
                        </td>
                        <td className="p-3 text-slate-600">{threshPct}%</td>
                        <td className="p-3 text-slate-600 font-sans">
                          {log.model_name || 'LogisticRegression'} v{log.model_version || '1.0.0'}
                        </td>
                        <td className="p-3 text-slate-600 font-sans">
                          {log.explanation_count || 0} Drivers / {log.action_count || 0} Actions
                        </td>
                        <td className="p-3 text-slate-500 font-sans whitespace-nowrap">
                          <div className="flex items-center gap-1.5">
                            <Clock className="w-3 h-3 text-slate-400" />
                            <span>{log.timestamp ? new Date(log.timestamp).toLocaleString() : 'N/A'}</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={8} className="p-12 text-center text-slate-500 font-sans space-y-2">
                      <p className="text-sm font-semibold text-slate-700">No prediction audit records found.</p>
                      <p className="text-xs text-slate-500">Run a prediction to create an audit entry.</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
