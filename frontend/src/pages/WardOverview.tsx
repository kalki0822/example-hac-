import React, { useEffect, useState } from 'react';
import { BatchPredictionResponse, BatchPatientResult } from '../types';
import { fetchPatients, predictBatch, predictBatchCsv } from '../api/client';
import { PatientRow } from '../components/PatientRow';
import { Search, Upload, RefreshCw, AlertTriangle, Users, Filter, CheckCircle, Database, ChevronLeft, ChevronRight, Info } from 'lucide-react';

interface WardOverviewProps {
  onSelectPatient: (patient: BatchPatientResult) => void;
}

export const WardOverview: React.FC<WardOverviewProps> = ({ onSelectPatient }) => {
  const [batchData, setBatchData] = useState<BatchPredictionResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedFilter, setSelectedFilter] = useState<'ALL' | 'High Risk' | 'Moderate Risk' | 'Low Risk'>('ALL');
  const [sortBy, setSortBy] = useState<'RISK_DESC' | 'RISK_ASC' | 'STAY_DESC'>('RISK_DESC');

  // Pagination state for 25,000 real Kaggle dataset rows
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize] = useState<number>(15);
  const [totalRecords, setTotalRecords] = useState<number>(25000);
  const [totalPages, setTotalPages] = useState<number>(1667);
  const [isCsvUploaded, setIsCsvUploaded] = useState<boolean>(false);
  const [uploadedFileName, setUploadedFileName] = useState<string>('');

  // Load patient page on mount and page change
  useEffect(() => {
    if (!isCsvUploaded) {
      loadPage(currentPage);
    }
  }, [currentPage, isCsvUploaded]);

  const loadPage = async (page: number) => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch paginated patient slice from GET /patients?page=X&page_size=15
      const paginatedRes = await fetchPatients(page, pageSize);
      setTotalRecords(paginatedRes.total);
      setTotalPages(paginatedRes.total_pages);

      // 2. Score patient records live via POST /predict_batch
      const res = await predictBatch(paginatedRes.patients);

      // 3. Enrich predictions with patient data and stable IDs (PT-10001+)
      const enrichedPredictions = res.predictions.map((p, i) => ({
        ...p,
        patient_id: paginatedRes.patients[i]?.patient_id || `PT-${10001 + (page - 1) * pageSize + i}`,
        patient_data: paginatedRes.patients[i]
      }));

      setBatchData({ ...res, predictions: enrichedPredictions });
    } catch (err: any) {
      setError(err.message || 'Failed to load patient records from FastAPI endpoint.');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setLoading(true);
    setError(null);
    try {
      const res = await predictBatchCsv(files[0]);
      setBatchData(res);
      setIsCsvUploaded(true);
      setUploadedFileName(files[0].name);
    } catch (err: any) {
      setError(`CSV Batch Processing Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleResetToDataset = () => {
    setIsCsvUploaded(false);
    setUploadedFileName('');
    setCurrentPage(1);
    loadPage(1);
  };

  const handlePrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage((prev) => prev - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage((prev) => prev + 1);
    }
  };

  // Calculate dynamic X and Y range for UI display
  const rangeStart = isCsvUploaded ? 1 : (currentPage - 1) * pageSize + 1;
  const rangeEnd = isCsvUploaded ? (batchData?.total_patients || 0) : Math.min(currentPage * pageSize, totalRecords);

  const filteredPatients = (batchData?.predictions || [])
    .filter((p) => {
      if (selectedFilter !== 'ALL' && p.clinical_risk_tier !== selectedFilter) return false;
      if (searchQuery.trim() === '') return true;

      const q = searchQuery.toLowerCase();
      const pId = (p.patient_id || `pt-${1000 + p.patient_index}`).toLowerCase();
      const driver = (p.primary_driver || '').toLowerCase();
      const spec = (p.patient_data?.medical_specialty || '').toLowerCase();

      return pId.includes(q) || driver.includes(q) || spec.includes(q);
    })
    .sort((a, b) => {
      if (sortBy === 'RISK_DESC') return b.readmission_probability - a.readmission_probability;
      if (sortBy === 'RISK_ASC') return a.readmission_probability - b.readmission_probability;
      if (sortBy === 'STAY_DESC') {
        const stayA = a.patient_data?.time_in_hospital || 0;
        const stayB = b.patient_data?.time_in_hospital || 0;
        return stayB - stayA;
      }
      return 0;
    });

  return (
    <div className="space-y-6">
      {/* Clinical Disclaimer Banner */}
      <div className="bg-amber-50/80 border border-amber-200 p-3.5 rounded-xl flex items-start gap-2.5 text-xs text-amber-900 shadow-2xs">
        <Info className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold">Clinical Decision Support Disclaimer: </span>
          Vitals is a clinical decision-support prototype for demonstration and research purposes. Predictions are not medical diagnoses and should not replace professional clinical judgment.
        </div>
      </div>

      {/* Ward Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-bold font-display text-[#12213A]">Ward Discharge Overview</h1>
            <span className="text-xs font-mono font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded flex items-center gap-1">
              <Database className="w-3.5 h-3.5 text-emerald-600" />
              {isCsvUploaded
                ? `Uploaded Ward Data (${uploadedFileName})`
                : `Showing ${rangeStart}–${rangeEnd} of ${totalRecords.toLocaleString()} Kaggle Patients`}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Predictions generated using the trained model on real Kaggle patient records.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {isCsvUploaded && (
            <button
              onClick={handleResetToDataset}
              className="px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-300 transition-colors"
            >
              Reset to Kaggle Dataset
            </button>
          )}

          <label className="flex items-center gap-2 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-[#12213A] text-xs font-semibold rounded-lg border border-slate-300 cursor-pointer transition-colors">
            <Upload className="w-4 h-4 text-slate-600" />
            <span>Upload Ward CSV</span>
            <input type="file" accept=".csv" onChange={handleFileUpload} className="hidden" />
          </label>

          <button
            onClick={() => loadPage(currentPage)}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 bg-[#12213A] text-white text-xs font-semibold rounded-lg hover:bg-slate-800 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Page</span>
          </button>
        </div>
      </div>

      {/* Ward Metrics Summary Cards */}
      {batchData && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
              <span>Page Scored</span>
              <Users className="w-4 h-4 text-slate-400" />
            </div>
            <p className="text-2xl font-bold font-mono text-[#12213A] mt-2 tabular-nums">
              {batchData.total_patients}
            </p>
            <span className="text-[11px] text-slate-500">
              {isCsvUploaded ? 'Uploaded records' : `Page ${currentPage} of ${totalPages}`}
            </span>
          </div>

          <div className="bg-red-50/50 p-4 rounded-xl border border-red-200 shadow-2xs">
            <div className="flex items-center justify-between text-red-800 text-xs font-semibold">
              <span>High Risk</span>
              <AlertTriangle className="w-4 h-4 text-red-600" />
            </div>
            <p className="text-2xl font-bold font-mono text-red-900 mt-2 tabular-nums">
              {batchData.high_risk_count}
            </p>
            <span className="text-[11px] text-red-700 font-medium">Require intervention</span>
          </div>

          <div className="bg-amber-50/50 p-4 rounded-xl border border-amber-200 shadow-2xs">
            <div className="flex items-center justify-between text-amber-800 text-xs font-semibold">
              <span>Moderate Risk</span>
              <Filter className="w-4 h-4 text-amber-600" />
            </div>
            <p className="text-2xl font-bold font-mono text-amber-900 mt-2 tabular-nums">
              {batchData.moderate_risk_count}
            </p>
            <span className="text-[11px] text-amber-700 font-medium">Close monitoring</span>
          </div>

          <div className="bg-slate-100/60 p-4 rounded-xl border border-slate-200 shadow-2xs">
            <div className="flex items-center justify-between text-slate-700 text-xs font-semibold">
              <span>Low Risk</span>
              <CheckCircle className="w-4 h-4 text-slate-500" />
            </div>
            <p className="text-2xl font-bold font-mono text-slate-800 mt-2 tabular-nums">
              {batchData.low_risk_count}
            </p>
            <span className="text-[11px] text-slate-600 font-medium">Standard discharge</span>
          </div>
        </div>
      )}

      {/* Filter, Search, and Pagination Control Bar */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
          {(['ALL', 'High Risk', 'Moderate Risk', 'Low Risk'] as const).map((filter) => (
            <button
              key={filter}
              onClick={() => setSelectedFilter(filter)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold whitespace-nowrap transition-colors ${
                selectedFilter === filter
                  ? 'bg-[#12213A] text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {filter === 'ALL' ? 'All Patients' : filter}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 sm:w-56">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search ID, specialty..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#12213A] text-[#12213A]"
            />
          </div>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-md focus:outline-none text-[#12213A] font-medium"
          >
            <option value="RISK_DESC">Highest Risk First</option>
            <option value="RISK_ASC">Lowest Risk First</option>
            <option value="STAY_DESC">Longest Stay First</option>
          </select>

          {/* Dataset Pagination Controls */}
          {!isCsvUploaded && (
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-md border border-slate-200">
              <button
                onClick={handlePrevPage}
                disabled={currentPage <= 1 || loading}
                className="p-1 rounded text-slate-700 hover:bg-white disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                title="Previous Page"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-[11px] font-mono font-semibold px-2 text-[#12213A] whitespace-nowrap">
                Page {currentPage} of {totalPages.toLocaleString()}
              </span>
              <button
                onClick={handleNextPage}
                disabled={currentPage >= totalPages || loading}
                className="p-1 rounded text-slate-700 hover:bg-white disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                title="Next Page"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-800 rounded-xl text-xs flex items-center gap-2 font-medium">
          <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Patient List View */}
      {loading ? (
        <div className="bg-white p-12 rounded-xl border border-slate-200 text-center">
          <RefreshCw className="w-6 h-6 text-slate-400 animate-spin mx-auto mb-2" />
          <p className="text-sm font-medium text-slate-600">
            Fetching patient page {currentPage} from 25,000 real Kaggle records...
          </p>
        </div>
      ) : filteredPatients.length === 0 ? (
        <div className="bg-white p-12 rounded-xl border border-slate-200 text-center">
          <Users className="w-8 h-8 text-slate-300 mx-auto mb-2" />
          <p className="text-sm font-semibold text-slate-700">No matching patient records found on this page.</p>
          <p className="text-xs text-slate-500 mt-1">Try clearing search query or navigating to another page.</p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {filteredPatients.map((patient) => (
            <PatientRow
              key={patient.patient_id || patient.patient_index}
              patient={patient}
              onSelect={onSelectPatient}
            />
          ))}
        </div>
      )}
    </div>
  );
};
