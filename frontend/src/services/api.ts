import axios from 'axios';

const API_BASE_URL = 'http://localhost:8080';

export interface Citation {
  file_name: string;
  type: 'page' | 'time';
  value: string;
}

export interface RetrievedChunk {
  chunk_id: string;
  file_name: string;
  media_type: string;
  page_number: number;
  timestamp_label?: string;
  text: string;
  rrf_score?: number;
}

export interface QueryResponse {
  query: string;
  answer: string;
  citations: Citation[];
  retrieved_chunks: RetrievedChunk[];
}

export async function checkBackendHealth() {
  try {
    const res = await axios.get(`${API_BASE_URL}/`);
    return res.data;
  } catch (err) {
    console.warn('Backend health check warning:', err);
    return null;
  }
}

export async function submitIntelligenceQuery(query: string, topK: number = 5): Promise<QueryResponse> {
  const res = await axios.post(`${API_BASE_URL}/api/query`, {
    query,
    top_k: topK
  });
  return res.data;
}

export async function uploadEvidenceFile(file: File) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await axios.post(`${API_BASE_URL}/api/ingest`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return res.data;
}
