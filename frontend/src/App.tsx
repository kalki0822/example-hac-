import React, { useState } from 'react';
import { Nav } from './components/Nav';
import { WardOverview } from './pages/WardOverview';
import { PatientDetail } from './pages/PatientDetail';
import { NewAssessment } from './pages/NewAssessment';
import { ModelPerformance } from './pages/ModelPerformance';
import { BatchPatientResult } from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'ward' | 'assessment' | 'performance' | 'detail'>('ward');
  const [selectedPatient, setSelectedPatient] = useState<BatchPatientResult | null>(null);

  const handleSelectPatient = (patient: BatchPatientResult) => {
    setSelectedPatient(patient);
    setActiveTab('detail');
  };

  const handleBackToWard = () => {
    setSelectedPatient(null);
    setActiveTab('ward');
  };

  return (
    <div className="min-h-screen bg-[#F7F8FA] text-[#12213A] flex flex-col font-sans">
      <Nav activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'ward' && (
          <WardOverview onSelectPatient={handleSelectPatient} />
        )}

        {activeTab === 'detail' && selectedPatient && (
          <PatientDetail patient={selectedPatient} onBack={handleBackToWard} />
        )}

        {activeTab === 'assessment' && <NewAssessment />}

        {activeTab === 'performance' && <ModelPerformance />}
      </main>

      <footer className="bg-white border-t border-slate-200 py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
          <span>Vitals — Hospital Readmission Risk Decision Support System</span>
          <span className="font-mono text-[11px]">Backend API :8000 | Frontend :5173</span>
        </div>
      </footer>
    </div>
  );
};

export default App;
