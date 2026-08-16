import React, { useState } from 'react';
import { PatientRecord, PredictionResult } from '../types';
import { predictPatient } from '../api/client';
import { ScoreGauge } from '../components/ScoreGauge';
import { RiskDriverBar } from '../components/RiskDriverBar';
import { UserPlus, Sparkles, Send, RefreshCw, AlertCircle, ShieldAlert, CheckCircle2, Info, User } from 'lucide-react';

const INITIAL_PATIENT: PatientRecord = {
  age: '[70-80)',
  time_in_hospital: 5,
  n_procedures: 2,
  n_lab_procedures: 45,
  n_medications: 18,
  n_outpatient: 1,
  n_inpatient: 2,
  n_emergency: 1,
  medical_specialty: 'InternalMedicine',
  diag_1: 'Circulatory',
  diag_2: 'Respiratory',
  diag_3: 'Diabetes',
  glucose_test: 'high',
  A1Ctest: 'high',
  change: 'yes',
  diabetes_med: 'yes'
};

const CLINICAL_PRESETS = [
  {
    name: 'High Risk Cardiac',
    data: {
      ...INITIAL_PATIENT,
      age: '[80-90)',
      time_in_hospital: 8,
      n_inpatient: 4,
      n_emergency: 3,
      n_medications: 26,
      medical_specialty: 'Cardiology',
      diag_1: 'Circulatory',
      diag_2: 'Respiratory',
      diag_3: 'Diabetes'
    }
  },
  {
    name: 'Moderate Risk Respiratory',
    data: {
      ...INITIAL_PATIENT,
      age: '[60-70)',
      time_in_hospital: 4,
      n_inpatient: 1,
      n_emergency: 1,
      n_medications: 12,
      medical_specialty: 'InternalMedicine',
      diag_1: 'Respiratory',
      diag_2: 'Diabetes',
      diag_3: 'Other'
    }
  },
  {
    name: 'Low Risk Post-Op',
    data: {
      ...INITIAL_PATIENT,
      age: '[40-50)',
      time_in_hospital: 2,
      n_inpatient: 0,
      n_emergency: 0,
      n_medications: 5,
      medical_specialty: 'Surgery',
      diag_1: 'Digestive',
      diag_2: 'Other',
      diag_3: 'Other',
      glucose_test: 'no',
      A1Ctest: 'no',
      change: 'no',
      diabetes_med: 'no'
    }
  }
];

export const NewAssessment: React.FC = () => {
  const [formData, setFormData] = useState<PatientRecord>(INITIAL_PATIENT);
  const [patientName, setPatientName] = useState<string>('Arun Kumar');
  const [dateOfBirth, setDateOfBirth] = useState<string>('15/08/1954');
  const [customPatientId, setCustomPatientId] = useState<string>('');

  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (field: keyof PatientRecord, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value
    }));
  };

  const handleApplyPreset = (presetData: PatientRecord) => {
    setFormData(presetData);
    setPrediction(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = {
        ...formData,
        patient_name: patientName.trim() || 'Manual Patient Intake',
        date_of_birth: dateOfBirth.trim() || 'N/A',
        patient_id: customPatientId.trim() || undefined
      };
      const res = await predictPatient(payload);
      setPrediction(res);
    } catch (err: any) {
      setError(err.message || 'Failed to generate readmission risk prediction.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <UserPlus className="w-5 h-5 text-[#12213A]" />
            <h1 className="text-xl font-bold font-display text-[#12213A]">New Patient Assessment</h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Input patient identity & clinical parameters to compute real-time readmission risk probability, SHAP drivers, and personalized preventive recommendations.
          </p>
        </div>

        {/* Clinical Presets Bar */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-amber-600" /> Presets:
          </span>
          {CLINICAL_PRESETS.map((preset) => (
            <button
              key={preset.name}
              type="button"
              onClick={() => handleApplyPreset(preset.data)}
              className="px-2.5 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-[#12213A] font-medium rounded border border-slate-200 transition-colors"
            >
              {preset.name}
            </button>
          ))}
        </div>
      </div>

      {/* Grid Layout: Form vs Results Card */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Form Column */}
        <form onSubmit={handleSubmit} className="lg:col-span-7 bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-sm font-bold font-display text-[#12213A] border-b border-slate-100 pb-2 flex items-center gap-1.5">
            <User className="w-4 h-4 text-purple-700" /> Patient Identity & Demographics
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div>
              <label className="block font-medium text-slate-700 mb-1">Patient Full Name</label>
              <input
                type="text"
                placeholder="e.g. Arun Kumar"
                value={patientName}
                onChange={(e) => setPatientName(e.target.value)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md text-xs"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Date of Birth (DD/MM/YYYY)</label>
              <input
                type="text"
                placeholder="DD/MM/YYYY"
                value={dateOfBirth}
                onChange={(e) => setDateOfBirth(e.target.value)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md text-xs font-mono"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Hospital Patient ID (Optional)</label>
              <input
                type="text"
                placeholder="Auto-generated if empty"
                value={customPatientId}
                onChange={(e) => setCustomPatientId(e.target.value)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md text-xs font-mono"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs pt-1">
            <div>
              <label className="block font-medium text-slate-700 mb-1">Age Bracket</label>
              <select
                value={formData.age}
                onChange={(e) => handleChange('age', e.target.value)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md font-mono"
              >
                {['[40-50)', '[50-60)', '[60-70)', '[70-80)', '[80-90)', '[90-100)'].map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Stay Duration (days)</label>
              <input
                type="number"
                min="1"
                max="30"
                value={formData.time_in_hospital}
                onChange={(e) => handleChange('time_in_hospital', parseInt(e.target.value) || 1)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md font-mono"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Medical Specialty</label>
              <select
                value={formData.medical_specialty}
                onChange={(e) => handleChange('medical_specialty', e.target.value)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md"
              >
                {['InternalMedicine', 'Cardiology', 'Family/GeneralPractice', 'Emergency/Trauma', 'Surgery', 'Other', 'Missing'].map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>

          <h2 className="text-sm font-bold font-display text-[#12213A] border-b border-slate-100 pb-2 pt-2">
            Prior Health System Utilization
          </h2>

          <div className="grid grid-cols-3 gap-3 text-xs">
            <div>
              <label className="block font-medium text-slate-700 mb-1">Prior Inpatient</label>
              <input
                type="number"
                min="0"
                max="30"
                value={formData.n_inpatient}
                onChange={(e) => handleChange('n_inpatient', parseInt(e.target.value) || 0)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md font-mono"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Prior Emergency</label>
              <input
                type="number"
                min="0"
                max="64"
                value={formData.n_emergency}
                onChange={(e) => handleChange('n_emergency', parseInt(e.target.value) || 0)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md font-mono"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Prior Outpatient</label>
              <input
                type="number"
                min="0"
                max="33"
                value={formData.n_outpatient}
                onChange={(e) => handleChange('n_outpatient', parseInt(e.target.value) || 0)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md font-mono"
              />
            </div>
          </div>

          <h2 className="text-sm font-bold font-display text-[#12213A] border-b border-slate-100 pb-2 pt-2">
            Diagnoses & Inpatient Care
          </h2>

          <div className="grid grid-cols-3 gap-3 text-xs">
            <div>
              <label className="block font-medium text-slate-700 mb-1">Primary Diagnosis</label>
              <select
                value={formData.diag_1}
                onChange={(e) => handleChange('diag_1', e.target.value)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md"
              >
                {['Circulatory', 'Respiratory', 'Diabetes', 'Digestive', 'Injury', 'Musculoskeletal', 'Other', 'Missing'].map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Secondary Diagnosis</label>
              <select
                value={formData.diag_2}
                onChange={(e) => handleChange('diag_2', e.target.value)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md"
              >
                {['Circulatory', 'Respiratory', 'Diabetes', 'Digestive', 'Injury', 'Musculoskeletal', 'Other', 'Missing'].map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Comorbid Diagnosis</label>
              <select
                value={formData.diag_3}
                onChange={(e) => handleChange('diag_3', e.target.value)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md"
              >
                {['Circulatory', 'Respiratory', 'Diabetes', 'Digestive', 'Injury', 'Musculoskeletal', 'Other', 'Missing'].map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-1">
            <div>
              <label className="block font-medium text-slate-700 mb-1">Medications</label>
              <input
                type="number"
                min="1"
                max="100"
                value={formData.n_medications}
                onChange={(e) => handleChange('n_medications', parseInt(e.target.value) || 1)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md font-mono"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Lab Tests</label>
              <input
                type="number"
                min="1"
                max="150"
                value={formData.n_lab_procedures}
                onChange={(e) => handleChange('n_lab_procedures', parseInt(e.target.value) || 1)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md font-mono"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Glucose Test</label>
              <select
                value={formData.glucose_test}
                onChange={(e) => handleChange('glucose_test', e.target.value)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md"
              >
                <option value="no">no</option>
                <option value="normal">normal</option>
                <option value="high">high</option>
              </select>
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">A1C Test</label>
              <select
                value={formData.A1Ctest}
                onChange={(e) => handleChange('A1Ctest', e.target.value)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md"
              >
                <option value="no">no</option>
                <option value="normal">normal</option>
                <option value="high">high</option>
              </select>
            </div>
          </div>

          <div className="pt-3">
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-[#12213A] hover:bg-slate-800 text-white font-semibold text-xs rounded-lg flex items-center justify-center gap-2 transition-colors shadow-2xs"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Evaluating Live Prediction...</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>Run Readmission Risk Assessment</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Prediction Results Card Column */}
        <div className="lg:col-span-5 space-y-4">
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 text-red-800 rounded-xl text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {prediction ? (
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-5">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div>
                  <h2 className="text-sm font-bold font-display text-[#12213A]">Assessment Result</h2>
                  <p className="text-[11px] text-slate-500">
                    Patient ID: <span className="font-mono font-bold text-[#12213A]">{prediction.patient_id}</span>
                  </p>
                </div>
                <span className="text-xs font-mono text-emerald-700 bg-emerald-50 px-2 py-1 rounded border border-emerald-200 font-bold">
                  PERSISTED TO DB
                </span>
              </div>

              {/* Full SVG Score Gauge */}
              <ScoreGauge
                probability={prediction.readmission_probability}
                tier={prediction.clinical_risk_tier}
                threshold={prediction.operating_threshold}
                variant="full"
              />

              {/* SHAP Drivers */}
              <div className="space-y-2 pt-2 border-t border-slate-100">
                <span className="text-xs font-bold font-display text-[#12213A] block">
                  Top 3 SHAP Risk Drivers
                </span>
                <RiskDriverBar drivers={prediction.top_3_shap_drivers} />
              </div>

              {/* SUGGESTED PREVENTIVE ACTIONS SECTION */}
              <div className="space-y-3 pt-3 border-t border-slate-100">
                <div>
                  <div className="flex items-center gap-1.5">
                    <ShieldAlert className="w-4 h-4 text-[#12213A]" />
                    <h3 className="text-xs font-bold font-display text-[#12213A]">Suggested Preventive Actions</h3>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Actions for clinician consideration based on predicted risk and patient-specific factors.
                  </p>
                </div>

                <div className="space-y-2">
                  {prediction.preventive_actions && prediction.preventive_actions.length > 0 ? (
                    prediction.preventive_actions.map((act, i) => {
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
                  <span>Vitals is a clinical decision-support prototype using de-identified research data. Predictions and recommendations are decision-support suggestions for clinician consideration and are not medical diagnoses or treatment instructions.</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white p-12 rounded-xl border border-slate-200 text-center space-y-3">
              <Sparkles className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-sm font-semibold text-slate-700">Ready for Patient Assessment</p>
              <p className="text-xs text-slate-500 max-w-xs mx-auto">
                Fill in patient clinical parameters on the left or select a preset, then click 'Run Readmission Risk Assessment'.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
