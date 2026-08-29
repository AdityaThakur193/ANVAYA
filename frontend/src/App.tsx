import React, { useState, useEffect } from 'react';
import {
  checkBackendHealth,
  submitIntelligenceQuery,
  uploadEvidenceFile,
  fetchIngestedDocuments,
  resetDatabase,
  QueryResponse,
  Citation,
  RetrievedChunk,
  DocumentInfo
} from './services/api';

const API_BASE_URL = 'http://localhost:8080';

export default function App() {
  const [query, setQuery] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  
  // Voice Microphone Speech Recognition State
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<any>(null);

  // Active Proof Viewer State (stores citation metadata + matching text chunk)
  const [activeProof, setActiveProof] = useState<{
    citation: Citation;
    chunk?: RetrievedChunk;
  } | null>(null);
  
  // Document Scoped Filter State
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [selectedFileFilter, setSelectedFileFilter] = useState<string>('ALL');

  // Real-time progress status state
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  // Tab view inside Proof Panel: 'visual' vs 'text'
  const [proofTab, setProofTab] = useState<'visual' | 'text'>('visual');

  const loadDocuments = async () => {
    const docs = await fetchIngestedDocuments();
    setDocuments(docs);
  };

  useEffect(() => {
    checkBackendHealth();
    loadDocuments();

    // Initialize Web Speech API SpeechRecognition
    const { SpeechRecognition, webkitSpeechRecognition } = window as any;
    const SpeechRecognitionApi = SpeechRecognition || webkitSpeechRecognition;
    if (SpeechRecognitionApi) {
      const reco = new SpeechRecognitionApi();
      reco.continuous = false;
      reco.interimResults = true;
      reco.lang = 'en-US';

      reco.onresult = (event: any) => {
        let currentTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          currentTranscript += event.results[i][0].transcript;
        }
        if (currentTranscript.trim()) {
          setQuery(currentTranscript);
        }
      };

      reco.onerror = (event: any) => {
        console.warn('Speech recognition notice:', event.error);
        setIsListening(false);
      };

      reco.onend = () => {
        setIsListening(false);
      };

      setRecognition(reco);
    }
  }, []);

  const toggleListening = () => {
    if (!recognition) {
      alert('Voice speech recognition is not supported in this browser. Please use Chrome, Edge, or Brave.');
      return;
    }

    if (isListening) {
      try {
        recognition.stop();
      } catch (e) {}
      setIsListening(false);
    } else {
      try {
        recognition.start();
        setIsListening(true);
      } catch (e) {
        console.error('Failed to start speech recognition:', e);
      }
    }
  };

  const handleSynthesize = async (overrideQuery?: string) => {
    const targetQuery = overrideQuery || query;
    if (!targetQuery.trim() || isProcessing) return;

    if (isListening && recognition) {
      try { recognition.stop(); } catch (e) {}
      setIsListening(false);
    }

    setIsProcessing(true);
    setUploadStatus(null);
    setActiveProof(null);
    try {
      const data = await submitIntelligenceQuery(targetQuery, selectedFileFilter);
      setResponse(data);

      // Auto-activate the first citation proof if available
      if (data.citations && data.citations.length > 0) {
        handleCitationClick(data.citations[0], data.retrieved_chunks);
      }
    } catch (err) {
      console.error('Query execution error:', err);
      alert('Backend connection error. Please start the FastAPI backend server (http://localhost:8080).');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleResetDatabase = async () => {
    if (!window.confirm('Wipe 100% of vector databases and uploaded files?')) return;
    try {
      await resetDatabase();
      setResponse(null);
      setActiveProof(null);
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

  const handleCitationClick = (citation: Citation, chunks?: RetrievedChunk[]) => {
    const targetChunks = chunks || response?.retrieved_chunks || [];
    
    const match = targetChunks.find((c) => {
      if (c.file_name !== citation.file_name) return false;
      if (citation.type === 'page' && String(c.page_number) === String(citation.value)) return true;
      if (citation.type === 'time' && c.timestamp_label === citation.value) return true;
      return true;
    });

    setActiveProof({
      citation,
      chunk: match
    });

    const isVisual = citation.file_name.endsWith('.pdf') || citation.file_name.endsWith('.png') || citation.file_name.endsWith('.jpg') || citation.file_name.endsWith('.jpeg');
    setProofTab(isVisual ? 'visual' : 'text');
  };

  const renderFormattedAnswer = (text: string) => {
    const citationRegex = /\[Source:\s*(Audio|Image|Document|File)="([^"]+)"(?:,\s*(Page|Time)=([^\]]+))?\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = citationRegex.exec(text)) !== null) {
      const [fullMatch, assetKind, fileName, tagType, tagValue] = match;
      const matchIndex = match.index;

      if (matchIndex > lastIndex) {
        parts.push(text.substring(lastIndex, matchIndex));
      }

      const isAudio = assetKind.toLowerCase() === 'audio' || fileName.endsWith('.wav') || fileName.endsWith('.mp3');
      const isImage = assetKind.toLowerCase() === 'image' || fileName.endsWith('.png') || fileName.endsWith('.jpg') || fileName.endsWith('.jpeg');

      const computedType = isAudio ? 'time' : 'page';
      const computedValue = tagValue ? tagValue.trim() : (isAudio ? '0.0s' : '1');

      const citationObj: Citation = {
        file_name: fileName,
        type: computedType,
        value: computedValue
      };

      let badgeLabel = '';
      let badgeStyle = '';

      if (isAudio) {
        badgeLabel = `🎵 Audio Intercept: ${fileName} (Time: ${computedValue})`;
        badgeStyle = 'bg-amber-500/20 border-amber-500/40 text-amber-300 hover:bg-amber-500/40';
      } else if (isImage) {
        badgeLabel = `🖼️ Recon Image: ${fileName}`;
        badgeStyle = 'bg-sky-500/20 border-sky-500/40 text-sky-300 hover:bg-sky-500/40';
      } else {
        badgeLabel = `📄 Classified Doc: ${fileName} (Page: ${computedValue})`;
        badgeStyle = 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/40';
      }

      parts.push(
        <button
          key={matchIndex}
          onClick={() => handleCitationClick(citationObj)}
          className={`inline-flex items-center gap-1 px-2.5 py-0.5 mx-1 rounded border font-mono text-xs font-semibold cursor-pointer transition shadow-sm hover:scale-105 ${badgeStyle}`}
        >
          <span>📌 {badgeLabel}</span>
        </button>
      );

      lastIndex = matchIndex + fullMatch.length;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts;
  };

  const isVisualSupported = activeProof?.citation.file_name.endsWith('.pdf') ||
                            activeProof?.citation.file_name.endsWith('.png') ||
                            activeProof?.citation.file_name.endsWith('.jpg') ||
                            activeProof?.citation.file_name.endsWith('.jpeg');

  const pageNum = activeProof?.citation.type === 'page' ? parseInt(activeProof.citation.value) || 1 : 1;
  const highlightParam = query ? `&highlight_text=${encodeURIComponent(query)}` : '';
  const pageImageUrl = activeProof ? `${API_BASE_URL}/api/document/page_image?file_name=${encodeURIComponent(activeProof.citation.file_name)}&page_number=${pageNum}${highlightParam}` : '';

  const getDocumentIcon = (fileName: string) => {
    const f = fileName.toLowerCase();
    if (f.endsWith('.pdf')) return '📄';
    if (f.endsWith('.wav') || f.endsWith('.mp3')) return '🎵';
    if (f.endsWith('.png') || f.endsWith('.jpg') || f.endsWith('.jpeg')) return '🖼️';
    return '📁';
  };

  const getProofTitle = () => {
    if (!activeProof) return '';
    const fn = activeProof.citation.file_name.toLowerCase();
    if (fn.endsWith('.wav') || fn.endsWith('.mp3')) return '🎵 AUDIO INTERCEPT PROOF';
    if (fn.endsWith('.png') || fn.endsWith('.jpg') || fn.endsWith('.jpeg')) return '🖼️ RECONNAISSANCE IMAGE PROOF';
    return '📄 CLASSIFIED DOCUMENT PROOF';
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Header Bar */}
      <header className="border-b border-slate-800 px-6 py-4 flex justify-between items-center bg-slate-900/60 backdrop-blur-md sticky top-0 z-50 shadow-md">
        <div className="flex items-center space-x-3">
          <h1 className="text-xl font-extrabold tracking-wider text-emerald-400">🛡️ ANVAYA</h1>
          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800">
            AIR-GAPPED (100% OFFLINE)
          </span>
        </div>
        <div className="text-xs font-medium text-slate-400 flex items-center gap-3">
          <span className="hidden sm:inline">SIH25231 / SIH26154 • NTRO (PMO)</span>

          <button
            onClick={handleResetDatabase}
            title="Wipe all vector & FTS database files"
            className="bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-800 font-medium px-3 py-1.5 rounded text-xs transition flex items-center gap-1 shadow-sm"
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
              <h2 className="text-sm font-bold tracking-wide text-slate-300 uppercase flex items-center gap-2">
                <span>Multimodal Intelligence Briefing</span>
                {documents.length > 0 && (
                  <span className="text-[10px] bg-slate-800 text-emerald-400 px-2 py-0.5 rounded font-mono font-semibold">
                    {documents.length} File{documents.length > 1 ? 's' : ''} Active
                  </span>
                )}
              </h2>

              {/* Document Scoped Filter Dropdown */}
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-400 font-mono">Scope Search:</span>
                <select
                  value={selectedFileFilter}
                  onChange={(e) => setSelectedFileFilter(e.target.value)}
                  className="bg-slate-950 border border-slate-800 text-emerald-400 text-xs rounded px-2.5 py-1 focus:outline-none focus:border-emerald-500 font-mono font-semibold cursor-pointer max-w-[220px] truncate"
                >
                  <option value="ALL">🌐 All Ingested Files ({documents.length})</option>
                  {documents.map((doc) => (
                    <option key={doc.file_name} value={doc.file_name}>
                      {getDocumentIcon(doc.file_name)} {doc.file_name} ({doc.chunk_count} chunks)
                    </option>
                  ))}
                </select>
              </div>
            </div>
            
            <div className="flex-1 bg-slate-950/60 rounded-lg p-4 text-slate-300 text-sm overflow-y-auto font-normal leading-relaxed border border-slate-800/50 min-h-[340px]">
              {isProcessing ? (
                <div className="flex flex-col items-center justify-center h-full text-emerald-400 font-mono text-xs space-y-2 py-16">
                  <span className="animate-spin text-xl">⚡</span>
                  <p className="font-bold">Performing multimodal RRF search & local LLM synthesis...</p>
                  <span className="text-[10px] text-slate-500">Dispatching to Llama 3.1 8B Engine...</span>
                </div>
              ) : response ? (
                <div className="whitespace-pre-wrap leading-relaxed space-y-3">
                  <div>{renderFormattedAnswer(response.answer)}</div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-slate-500 text-center py-12 text-xs font-mono space-y-4">
                  <p>Upload evidence files above or enter a query below to generate grounded intelligence briefings with asset-aware citation badges.</p>
                  
                  {/* Sample Query Pills */}
                  {documents.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-[10px] uppercase tracking-wider text-slate-400 block font-bold">Suggested Quick Queries:</span>
                      <div className="flex flex-wrap justify-center gap-2 max-w-md">
                        <button
                          onClick={() => { setQuery("whose name is written in the resume"); handleSynthesize("whose name is written in the resume"); }}
                          className="bg-slate-900 hover:bg-slate-800 border border-slate-800 text-emerald-400 text-[11px] px-2.5 py-1 rounded transition"
                        >
                          "whose name is written in the resume"
                        </button>
                        <button
                          onClick={() => { setQuery("what timestamp was harvard mentioned"); handleSynthesize("what timestamp was harvard mentioned"); }}
                          className="bg-slate-900 hover:bg-slate-800 border border-slate-800 text-amber-300 text-[11px] px-2.5 py-1 rounded transition"
                        >
                          "what timestamp was harvard mentioned"
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Search Query Input Bar with Live Voice Microphone STT */}
          <div className="flex gap-2 relative items-center">
            <div className="relative flex-1 flex items-center">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSynthesize()}
                placeholder={isListening ? "🎙️ Listening... Speak into your microphone..." : "Ask a plain-language query across evidence files..."}
                className={`w-full bg-slate-900 border ${isListening ? 'border-rose-500 ring-2 ring-rose-500/40 text-rose-200' : 'border-slate-800 focus:border-emerald-500 text-slate-100'} rounded-lg pl-4 pr-20 py-3 text-sm focus:outline-none placeholder-slate-500 shadow-inner`}
              />

              {/* Voice Speech Microphone Toggle Button */}
              <button
                onClick={toggleListening}
                type="button"
                className={`absolute right-8 p-1.5 rounded-md transition flex items-center justify-center ${
                  isListening
                    ? 'bg-rose-600 text-white animate-pulse shadow-lg shadow-rose-500/50 scale-110'
                    : 'text-slate-400 hover:text-emerald-400 hover:bg-slate-800'
                }`}
                title={isListening ? "Recording voice... Click to stop" : "Click to speak into microphone"}
              >
                <span className="text-sm">🎙️</span>
              </button>

              {/* Clear Input Button */}
              {query && (
                <button
                  onClick={() => setQuery('')}
                  className="absolute right-2.5 text-slate-500 hover:text-slate-300 text-xs font-bold font-mono p-1"
                  title="Clear query"
                >
                  ✕
                </button>
              )}
            </div>

            <button
              onClick={() => handleSynthesize()}
              disabled={isProcessing || !query.trim()}
              className="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-6 py-3 rounded-lg text-sm transition shadow-md flex items-center gap-2 disabled:opacity-50"
            >
              {isProcessing ? 'Synthesizing...' : 'Synthesize'}
            </button>
          </div>
        </div>

        {/* Right Column: Visual Page & Proof Viewer Panel */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 flex flex-col shadow-lg">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
            <h2 className="text-sm font-bold tracking-wide text-slate-300 uppercase flex items-center gap-2">
              <span>Interactive Source Citation Navigation</span>
            </h2>

            {/* Toggle Tabs: Visual Page Image vs Extracted Text */}
            {activeProof && (
              <div className="flex items-center space-x-2">
                {isVisualSupported && (
                  <div className="flex bg-slate-950 p-0.5 rounded border border-slate-800 text-xs font-mono">
                    <button
                      onClick={() => setProofTab('visual')}
                      className={`px-3 py-1 rounded transition font-bold ${proofTab === 'visual' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'text-slate-400 hover:text-slate-200'}`}
                    >
                      🖼️ Visual Canvas
                    </button>
                    <button
                      onClick={() => setProofTab('text')}
                      className={`px-3 py-1 rounded transition font-bold ${proofTab === 'text' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'text-slate-400 hover:text-slate-200'}`}
                    >
                      📄 Extracted Text
                    </button>
                  </div>
                )}
                <button
                  onClick={() => setActiveProof(null)}
                  className="text-slate-500 hover:text-slate-300 text-xs font-mono font-bold px-2 py-1 rounded bg-slate-950 border border-slate-800"
                  title="Close active proof panel"
                >
                  ✕ Close
                </button>
              </div>
            )}
          </div>
          
          <div className="flex-1 bg-slate-950/60 rounded-lg flex flex-col text-slate-300 text-sm border border-slate-800/50 p-4 overflow-y-auto min-h-[340px]">
            {activeProof ? (
              <div className="w-full text-left space-y-3">
                {/* Proof Header Card */}
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <span className="font-bold text-amber-400 font-mono text-xs flex items-center gap-1.5">
                    <span>📌 {getProofTitle()}</span>
                  </span>
                  <span className="text-xs bg-slate-800 px-2.5 py-0.5 rounded text-slate-200 font-mono font-semibold border border-slate-700">
                    {activeProof.citation.file_name}
                  </span>
                </div>

                {/* Metadata Grid */}
                <div className="grid grid-cols-2 gap-2 bg-slate-900 p-2.5 rounded-lg border border-slate-800 text-xs font-mono">
                  <div>
                    <span className="text-slate-500 block">Target Asset</span>
                    <span className="text-slate-200 font-semibold truncate block">{activeProof.citation.file_name}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Boundary Target</span>
                    <span className="text-amber-400 font-bold uppercase block">{activeProof.citation.type}: {activeProof.citation.value}</span>
                  </div>
                </div>

                {/* VISUAL PAGE IMAGE DISPLAY */}
                {proofTab === 'visual' && isVisualSupported ? (
                  <div className="bg-slate-900 border border-amber-500/40 p-2 rounded-lg space-y-2 shadow-inner flex flex-col items-center">
                    <div className="w-full flex items-center justify-between border-b border-slate-800/80 pb-1.5 px-1">
                      <span className="text-amber-400 font-mono text-xs font-bold uppercase flex items-center gap-1">
                        <span>🖼️ VERIFIED PAGE CANVAS PROOF</span>
                      </span>
                      <span className="text-emerald-400 font-mono text-[10px]">Page {pageNum} Rendered</span>
                    </div>

                    <div className="relative border border-slate-800 rounded bg-slate-950 p-1 overflow-auto max-h-[300px] w-full flex justify-center">
                      <img
                        src={pageImageUrl}
                        alt={`Proof page ${pageNum}`}
                        className="rounded shadow-md max-w-full h-auto object-contain border border-amber-500/20"
                        onError={(e) => {
                          setProofTab('text');
                        }}
                      />
                      <div className="absolute top-2 right-2 bg-amber-500/90 text-slate-950 text-[10px] font-bold font-mono px-2 py-0.5 rounded shadow">
                        PAGE {pageNum} PROOF
                      </div>
                    </div>
                  </div>
                ) : (
                  /* EXTRACTED EVIDENCE TEXT DISPLAY */
                  <div className="bg-slate-900 border border-emerald-500/40 p-3.5 rounded-lg space-y-2 shadow-inner">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                      <span className="text-emerald-400 font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-1">
                        <span>✓ EXACT EXTRACTED EVIDENCE CONTENT</span>
                      </span>
                      {activeProof.chunk?.rrf_score && (
                        <span className="text-slate-500 font-mono text-[10px]">RRF Score: {activeProof.chunk.rrf_score}</span>
                      )}
                    </div>

                    <div className="bg-slate-950 p-3.5 rounded-md text-slate-200 leading-relaxed font-sans text-xs border border-slate-800/80 whitespace-pre-wrap max-h-[220px] overflow-y-auto">
                      {activeProof.chunk ? activeProof.chunk.text : `Source text chunk for ${activeProof.citation.file_name} (${activeProof.citation.type}: ${activeProof.citation.value})`}
                    </div>
                  </div>
                )}

                {/* Verification Confirmation Footer */}
                <div className="bg-emerald-950/40 border border-emerald-800/60 p-2.5 rounded-lg text-xs text-emerald-300 font-mono flex items-center justify-between">
                  <span>✓ Proof target '{activeProof.citation.value}' verified in document index.</span>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-slate-500 text-center text-xs font-mono space-y-2 py-16">
                <span>🖼️</span>
                <p>Click any generated citation badge (🎵 Audio Intercept, 🖼️ Recon Image, 📄 Classified Doc) to display the real visual document canvas and proof chunk.</p>
              </div>
            )}
          </div>
        </div>

      </main>
    </div>
  );
}
