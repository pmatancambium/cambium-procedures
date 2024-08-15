# search_service.py
from embedder import Embedder
from vectordb import VectorDB


class SearchService:
    def __init__(self, embedder: Embedder, vector_db: VectorDB):
        self.embedder = embedder
        self.vector_db = vector_db

    def search(
        self,
        query: str,
        num_candidates: int = 100,
        limit: int = 10,
        threshold: float = 0.9,
    ) -> list:
        query_embedding = self.embedder.embed(query)
        results = self.vector_db.search(
            query_embedding,
            num_candidates=num_candidates,
            limit=limit,
            threshold=threshold,
        )
        if not results:
            self.vector_db.store_unanswered_question(query)
            return []

        # Aggregate results by filename
        aggregated_results = {}

        for result in results:
            filename = result["document"]["filename"]
            chunk_text = result["document"]["text"]
            heading = result["document"].get("heading", "")

            if filename not in aggregated_results:
                aggregated_results[filename] = {
                    "filename": filename,
                    "chunks": [],
                    "highlights": [],
                }

            if heading:
                chunk_text = f"{heading}\n{chunk_text}"

            aggregated_results[filename]["chunks"].append(chunk_text)
            aggregated_results[filename]["highlights"].append(
                result["document"]["text"]
            )

        # Fetch all chunks for each document found
        combined_results = []
        for filename, doc in aggregated_results.items():
            all_chunks = self.vector_db.fetch_all_chunks(filename)

            # Sort chunks by heading, handling cases where heading might be None
            all_chunks.sort(key=lambda x: x.get("heading", "") or "")

            full_text = []
            highlights = []
            for chunk in all_chunks:
                chunk_text = chunk["text"]
                if chunk.get("heading"):
                    chunk_text = f"{chunk['heading']}\n{chunk_text}"
                full_text.append(chunk_text)

                if chunk["text"] in doc["highlights"]:
                    highlights.append(chunk_text)

            # Highlight the found chunks
            text_with_highlights = "\n\n".join(full_text)
            for highlight in highlights:
                text_with_highlights = text_with_highlights.replace(
                    highlight,
                    f'<span style="background-color: yellow;">{highlight}</span>',
                )

            combined_results.append(
                {
                    "filename": filename,
                    "text": text_with_highlights,
                    "highlights": highlights,
                }
            )

        return combined_results
