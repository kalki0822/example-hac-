import React, { useEffect, useState } from 'react';
import { fetchDashboardSummary, fetchAuditLogs } from '../api/client';
import { Shield, Server, Database, Users, Activity, FileText, CheckCircle2, Clock } from 'lucide-react';

export const AdminDashboard: React.FC = () => {
  const [summary, setSummary] = useState<any>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  useEffect(() => {
    loadAdminData();
  }, []);

  const loadAdminData = async () => {
    try {
      const [sumRes, logsRes] = await Promise.all([
        fetchDashboardSummary(),
        fetchAuditLogs(20)
      ]);
      setSummary(sumRes);
      setAuditLogs(logsRes);
    } catch (err) {
      console.error('Failed to load admin dashboard data:', err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex items-center justify-between bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-red-600" />
            <h1 className="text-xl font-bold font-display text-[#12213A]">Admin System Portal</h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            System status, persistence health, model metadata, and user activity logging.
          </p>
        </div>
        <span className="text-xs font-mono font-bold text-slate-600 bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
          Role: ADMIN
        </span>
      </div>

      {/* System Health Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-1">
          <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
            <Server className="w-3.5 h-3.5 text-emerald-600" /> API Engine
          </span>
          <p className="text-lg font-mono font-bold text-emerald-600 flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4" /> Healthy
          </p>
          <span className="text-[11px] text-slate-400 font-mono">FastAPI v1.0.0</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-1">
          <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
            <Database className="w-3.5 h-3.5 text-blue-600" /> Operational DB
          </span>
          <p className="text-lg font-mono font-bold text-[#12213A]">
            {summary ? `${summary.total_predictions_logged} Records` : 'Active'}
          </p>
          <span className="text-[11px] text-slate-400 font-mono">SQLAlchemy ORM</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-1">
          <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-purple-600" /> Model Pipeline
          </span>
          <p className="text-lg font-mono font-bold text-[#12213A]">
            {summary ? summary.model_name : 'LogisticRegression'}
          </p>
          <span className="text-[11px] text-slate-400 font-mono">v1.0.0 (OOF Quartile Stratification)</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-1">
          <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
            <Users className="w-3.5 h-3.5 text-amber-600" /> Active Users
          </span>
          <p className="text-lg font-mono font-bold text-[#12213A]">
            {summary ? summary.active_users_count : '3'}
          </p>
          <span className="text-[11px] text-slate-400 font-mono">CLINICIAN, ANALYST, ADMIN</span>
        </div>
      </div>

      {/* Recent Prediction Audit Table */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-slate-600" />
            <h2 className="text-sm font-bold font-display text-[#12213A]">
              Recent Audit Log Activity
            </h2>
          </div>
          <span className="text-xs font-mono text-slate-500">{auditLogs.length} Events</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-slate-50 text-slate-500 border-b border-slate-200 font-mono">
                <th className="p-2.5">ID</th>
                <th className="p-2.5">Patient Ref</th>
                <th className="p-2.5">User</th>
                <th className="p-2.5">Probability</th>
                <th className="p-2.5">Risk Tier</th>
                <th className="p-2.5">Model</th>
                <th className="p-2.5">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {auditLogs.length > 0 ? (
                auditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50">
                    <td className="p-2.5 font-bold text-slate-700">#{log.id}</td>
                    <td className="p-2.5 font-semibold text-[#12213A]">{log.patient_reference}</td>
                    <td className="p-2.5 text-slate-600">{log.user_email}</td>
                    <td className="p-2.5 font-bold text-[#12213A]">{(log.probability * 100).toFixed(1)}%</td>
                    <td className="p-2.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        log.risk_tier === 'High Risk'
                          ? 'bg-red-100 text-red-800'
                          : log.risk_tier === 'Moderate Risk'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-slate-100 text-slate-700'
                      }`}>
                        {log.risk_tier}
                      </span>
                    </td>
                    <td className="p-2.5 text-slate-500">{log.model_name} v{log.model_version}</td>
                    <td className="p-2.5 text-slate-400 flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-300" />
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="p-6 text-center text-slate-400 italic font-sans">
                    No prediction audit logs recorded yet. Run a prediction to see audit entries.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
