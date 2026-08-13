import React, { useEffect, useState } from 'react';
import { BatchPatientResult, PredictionResult, PatientRecord } from '../types';
import { predictPatient } from '../api/client';
import { ScoreGauge } from '../components/ScoreGauge';
import { RiskDriverBar } from '../components/RiskDriverBar';
import { ArrowLeft, Activity, ShieldAlert, FileText, RefreshCw } from 'lucide-react';

interface PatientDetailProps {
  patient: BatchPatientResult;
  onBack: () => void;
}

export const PatientDetail: React.FC<PatientDetailProps> = ({ patient, onBack }) => {
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const rawData: PatientRecord = patient.patient_data || {
    age: '[70-80)',
    time_in_hospital: 6,
    n_procedures: 2,
    n_lab_procedures: 55,
    n_medications: 22,
    n_outpatient: 1,
    n_inpatient: 3,
    n_emergency: 2,
    medical_specialty: 'InternalMedicine',
    diag_1: 'Circulatory',
    diag_2: 'Respiratory',
    diag_3: 'Diabetes',
    glucose_test: 'high',
    A1Ctest: 'high',
    change: 'yes',
    diabetes_med: 'yes'
  };

  useEffect(() => {
    fetchSinglePrediction();
  }, [patient]);

  const fetchSinglePrediction = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await predictPatient(rawData);
      setPrediction(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch detailed SHAP driver analysis.');
    } finally {
      setLoading(false);
    }
  };

  const patientId = `PT-${1000 + patient.patient_index}`;
  const probability = prediction ? prediction.readmission_probability : patient.readmission_probability;
  const tier = prediction ? prediction.clinical_risk_tier : patient.clinical_risk_tier;
  const threshold = prediction ? prediction.operating_threshold : 0.2021;

  return (
    <div className="space-y-6">
      {/* Top Header Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-3 py-1.5 bg-white text-[#12213A] text-xs font-semibold rounded-md border border-slate-200 hover:bg-slate-50 transition-colors shadow-2xs"
        >
          <ArrowLeft className="w-4 h-4 text-slate-500" />
          <span>Back to Ward Overview</span>
        </button>

        <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
          <span>Patient Reference:</span>
          <span className="font-bold text-[#12213A]">{patientId}</span>
        </div>
      </div>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Full Score Gauge & Summary Card */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="text-sm font-bold font-display text-[#12213A]">Risk Profile Score</h2>
              <span className="text-[10px] uppercase font-mono tracking-wider text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                Model v1.0
              </span>
            </div>

            {/* Signature Full SVG Score Gauge */}
            <ScoreGauge
              probability={probability}
              tier={tier}
              threshold={threshold}
              variant="full"
            />

            {/* Patient Header Stats */}
            <div className="pt-2 border-t border-slate-100 space-y-2 text-xs text-slate-600">
              <div className="flex justify-between py-1 border-b border-slate-50">
                <span className="text-slate-500">Age Bracket:</span>
                <span className="font-mono font-bold text-[#12213A]">{rawData.age}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-50">
                <span className="text-slate-500">Admitting Specialty:</span>
                <span className="font-medium text-[#12213A]">{rawData.medical_specialty}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-50">
                <span className="text-slate-500">Hospital Stay Duration:</span>
                <span className="font-mono font-bold text-[#12213A]">{rawData.time_in_hospital} days</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Operating Cutoff:</span>
                <span className="font-mono text-slate-700">{(threshold * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>

          {/* Cohort Comparison Card */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between text-xs mb-2">
              <span className="font-semibold text-[#12213A]">Cohort Risk Context</span>
              <Activity className="w-3.5 h-3.5 text-slate-400" />
            </div>
            <p className="text-xs text-slate-600 leading-normal">
              This patient's predicted readmission score ({Math.round(probability * 100)}%) is{' '}
              <span className="font-bold text-red-800">
                {probability >= threshold ? 'ABOVE' : 'BELOW'}
              </span>{' '}
              the optimal clinical decision cutoff ({(threshold * 100).toFixed(1)}%).
            </p>
          </div>
        </div>

        {/* Right Column: SHAP Drivers & Clinical Raw Data Table */}
        <div className="lg:col-span-2 space-y-6">
          {/* Plain-Language SHAP Risk Drivers */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-red-700" />
                <h2 className="text-sm font-bold font-display text-[#12213A]">
                  Top 3 Plain-Language SHAP Drivers
                </h2>
              </div>
              <span className="text-xs text-slate-500">Feature impact breakdown</span>
            </div>

            {loading ? (
              <div className="p-8 text-center">
                <RefreshCw className="w-5 h-5 text-slate-400 animate-spin mx-auto mb-2" />
                <p className="text-xs text-slate-500">Calculating SHAP driver impact values...</p>
              </div>
            ) : error ? (
              <p className="text-xs text-red-600">{error}</p>
            ) : prediction ? (
              <RiskDriverBar drivers={prediction.top_3_shap_drivers} />
            ) : null}
          </div>

          {/* Raw Feature Parameters Table */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-slate-600" />
                <h2 className="text-sm font-bold font-display text-[#12213A]">
                  Raw Clinical Parameters
                </h2>
              </div>
              <span className="text-xs text-slate-500">Input features list</span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Primary Diagnosis (diag_1)</span>
                <span className="font-semibold text-[#12213A]">{rawData.diag_1}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Secondary Diagnosis (diag_2)</span>
                <span className="font-semibold text-[#12213A]">{rawData.diag_2}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Comorbid Diagnosis (diag_3)</span>
                <span className="font-semibold text-[#12213A]">{rawData.diag_3}</span>
              </div>

              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Prior Inpatient Visits</span>
                <span className="font-mono font-bold text-[#12213A]">{rawData.n_inpatient}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Prior ER Visits</span>
                <span className="font-mono font-bold text-[#12213A]">{rawData.n_emergency}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Prior Outpatient Visits</span>
                <span className="font-mono font-bold text-[#12213A]">{rawData.n_outpatient}</span>
              </div>

              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Prescribed Medications</span>
                <span className="font-mono font-bold text-[#12213A]">{rawData.n_medications}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Lab Tests Count</span>
                <span className="font-mono font-bold text-[#12213A]">{rawData.n_lab_procedures}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Diabetes Med / Change</span>
                <span className="font-semibold text-[#12213A]">
                  {rawData.diabetes_med} / {rawData.change}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
