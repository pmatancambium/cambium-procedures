# vectordb.py
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pymongo import MongoClient, UpdateOne, errors


class VectorDB(ABC):
    @abstractmethod
    def store_embedding(self, embedding: list, metadata: dict):
        pass

    @abstractmethod
    def search(
        self,
        query_embedding: list,
        num_candidates: int = 100,
        limit: int = 10,
        threshold: float = 0.9,
    ) -> list:
        pass

    @abstractmethod
    def document_exists(self, filename: str) -> bool:
        pass

    @abstractmethod
    def fetch_all_chunks(self, filename: str) -> list:
        pass


class MongoVectorDB(VectorDB):
    def __init__(self, connection_string: str, db_name: str, collection_name: str):
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        self.unanswered_collection = self.db["unanswered_questions"]
        self.ensure_indexes()

    def ensure_indexes(self):
        try:
            self.collection.drop_index("unique_chunk_identifier_1")
        except errors.OperationFailure as e:
            if "index not found with name" not in str(e):
                raise e
        self.collection.create_index("unique_chunk_identifier", unique=True)

    def store_embedding(self, embedding: list, metadata: dict):
        metadata["embedding"] = embedding
        unique_chunk_identifier = f"{metadata['filename']}-{metadata.get('heading', '')}-{len(metadata['text'])}"
        metadata["unique_chunk_identifier"] = unique_chunk_identifier
        self.collection.update_one(
            {"unique_chunk_identifier": unique_chunk_identifier},
            {"$set": metadata},
            upsert=True,
        )

    def search(
        self,
        query_embedding: list,
        num_candidates: int = 100,
        limit: int = 10,
        threshold: float = 0.9,
    ) -> list:
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": num_candidates,
                    "limit": limit,
                }
            },
            {
                "$project": {
                    "filename": 1,
                    "heading": 1,
                    "text": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
            {"$match": {"score": {"$gte": threshold}}},
        ]
        results = list(self.collection.aggregate(pipeline))
        formatted_results = [{"document": result} for result in results]
        return formatted_results

    def fetch_all_chunks(self, filename: str) -> list:
        return list(self.collection.find({"filename": filename}))

    def document_exists(self, unique_chunk_identifier: str) -> bool:
        return (
            self.collection.find_one(
                {"unique_chunk_identifier": unique_chunk_identifier}
            )
            is not None
        )

    def store_unanswered_question(self, question: str):
        self.unanswered_collection.insert_one(
            {"question": question, "timestamp": datetime.now(timezone.utc)}
        )

    def delete_unanswered_question(self, question_id: str):
        result = self.unanswered_collection.delete_one({"_id": question_id})
        return result.deleted_count > 0
