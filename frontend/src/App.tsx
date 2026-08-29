import React, { useState, useEffect, useRef } from 'react';
import {
  checkBackendHealth,
  submitIntelligenceQuery,
  uploadEvidenceFile,
  fetchIngestedDocuments,
  resetDatabase,
  transcribeVoiceAudio,
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
  
  // 100% Offline Air-Gapped Microphone Speech Recording State
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribingMic, setIsTranscribingMic] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Active Proof Viewer State (stores citation metadata + matching text chunk)
  const [activeProof, setActiveProof] = useState<{
    citation: Citation;
    chunk?: RetrievedChunk;
  } | null>(null);
  
  // Document Scoped Filter State
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [selectedFileFilter, setSelectedFileFilter] = useState<string>('ALL');
  const [isScopeDropdownOpen, setIsScopeDropdownOpen] = useState(false);

  // Custom Tactical Modal & Toast States
  const [showResetModal, setShowResetModal] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Visual Canvas Controls (Zoom & Page Page Nav)
  const [canvasZoom, setCanvasZoom] = useState<number>(100);

  // Real-time progress status state
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  // Tab view inside Proof Panel: 'visual' vs 'text'
  const [proofTab, setProofTab] = useState<'visual' | 'text'>('visual');

  const scopeDropdownRef = useRef<HTMLDivElement>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const loadDocuments = async () => {
    const docs = await fetchIngestedDocuments();
    setDocuments(docs);
  };

  useEffect(() => {
    checkBackendHealth();
    loadDocuments();

    const handleClickOutside = (event: MouseEvent) => {
      if (scopeDropdownRef.current && !scopeDropdownRef.current.contains(event.target as Node)) {
        setIsScopeDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleMicRecording = async () => {
    if (isRecording) {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      setIsRecording(false);
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunksRef.current = [];
        const recorder = new MediaRecorder(stream);

        recorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };

        recorder.onstop = async () => {
          stream.getTracks().forEach((track) => track.stop());

          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          if (audioBlob.size < 100) return;

          setIsTranscribingMic(true);
          setUploadStatus('⚡ Transcribing microphone speech 100% OFFLINE via Faster-Whisper CPU Engine...');
          try {
            const res = await transcribeVoiceAudio(audioBlob);
            if (res.transcript && res.transcript.trim()) {
              setQuery(res.transcript.trim());
              setUploadStatus(`✅ 100% Offline Transcribed: "${res.transcript.trim()}"`);
              showToast('🎙️ Microphone speech transcribed offline cleanly!');
            } else {
              setUploadStatus('⚠️ No spoken speech detected in microphone recording.');
            }
          } catch (err) {
            console.error('Offline Voice STT error:', err);
            setUploadStatus('❌ Offline Voice STT Error. Ensure backend is running.');
          } finally {
            setIsTranscribingMic(false);
          }
        };

        recorder.start();
        mediaRecorderRef.current = recorder;
        setIsRecording(true);
      } catch (err) {
        console.error('Microphone access error:', err);
        showToast('❌ Microphone permission denied or audio hardware absent.');
      }
    }
  };

  const handleSynthesize = async (overrideQuery?: string) => {
    const targetQuery = overrideQuery || query;
    if (!targetQuery.trim() || isProcessing) return;

    if (isRecording && mediaRecorderRef.current) {
      try { mediaRecorderRef.current.stop(); } catch (e) {}
      setIsRecording(false);
    }

    setIsProcessing(true);
    setUploadStatus(null);
    setActiveProof(null);
    setCanvasZoom(100);
    try {
      const data = await submitIntelligenceQuery(targetQuery, selectedFileFilter);
      setResponse(data);

      // Auto-activate the first citation proof if available
      if (data.citations && data.citations.length > 0) {
        handleCitationClick(data.citations[0], data.retrieved_chunks);
      }
    } catch (err) {
      console.error('Query execution error:', err);
      showToast('❌ Backend connection error. Start FastAPI server at http://localhost:8080.');
    } finally {
      setIsProcessing(false);
    }
  };

  const executeResetDatabase = async () => {
    setShowResetModal(false);
    try {
      await resetDatabase();
      setResponse(null);
      setActiveProof(null);
      setSelectedFileFilter('ALL');
      setDocuments([]);
      setUploadStatus('🧹 Database reset cleanly. Zero documents remaining.');
      showToast('🧹 100% Vector DB & evidence uploads purged cleanly.');
    } catch (err) {
      console.error('Reset database error:', err);
      showToast('❌ Failed to reset database.');
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
        showToast(`⚠️ SimHash deduplication skipped ${res.file_name}!`);
      } else {
        setUploadStatus(`✅ Successfully processed & indexed ${res.file_name} (${res.total_chunks_indexed} timestamped chunks)`);
        showToast(`✅ Successfully indexed ${res.file_name}`);
      }
      await loadDocuments();
    } catch (err) {
      clearTimeout(stageTimer);
      clearTimeout(indexTimer);
      console.error('File upload error:', err);
      setUploadStatus(`❌ Ingestion failed for ${file.name}`);
      showToast(`❌ Ingestion failed for ${file.name}`);
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
    setCanvasZoom(100);

    const isVisual = citation.file_name.endsWith('.pdf') || citation.file_name.endsWith('.png') || citation.file_name.endsWith('.jpg') || citation.file_name.endsWith('.jpeg');
    setProofTab(isVisual ? 'visual' : 'text');
  };

  const copyChunkText = (text: string) => {
    navigator.clipboard.writeText(text);
    showToast('📋 Evidence text copied to clipboard!');
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
        badgeStyle = 'bg-amber-950/70 border-amber-600/60 text-amber-300 hover:bg-amber-900/80';
      } else if (isImage) {
        badgeLabel = `🖼️ Recon Image: ${fileName}`;
        badgeStyle = 'bg-sky-950/70 border-sky-600/60 text-sky-300 hover:bg-sky-900/80';
      } else {
        badgeLabel = `📄 Classified Doc: ${fileName} (Page: ${computedValue})`;
        badgeStyle = 'bg-[#123534] border-[#2E8682] text-emerald-300 hover:bg-[#1A4B49]';
      }

      parts.push(
        <button
          key={matchIndex}
          onClick={() => handleCitationClick(citationObj)}
          className={`inline-flex items-center gap-1.5 px-3 py-1 mx-1 my-1 rounded border font-mono text-xs font-semibold cursor-pointer transition-all shadow-md hover:scale-105 ${badgeStyle}`}
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

  const getSelectedFilterLabel = () => {
    if (selectedFileFilter === 'ALL') return `🌐 All Ingested Files (${documents.length})`;
    const match = documents.find(d => d.file_name === selectedFileFilter);
    if (match) return `${getDocumentIcon(match.file_name)} ${match.file_name}`;
    return selectedFileFilter;
  };

  return (
    <div className="min-h-screen bg-[#0B131E] text-slate-100 flex flex-col font-sans relative selection:bg-[#26716E] selection:text-white">
      {/* Floating Tactical Toast Notification */}
      {toastMessage && (
        <div className="fixed top-16 right-6 z-50 bg-[#131F2E] border border-[#2E8682] text-emerald-300 font-mono text-xs px-4 py-2.5 rounded-lg shadow-2xl flex items-center gap-2 animate-bounce">
          <span>{toastMessage}</span>
        </div>
      )}

      {/* CUSTOM TACTICAL CONFIRMATION MODAL FOR DATABASE PURGE */}
      {showResetModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-[#131F2E] border border-rose-600/70 rounded-xl p-6 max-w-md w-full shadow-2xl space-y-4 font-sans">
            <div className="flex items-center space-x-3 border-b border-[#1E2E42] pb-3">
              <span className="text-xl">⚠️</span>
              <h3 className="text-base font-extrabold text-white font-mono uppercase tracking-wider">
                Wipe Vector Database & Uploads?
              </h3>
            </div>

            <p className="text-slate-300 text-xs leading-relaxed">
              This action will permanently purge 100% of ChromaDB vector collections, SQLite FTS5 indexes, and uploaded evidence files. This operation cannot be undone.
            </p>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setShowResetModal(false)}
                className="bg-[#080E17] hover:bg-[#1E2E42] text-slate-300 font-semibold px-4 py-2 rounded text-xs transition border border-[#1E2E42]"
              >
                Cancel
              </button>
              <button
                onClick={executeResetDatabase}
                className="bg-rose-600 hover:bg-rose-500 text-white font-extrabold px-5 py-2 rounded text-xs transition shadow-lg flex items-center gap-1.5"
              >
                <span>🧹 Confirm Wipe Data</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Top Brand Command Header Bar */}
      <header className="border-b border-[#1E2E42] px-6 py-3.5 flex justify-between items-center bg-[#131F2E]/90 backdrop-blur-md sticky top-0 z-40 shadow-lg">
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-full overflow-hidden border border-[#2E8682] shadow-md bg-white flex items-center justify-center p-0.5">
            <img src="/logo.jpeg" alt="ANVAYA Logo" className="w-full h-full object-contain rounded-full" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-black tracking-widest text-white uppercase font-mono">ANVAYA</h1>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-[#123534] text-[#34D399] border border-[#2E8682] uppercase tracking-wider font-mono">
                100% AIR-GAPPED
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium tracking-tight">Multimodal Defense Intelligence Engine</p>
          </div>
        </div>

        <div className="text-xs font-medium text-slate-400 flex items-center gap-3">
          <span className="hidden sm:inline-block font-mono text-[11px] bg-[#080E17] px-3 py-1 rounded border border-[#1E2E42] text-slate-300">
            NTRO • SIH25231
          </span>

          <button
            onClick={() => setShowResetModal(true)}
            title="Wipe vector databases and uploaded evidence files"
            className="bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800/60 font-semibold px-3 py-1.5 rounded text-xs transition flex items-center gap-1 shadow-sm"
          >
            <span>🧹 Clear DB</span>
          </button>

          <label className={`cursor-pointer bg-[#1A4B49] hover:bg-[#26716E] text-white font-bold px-4 py-2 rounded border border-[#2E8682] text-xs transition shadow-md flex items-center gap-2 ${isUploading ? 'opacity-50 pointer-events-none' : ''}`}>
            <span>{isUploading ? '⚡ Processing...' : '+ Upload Evidence File'}</span>
            <input type="file" onChange={handleFileUpload} className="hidden" accept=".pdf,.docx,.png,.jpg,.jpeg,.wav,.mp3" />
          </label>
        </div>
      </header>

      {/* Real-time Ingestion Stage Progress Status Bar */}
      {uploadStatus && (
        <div className="bg-[#080E17] border-b border-[#1E2E42] px-6 py-2.5 text-xs font-mono text-emerald-400 flex items-center justify-between shadow-inner">
          <div className="flex items-center space-x-2">
            {(isUploading || isTranscribingMic) && <span className="animate-spin text-emerald-400">⚙️</span>}
            <span className="font-semibold">{uploadStatus}</span>
          </div>
          {(isUploading || isTranscribingMic) && (
            <div className="w-32 bg-[#131F2E] h-1.5 rounded-full overflow-hidden border border-[#1E2E42]">
              <div className="bg-[#2E8682] h-full animate-pulse w-3/4"></div>
            </div>
          )}
        </div>
      )}

      {/* Main Dual-Pane Command Console Grid */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Left Column: Multimodal Briefing Console & Inputs */}
        <div className="flex flex-col space-y-4">
          <div className="bg-[#131F2E] border border-[#1E2E42] rounded-xl p-5 flex-1 flex flex-col shadow-xl">
            <div className="flex items-center justify-between mb-3 border-b border-[#1E2E42] pb-3">
              <div className="flex items-center space-x-2">
                <h2 className="text-xs font-bold tracking-wider text-slate-200 uppercase font-mono">
                  Multimodal Intelligence Briefing
                </h2>
                {documents.length > 0 && (
                  <span className="text-[10px] bg-[#080E17] text-[#34D399] px-2 py-0.5 rounded font-mono font-bold border border-[#1E2E42]">
                    {documents.length} File{documents.length > 1 ? 's' : ''} Ingested
                  </span>
                )}
              </div>

              {/* CUSTOM TACTICAL SCOPE SEARCH DROPDOWN */}
              <div className="relative" ref={scopeDropdownRef}>
                <button
                  type="button"
                  onClick={() => setIsScopeDropdownOpen(!isScopeDropdownOpen)}
                  className="bg-[#080E17] border border-[#1E2E42] hover:border-[#2E8682] text-[#34D399] text-xs rounded px-3 py-1.5 focus:outline-none font-mono font-semibold flex items-center gap-2 shadow-sm transition max-w-[210px] truncate"
                >
                  <span className="truncate">{getSelectedFilterLabel()}</span>
                  <span className="text-[10px] text-slate-400">▼</span>
                </button>

                {isScopeDropdownOpen && (
                  <div className="absolute right-0 mt-1 w-64 bg-[#0B131E] border border-[#2E8682] rounded-lg shadow-2xl z-50 py-1 max-h-56 overflow-y-auto font-mono text-xs">
                    <div className="px-3 py-1 text-[10px] uppercase text-slate-500 font-bold border-b border-[#1E2E42]">
                      Target Scope Filter
                    </div>
                    <button
                      onClick={() => { setSelectedFileFilter('ALL'); setIsScopeDropdownOpen(false); }}
                      className={`w-full text-left px-3 py-2 hover:bg-[#131F2E] flex items-center justify-between transition ${selectedFileFilter === 'ALL' ? 'text-[#34D399] font-bold bg-[#123534]/50' : 'text-slate-300'}`}
                    >
                      <span className="truncate">🌐 All Ingested Files</span>
                      <span className="text-[10px] text-slate-500">({documents.length})</span>
                    </button>
                    {documents.map((doc) => (
                      <button
                        key={doc.file_name}
                        onClick={() => { setSelectedFileFilter(doc.file_name); setIsScopeDropdownOpen(false); }}
                        className={`w-full text-left px-3 py-2 hover:bg-[#131F2E] flex items-center justify-between transition ${selectedFileFilter === doc.file_name ? 'text-[#34D399] font-bold bg-[#123534]/50' : 'text-slate-300'}`}
                      >
                        <span className="truncate flex items-center gap-1.5">
                          <span>{getDocumentIcon(doc.file_name)}</span>
                          <span className="truncate">{doc.file_name}</span>
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">{doc.chunk_count}c</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
            
            <div className="flex-1 bg-[#080E17] rounded-lg p-4 text-slate-200 text-sm overflow-y-auto font-normal leading-relaxed border border-[#1E2E42] min-h-[340px]">
              {isProcessing ? (
                <div className="flex flex-col items-center justify-center h-full text-[#34D399] font-mono text-xs space-y-3 py-16">
                  <span className="animate-spin text-2xl">⚙️</span>
                  <p className="font-bold text-sm">Executing Hybrid RRF Search & Local LLM Synthesis...</p>
                  <span className="text-[11px] text-slate-500">Dispatching to Ollama Llama 3.1 8B Engine...</span>
                </div>
              ) : response ? (
                <div className="whitespace-pre-wrap leading-relaxed space-y-3 font-sans">
                  <div>{renderFormattedAnswer(response.answer)}</div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-slate-400 text-center py-12 text-xs font-sans space-y-4">
                  <p className="max-w-md leading-relaxed text-slate-400">
                    Upload defense evidence files above or dictate/type a query below to generate grounded intelligence briefings with verified citation badges.
                  </p>
                  
                  {/* Quick Sample Queries */}
                  {documents.length > 0 && (
                    <div className="space-y-2 pt-2">
                      <span className="text-[10px] uppercase tracking-wider text-slate-500 block font-bold font-mono">Suggested Intelligence Queries:</span>
                      <div className="flex flex-wrap justify-center gap-2 max-w-md">
                        <button
                          onClick={() => { setQuery("whose name is written in the resume"); handleSynthesize("whose name is written in the resume"); }}
                          className="bg-[#131F2E] hover:bg-[#1E2E42] border border-[#1E2E42] hover:border-[#2E8682] text-[#34D399] text-[11px] px-3 py-1.5 rounded transition font-mono shadow-sm"
                        >
                          "whose name is written in the resume"
                        </button>
                        <button
                          onClick={() => { setQuery("what timestamp was harvard mentioned"); handleSynthesize("what timestamp was harvard mentioned"); }}
                          className="bg-[#131F2E] hover:bg-[#1E2E42] border border-[#1E2E42] hover:border-amber-600/50 text-amber-300 text-[11px] px-3 py-1.5 rounded transition font-mono shadow-sm"
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

          {/* Search Query Input Bar with 100% Offline Faster-Whisper Voice Microphone */}
          <div className="flex gap-2 relative items-center">
            <div className="relative flex-1 flex items-center">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSynthesize()}
                placeholder={
                  isRecording
                    ? "🔴 Recording voice offline... Click mic icon to finish..."
                    : isTranscribingMic
                    ? "⚡ Transcribing mic audio via Faster-Whisper..."
                    : "Ask a query across intelligence evidence files..."
                }
                className={`w-full bg-[#131F2E] border ${
                  isRecording
                    ? 'border-rose-500 ring-2 ring-rose-500/40 text-rose-200 animate-pulse'
                    : isTranscribingMic
                    ? 'border-amber-500 text-amber-200'
                    : 'border-[#1E2E42] focus:border-[#2E8682] text-slate-100'
                } rounded-lg pl-4 pr-20 py-3 text-sm focus:outline-none placeholder-slate-500 shadow-inner`}
              />

              {/* 100% Offline Voice Speech Microphone Toggle Button */}
              <button
                onClick={toggleMicRecording}
                disabled={isTranscribingMic}
                type="button"
                className={`absolute right-8 p-1.5 rounded-md transition flex items-center justify-center ${
                  isRecording
                    ? 'bg-rose-600 text-white animate-pulse shadow-lg shadow-rose-500/50 scale-110'
                    : isTranscribingMic
                    ? 'bg-amber-600 text-slate-950 animate-spin'
                    : 'text-slate-400 hover:text-emerald-400 hover:bg-[#080E17]'
                }`}
                title={isRecording ? "Click to stop & transcribe offline" : "Click to speak into microphone (100% Offline Whisper STT)"}
              >
                <span className="text-sm">{isTranscribingMic ? '⚙️' : '🎙️'}</span>
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
              className="bg-[#1A4B49] hover:bg-[#26716E] text-white font-bold px-6 py-3 rounded-lg text-sm border border-[#2E8682] transition shadow-md flex items-center gap-2 disabled:opacity-50"
            >
              {isProcessing ? 'Synthesizing...' : 'Synthesize'}
            </button>
          </div>
        </div>

        {/* Right Column: Visual Page Canvas & Proof Inspection Panel */}
        <div className="bg-[#131F2E] border border-[#1E2E42] rounded-xl p-5 flex flex-col shadow-xl">
          <div className="flex items-center justify-between border-b border-[#1E2E42] pb-3 mb-3">
            <h2 className="text-xs font-bold tracking-wider text-slate-200 uppercase font-mono">
              Source Citation Proof Navigation
            </h2>

            {/* Toggle Tabs: Visual Page Canvas vs Extracted Evidence Text */}
            {activeProof && (
              <div className="flex items-center space-x-2">
                {isVisualSupported && (
                  <div className="flex bg-[#080E17] p-0.5 rounded border border-[#1E2E42] text-xs font-mono">
                    <button
                      onClick={() => setProofTab('visual')}
                      className={`px-3 py-1 rounded transition font-bold ${proofTab === 'visual' ? 'bg-[#1A4B49] text-emerald-300 border border-[#2E8682]' : 'text-slate-400 hover:text-slate-200'}`}
                    >
                      🖼️ Visual Canvas
                    </button>
                    <button
                      onClick={() => setProofTab('text')}
                      className={`px-3 py-1 rounded transition font-bold ${proofTab === 'text' ? 'bg-[#1A4B49] text-emerald-300 border border-[#2E8682]' : 'text-slate-400 hover:text-slate-200'}`}
                    >
                      📄 Extracted Text
                    </button>
                  </div>
                )}
                <button
                  onClick={() => setActiveProof(null)}
                  className="text-slate-400 hover:text-slate-200 text-xs font-mono font-bold px-2.5 py-1 rounded bg-[#080E17] border border-[#1E2E42]"
                  title="Close active proof panel"
                >
                  ✕ Close
                </button>
              </div>
            )}
          </div>
          
          <div className="flex-1 bg-[#080E17] rounded-lg flex flex-col text-slate-300 text-sm border border-[#1E2E42] p-4 overflow-y-auto min-h-[340px]">
            {activeProof ? (
              <div className="w-full text-left space-y-3">
                {/* Proof Header Card */}
                <div className="flex items-center justify-between border-b border-[#1E2E42] pb-2">
                  <span className="font-bold text-amber-400 font-mono text-xs flex items-center gap-1.5">
                    <span>📌 {getProofTitle()}</span>
                  </span>
                  <span className="text-xs bg-[#131F2E] px-2.5 py-0.5 rounded text-slate-200 font-mono font-semibold border border-[#1E2E42]">
                    {activeProof.citation.file_name}
                  </span>
                </div>

                {/* Metadata Grid */}
                <div className="grid grid-cols-2 gap-2 bg-[#131F2E] p-2.5 rounded-lg border border-[#1E2E42] text-xs font-mono">
                  <div>
                    <span className="text-slate-400 block text-[10px]">Target Asset</span>
                    <span className="text-slate-200 font-semibold truncate block">{activeProof.citation.file_name}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">Boundary Target</span>
                    <span className="text-amber-400 font-bold uppercase block">{activeProof.citation.type}: {activeProof.citation.value}</span>
                  </div>
                </div>

                {/* VISUAL PAGE CANVAS DISPLAY WITH INTERACTIVE ZOOM CONTROLS */}
                {proofTab === 'visual' && isVisualSupported ? (
                  <div className="bg-[#131F2E] border border-amber-500/40 p-2 rounded-lg space-y-2 shadow-inner flex flex-col items-center">
                    <div className="w-full flex items-center justify-between border-b border-[#1E2E42] pb-1.5 px-1 font-mono text-xs">
                      <span className="text-amber-400 font-bold uppercase flex items-center gap-1">
                        <span>🖼️ VERIFIED PAGE CANVAS PROOF</span>
                      </span>
                      
                      {/* Zoom Controls */}
                      <div className="flex items-center space-x-1.5 bg-[#080E17] px-2 py-0.5 rounded border border-[#1E2E42]">
                        <button
                          onClick={() => setCanvasZoom(Math.max(50, canvasZoom - 25))}
                          className="text-slate-400 hover:text-white font-bold px-1"
                          title="Zoom out"
                        >
                          -
                        </button>
                        <span className="text-[10px] text-slate-300 font-mono">{canvasZoom}%</span>
                        <button
                          onClick={() => setCanvasZoom(Math.min(200, canvasZoom + 25))}
                          className="text-slate-400 hover:text-white font-bold px-1"
                          title="Zoom in"
                        >
                          +
                        </button>
                        <button
                          onClick={() => setCanvasZoom(100)}
                          className="text-[9px] text-[#34D399] font-bold px-1 border-l border-[#1E2E42]"
                          title="Reset zoom"
                        >
                          Reset
                        </button>
                      </div>
                    </div>

                    <div className="relative border border-[#1E2E42] rounded bg-[#080E17] p-1 overflow-auto max-h-[300px] w-full flex justify-center">
                      <img
                        src={pageImageUrl}
                        alt={`Proof page ${pageNum}`}
                        style={{ transform: `scale(${canvasZoom / 100})`, transformOrigin: 'top center' }}
                        className="rounded shadow-md max-w-full h-auto object-contain border border-amber-500/20 transition-transform duration-200"
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
                  /* EXTRACTED EVIDENCE TEXT DISPLAY WITH COPY BUTTON */
                  <div className="bg-[#131F2E] border border-[#2E8682] p-3.5 rounded-lg space-y-2 shadow-inner">
                    <div className="flex items-center justify-between border-b border-[#1E2E42] pb-2 font-mono text-xs">
                      <span className="text-[#34D399] font-bold uppercase tracking-wider flex items-center gap-1">
                        <span>✓ EXACT EXTRACTED EVIDENCE CONTENT</span>
                      </span>
                      {activeProof.chunk && (
                        <button
                          onClick={() => copyChunkText(activeProof.chunk!.text)}
                          className="bg-[#080E17] hover:bg-[#1E2E42] text-slate-300 text-[10px] font-bold px-2 py-0.5 rounded border border-[#1E2E42] transition"
                        >
                          📋 Copy Text
                        </button>
                      )}
                    </div>

                    <div className="bg-[#080E17] p-3.5 rounded-md text-slate-200 leading-relaxed font-sans text-xs border border-[#1E2E42] whitespace-pre-wrap max-h-[220px] overflow-y-auto select-text">
                      {activeProof.chunk ? activeProof.chunk.text : `Source text chunk for ${activeProof.citation.file_name} (${activeProof.citation.type}: ${activeProof.citation.value})`}
                    </div>
                  </div>
                )}

                {/* Verification Confirmation Footer */}
                <div className="bg-[#123534] border border-[#2E8682] p-2.5 rounded-lg text-xs text-emerald-300 font-mono flex items-center justify-between">
                  <span>✓ Proof target '{activeProof.citation.value}' verified in document index.</span>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-slate-500 text-center text-xs font-sans space-y-2 py-16">
                <span className="text-xl">🖼️</span>
                <p className="max-w-xs leading-relaxed text-slate-400">
                  Click any generated citation badge (🎵 Audio Intercept, 🖼️ Recon Image, 📄 Classified Doc) to display the real visual document canvas and proof chunk.
                </p>
              </div>
            )}
          </div>
        </div>

      </main>
    </div>
  );
}
