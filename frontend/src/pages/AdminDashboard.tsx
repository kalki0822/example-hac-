import React, { useEffect, useState } from 'react';
import { fetchDashboardSummary, fetchAuditLogs, fetchUsers, adminCreateUser, deleteUser } from '../api/client';
import { Shield, Server, Database, Users, Activity, FileText, CheckCircle2, Clock, UserPlus, Trash2, AlertCircle } from 'lucide-react';

export const AdminDashboard: React.FC = () => {
  const [summary, setSummary] = useState<any>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [userList, setUserList] = useState<any[]>([]);

  // Form fields for creating user
  const [showAddUserModal, setShowAddUserModal] = useState<boolean>(false);
  const [newFullName, setNewFullName] = useState<string>('');
  const [newEmail, setNewEmail] = useState<string>('');
  const [newPassword, setNewPassword] = useState<string>('');
  const [newRole, setNewRole] = useState<string>('CLINICIAN');

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    loadAdminData();
  }, []);

  const loadAdminData = async () => {
    try {
      const [sumRes, logsRes, usersRes] = await Promise.all([
        fetchDashboardSummary(),
        fetchAuditLogs(20),
        fetchUsers()
      ]);
      setSummary(sumRes);
      setAuditLogs(logsRes);
      setUserList(usersRes);
    } catch (err) {
      console.error('Failed to load admin dashboard data:', err);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      if (!newFullName.trim() || !newEmail.trim() || !newPassword.trim()) {
        throw new Error('Please fill in all user account fields.');
      }
      await adminCreateUser({
        full_name: newFullName.trim(),
        email: newEmail.trim(),
        password: newPassword,
        role: newRole
      });
      setSuccessMsg(`User account '${newEmail}' successfully provisioned as ${newRole}.`);
      setNewFullName('');
      setNewEmail('');
      setNewPassword('');
      setShowAddUserModal(false);
      const updatedUsers = await fetchUsers();
      setUserList(updatedUsers);
    } catch (err: any) {
      setError(err.message || 'Failed to create user account.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async (userId: number, userEmail: string) => {
    if (!window.confirm(`Are you sure you want to delete user account '${userEmail}'?`)) {
      return;
    }

    try {
      await deleteUser(userId);
      setSuccessMsg(`User account '${userEmail}' deleted successfully.`);
      const updatedUsers = await fetchUsers();
      setUserList(updatedUsers);
    } catch (err: any) {
      alert(err.message || 'Failed to delete user.');
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
            System status, persistence health, user management, and activity logging.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowAddUserModal(true)}
            className="px-3.5 py-1.5 bg-[#12213A] hover:bg-slate-800 text-white font-semibold text-xs rounded-lg flex items-center gap-1.5 transition-colors shadow-xs"
          >
            <UserPlus className="w-4 h-4" />
            <span>Add Clinician / Analyst</span>
          </button>
          <span className="text-xs font-mono font-bold text-slate-600 bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
            Role: ADMIN
          </span>
        </div>
      </div>

      {/* Global Status Alerts */}
      {successMsg && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-600 hover:text-emerald-800 font-bold">×</button>
        </div>
      )}

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
            <Database className="w-3.5 h-3.5 text-blue-600" /> PostgreSQL DB
          </span>
          <p className="text-lg font-mono font-bold text-[#12213A]">
            {summary ? `${summary.total_patients_db.toLocaleString()} Records` : 'Active'}
          </p>
          <span className="text-[11px] text-slate-400 font-mono">vitals_db (Port 5432)</span>
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
            <Users className="w-3.5 h-3.5 text-amber-600" /> User Accounts
          </span>
          <p className="text-lg font-mono font-bold text-[#12213A]">
            {userList.length} Active
          </p>
          <span className="text-[11px] text-slate-400 font-mono">CLINICIAN, ANALYST, ADMIN</span>
        </div>
      </div>

      {/* User Management Section */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-slate-600" />
            <h2 className="text-sm font-bold font-display text-[#12213A]">
              Platform User Accounts & Access Management
            </h2>
          </div>
          <button
            onClick={() => setShowAddUserModal(true)}
            className="text-xs text-blue-700 font-semibold hover:underline flex items-center gap-1"
          >
            <UserPlus className="w-3.5 h-3.5" /> Provision New User
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-slate-50 text-slate-500 border-b border-slate-200 font-mono">
                <th className="p-2.5">User ID</th>
                <th className="p-2.5">Full Name</th>
                <th className="p-2.5">Work Email</th>
                <th className="p-2.5">Assigned Role</th>
                <th className="p-2.5">Status</th>
                <th className="p-2.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {userList.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50">
                  <td className="p-2.5 font-bold text-slate-700">#{u.id}</td>
                  <td className="p-2.5 font-semibold text-[#12213A]">{u.full_name || 'N/A'}</td>
                  <td className="p-2.5 text-slate-600">{u.email}</td>
                  <td className="p-2.5">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      u.role === 'ADMIN'
                        ? 'bg-red-100 text-red-800'
                        : u.role === 'ANALYST'
                        ? 'bg-purple-100 text-purple-800'
                        : 'bg-emerald-100 text-emerald-800'
                    }`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="p-2.5 text-emerald-700 font-semibold">
                    {u.is_active ? 'Active' : 'Inactive'}
                  </td>
                  <td className="p-2.5 text-right">
                    <button
                      onClick={() => handleDeleteUser(u.id, u.email)}
                      className="px-2 py-1 bg-red-50 hover:bg-red-100 text-red-700 rounded font-semibold text-[11px] inline-flex items-center gap-1 transition-colors"
                      title="Delete User Account"
                    >
                      <Trash2 className="w-3 h-3" /> Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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

      {/* Add User Modal */}
      {showAddUserModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white max-w-md w-full rounded-2xl border border-slate-200 shadow-xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-[#12213A]" />
                <h3 className="text-base font-bold font-display text-[#12213A]">Provision User Account</h3>
              </div>
              <button
                onClick={() => setShowAddUserModal(false)}
                className="text-slate-400 hover:text-slate-700 font-bold"
              >
                ×
              </button>
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleCreateUser} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  placeholder="Dr. Arun Kumar"
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-[#12213A]"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Work Email Address</label>
                <input
                  type="email"
                  required
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="clinician@vitals.health"
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-[#12213A]"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Account Password</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-[#12213A]"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">System Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-[#12213A] font-semibold"
                >
                  <option value="CLINICIAN">Clinician (Ward Discharge Monitoring)</option>
                  <option value="ANALYST">Analyst (Data Analytics & Audit)</option>
                  <option value="ADMIN">Administrator (Full Admin System Access)</option>
                </select>
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddUserModal(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 bg-[#12213A] hover:bg-slate-800 text-white rounded-lg font-semibold"
                >
                  {loading ? 'Creating...' : 'Provision Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
