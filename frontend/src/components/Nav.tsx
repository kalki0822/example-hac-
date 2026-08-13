import React, { useEffect, useState } from 'react';
import { Activity, LayoutDashboard, UserPlus, BarChart3, CheckCircle2, AlertCircle } from 'lucide-react';
import { fetchHealth } from '../api/client';

interface NavProps {
  activeTab: 'ward' | 'assessment' | 'performance' | 'detail';
  setActiveTab: (tab: 'ward' | 'assessment' | 'performance') => void;
}

export const Nav: React.FC<NavProps> = ({ activeTab, setActiveTab }) => {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    fetchHealth()
      .then((data) => setIsHealthy(data.model_loaded))
      .catch(() => setIsHealthy(false));
  }, []);

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand logo & clinical title */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => setActiveTab('ward')}>
            <div className="w-9 h-9 rounded-lg bg-[#12213A] flex items-center justify-center text-white shadow-xs">
              <Activity className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-display font-bold text-lg text-[#12213A] tracking-tight">Vitals</span>
                <span className="text-[10px] uppercase tracking-widest font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded border border-slate-200">
                  Decision Support
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">Hospital Readmission Risk Platform</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center space-x-1 sm:space-x-2">
            <button
              onClick={() => setActiveTab('ward')}
              className={`flex items-center gap-2 px-3 py-2 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                activeTab === 'ward' || activeTab === 'detail'
                  ? 'bg-slate-100 text-[#12213A] font-semibold border border-slate-200'
                  : 'text-slate-600 hover:text-[#12213A] hover:bg-slate-50'
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Ward Overview</span>
            </button>

            <button
              onClick={() => setActiveTab('assessment')}
              className={`flex items-center gap-2 px-3 py-2 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                activeTab === 'assessment'
                  ? 'bg-slate-100 text-[#12213A] font-semibold border border-slate-200'
                  : 'text-slate-600 hover:text-[#12213A] hover:bg-slate-50'
              }`}
            >
              <UserPlus className="w-4 h-4" />
              <span>New Assessment</span>
            </button>

            <button
              onClick={() => setActiveTab('performance')}
              className={`flex items-center gap-2 px-3 py-2 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                activeTab === 'performance'
                  ? 'bg-slate-100 text-[#12213A] font-semibold border border-slate-200'
                  : 'text-slate-600 hover:text-[#12213A] hover:bg-slate-50'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              <span>Model Performance</span>
            </button>
          </nav>

          {/* System Backend Health Status Indicator */}
          <div className="hidden md:flex items-center gap-2 text-xs font-mono text-slate-600 bg-slate-50 px-2.5 py-1.5 rounded-md border border-slate-200">
            {isHealthy === true ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>API :8000 Ready</span>
              </>
            ) : isHealthy === false ? (
              <>
                <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                <span>API Disconnected</span>
              </>
            ) : (
              <span className="animate-pulse">Connecting...</span>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
