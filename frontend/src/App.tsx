import React, { useState, useEffect } from 'react';
import { checkBackendHealth, submitIntelligenceQuery, uploadEvidenceFile, QueryResponse, Citation } from './services/api';

export default function App() {
  const [query, setQuery] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);

  useEffect(() => {
    checkBackendHealth();
  }, []);

  const handleSynthesize = async () => {
    if (!query.trim()) return;
    setIsProcessing(true);
    setUploadStatus(null);
    try {
      const data = await submitIntelligenceQuery(query);
      setResponse(data);
    } catch (err) {
      console.error('Query execution error:', err);
      alert('Backend connection error. Make sure FastAPI backend server is running on http://localhost:8000');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setUploadStatus(`Ingesting ${file.name}...`);
    try {
      const res = await uploadEvidenceFile(file);
      setUploadStatus(`✅ Successfully indexed ${res.file_name} (${res.total_chunks_indexed} chunks)`);
    } catch (err) {
      console.error('File upload error:', err);
      setUploadStatus(`❌ Ingestion failed for ${file.name}`);
    }
  };

  const renderFormattedAnswer = (text: string) => {
    const citationRegex = /\[Source:\s*File="([^"]+)",\s*(Page|Time)=([^\]]+)\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = citationRegex.exec(text)) !== null) {
      const [fullMatch, fileName, tagType, tagValue] = match;
      const matchIndex = match.index;

      if (matchIndex > lastIndex) {
        parts.push(text.substring(lastIndex, matchIndex));
      }

      parts.push(
        <button
          key={matchIndex}
          onClick={() => setActiveCitation({ file_name: fileName, type: tagType.toLowerCase() as 'page' | 'time', value: tagValue })}
          className="inline-flex items-center gap-1 px-2 py-0.5 mx-1 rounded bg-amber-500/20 border border-amber-500/40 text-amber-300 hover:bg-amber-500/40 font-mono text-xs font-semibold cursor-pointer transition"
        >
          <span>📌 {fileName} ({tagType}: {tagValue})</span>
        </button>
      );

      lastIndex = matchIndex + fullMatch.length;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Header Bar */}
      <header className="border-b border-slate-800 px-6 py-4 flex justify-between items-center bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center space-x-3">
          <h1 className="text-xl font-extrabold tracking-wider text-emerald-400">🛡️ ANVAYA</h1>
          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800">
            AIR-GAPPED (100% OFFLINE)
          </span>
        </div>
        <div className="text-xs font-medium text-slate-400 flex items-center gap-4">
          <span>SIH25231 / SIH26154 • NTRO (PMO)</span>
          <label className="cursor-pointer bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded text-xs transition border border-slate-700">
            <span>+ Upload File</span>
            <input type="file" onChange={handleFileUpload} className="hidden" accept=".pdf,.docx,.png,.jpg,.jpeg,.wav,.mp3" />
          </label>
        </div>
      </header>

      {uploadStatus && (
        <div className="bg-slate-900 border-b border-slate-800 px-6 py-2 text-xs font-mono text-emerald-400 flex justify-between">
          <span>{uploadStatus}</span>
        </div>
      )}

      {/* Main Dual-Pane Console Grid */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Left Column: Grounded Intelligence Response & Input */}
        <div className="flex flex-col space-y-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 flex-1 flex flex-col shadow-lg">
            <h2 className="text-sm font-bold tracking-wide text-slate-300 mb-3 uppercase flex items-center justify-between">
              <span>Grounded Intelligence Briefing</span>
              <span className="text-xs text-slate-500 font-mono">Llama 3.2 3B GGUF</span>
            </h2>
            
            <div className="flex-1 bg-slate-950/60 rounded-lg p-4 text-slate-300 text-sm overflow-y-auto font-normal leading-relaxed border border-slate-800/50 min-h-[300px]">
              {isProcessing ? (
                <div className="flex items-center justify-center h-full text-emerald-400 font-mono text-xs animate-pulse">
                  ⚡ Performing hybrid vector search & local LLM synthesis...
                </div>
              ) : response ? (
                <div className="whitespace-pre-wrap leading-relaxed">
                  {renderFormattedAnswer(response.answer)}
                </div>
              ) : (
                <div className="text-slate-500 text-center py-12">
                  Upload evidence files or enter a query to generate grounded intelligence briefings with clickable proof.
                </div>
              )}
            </div>
          </div>

          {/* Search Query Input */}
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSynthesize()}
              placeholder="Ask a plain-language query across evidence files..."
              className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-emerald-500 text-slate-100 placeholder-slate-500"
            />
            <button
              onClick={handleSynthesize}
              disabled={isProcessing}
              className="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-6 py-3 rounded-lg text-sm transition shadow-md flex items-center gap-2 disabled:opacity-50"
            >
              {isProcessing ? 'Synthesizing...' : 'Synthesize'}
            </button>
          </div>
        </div>

        {/* Right Column: Dual Citation Navigation Panel */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 flex flex-col shadow-lg">
          <h2 className="text-sm font-bold tracking-wide text-slate-300 mb-3 uppercase flex items-center justify-between">
            <span>Interactive Source Citation Navigation</span>
            <span className="text-xs text-slate-500 font-mono">Proof Viewer</span>
          </h2>
          
          <div className="flex-1 bg-slate-950/60 rounded-lg flex flex-col items-center justify-center text-slate-300 text-sm border border-slate-800/50 p-6">
            {activeCitation ? (
              <div className="w-full text-left space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <span className="font-bold text-amber-400 font-mono text-sm">📌 ACTIVE SOURCE PROOF</span>
                  <span className="text-xs bg-slate-800 px-2 py-0.5 rounded text-slate-300">{activeCitation.file_name}</span>
                </div>
                <div className="bg-slate-900 p-4 rounded-lg border border-slate-800 text-xs space-y-2 font-mono">
                  <p><span className="text-slate-500">File:</span> {activeCitation.file_name}</p>
                  <p><span className="text-slate-500">Citation Type:</span> {activeCitation.type.toUpperCase()}</p>
                  <p><span className="text-slate-500">Target Value:</span> {activeCitation.value}</p>
                </div>
                <p className="text-xs text-emerald-400 font-mono pt-2">
                  ✓ Highlighting Page {activeCitation.value} in PDF viewer...
                </p>
              </div>
            ) : (
              <div className="text-slate-500 text-center">
                Click any generated citation button [📌 Source: File="...", Page=N] in the briefing to navigate directly to the exact source proof page or audio timestamp.
              </div>
            )}
          </div>
        </div>

      </main>
    </div>
  );
}
