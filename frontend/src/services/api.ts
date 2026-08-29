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

export interface DocumentInfo {
  file_name: string;
  media_type: string;
  case_id: string;
  chunk_count: number;
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

export async function fetchIngestedDocuments(): Promise<DocumentInfo[]> {
  try {
    const res = await axios.get(`${API_BASE_URL}/api/documents`);
    return res.data.documents || [];
  } catch (err) {
    console.warn('Fetch documents warning:', err);
    return [];
  }
}

export async function resetDatabase() {
  const res = await axios.delete(`${API_BASE_URL}/api/reset`);
  return res.data;
}

export async function submitIntelligenceQuery(
  query: string,
  fileFilter: string = 'ALL',
  caseId: string = 'default_case',
  topK: number = 5
): Promise<QueryResponse> {
  const res = await axios.post(`${API_BASE_URL}/api/query`, {
    query,
    file_filter: fileFilter,
    case_id: caseId,
    top_k: topK
  });
  return res.data;
}

export async function uploadEvidenceFile(file: File, caseId: string = 'default_case') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('case_id', caseId);

  const res = await axios.post(`${API_BASE_URL}/api/ingest`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return res.data;
}
