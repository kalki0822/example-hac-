import React from 'react';
import { Activity, Users, BarChart3, UserPlus, LogOut, Shield, FileText } from 'lucide-react';
import { HealthResponse } from '../types';
import { useAuth } from '../context/AuthContext';

interface NavProps {
  activeTab: 'ward' | 'assessment' | 'performance' | 'audit' | 'admin';
  setActiveTab: (tab: 'ward' | 'assessment' | 'performance' | 'audit' | 'admin') => void;
  health: HealthResponse | null;
}

export const Nav: React.FC<NavProps> = ({ activeTab, setActiveTab, health }) => {
  const { user, logout } = useAuth();
  const role = user?.role || 'CLINICIAN';

  const roleColors: Record<string, string> = {
    ADMIN: 'bg-red-100 text-red-800 border-red-200',
    ANALYST: 'bg-purple-100 text-purple-800 border-purple-200',
    CLINICIAN: 'bg-emerald-100 text-emerald-800 border-emerald-200'
  };

  return (
    <header className="bg-[#12213A] text-white border-b border-slate-800 sticky top-0 z-50 shadow-md">
      {/* Upper Bar: Title & User Info */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-emerald-500/20 border border-emerald-500/30 rounded-lg flex items-center justify-center">
            <Activity className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold font-display text-base tracking-tight text-white">VITALS</span>
              <span className="text-[10px] font-mono uppercase bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded border border-slate-700">
                Enterprise v1.0
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-mono hidden sm:block">
              Hospital Readmission Risk Platform
            </p>
          </div>
        </div>

        {/* User Identity & Logout */}
        <div className="flex items-center gap-3">
          {health && (
            <div className="hidden lg:flex items-center gap-1.5 text-[11px] font-mono text-slate-300 bg-slate-800/60 px-2.5 py-1 rounded-md border border-slate-700">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>{health.model_name || 'Logistic Regression'} v{health.version || '1.0.0'}</span>
            </div>
          )}

          {user && (
            <div className="flex items-center gap-2 bg-slate-800/80 px-2.5 py-1 rounded-lg border border-slate-700 text-xs">
              <span className="font-semibold text-slate-200">{user.full_name || user.email}</span>
              <span className={`text-[10px] font-mono font-bold uppercase px-1.5 py-0.5 rounded border ${roleColors[role] || 'bg-slate-700 text-slate-300'}`}>
                {role}
              </span>
              <button
                onClick={logout}
                title="Log out"
                className="p-1 hover:bg-slate-700 rounded text-slate-400 hover:text-white transition-colors ml-1"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Lower Bar: Role-Aware Tab Navigation */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center gap-1 overflow-x-auto py-1">
        <button
          onClick={() => setActiveTab('ward')}
          className={`px-3 py-2 text-xs font-semibold rounded-md flex items-center gap-1.5 transition-colors whitespace-nowrap ${
            activeTab === 'ward'
              ? 'bg-slate-800 text-white border border-slate-700 shadow-xs'
              : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
          }`}
        >
          <Users className="w-3.5 h-3.5 text-emerald-400" />
          <span>Ward Discharge Overview</span>
        </button>

        <button
          onClick={() => setActiveTab('assessment')}
          className={`px-3 py-2 text-xs font-semibold rounded-md flex items-center gap-1.5 transition-colors whitespace-nowrap ${
            activeTab === 'assessment'
              ? 'bg-slate-800 text-white border border-slate-700 shadow-xs'
              : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
          }`}
        >
          <UserPlus className="w-3.5 h-3.5 text-amber-400" />
          <span>New Patient Intake</span>
        </button>

        <button
          onClick={() => setActiveTab('performance')}
          className={`px-3 py-2 text-xs font-semibold rounded-md flex items-center gap-1.5 transition-colors whitespace-nowrap ${
            activeTab === 'performance'
              ? 'bg-slate-800 text-white border border-slate-700 shadow-xs'
              : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
          }`}
        >
          <BarChart3 className="w-3.5 h-3.5 text-blue-400" />
          <span>Model Analytics & Performance</span>
        </button>

        {(role === 'ADMIN' || role === 'ANALYST') && (
          <button
            onClick={() => setActiveTab('audit')}
            className={`px-3 py-2 text-xs font-semibold rounded-md flex items-center gap-1.5 transition-colors whitespace-nowrap ${
              activeTab === 'audit'
                ? 'bg-slate-800 text-white border border-slate-700 shadow-xs'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
            }`}
          >
            <FileText className="w-3.5 h-3.5 text-purple-400" />
            <span>Prediction Audit Log</span>
          </button>
        )}

        {role === 'ADMIN' && (
          <button
            onClick={() => setActiveTab('admin')}
            className={`px-3 py-2 text-xs font-semibold rounded-md flex items-center gap-1.5 transition-colors whitespace-nowrap ${
              activeTab === 'admin'
                ? 'bg-slate-800 text-white border border-slate-700 shadow-xs'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
            }`}
          >
            <Shield className="w-3.5 h-3.5 text-red-400" />
            <span>Admin Portal</span>
          </button>
        )}
      </div>
    </header>
  );
};
