import React from 'react';
import { BatchPatientResult } from '../types';
import { ScoreGauge } from './ScoreGauge';
import { ChevronRight, Clock, ShieldAlert } from 'lucide-react';

interface PatientRowProps {
  patient: BatchPatientResult;
  threshold?: number;
  onSelect: (patient: BatchPatientResult) => void;
}

export const PatientRow: React.FC<PatientRowProps> = ({ patient, threshold = 0.2021, onSelect }) => {
  const patientData: Record<string, any> = patient.patient_data || {};
  const patientId = `PT-${1000 + patient.patient_index}`;
  const age = patientData.age || '[70-80)';
  const stayDays = patientData.time_in_hospital || 4;
  const specialty = patientData.medical_specialty || 'General';

  return (
    <div
      onClick={() => onSelect(patient)}
      className="group bg-white hover:bg-slate-50 border border-slate-200 hover:border-slate-300 rounded-lg p-3.5 sm:p-4 transition-all duration-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer shadow-2xs"
    >
      {/* Patient Identifier & Compact Gauge */}
      <div className="flex items-center gap-4">
        <ScoreGauge
          probability={patient.readmission_probability}
          tier={patient.clinical_risk_tier}
          threshold={threshold}
          variant="compact"
          showLabel={false}
        />

        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-sm text-[#12213A] tracking-tight">{patientId}</span>
            <span className="text-xs text-slate-500">•</span>
            <span className="text-xs font-medium text-slate-600">{specialty}</span>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-500 mt-0.5">
            <span className="font-mono">{age}</span>
            <span className="flex items-center gap-1 font-mono">
              <Clock className="w-3 h-3 text-slate-400" />
              {stayDays}d stay
            </span>
          </div>
        </div>
      </div>

      {/* Primary Driver & Risk Tier Badge */}
      <div className="flex-1 sm:px-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-t sm:border-t-0 pt-2 sm:pt-0 border-slate-100">
        <div className="flex items-center gap-2 text-xs text-slate-700 max-w-md">
          <ShieldAlert className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span className="truncate font-medium">
            {patient.primary_driver || 'High health system utilization score'}
          </span>
        </div>

        <ScoreGauge
          probability={patient.readmission_probability}
          tier={patient.clinical_risk_tier}
          threshold={threshold}
          variant="compact"
          showLabel={true}
        />
      </div>

      {/* Trigger CTA */}
      <div className="hidden sm:flex items-center justify-end text-slate-400 group-hover:text-[#12213A] transition-colors">
        <ChevronRight className="w-5 h-5 group-hover:translate-x-0.5 transition-transform" />
      </div>
    </div>
  );
};
