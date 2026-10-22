/**
 * frontend/src/components/EHRInputForm.tsx
 */
import React, { useState } from 'react';
import { FileText, Code, Upload, Sparkles, Loader2 } from 'lucide-react';

interface EHRInputFormProps {
  onSubmitNote: (note: string) => Promise<void>;
  onSubmitFHIR: (bundle: object) => Promise<void>;
  isLoading: boolean;
}

export const EHRInputForm: React.FC<EHRInputFormProps> = ({
  onSubmitNote,
  onSubmitFHIR,
  isLoading,
}) => {
  const [activeTab, setActiveTab] = useState<'note' | 'fhir'>('note');
  const [clinicalNote, setClinicalNote] = useState<string>(
    'Patient is a 58-year-old male presenting with uncontrolled Type 2 Diabetes Mellitus (HbA1c 8.8%) and mild hypertension. Currently prescribed Metformin 1000mg BID and Lisinopril 10mg daily. No prior history of severe hepatic impairment or renal failure.'
  );
  const [fhirJson, setFhirJson] = useState<string>(
    JSON.stringify(
      {
        resourceType: 'Bundle',
        type: 'collection',
        entry: [
          {
            resource: {
              resourceType: 'Patient',
              id: 'pt-fhir-99',
              gender: 'male',
              birthDate: '1968-04-12',
            },
          },
          {
            resource: {
              resourceType: 'Condition',
              code: {
                coding: [{ display: 'Type 2 Diabetes Mellitus', code: '44054006' }],
              },
            },
          },
        ],
      },
      null,
      2
    )
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (activeTab === 'note') {
      onSubmitNote(clinicalNote);
    } else {
      try {
        const parsed = JSON.parse(fhirJson);
        onSubmitFHIR(parsed);
      } catch (err) {
        alert('Invalid JSON format for FHIR bundle.');
      }
    }
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm overflow-hidden">
      {/* Header Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50">
        <button
          type="button"
          onClick={() => setActiveTab('note')}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'note'
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 bg-white dark:bg-slate-900'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400'
          }`}
        >
          <FileText className="w-4 h-4" />
          Clinical Note (Text)
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('fhir')}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'fhir'
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 bg-white dark:bg-slate-900'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400'
          }`}
        >
          <Code className="w-4 h-4" />
          HL7 FHIR R4 Bundle (JSON)
        </button>
      </div>

      {/* Form Content */}
      <form onSubmit={handleSubmit} className="p-4 space-y-4">
        {activeTab === 'note' ? (
          <div>
            <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-2">
              Unstructured Clinical Note / EHR Narrative
            </label>
            <textarea
              rows={6}
              value={clinicalNote}
              onChange={(e) => setClinicalNote(e.target.value)}
              placeholder="Paste patient clinical summary or physician notes..."
              className="w-full p-3 text-sm font-sans bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none dark:text-slate-100 resize-none"
            />
          </div>
        ) : (
          <div>
            <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-2">
              HL7 FHIR JSON Bundle Payload
            </label>
            <textarea
              rows={8}
              value={fhirJson}
              onChange={(e) => setFhirJson(e.target.value)}
              className="w-full p-3 font-mono text-xs bg-slate-950 text-emerald-400 border border-slate-800 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none resize-none"
            />
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm rounded-lg shadow-sm transition-all disabled:opacity-50"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Processing Clinical Data via BioBERT...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Analyze EHR & Extract Medical Entities
            </>
          )}
        </button>
      </form>
    </div>
  );
};