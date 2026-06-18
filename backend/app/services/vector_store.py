from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from app.core.config import settings


class VectorStore:
    def __init__(self) -> None:
        self.client = QdrantClient(url=settings.qdrant_url)

    def ensure_collection(self) -> None:
        collections = self.client.get_collections().collections
        if any(collection.name == settings.qdrant_collection for collection in collections):
            return
        self.client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
        )

    def upsert(self, points: list[PointStruct]) -> None:
        self.ensure_collection()
        self.client.upsert(collection_name=settings.qdrant_collection, points=points)

    def search(self, vector: list[float], limit: int) -> list:
        self.ensure_collection()
        return self.client.search(
            collection_name=settings.qdrant_collection,
            query_vector=vector,
            limit=limit,
            with_payload=True,
        )
