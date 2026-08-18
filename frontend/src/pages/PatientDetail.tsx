import React, { useEffect, useState } from 'react';
import { BatchPatientResult, PredictionResult } from '../types';
import { predictPatient, fetchPatientShap } from '../api/client';
import { ScoreGauge } from '../components/ScoreGauge';
import { RiskDriverBar } from '../components/RiskDriverBar';
import { ArrowLeft, Activity, ShieldAlert, FileText, RefreshCw, CheckCircle2, Info, User, Calendar, Database, FileSpreadsheet } from 'lucide-react';

interface PatientDetailProps {
  patient: BatchPatientResult & Record<string, any>;
  onBack: () => void;
}

export const PatientDetail: React.FC<PatientDetailProps> = ({ patient, onBack }) => {
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [shapDrivers, setShapDrivers] = useState<any[]>([]);
  const [fetchedActions, setFetchedActions] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const rawData: any = patient.patient_data || patient;
  const patientId = patient.patient_id || rawData.patient_id || `PT-${1000 + (patient.patient_index || 1)}`;
  const patientName = patient.patient_name || rawData.patient_name || 'N/A';
  const dob = patient.date_of_birth || rawData.date_of_birth || 'N/A';
  const source = (patient.source || rawData.source || 'KAGGLE').toUpperCase();
  const sourceFilename = patient.source_filename || rawData.source_filename;

  useEffect(() => {
    fetchSinglePrediction();
  }, [patient]);

  const fetchSinglePrediction = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch dedicated SHAP driver analysis & preventive actions from PostgreSQL DB
      try {
        const shapData = await fetchPatientShap(patientId);
        if (shapData) {
          if (shapData.drivers && shapData.drivers.length > 0) {
            const formatted = shapData.drivers.map((d: any) => ({
              feature: d.feature,
              shap_value: d.shap_value,
              direction: d.shap_value > 0 ? 'Increases Readmission Risk' : 'Decreases Readmission Risk',
              plain_language_driver: d.label || d.feature
            }));
            setShapDrivers(formatted);
          }
          if (shapData.preventive_actions && shapData.preventive_actions.length > 0) {
            setFetchedActions(shapData.preventive_actions);
          }
        }
      } catch (shapErr) {
        console.warn('Dedicated SHAP query failed:', shapErr);
      }

      // 2. If probability is missing, trigger inference prediction
      if (!patient.readmission_probability && !prediction) {
        const payload = {
          ...rawData,
          patient_name: patientName !== 'N/A' ? patientName : undefined,
          date_of_birth: dob !== 'N/A' ? dob : undefined,
          patient_id: patientId
        };
        const predRes = await predictPatient(payload);
        setPrediction(predRes);
        if (shapDrivers.length === 0 && predRes.top_3_shap_drivers) {
          setShapDrivers(predRes.top_3_shap_drivers);
        }
        if (fetchedActions.length === 0 && predRes.preventive_actions) {
          setFetchedActions(predRes.preventive_actions);
        }
      }
    } catch (err: any) {
      if (shapDrivers.length === 0) {
        setError('SHAP driver analysis unavailable for this patient record.');
      }
    } finally {
      setLoading(false);
    }
  };

  const probability = prediction ? prediction.readmission_probability : (patient.readmission_probability || 0.25);
  const tier = prediction ? prediction.clinical_risk_tier : (patient.clinical_risk_tier || 'Low Risk');
  const threshold = prediction ? prediction.operating_threshold : 0.2562;
  const preventiveActions = prediction?.preventive_actions || (fetchedActions.length > 0 ? fetchedActions : (patient.preventive_actions || []));


  return (
    <div className="space-y-6">
      {/* Top Header Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-[#12213A] text-xs font-semibold rounded-md border border-slate-200 transition-colors shadow-2xs w-fit"
        >
          <ArrowLeft className="w-4 h-4 text-slate-500" />
          <span>Back to Ward Overview</span>
        </button>

        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 font-mono">
            <span className="text-slate-500">Patient ID:</span>
            <span className="font-bold text-[#12213A] text-sm">{patientId}</span>
          </div>

          {patientName !== 'N/A' && (
            <div className="flex items-center gap-1 font-semibold text-slate-800 bg-slate-100 px-2 py-0.5 rounded">
              <User className="w-3.5 h-3.5 text-purple-700" /> {patientName}
            </div>
          )}

          {dob !== 'N/A' && (
            <div className="flex items-center gap-1 text-slate-600 bg-slate-100 px-2 py-0.5 rounded font-mono">
              <Calendar className="w-3.5 h-3.5 text-slate-400" /> DOB: {dob}
            </div>
          )}

          <div className="flex items-center gap-1 bg-purple-50 text-purple-900 border border-purple-200 px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold">
            <Database className="w-3 h-3 text-purple-700" /> {source}
          </div>

          {sourceFilename && (
            <div className="flex items-center gap-1 bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-[11px] font-mono">
              <FileSpreadsheet className="w-3.5 h-3.5 text-slate-500" /> {sourceFilename}
            </div>
          )}
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
                <span className="font-mono font-bold text-[#12213A]">{rawData.age || '[50-60)'}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-50">
                <span className="text-slate-500">Admitting Specialty:</span>
                <span className="font-medium text-[#12213A]">{rawData.medical_specialty || 'General'}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-50">
                <span className="text-slate-500">Hospital Stay Duration:</span>
                <span className="font-mono font-bold text-[#12213A]">{rawData.time_in_hospital || 1} days</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-50">
                <span className="text-slate-500">Estimated Prob (Platt):</span>
                <span className="font-mono font-bold text-emerald-700">{(probability * 100).toFixed(1)}%</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Reference Cohort Rank:</span>
                <span className="font-mono font-bold text-slate-800">Q{tier === 'Minimal Risk' ? '1' : (tier === 'Moderate Risk' ? '2' : (tier === 'Elevated Risk' ? '3' : '4'))} · {tier}</span>
              </div>
            </div>
          </div>

          {/* Cohort Comparison & Methodology Card */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-[#12213A]">Cohort Risk Context & Ranking</span>
              <Activity className="w-3.5 h-3.5 text-slate-400" />
            </div>
            <p className="text-xs text-slate-600 leading-normal">
              This patient's calibrated probability of <strong className="text-emerald-700">{(probability * 100).toFixed(1)}%</strong> places them in <strong className="text-slate-900">Q{tier === 'Minimal Risk' ? '1' : (tier === 'Moderate Risk' ? '2' : (tier === 'Elevated Risk' ? '3' : '4'))} ({tier})</strong> relative to the 25,000-patient reference hospital population.
            </p>
            <div className="bg-slate-50 p-2.5 rounded border border-slate-200 text-[11px] text-slate-500 font-mono">
              Reference Q4 Cutoff: ≥ 52.01%
            </div>
          </div>
        </div>

        {/* Right Column: SHAP Drivers, Preventive Actions & Clinical Data Table */}
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
              <p className="text-xs text-red-600 font-medium">{error}</p>
            ) : shapDrivers.length > 0 ? (
              <RiskDriverBar drivers={shapDrivers} />
            ) : prediction ? (
              <RiskDriverBar drivers={prediction.top_3_shap_drivers} />
            ) : (
              <p className="text-xs text-slate-500 italic">SHAP explanation unavailable for this patient record.</p>
            )}
          </div>

          {/* SUGGESTED PREVENTIVE ACTIONS PANEL */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-sm font-bold font-display text-[#12213A]">
                  Suggested Preventive Actions
                </h2>
                <span className="text-xs text-slate-500 block mt-0.5">
                  Actions for clinician consideration based on predicted risk and patient-specific factors
                </span>
              </div>
              <span className="text-xs font-mono font-bold text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                {preventiveActions.length} Action(s)
              </span>
            </div>

            <div className="space-y-2.5">
              {preventiveActions.length > 0 ? (
                preventiveActions.map((act, i) => {
                  const isHigh = act.priority === 'High';
                  const isMed = act.priority === 'Medium';
                  return (
                    <div
                      key={i}
                      className={`p-3 rounded-lg border text-xs space-y-1 ${
                        isHigh
                          ? 'bg-red-50/50 border-red-200 text-red-900'
                          : isMed
                          ? 'bg-amber-50/50 border-amber-200 text-amber-900'
                          : 'bg-slate-50 border-slate-200 text-slate-800'
                      }`}
                    >
                      <div className="flex items-center justify-between font-semibold">
                        <span className="flex items-center gap-1.5">
                          <CheckCircle2 className={`w-3.5 h-3.5 ${isHigh ? 'text-red-600' : isMed ? 'text-amber-600' : 'text-slate-500'}`} />
                          {act.title}
                        </span>
                        <span
                          className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded font-bold ${
                            isHigh
                              ? 'bg-red-100 text-red-800'
                              : isMed
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-slate-200 text-slate-700'
                          }`}
                        >
                          {act.priority} Priority
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600 font-normal pl-5">
                        <span className="font-semibold text-slate-700">Reason: </span>
                        {act.reason}
                      </p>
                    </div>
                  );
                })
              ) : (
                <p className="text-xs text-slate-500 italic">No specific preventive actions generated.</p>
              )}
            </div>

            <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 flex items-start gap-1.5 text-[11px] text-slate-500">
              <Info className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
              <span>Vitals is a clinical decision-support platform. Predictions and recommendations are decision-support suggestions for clinician consideration and are not medical diagnoses or treatment instructions.</span>
            </div>
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
                <span className="font-semibold text-[#12213A]">{rawData.diag_1 || 'Other'}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Secondary Diagnosis (diag_2)</span>
                <span className="font-semibold text-[#12213A]">{rawData.diag_2 || 'Other'}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Comorbid Diagnosis (diag_3)</span>
                <span className="font-semibold text-[#12213A]">{rawData.diag_3 || 'Other'}</span>
              </div>

              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Prior Inpatient Visits</span>
                <span className="font-mono font-bold text-[#12213A]">{rawData.n_inpatient || 0}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Prior ER Visits</span>
                <span className="font-mono font-bold text-[#12213A]">{rawData.n_emergency || 0}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Prior Outpatient Visits</span>
                <span className="font-mono font-bold text-[#12213A]">{rawData.n_outpatient || 0}</span>
              </div>

              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Prescribed Medications</span>
                <span className="font-mono font-bold text-[#12213A]">{rawData.n_medications || 0}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Lab Tests Count</span>
                <span className="font-mono font-bold text-[#12213A]">{rawData.n_lab_procedures || 0}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[11px]">Diabetes Med / Change</span>
                <span className="font-semibold text-[#12213A]">
                  {rawData.diabetes_med || 'no'} / {rawData.change || 'no'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
