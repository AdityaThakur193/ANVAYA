import React, { useState } from 'react';

export default function App() {
  const [query, setQuery] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

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
        <div className="text-xs font-medium text-slate-400">
          SIH25231 / SIH26154 • NTRO (Prime Minister's Office)
        </div>
      </header>

      {/* Main Dual-Pane Console Grid */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Left Column: Grounded Intelligence Response & Input */}
        <div className="flex flex-col space-y-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 flex-1 flex flex-col shadow-lg">
            <h2 className="text-sm font-bold tracking-wide text-slate-300 mb-3 uppercase flex items-center justify-between">
              <span>Grounded Intelligence Synthesis</span>
              <span className="text-xs text-slate-500 font-mono">Llama 3.2 3B GGUF</span>
            </h2>
            <div className="flex-1 bg-slate-950/60 rounded-lg p-4 text-slate-300 text-sm overflow-y-auto font-normal leading-relaxed border border-slate-800/50">
              Select or ingest evidence files (PDFs, Images, Audio) to begin 100% offline grounded semantic retrieval...
            </div>
          </div>

          {/* Search Query Input */}
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a plain-language query across evidence files..."
              className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-emerald-500 text-slate-100 placeholder-slate-500"
            />
            <button
              onClick={() => setIsProcessing(true)}
              className="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-6 py-3 rounded-lg text-sm transition shadow-md flex items-center gap-2"
            >
              Synthesize
            </button>
          </div>
        </div>

        {/* Right Column: Dual Citation Navigation Panel */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 flex flex-col shadow-lg">
          <h2 className="text-sm font-bold tracking-wide text-slate-300 mb-3 uppercase flex items-center justify-between">
            <span>Interactive Source Citation Navigation</span>
            <span className="text-xs text-slate-500 font-mono">PDF & Audio Viewer</span>
          </h2>
          <div className="flex-1 bg-slate-950/60 rounded-lg flex items-center justify-center text-slate-500 text-sm border border-slate-800/50 p-6 text-center">
            Click any generated citation [Page N / Timestamp] in the briefing to display original document proof
          </div>
        </div>

      </main>
    </div>
  );
}
