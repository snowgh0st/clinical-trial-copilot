/**
 * frontend/src/App.tsx
 */
import { useState } from 'react';
import { api } from './services/api';
import type { EHRProcessingResponse, TrialMatchResponse } from './services/api';
import { EHRInputForm } from './components/EHRInputForm';
import { ClinicalEntityBadge } from './components/ClinicalEntityBadge';
import { TrialMatchCard } from './components/TrialMatchCard';
import { Stethoscope, Dna, FileCheck, Search, AlertCircle } from 'lucide-react';

export default function App() {
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isMatching, setIsMatching] = useState<boolean>(false);
  const [ehrData, setEhrData] = useState<EHRProcessingResponse | null>(null);
  const [matchResults, setMatchResults] = useState<TrialMatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleProcessNote = async (note: string) => {
    setIsProcessing(true);
    setError(null);
    try {
      const response = await api.processEHR({ clinical_note: note });
      setEhrData(response);
      setMatchResults(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to process EHR note.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleProcessFHIR = async (bundle: object) => {
    setIsProcessing(true);
    setError(null);
    try {
      const response = await api.processEHR({ fhir_bundle: bundle });
      setEhrData(response);
      setMatchResults(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to process FHIR bundle.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRunMatch = async () => {
    if (!ehrData) return;
    setIsMatching(true);
    setError(null);
    try {
      const results = await api.matchTrials({
        parsed_patient: ehrData.parsed_patient,
        extracted_entities: ehrData.extracted_entities,
      });
      setMatchResults(results);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error running clinical trial matching agent.');
    } finally {
      setIsMatching(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans">
      {/* Top Header Navigation */}
      <header className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-600 rounded-lg text-white">
              <Stethoscope className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-bold text-lg leading-tight">Clinical Trial Copilot</h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                PyTorch BioBERT + LangChain Trial Matching Engine
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              FastAPI System Ready
            </span>
          </div>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 p-4 bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800 rounded-xl text-rose-700 dark:text-rose-300 text-sm flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: EHR Ingestion & BioBERT Extraction */}
          <div className="lg:col-span-6 space-y-6">
            <div className="flex items-center gap-2">
              <FileCheck className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              <h2 className="text-base font-bold">1. Patient EHR Ingestion</h2>
            </div>

            <EHRInputForm
              onSubmitNote={handleProcessNote}
              onSubmitFHIR={handleProcessFHIR}
              isLoading={isProcessing}
            />

            {/* Ingested Patient Profile & BioBERT Entities */}
            {ehrData && (
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                  <div>
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Patient Record
                    </span>
                    <h3 className="font-bold text-slate-900 dark:text-slate-100">
                      ID: {ehrData.parsed_patient.demographics.patient_id}
                    </h3>
                  </div>
                  <span className="text-xs text-slate-500">
                    Vector Chunk ID: {ehrData.indexed_chunk_id}
                  </span>
                </div>

                {/* Extracted BioBERT Badges */}
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Dna className="w-4 h-4 text-indigo-500" />
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                      BioBERT Extracted Entities ({ehrData.extracted_entities.length})
                    </h4>
                  </div>

                  <div className="flex flex-wrap gap-2 pt-1">
                    {ehrData.extracted_entities.map((entity, idx) => (
                      <ClinicalEntityBadge key={idx} entity={entity} />
                    ))}
                  </div>
                </div>

                {/* Match Trigger Button */}
                <button
                  onClick={handleRunMatch}
                  disabled={isMatching}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-lg shadow-sm transition-all disabled:opacity-50 mt-4"
                >
                  <Search className="w-4 h-4" />
                  {isMatching ? 'Running RAG Trial Matching Agent...' : 'Match Patient to Clinical Trials'}
                </button>
              </div>
            )}
          </div>

          {/* Right Column: Trial Match Agent Results */}
          <div className="lg:col-span-6 space-y-6">
            <div className="flex items-center gap-2">
              <Dna className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              <h2 className="text-base font-bold">2. Clinical Trial Compatibility</h2>
            </div>

            {matchResults ? (
              <div className="space-y-4">
                {matchResults.matches.map((match) => (
                  <TrialMatchCard key={match.trial_id} match={match} />
                ))}
              </div>
            ) : (
              <div className="bg-white dark:bg-slate-900 border border-dashed border-slate-300 dark:border-slate-800 rounded-xl p-12 text-center flex flex-col items-center justify-center min-h-[300px]">
                <Search className="w-10 h-10 text-slate-300 dark:text-slate-700 mb-3" />
                <h3 className="font-semibold text-slate-700 dark:text-slate-300 text-sm">
                  No Trial Evaluations Yet
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-500 max-w-xs mt-1">
                  Upload an EHR patient record or note on the left and click "Match Patient to Clinical Trials".
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}