import React, { useEffect, useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Nav } from './components/Nav';
import { Login } from './pages/Login';
import { WardOverview } from './pages/WardOverview';
import { NewAssessment } from './pages/NewAssessment';
import { ModelPerformance } from './pages/ModelPerformance';
import { AuditView } from './pages/AuditView';
import { AdminDashboard } from './pages/AdminDashboard';
import { RoleGuard } from './components/RoleGuard';
import { fetchHealth } from './api/client';
import { HealthResponse } from './types';
import { Info } from 'lucide-react';

const MainAppContent: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<'ward' | 'assessment' | 'performance' | 'audit' | 'admin'>('ward');
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      fetchHealth()
        .then(setHealth)
        .catch((err) => console.warn('Backend connection warning:', err));
    }
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return <Login />;
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900 antialiased">
      {/* Top Header Navigation */}
      <Nav activeTab={activeTab} setActiveTab={setActiveTab} health={health} />

      {/* Main Clinical Content Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
        {activeTab === 'ward' && <WardOverview />}
        {activeTab === 'assessment' && <NewAssessment />}
        {activeTab === 'performance' && <ModelPerformance />}
        {activeTab === 'audit' && (
          <RoleGuard allowedRoles={['ADMIN', 'ANALYST']}>
            <AuditView />
          </RoleGuard>
        )}
        {activeTab === 'admin' && (
          <RoleGuard allowedRoles={['ADMIN']}>
            <AdminDashboard />
          </RoleGuard>
        )}
      </main>

      {/* Global Clinical Decision-Support Disclaimer Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 px-4 sm:px-6 text-center text-xs text-slate-500 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-left">
            <Info className="w-4 h-4 text-slate-400 shrink-0" />
            <span>
              <strong>Clinical Decision-Support Disclaimer:</strong> Vitals is a clinical decision-support prototype using de-identified research data. Predictions and recommendations are decision-support suggestions for clinician consideration and are not medical diagnoses or treatment instructions.
            </span>
          </div>
          <span className="font-mono text-[11px] text-slate-400 shrink-0">
            Cognizant Hackathon • Use Case 2
          </span>
        </div>
      </footer>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MainAppContent />
    </AuthProvider>
  );
};

export default App;
