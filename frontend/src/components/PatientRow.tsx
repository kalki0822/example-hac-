import React from 'react';
import { BatchPatientResult } from '../types';
import { ScoreGauge } from './ScoreGauge';
import { ChevronRight, Clock, ShieldAlert, User, Calendar, Trash2 } from 'lucide-react';

interface PatientRowProps {
  patient: BatchPatientResult & Record<string, any>;
  threshold?: number;
  onSelect: (patient: BatchPatientResult) => void;
  onDelete?: (patientId: string, e: React.MouseEvent) => void;
  canDelete?: boolean;
}

export const PatientRow: React.FC<PatientRowProps> = ({
  patient,
  threshold = 0.2562,
  onSelect,
  onDelete,
  canDelete = false
}) => {
  const patientData: Record<string, any> = patient.patient_data || patient;
  const patientId = patient.patient_id || patientData.patient_id || `PT-100${patient.patient_index || 1}`;
  const patientName = patient.patient_name || patientData.patient_name || 'N/A';
  const dob = patient.date_of_birth || patientData.date_of_birth || 'N/A';
  const source = (patient.source || patientData.source || 'KAGGLE').toUpperCase();
  const age = patientData.age || '[70-80)';
  const stayDays = patientData.time_in_hospital || 4;
  const specialty = patientData.medical_specialty || 'General';

  const sourceBadges: Record<string, { label: string; style: string }> = {
    UPLOADED_CSV: { label: 'UPLOADED CSV', style: 'bg-purple-100 text-purple-900 border-purple-200' },
    MANUAL: { label: 'MANUAL INTAKE', style: 'bg-emerald-100 text-emerald-900 border-emerald-200' },
    KAGGLE: { label: 'KAGGLE SEEDED', style: 'bg-slate-100 text-slate-700 border-slate-200' }
  };

  const badge = sourceBadges[source] || sourceBadges.KAGGLE;

  return (
    <div
      onClick={() => onSelect(patient)}
      className="group bg-white hover:bg-slate-50 border border-slate-200 hover:border-slate-300 rounded-lg p-3.5 sm:p-4 transition-all duration-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer shadow-2xs"
    >
      {/* Patient Identifier & Compact Gauge */}
      <div className="flex items-center gap-4">
        <ScoreGauge
          probability={patient.readmission_probability || 0.3}
          tier={patient.clinical_risk_tier || 'Moderate Risk'}
          threshold={threshold}
          variant="compact"
          showLabel={false}
        />

        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-sm text-[#12213A] tracking-tight">{patientId}</span>
            {patientName !== 'N/A' && (
              <span className="text-xs font-semibold text-slate-800 flex items-center gap-1">
                <User className="w-3 h-3 text-slate-400" /> {patientName}
              </span>
            )}
            <span className={`text-[10px] font-mono uppercase px-1.5 py-0.2 rounded border ${badge.style}`}>
              {badge.label}
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-500 mt-0.5">
            <span className="font-semibold text-slate-600">{specialty}</span>
            <span className="text-slate-300">•</span>
            <span className="font-mono">{age}</span>
            {dob !== 'N/A' && (
              <span className="flex items-center gap-1 font-mono text-slate-400">
                <Calendar className="w-3 h-3" /> DOB: {dob}
              </span>
            )}
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
          probability={patient.readmission_probability || 0.3}
          tier={patient.clinical_risk_tier || 'Moderate Risk'}
          threshold={threshold}
          variant="compact"
          showLabel={true}
        />
      </div>

      {/* Actions: Delete (Admin/Analyst) & Trigger Chevron CTA */}
      <div className="flex items-center justify-end gap-2">
        {canDelete && onDelete && (
          <button
            type="button"
            onClick={(e) => onDelete(patientId, e)}
            className="p-1.5 text-slate-400 hover:text-red-700 hover:bg-red-50 border border-transparent hover:border-red-200 rounded transition-colors"
            title={`Delete patient record ${patientId}`}
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
        <div className="hidden sm:flex items-center text-slate-400 group-hover:text-[#12213A] transition-colors">
          <ChevronRight className="w-5 h-5 group-hover:translate-x-0.5 transition-transform" />
        </div>
      </div>
    </div>
  );
};
