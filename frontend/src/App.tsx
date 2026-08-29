import React, { useState, useEffect } from 'react';
import {
  checkBackendHealth,
  submitIntelligenceQuery,
  uploadEvidenceFile,
  fetchIngestedDocuments,
  resetDatabase,
  QueryResponse,
  Citation,
  DocumentInfo
} from './services/api';

export default function App() {
  const [query, setQuery] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  
  // Document Scoped Filter State
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [selectedFileFilter, setSelectedFileFilter] = useState<string>('ALL');

  // Real-time progress status state
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const loadDocuments = async () => {
    const docs = await fetchIngestedDocuments();
    setDocuments(docs);
  };

  useEffect(() => {
    checkBackendHealth();
    loadDocuments();
  }, []);

  const handleSynthesize = async () => {
    if (!query.trim()) return;
    setIsProcessing(true);
    setUploadStatus(null);
    try {
      const data = await submitIntelligenceQuery(query, selectedFileFilter);
      setResponse(data);
    } catch (err) {
      console.error('Query execution error:', err);
      alert('Backend connection error. Make sure FastAPI backend server is running on http://localhost:8080');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleResetDatabase = async () => {
    if (!window.confirm('Wipe 100% of vector databases and uploaded files?')) return;
    try {
      await resetDatabase();
      setResponse(null);
      setActiveCitation(null);
      setSelectedFileFilter('ALL');
      setDocuments([]);
      setUploadStatus('🧹 Database reset cleanly. Zero documents remaining.');
    } catch (err) {
      console.error('Reset database error:', err);
      alert('Failed to reset database.');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    const isAudio = file.name.endsWith('.wav') || file.name.endsWith('.mp3') || file.name.endsWith('.m4a');
    
    setIsUploading(true);
    setUploadStatus(`⚡ Stage 1/3: Uploaded ${file.name}. Initializing ${isAudio ? 'Whisper Speech Engine...' : 'Document Parser...'}`);
    
    const stageTimer = setTimeout(() => {
      setUploadStatus(`⚡ Stage 2/3: ${isAudio ? 'Transcribing audio speech & filtering static (Whisper VAD)...' : 'Extracting layout blocks & tables...'}`);
    }, 2000);

    const indexTimer = setTimeout(() => {
      setUploadStatus(`⚡ Stage 3/3: Vectorizing chunks & indexing into ChromaDB + SQLite FTS5...`);
    }, 6000);

    try {
      const res = await uploadEvidenceFile(file);
      clearTimeout(stageTimer);
      clearTimeout(indexTimer);
      
      if (res.is_duplicate) {
        setUploadStatus(`⚠️ SimHash Near-Duplicate Detected: ${res.file_name} is a near-duplicate of ${res.duplicate_of}. Database bloat skipped!`);
      } else {
        setUploadStatus(`✅ Successfully processed & indexed ${res.file_name} (${res.total_chunks_indexed} timestamped chunks)`);
      }
      await loadDocuments();
    } catch (err) {
      clearTimeout(stageTimer);
      clearTimeout(indexTimer);
      console.error('File upload error:', err);
      setUploadStatus(`❌ Ingestion failed for ${file.name}`);
    } finally {
      setIsUploading(false);
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
          className="inline-flex items-center gap-1 px-2 py-0.5 mx-1 rounded bg-amber-500/20 border border-amber-500/40 text-amber-300 hover:bg-amber-500/40 font-mono text-xs font-semibold cursor-pointer transition shadow-sm"
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
        <div className="text-xs font-medium text-slate-400 flex items-center gap-3">
          <span>SIH25231 / SIH26154 • NTRO (PMO)</span>

          <button
            onClick={handleResetDatabase}
            className="bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-800 font-medium px-3 py-1.5 rounded text-xs transition flex items-center gap-1"
          >
            <span>🧹 Clear DB</span>
          </button>

          <label className={`cursor-pointer bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-4 py-2 rounded text-xs transition shadow-md flex items-center gap-2 ${isUploading ? 'opacity-50 pointer-events-none' : ''}`}>
            <span>{isUploading ? '⚡ Processing...' : '+ Upload Evidence File'}</span>
            <input type="file" onChange={handleFileUpload} className="hidden" accept=".pdf,.docx,.png,.jpg,.jpeg,.wav,.mp3" />
          </label>
        </div>
      </header>

      {/* Real-time Ingestion Stage Progress Bar */}
      {uploadStatus && (
        <div className="bg-slate-900 border-b border-slate-800 px-6 py-2.5 text-xs font-mono text-emerald-400 flex items-center justify-between shadow-inner">
          <div className="flex items-center space-x-2">
            {isUploading && <span className="animate-spin text-emerald-400">⚙️</span>}
            <span>{uploadStatus}</span>
          </div>
          {isUploading && (
            <div className="w-32 bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div className="bg-emerald-400 h-full animate-pulse w-3/4"></div>
            </div>
          )}
        </div>
      )}

      {/* Main Dual-Pane Console Grid */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Left Column: Grounded Intelligence Response & Input */}
        <div className="flex flex-col space-y-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 flex-1 flex flex-col shadow-lg">
            <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-3">
              <h2 className="text-sm font-bold tracking-wide text-slate-300 uppercase">
                Grounded Intelligence Briefing
              </h2>

              {/* Document Scoped Filter Dropdown */}
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-400 font-mono">Scope Search:</span>
                <select
                  value={selectedFileFilter}
                  onChange={(e) => setSelectedFileFilter(e.target.value)}
                  className="bg-slate-950 border border-slate-800 text-emerald-400 text-xs rounded px-2.5 py-1 focus:outline-none focus:border-emerald-500 font-mono font-semibold"
                >
                  <option value="ALL">🌐 All Ingested Files ({documents.length})</option>
                  {documents.map((doc) => (
                    <option key={doc.file_name} value={doc.file_name}>
                      📄 {doc.file_name} ({doc.chunk_count} chunks)
                    </option>
                  ))}
                </select>
              </div>
            </div>
            
            <div className="flex-1 bg-slate-950/60 rounded-lg p-4 text-slate-300 text-sm overflow-y-auto font-normal leading-relaxed border border-slate-800/50 min-h-[320px]">
              {isProcessing ? (
                <div className="flex flex-col items-center justify-center h-full text-emerald-400 font-mono text-xs space-y-2 py-12">
                  <span className="animate-spin text-lg">⚡</span>
                  <p>Performing hybrid vector search (ChromaDB + SQLite FTS5) & local LLM synthesis...</p>
                </div>
              ) : response ? (
                <div className="whitespace-pre-wrap leading-relaxed">
                  {renderFormattedAnswer(response.answer)}
                </div>
              ) : (
                <div className="text-slate-500 text-center py-16 text-xs font-mono">
                  Upload evidence files above or enter a query below to generate grounded intelligence briefings with clickable proof.
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
              className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-emerald-500 text-slate-100 placeholder-slate-500 shadow-inner"
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
          <h2 className="text-sm font-bold tracking-wide text-slate-300 mb-3 uppercase flex items-center justify-between border-b border-slate-800 pb-3">
            <span>Interactive Source Citation Navigation</span>
            <span className="text-xs text-slate-500 font-mono">Proof Viewer</span>
          </h2>
          
          <div className="flex-1 bg-slate-950/60 rounded-lg flex flex-col items-center justify-center text-slate-300 text-sm border border-slate-800/50 p-6">
            {activeCitation ? (
              <div className="w-full text-left space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <span className="font-bold text-amber-400 font-mono text-sm">📌 ACTIVE SOURCE PROOF</span>
                  <span className="text-xs bg-slate-800 px-2.5 py-1 rounded text-slate-300 font-mono">{activeCitation.file_name}</span>
                </div>
                <div className="bg-slate-900 p-4 rounded-lg border border-slate-800 text-xs space-y-2 font-mono">
                  <p><span className="text-slate-500">Target File:</span> <span className="text-slate-200 font-semibold">{activeCitation.file_name}</span></p>
                  <p><span className="text-slate-500">Citation Type:</span> <span className="text-amber-400 font-bold">{activeCitation.type.toUpperCase()}</span></p>
                  <p><span className="text-slate-500">Source Boundary:</span> <span className="text-emerald-400 font-bold">{activeCitation.value}</span></p>
                </div>
                <div className="bg-emerald-950/40 border border-emerald-800/60 p-3 rounded-lg text-xs text-emerald-300 font-mono">
                  ✓ Highlighting boundary target {activeCitation.value} in source document viewer...
                </div>
              </div>
            ) : (
              <div className="text-slate-500 text-center text-xs font-mono">
                Click any generated citation button [📌 Source: File="...", Page=N] in the briefing to navigate directly to the exact source proof page or audio timestamp.
              </div>
            )}
          </div>
        </div>

      </main>
    </div>
  );
}
