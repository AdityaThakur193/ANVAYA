import os
import json
import sqlite3
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any

class VectorStoreManager:
    """
    ANVAYA 1-for-All Hybrid Vector & Lexical Store
    Combines ChromaDB dense vector search (BAAI/bge-small-en-v1.5) with
    SQLite FTS5 BM25 keyword search using Reciprocal Rank Fusion (RRF k=60).
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
        self._init_fts5()

    def _init_fts5(self):
        """Creates SQLite FTS5 Virtual Table for exact keyword search."""
        with self.conn:
            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS evidence_fts USING fts5(
                    chunk_id UNINDEXED,
                    file_name UNINDEXED,
                    media_type UNINDEXED,
                    page_number UNINDEXED,
                    timestamp_label UNINDEXED,
                    bbox UNINDEXED,
                    content,
                    tokenize='porter unicode61'
                );
            """)

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        """Indexes multimodal chunks into ChromaDB vector store and SQLite FTS5 keyword index."""
        if not chunks:
            return

        documents = []
        metadatas = []
        ids = []

        with self.conn:
            for idx, chunk in enumerate(chunks):
                cid = f"{chunk['file_name']}_chunk_{idx}_{chunk.get('page_number', 1)}"
                content = chunk["text"]
                media_type = chunk.get("media_type", "pdf")
                page_no = chunk.get("page_number", 1)
                time_label = chunk.get("timestamp_label", "")
                bbox_str = json.dumps(chunk.get("bbox", [0, 0, 0, 0]))

                documents.append(content)
                ids.append(cid)
                metadatas.append({
                    "file_name": chunk["file_name"],
                    "media_type": media_type,
                    "page_number": page_no,
                    "timestamp_label": time_label,
                    "bbox": bbox_str
                })

                # Insert into SQLite FTS5 keyword index (Replace on duplicate cid)
                self.conn.execute("""
                    INSERT OR REPLACE INTO evidence_fts(chunk_id, file_name, media_type, page_number, timestamp_label, bbox, content)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (cid, chunk["file_name"], media_type, page_no, time_label, bbox_str, content))

        # Upsert into ChromaDB
        self.collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        print(f"[OK] Indexed {len(chunks)} chunks into ChromaDB & SQLite FTS5")

    def hybrid_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Executes Dense Vector Search + BM25 Sparse Search and merges results
        using Reciprocal Rank Fusion (RRF k=60).
        """
        # 1. Dense Vector Search via ChromaDB
        dense_res = self.collection.query(
            query_texts=[query],
            n_results=min(20, max(self.collection.count(), 1))
        )

        dense_chunks = []
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
                    "file_name": meta["file_name"],
                    "media_type": meta["media_type"],
                    "page_number": meta["page_number"],
                    "timestamp_label": meta.get("timestamp_label", ""),
                    "bbox": bbox_val,
                    "text": dense_res["documents"][0][i]
                })

        # 2. Sparse Lexical Search via SQLite FTS5
        clean_query = ' '.join([f'"{w}"' for w in query.split() if w.isalnum()])
        sparse_chunks = []

        if clean_query:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT chunk_id, file_name, media_type, page_number, timestamp_label, bbox, content, bm25(evidence_fts) AS score
                    FROM evidence_fts
                    WHERE evidence_fts MATCH ?
                    ORDER BY score
                    LIMIT 20;
                """, (clean_query,))
                
                for row in cursor.fetchall():
                    bbox_val = [0, 0, 0, 0]
                    if row["bbox"]:
                        try:
                            bbox_val = json.loads(row["bbox"])
                        except Exception:
                            pass

                    sparse_chunks.append({
                        "chunk_id": row["chunk_id"],
                        "file_name": row["file_name"],
                        "media_type": row["media_type"],
                        "page_number": row["page_number"],
                        "timestamp_label": row["timestamp_label"],
                        "bbox": bbox_val,
                        "text": row["content"]
                    })
            except Exception as err:
                print(f"[WARN] BM25 FTS5 search notice: {err}")

        # 3. Reciprocal Rank Fusion (RRF)
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

        # Sort by final accumulated RRF Score descending
        sorted_chunks = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        final_results = []
        for cid, score in sorted_chunks[:top_k]:
            item = chunk_map[cid]
            item["rrf_score"] = round(score, 5)
            final_results.append(item)

        return final_results
