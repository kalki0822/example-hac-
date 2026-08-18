import React, { useEffect, useState } from 'react';
import { BatchPatientResult } from '../types';
import { fetchPatients, fetchUploads, predictBatchCsv, deletePatient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { PatientRow } from '../components/PatientRow';
import { PatientDetail } from './PatientDetail';
import { Search, Upload, RefreshCw, AlertTriangle, Users, Filter, CheckCircle, Database, ChevronLeft, ChevronRight, FileSpreadsheet } from 'lucide-react';

interface WardOverviewProps {
  onSelectPatient?: (patient: BatchPatientResult) => void;
}

export const WardOverview: React.FC<WardOverviewProps> = ({ onSelectPatient }) => {
  const { user } = useAuth();
  const userRole = (user?.role || 'CLINICIAN').toUpperCase();
  const canDeletePatients = userRole === 'ADMIN' || userRole === 'ANALYST';

  const [patientsList, setPatientsList] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Active Query & Filter State
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [riskFilter, setRiskFilter] = useState<string>('ALL'); // ALL, High Risk, Moderate Risk, Low Risk
  const [sourceFilter, setSourceFilter] = useState<string>('ALL'); // ALL, KAGGLE, UPLOADED_CSV, MANUAL
  const [uploadIdFilter, setUploadIdFilter] = useState<string>(''); // Selected CSV upload_id
  const [sortBy, setSortBy] = useState<string>('RISK_DESC');

  // Database Pagination & Global Counts State
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageInput, setPageInput] = useState<string>('1');
  const [pageSize] = useState<number>(15);
  const [totalRecords, setTotalRecords] = useState<number>(25000);
  const [totalPages, setTotalPages] = useState<number>(1667);
  const [highCount, setHighCount] = useState<number>(0);
  const [elevatedCount, setElevatedCount] = useState<number>(0);
  const [modCount, setModCount] = useState<number>(0);
  const [minimalCount, setMinimalCount] = useState<number>(0);


  const [uploadedFilesList, setUploadedFilesList] = useState<any[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<any | null>(null);
  const [uploadedInfo, setUploadedInfo] = useState<string | null>(null);


  // Trigger server-side query on filter, page, or search change
  useEffect(() => {
    loadDatabasePatients();
  }, [currentPage, sourceFilter, uploadIdFilter, riskFilter, sortBy]);

  // Load uploaded CSV files list
  useEffect(() => {
    loadUploadedFiles();
  }, []);

  const loadUploadedFiles = async () => {
    try {
      const files = await fetchUploads();
      setUploadedFilesList(files);
    } catch (e) {
      console.error('Failed to load CSV uploads list:', e);
    }
  };

  const loadDatabasePatients = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchPatients(
        currentPage,
        pageSize,
        searchQuery,
        sourceFilter,
        uploadIdFilter || undefined,
        riskFilter,
        sortBy
      );

      setTotalRecords(res.total);
      setTotalPages(res.total_pages);
      setHighCount(res.high_risk_count || 0);
      setElevatedCount(res.elevated_risk_count || 0);
      setModCount(res.moderate_risk_count || 0);
      setMinimalCount(res.minimal_risk_count || 0);

      setPageInput(String(res.page));

      const items = res.patients.map((p: any) => {
        const latest = p.latest_prediction || {};
        return {
          ...p,
          patient_id: p.patient_id,
          patient_name: p.patient_name,
          date_of_birth: p.date_of_birth,
          source: p.source,
          source_filename: p.source_filename,
          readmission_probability: latest.readmission_probability || p.readmission_probability || 0.25,
          predicted_readmitted: latest.predicted_readmitted || p.predicted_readmitted || 'no',
          clinical_risk_tier: latest.risk_tier || p.clinical_risk_tier || 'Minimal Risk',
          primary_driver: p.medical_specialty ? `${p.medical_specialty} admission (${p.time_in_hospital}d stay)` : 'Care utilization',
          patient_data: { ...p }
        };
      });

      setPatientsList(items);
    } catch (err: any) {
      setError(err.message || 'Failed to query database patient records.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    loadDatabasePatients();
  };

  const handlePageJumpSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const p = parseInt(pageInput, 10);
    if (!isNaN(p) && p >= 1 && p <= totalPages) {
      setCurrentPage(p);
    } else {
      setPageInput(String(currentPage));
    }
  };

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setUploadedInfo(null);
    try {
      const batchRes = await predictBatchCsv(file);
      setUploadedInfo(`Uploaded & persisted ${batchRes.total_patients} patients from '${file.name}' (Upload ID: ${batchRes.upload_id})!`);
      await loadUploadedFiles();
      setSourceFilter('UPLOADED_CSV');
      setUploadIdFilter(batchRes.upload_id || '');
      setCurrentPage(1);
      await loadDatabasePatients();
    } catch (err: any) {
      setError(err.message || 'Failed to process CSV upload & database persistence.');
      setLoading(false);
    }
  };

  const handleDeletePatient = async (patientId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete patient record '${patientId}' from PostgreSQL database?`)) {
      return;
    }

    try {
      await deletePatient(patientId);
      setUploadedInfo(`Patient '${patientId}' deleted successfully.`);
      await loadDatabasePatients();
    } catch (err: any) {
      alert(err.message || `Failed to delete patient ${patientId}`);
    }
  };

  if (selectedPatient) {
    return <PatientDetail patient={selectedPatient} onBack={() => setSelectedPatient(null)} />;
  }


  return (
    <div className="space-y-6">
      {/* Top Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-[#12213A]" />
            <h1 className="text-xl font-bold font-display text-[#12213A]">Ward Discharge Risk Overview</h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Single Source-of-Truth patient readmission monitoring with persistent storage, global search, and SHAP decision support.
          </p>
        </div>

        {/* Dataset Actions */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 bg-slate-100 text-slate-700 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-mono">
            <Database className="w-3.5 h-3.5 text-emerald-600" />
            <span>Active DB Dataset: {totalRecords.toLocaleString()} Records</span>
          </div>

          <label className="cursor-pointer px-3 py-1.5 bg-[#12213A] hover:bg-slate-800 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-colors shadow-2xs">
            <Upload className="w-3.5 h-3.5" />
            <span>Upload Ward CSV</span>
            <input type="file" accept=".csv" onChange={handleCsvUpload} className="hidden" />
          </label>

          <button
            onClick={() => loadDatabasePatients()}
            className="p-1.5 text-slate-600 hover:text-[#12213A] bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors"
            title="Refresh database records"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* CSV Upload Success Alert */}
      {uploadedInfo && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs flex items-center justify-between shadow-2xs">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-medium">{uploadedInfo}</span>
          </div>
          <button onClick={() => setUploadedInfo(null)} className="text-emerald-700 font-bold hover:text-emerald-900">×</button>
        </div>
      )}

      {/* Primary Global Risk Metric Cards (Server-Side Calibrated Boundaries) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-1">
          <span className="text-xs font-semibold text-slate-500 block">Total Query Records</span>
          <p className="text-2xl font-mono font-bold text-[#12213A]">{totalRecords.toLocaleString()}</p>
          <span className="text-[11px] text-slate-400 font-mono">Global DB Query Count</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-red-200 shadow-xs space-y-1">
          <span className="text-xs font-bold text-red-700 block">High Risk (≥52.0%)</span>
          <p className="text-2xl font-mono font-bold text-red-800">{highCount.toLocaleString()}</p>
          <span className="text-[11px] text-slate-500 font-mono">Q4 (75th–100th %)</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-amber-200 shadow-xs space-y-1">
          <span className="text-xs font-bold text-amber-700 block">Elevated Risk (44.5%–52.0%)</span>
          <p className="text-2xl font-mono font-bold text-amber-800">{elevatedCount.toLocaleString()}</p>
          <span className="text-[11px] text-slate-500 font-mono">Q3 (50th–75th %)</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-blue-200 shadow-xs space-y-1">
          <span className="text-xs font-bold text-blue-700 block">Moderate Risk (38.7%–44.4%)</span>
          <p className="text-2xl font-mono font-bold text-blue-800">{modCount.toLocaleString()}</p>
          <span className="text-[11px] text-slate-500 font-mono">Q2 (25th–50th %)</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-emerald-200 shadow-xs space-y-1">
          <span className="text-xs font-bold text-emerald-700 block">Minimal Risk (&lt;38.7%)</span>
          <p className="text-2xl font-mono font-bold text-emerald-800">{minimalCount.toLocaleString()}</p>
          <span className="text-[11px] text-slate-500 font-mono">Q1 (0th–25th %)</span>
        </div>
      </div>

      {/* Filter & Control Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
        {/* Row 1: Source Selector Pills */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-slate-500" />
            <span className="text-xs font-bold text-slate-700">Patient Source:</span>
            <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg">
              {[
                { id: 'ALL', label: 'All Sources' },
                { id: 'KAGGLE', label: 'Kaggle Seeded' },
                { id: 'UPLOADED_CSV', label: 'Uploaded CSV' },
                { id: 'MANUAL', label: 'Manual Intake' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => {
                    setSourceFilter(tab.id);
                    if (tab.id !== 'UPLOADED_CSV') setUploadIdFilter('');
                    setCurrentPage(1);
                  }}
                  className={`px-2.5 py-1 text-xs rounded-md font-semibold transition-all ${
                    sourceFilter === tab.id
                      ? 'bg-[#12213A] text-white shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Sub-Filter: Dynamic Upload File Selector */}
          {sourceFilter === 'UPLOADED_CSV' && uploadedFilesList.length > 0 && (
            <div className="flex items-center gap-2 text-xs">
              <FileSpreadsheet className="w-4 h-4 text-purple-600" />
              <span className="font-semibold text-slate-700">Select Upload File:</span>
              <select
                value={uploadIdFilter}
                onChange={(e) => {
                  setUploadIdFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="bg-purple-50 border border-purple-200 text-purple-900 text-xs font-medium rounded-lg p-1.5 focus:outline-none"
              >
                <option value="">All Uploaded CSV Files ({uploadedFilesList.length})</option>
                {uploadedFilesList.map((f) => (
                  <option key={f.upload_id} value={f.upload_id}>
                    {f.filename} ({f.total_patients} pts, High: {f.high_risk_count})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Row 2: Search, Risk Tier Filter, Sorting & Pagination Controls */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 text-xs">
          {/* Risk Tier Pills */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-slate-500 font-medium flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" /> Risk Tier:
            </span>
            {[
              { id: 'ALL', label: 'All Risk Tiers' },
              { id: 'High Risk', label: 'High Risk' },
              { id: 'Elevated Risk', label: 'Elevated Risk' },
              { id: 'Moderate Risk', label: 'Moderate Risk' },
              { id: 'Minimal Risk', label: 'Minimal Risk' }
            ].map((tier) => (
              <button
                key={tier.id}
                onClick={() => {
                  setRiskFilter(tier.id);
                  setCurrentPage(1);
                }}
                className={`px-2.5 py-1 rounded-md font-semibold transition-all ${
                  riskFilter === tier.id
                    ? 'bg-slate-800 text-white shadow-2xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {tier.label}
              </button>
            ))}
          </div>

          {/* Search, Sort, and Editable Page Jump Box */}
          <div className="flex flex-wrap items-center gap-2">
            <form onSubmit={handleSearchSubmit} className="relative flex-1 min-w-[200px]">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search ID, Name, DOB, Specialty..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-[#12213A]"
              />
            </form>

            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-slate-50 border border-slate-200 rounded-lg p-1.5 font-medium text-slate-700 focus:outline-none"
            >
              <option value="RISK_DESC">Highest Risk First</option>
              <option value="RISK_ASC">Lowest Risk First</option>
              <option value="STAY_DESC">Longest Stay First</option>
              <option value="STAY_ASC">Shortest Stay First</option>
              <option value="NEWEST">Newest Records</option>
              <option value="OLDEST">Oldest Records</option>
            </select>

            {/* Editable Page Jump Box */}
            <form onSubmit={handlePageJumpSubmit} className="flex items-center gap-1.5 bg-slate-50 px-2 py-1 border border-slate-200 rounded-lg">
              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1 || loading}
                className="p-1 hover:bg-slate-200 disabled:opacity-40 rounded transition-colors text-slate-700"
                title="Previous Page"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              <span className="text-xs font-medium text-slate-600">Page</span>
              <input
                type="number"
                min="1"
                max={totalPages}
                value={pageInput}
                onChange={(e) => setPageInput(e.target.value)}
                onBlur={handlePageJumpSubmit}
                className="w-12 text-center py-0.5 px-1 bg-white border border-slate-300 rounded text-xs font-mono font-bold text-[#12213A]"
              />
              <span className="text-xs font-medium text-slate-600">of {totalPages}</span>

              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages || loading}
                className="p-1 hover:bg-slate-200 disabled:opacity-40 rounded transition-colors text-slate-700"
                title="Next Page"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Patient List */}
      {error ? (
        <div className="p-6 bg-red-50 border border-red-200 text-red-800 rounded-xl text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{error}</span>
        </div>
      ) : loading ? (
        <div className="bg-white p-12 rounded-xl border border-slate-200 text-center space-y-3">
          <RefreshCw className="w-6 h-6 text-slate-400 animate-spin mx-auto" />
          <p className="text-xs text-slate-500 font-medium">Fetching persistent database patient records...</p>
        </div>
      ) : patientsList.length === 0 ? (
        <div className="bg-white p-12 rounded-xl border border-slate-200 text-center space-y-2">
          <Users className="w-8 h-8 text-slate-300 mx-auto" />
          <p className="text-sm font-semibold text-slate-700">No Database Patients Match Selected Filters</p>
          <p className="text-xs text-slate-500">Try clearing search terms or selecting another Source / Risk filter.</p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {patientsList.map((patient) => (
            <PatientRow
              key={patient.patient_id}
              patient={patient}
              onSelect={(p) => (onSelectPatient ? onSelectPatient(p) : setSelectedPatient(p))}
              canDelete={canDeletePatients}
              onDelete={handleDeletePatient}
            />
          ))}
        </div>
      )}
    </div>
  );
};
