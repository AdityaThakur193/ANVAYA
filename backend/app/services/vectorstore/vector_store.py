import os
import re
import json
import sqlite3
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional

class VectorStoreManager:
    """
    ANVAYA Hardened Multi-Case Hybrid Vector & Lexical Store
    - Corrected ChromaDB $and metadata filter syntax.
    - Corrected SQLite FTS5 UNINDEXED column filtering.
    """
    def __init__(self, data_dir: str = "data", rrf_k: int = 60):
        self.data_dir = data_dir
        self.rrf_k = rrf_k
        os.makedirs(self.data_dir, exist_ok=True)

        # 1. Initialize BAAI/bge-small-en-v1.5 embedding function (100% offline, 133MB RAM)
        print("[VECTOR] Initializing BAAI/bge-small-en-v1.5 local embedding model...")
        self.bge_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-small-en-v1.5"
        )

        # 2. Initialize ChromaDB embedded vector database
        chroma_path = os.path.join(self.data_dir, "chroma_db")
        self.chroma_client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.chroma_client.get_or_create_collection(
            name="anvaya_unified_index",
            embedding_function=self.bge_ef
        )

        # 3. Initialize SQLite FTS5 for BM25 Keyword Search
        self.db_path = os.path.join(self.data_dir, "anvaya_fts.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA busy_timeout=5000;")
        self._init_fts5()

    def _init_fts5(self):
        """Creates SQLite FTS5 Virtual Table."""
        with self.conn:
            try:
                self.conn.execute("SELECT case_id FROM evidence_fts LIMIT 1;")
            except Exception:
                self.conn.execute("DROP TABLE IF EXISTS evidence_fts;")

            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS evidence_fts USING fts5(
                    chunk_id UNINDEXED,
                    case_id UNINDEXED,
                    file_name UNINDEXED,
                    media_type UNINDEXED,
                    page_number UNINDEXED,
                    timestamp_label UNINDEXED,
                    bbox UNINDEXED,
                    content,
                    tokenize='porter unicode61'
                );
            """)

    def purge_all_data(self):
        """100% Data Purge: Wipes ChromaDB vector collection and SQLite FTS index."""
        try:
            self.chroma_client.delete_collection("anvaya_unified_index")
        except Exception:
            pass

        self.collection = self.chroma_client.get_or_create_collection(
            name="anvaya_unified_index",
            embedding_function=self.bge_ef
        )

        with self.conn:
            self.conn.execute("DROP TABLE IF EXISTS evidence_fts;")

        self._init_fts5()
        print("[VECTOR] Purged 100% of all vector and FTS database entries cleanly.")

    def delete_file_index(self, file_name: str, case_id: str = "default_case"):
        """Deletes prior index entries for a file in a case to prevent orphaned vector bloat."""
        if not file_name:
            return
        try:
            self.collection.delete(where={"file_name": file_name})
            with self.conn:
                self.conn.execute("DELETE FROM evidence_fts WHERE file_name = ?;", (file_name,))
            print(f"[VECTOR] Purged prior entries for '{file_name}' in case '{case_id}'")
        except Exception as err:
            print(f"[WARN] Index cleanup note: {err}")

    def get_indexed_documents(self, case_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns list of all unique ingested files and metadata."""
        docs = []
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT file_name, media_type, case_id, COUNT(*) as chunk_count
                FROM evidence_fts
                GROUP BY file_name;
            """)
            
            for row in cursor.fetchall():
                docs.append({
                    "file_name": row["file_name"],
                    "media_type": row["media_type"],
                    "case_id": row["case_id"],
                    "chunk_count": row["chunk_count"]
                })
        except Exception as err:
            print(f"[WARN] Fetch documents note: {err}")
        return docs

    def add_chunks(self, chunks: List[Dict[str, Any]], case_id: str = "default_case", purge_existing: bool = True):
        """Indexes multimodal chunks into ChromaDB vector store and SQLite FTS5."""
        if not chunks:
            return

        first_filename = chunks[0].get("file_name", "")
        if purge_existing and first_filename:
            self.delete_file_index(first_filename, case_id=case_id)

        documents = []
        metadatas = []
        ids = []

        with self.conn:
            for idx, chunk in enumerate(chunks):
                file_name = chunk.get("file_name", "unknown")
                cid = f"{file_name}_chunk_{idx}_{chunk.get('page_number', 1)}"
                
                content = str(chunk.get("text", "")).replace("\x00", "").strip()
                if not content:
                    continue

                media_type = str(chunk.get("media_type") or "pdf")
                page_no = int(chunk.get("page_number") or 1)
                time_label = str(chunk.get("timestamp_label") or "")
                bbox_str = json.dumps(chunk.get("bbox") if chunk.get("bbox") else [0, 0, 0, 0])

                documents.append(content)
                ids.append(cid)
                metadatas.append({
                    "case_id": case_id,
                    "file_name": file_name,
                    "media_type": media_type,
                    "page_number": page_no,
                    "timestamp_label": time_label,
                    "bbox": bbox_str
                })

                self.conn.execute("""
                    INSERT OR REPLACE INTO evidence_fts(chunk_id, case_id, file_name, media_type, page_number, timestamp_label, bbox, content)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (cid, case_id, file_name, media_type, page_no, time_label, bbox_str, content))

        if documents:
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"[OK] Indexed {len(documents)} hardened chunks into ChromaDB & SQLite FTS5")

    def hybrid_search(
        self,
        query: str,
        case_id: Optional[str] = None,
        file_filter: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Executes Dense Vector + Sparse BM25 Search with strict Document Scoping.
        """
        clean_raw_query = str(query or "").replace("\x00", "").strip()
        if not clean_raw_query:
            return []

        # Construct ChromaDB metadata filter with valid operator syntax
        where_conditions = []
        if case_id and case_id != "ALL" and case_id != "default_case":
            where_conditions.append({"case_id": case_id})
        if file_filter and file_filter != "ALL":
            where_conditions.append({"file_name": file_filter})

        if len(where_conditions) == 1:
            where_clause = where_conditions[0]
        elif len(where_conditions) > 1:
            where_clause = {"$and": where_conditions}
        else:
            where_clause = None

        # 1. Dense Vector Search via ChromaDB
        dense_chunks = []
        try:
            query_kwargs = {"query_texts": [clean_raw_query], "n_results": min(25, max(self.collection.count(), 1))}
            if where_clause:
                query_kwargs["where"] = where_clause

            dense_res = self.collection.query(**query_kwargs)

            if dense_res["ids"] and dense_res["ids"][0]:
                for i in range(len(dense_res["ids"][0])):
                    meta = dense_res["metadatas"][0][i]
                    bbox_val = [0, 0, 0, 0]
                    if "bbox" in meta:
                        try:
                            bbox_val = json.loads(meta["bbox"])
                        except Exception:
                            pass

                    dense_chunks.append({
                        "chunk_id": dense_res["ids"][0][i],
                        "case_id": meta.get("case_id", "default_case"),
                        "file_name": meta.get("file_name", "unknown"),
                        "media_type": meta.get("media_type", "pdf"),
                        "page_number": meta.get("page_number", 1),
                        "timestamp_label": meta.get("timestamp_label", ""),
                        "bbox": bbox_val,
                        "text": dense_res["documents"][0][i]
                    })
        except Exception as err:
            print(f"[WARN] Dense vector query note: {err}")

        # 2. Sparse Lexical Search via SQLite FTS5
        clean_words = [w.strip() for w in re.findall(r'\w+', clean_raw_query) if w.strip()]
        clean_fts_query = ' OR '.join([f'"{w}"' for w in clean_words if len(w) > 2]) or ' '.join([f'"{w}"' for w in clean_words])
        sparse_chunks = []

        if clean_fts_query:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT chunk_id, case_id, file_name, media_type, page_number, timestamp_label, bbox, content, bm25(evidence_fts) AS score
                    FROM evidence_fts
                    WHERE evidence_fts MATCH ?
                    ORDER BY score
                    LIMIT 30;
                """, (clean_fts_query,))
                
                for row in cursor.fetchall():
                    f_name = row["file_name"]
                    c_id = row["case_id"]

                    # Apply Python-level strict filter matching for FTS5 UNINDEXED columns
                    if file_filter and file_filter != "ALL" and f_name != file_filter:
                        continue
                    if case_id and case_id != "ALL" and case_id != "default_case" and c_id != case_id:
                        continue

                    bbox_val = [0, 0, 0, 0]
                    if row["bbox"]:
                        try:
                            bbox_val = json.loads(row["bbox"])
                        except Exception:
                            pass

                    sparse_chunks.append({
                        "chunk_id": row["chunk_id"],
                        "case_id": row["case_id"],
                        "file_name": row["file_name"],
                        "media_type": row["media_type"],
                        "page_number": row["page_number"],
                        "timestamp_label": row["timestamp_label"],
                        "bbox": bbox_val,
                        "text": row["content"]
                    })
            except Exception as err:
                print(f"[WARN] BM25 FTS5 search note: {err}")

        # 3. Reciprocal Rank Fusion (RRF k=60)
        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Dict[str, Any]] = {}

        for rank, item in enumerate(dense_chunks, start=1):
            cid = item["chunk_id"]
            chunk_map[cid] = item
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.rrf_k + rank))

        for rank, item in enumerate(sparse_chunks, start=1):
            cid = item["chunk_id"]
            chunk_map[cid] = item
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.rrf_k + rank))

        sorted_chunks = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        final_results = []
        for cid, score in sorted_chunks[:top_k]:
            item = chunk_map[cid]
            item["rrf_score"] = round(score, 5)
            final_results.append(item)

        return final_results
