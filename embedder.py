# embedder.py
import os
import logging
from google.oauth2 import service_account
from abc import ABC, abstractmethod
from google.auth.transport.requests import Request
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Load environment variables from Streamlit secrets
PROJECT_ID = st.secrets["GCP_PROJECT_ID"]
REGION = st.secrets["GCP_REGION"]
MODEL = st.secrets["GCP_MODEL"]

if not all([PROJECT_ID, REGION, MODEL]):
    raise ValueError("GCP_PROJECT_ID, GCP_REGION, and GCP_MODEL environment variables must be set.")

# Initialize Vertex AI with project details
aiplatform.init(project=PROJECT_ID, location=REGION)

class Embedder(ABC):
    @abstractmethod
    def embed(self, text: str) -> list:
        pass

class GCPVertexAIEmbedder(Embedder):
    def __init__(self):
        log.info(f"Initializing GCPVertexAIEmbedder with model: {MODEL}, project: {PROJECT_ID}, region: {REGION}")
        self.model = TextEmbeddingModel.from_pretrained(MODEL)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=10, min=10, max=320),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(log, logging.WARNING)
    )
    def embed(self, text: str) -> list:
        """
        Creates embedding for the given text.
        
        Args:
            text (str): raw text to embed

        Returns:
            list: embedding vector
        """
        text_embedding_prep = [TextEmbeddingInput(task_type="SEMANTIC_SIMILARITY", text=text)]
        embedding = self.model.get_embeddings(text_embedding_prep)
        return embedding[0].values

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=10, min=10, max=320),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(log, logging.WARNING)
    )
    def embed_batch(self, texts: list) -> list:
        """
        Creates embeddings for a batch of texts.
        
        Args:
            texts (list): list of raw texts to embed

        Returns:
            list: list of embedding vectors
        """
        text_embedding_prep = [TextEmbeddingInput(task_type="SEMANTIC_SIMILARITY", text=text) for text in texts]
        embeddings = self.model.get_embeddings(text_embedding_prep)
        return [embedding.values for embedding in embeddings]

    async def get_google_auth_headers(self):
        credentials_info = st.secrets["gcp_service_account"]
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        credentials.refresh(Request())
        return {"Authorization": f"Bearer {credentials.token}"}
