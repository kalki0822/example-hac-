import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Activity, AlertCircle, ArrowRight, UserCheck } from 'lucide-react';

export const Login: React.FC = () => {
  const { login } = useAuth();
  const [email, setEmail] = useState<string>('clinician@vitals.health');
  const [password, setPassword] = useState<string>('Clinician123!');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handlePreset = (presetEmail: string, presetPass: string) => {
    setEmail(presetEmail);
    setPassword(presetPass);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl border border-slate-200 shadow-sm p-8 space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 bg-[#12213A] rounded-xl flex items-center justify-center mx-auto shadow-sm">
            <Activity className="w-6 h-6 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold font-display text-[#12213A] tracking-tight">VITALS</h1>
          <p className="text-xs text-slate-500 max-w-xs mx-auto">
            Hospital Readmission Risk Decision Support Platform — Enterprise Portal
          </p>
        </div>

        {/* Demo Account Quick-Login Buttons */}
        <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 space-y-2">
          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block flex items-center gap-1">
            <UserCheck className="w-3.5 h-3.5 text-slate-400" /> Hackathon Quick Demo Accounts:
          </span>
          <div className="grid grid-cols-3 gap-1.5 text-[11px]">
            <button
              type="button"
              onClick={() => handlePreset('clinician@vitals.health', 'Clinician123!')}
              className="py-1.5 px-2 bg-white border border-slate-200 hover:border-slate-300 rounded font-medium text-slate-700 hover:bg-slate-100 transition-colors truncate"
            >
              Clinician
            </button>
            <button
              type="button"
              onClick={() => handlePreset('analyst@vitals.health', 'Analyst123!')}
              className="py-1.5 px-2 bg-white border border-slate-200 hover:border-slate-300 rounded font-medium text-slate-700 hover:bg-slate-100 transition-colors truncate"
            >
              Analyst
            </button>
            <button
              type="button"
              onClick={() => handlePreset('admin@vitals.health', 'Admin123!')}
              className="py-1.5 px-2 bg-white border border-slate-200 hover:border-slate-300 rounded font-medium text-slate-700 hover:bg-slate-100 transition-colors truncate"
            >
              Admin
            </button>
          </div>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Work Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@hospital.health"
              className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-[#12213A]"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-[#12213A]"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-[#12213A] hover:bg-slate-800 text-white font-semibold rounded-lg flex items-center justify-center gap-2 transition-colors shadow-xs"
          >
            {loading ? (
              <span>Authenticating...</span>
            ) : (
              <>
                <span>Log In to Enterprise Portal</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Clinical Disclaimer Footer */}
        <div className="pt-2 border-t border-slate-100 text-center">
          <p className="text-[11px] text-slate-400 leading-tight">
            Protected clinical decision-support system. Unauthorized access prohibited.
          </p>
        </div>
      </div>
    </div>
  );
};
