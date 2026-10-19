import chromadb

from app.config import settings


class ChromaStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
        self.collection = self.client.get_or_create_collection(
            name="alawyer_knowledge_base",
            metadata={"hnsw:space": "cosine", "description": "alawyer 法律知识库"},
        )

    def add_document(self, doc_id: int, doc_name: str, chunks: list, vectors: list):
        if not chunks:
            return
        n = len(self.collection.get(where={"doc_id": doc_id}).get("ids", []))
        if n >= len(chunks):
            return
        self.delete_document(doc_id)
        ids = [f"doc{doc_id}-chunk{i}" for i in range(len(chunks))]
        metadatas = [
            {"doc_id": doc_id, "doc_name": doc_name, "chunk_index": i} for i in range(len(chunks))
        ]
        self.collection.add(ids=ids, documents=chunks, metadatas=metadatas, embeddings=vectors)

    def delete_document(self, doc_id: int):
        self.collection.delete(where={"doc_id": doc_id})

    def query(self, embedding: list, top_k: int = 8) -> list:
        res = self.collection.query(query_embeddings=[embedding], n_results=min(top_k, max(self.count(), 1)))
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        distances = (res.get("distances") or [[]])[0]
        items = []
        for i in range(len(ids)):
            items.append(
                {
                    "doc_id": metas[i]["doc_id"],
                    "doc_name": metas[i]["doc_name"],
                    "text": docs[i],
                    "distance": distances[i] if i < len(distances) else 1.0,
                }
            )
        return items

    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception:
            return 0


chroma_store = ChromaStore()