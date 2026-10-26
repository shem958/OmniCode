import os
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_MODE = os.getenv("QDRANT_MODE", "local").lower()

class VectorStore:
    def __init__(self, collection_name: str = "codebase"):
        self.collection_name = collection_name
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.use_fallback = False
        
        # Local JSON cache for when OpenAI API keys fail
        self.cache_dir = os.path.join(os.path.dirname(__file__), "..", "qdrant_storage")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.fallback_file = os.path.join(self.cache_dir, "fallback_chunks.json")
        
        # Initialize Qdrant client based on configuration mode
        if QDRANT_MODE == "local":
            self.qdrant_client = QdrantClient(path=self.cache_dir)
        elif QDRANT_MODE == "memory":
            self.qdrant_client = QdrantClient(":memory:")
        else:
            self.qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
            
        self.embedding_model = "text-embedding-3-small"
        self.vector_dim = 1536
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_dim,
                        distance=models.Distance.COSINE
                    )
                )
        except Exception as e:
            print(f"[VectorStore] Qdrant connection issue, will use local JSON storage: {e}")
            self.use_fallback = True

    def _get_embedding(self, text: str) -> List[float]:
        if self.use_fallback:
            raise Exception("Using local offline fallback mode")
            
        try:
            clean_text = text.replace("\n", " ").strip()
            if not clean_text:
                return [0.0] * self.vector_dim
                
            response = self.openai_client.embeddings.create(
                input=[clean_text],
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            # If 429 quota exceeded, trigger fallback
            if "quota" in str(e).lower() or "billing" in str(e).lower() or "429" in str(e).lower():
                print("[VectorStore] OpenAI API quota exceeded (429). Switching to Local Offline Fallback Mode.")
                self.use_fallback = True
            raise e

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        # Save to local JSON backup cache in all cases
        self._save_to_local_cache(chunks)
        
        points = []
        for i, chunk in enumerate(chunks):
            text_to_embed = f"File: {chunk['file_path']}\nSymbol: {chunk['name']}\nType: {chunk['type']}\nContent:\n{chunk['content']}"
            
            try:
                vector = self._get_embedding(text_to_embed)
                point_id = hash(f"{chunk['file_path']}_{chunk['name']}_{chunk['start_line']}") & 0xFFFFFFFF
                
                points.append(models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=chunk
                ))
            except Exception as e:
                # If fallback mode is triggered, stop trying to call OpenAI for remaining chunks
                if self.use_fallback:
                    break
                print(f"[VectorStore] Skipping Qdrant upload for {chunk['name']} in {chunk['file_path']}: {e}")
                
        if points and not self.use_fallback:
            try:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                print(f"[VectorStore] Successfully indexed {len(points)} chunks into Qdrant collection '{self.collection_name}'.")
            except Exception as e:
                print(f"[VectorStore] Failed to upsert to Qdrant, using local cache: {e}")
                self.use_fallback = True

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        # If fallback is active, perform offline keyword-overlap matching
        if self.use_fallback:
            print("[VectorStore] Performing local keyword search fallback...")
            return self._local_keyword_search(query, limit)
            
        try:
            query_vector = self._get_embedding(query)
            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit
            )
            
            hits = []
            for result in results:
                payload = result.payload
                payload["score"] = result.score
                hits.append(payload)
            return hits
        except Exception as e:
            print(f"[VectorStore] Search failed ({e}). Falling back to keyword search.")
            self.use_fallback = True
            return self._local_keyword_search(query, limit)

    def clear(self):
        try:
            self.qdrant_client.delete_collection(self.collection_name)
            self._ensure_collection()
        except Exception:
            pass
            
        # Clean local JSON cache
        if os.path.exists(self.fallback_file):
            try:
                os.remove(self.fallback_file)
            except Exception:
                pass

    def _save_to_local_cache(self, chunks: List[Dict[str, Any]]):
        existing = []
        if os.path.exists(self.fallback_file):
            try:
                with open(self.fallback_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []
                
        # Append and de-duplicate based on path + symbol + lines
        seen = {f"{c['file_path']}_{c['name']}_{c['start_line']}" for c in existing}
        for chunk in chunks:
            key = f"{chunk['file_path']}_{chunk['name']}_{chunk['start_line']}"
            if key not in seen:
                existing.append(chunk)
                seen.add(key)
                
        try:
            with open(self.fallback_file, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
            print(f"[VectorStore] Cached {len(chunks)} chunks locally in {self.fallback_file}")
        except Exception as e:
            print(f"[VectorStore] Failed to write fallback cache: {e}")

    def _local_keyword_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if not os.path.exists(self.fallback_file):
            return []
            
        try:
            with open(self.fallback_file, "r", encoding="utf-8") as f:
                chunks = json.load(f)
        except Exception:
            return []
            
        query_words = set(query.lower().split())
        scored_chunks = []
        
        for chunk in chunks:
            content_lower = chunk.get("content", "").lower()
            file_path_lower = chunk.get("file_path", "").lower()
            name_lower = chunk.get("name", "").lower()
            
            # Simple keyword overlap scoring
            score = sum(1.0 for word in query_words if word in content_lower)
            
            # Boost if search terms exist in path or function name
            for word in query_words:
                if word in file_path_lower:
                    score += 3.0
                if word in name_lower:
                    score += 5.0
                    
            if score > 0:
                chunk_copy = dict(chunk)
                chunk_copy["score"] = score
                scored_chunks.append((score, chunk_copy))
                
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_chunks[:limit]]
