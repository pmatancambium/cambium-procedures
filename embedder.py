# embedder.py
import logging
from google.oauth2 import service_account
from abc import ABC, abstractmethod
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
import streamlit as st
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.cloud import aiplatform
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Load environment variables from Streamlit secrets
PROJECT_ID = st.secrets["GCP_PROJECT_ID"]
REGION = st.secrets["GCP_REGION"]
MODEL = st.secrets["GCP_MODEL"]

if not all([PROJECT_ID, REGION, MODEL]):
    raise ValueError("GCP_PROJECT_ID, GCP_REGION, and GCP_MODEL must be set in .streamlit/secrets.toml")

class Embedder(ABC):
    @abstractmethod
    def embed(self, text: str) -> list:
        pass

class GCPVertexAIEmbedder(Embedder):
    def __init__(self):
        log.info(f"Initializing GCPVertexAIEmbedder with model: {MODEL}, project: {PROJECT_ID}, region: {REGION}")
        
        # Create credentials from the service account info in secrets
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        
        # Initialize Vertex AI with the credentials
        aiplatform.init(project=PROJECT_ID, location=REGION, credentials=credentials)
        
        # Initialize the model with the credentials
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
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(Request())
        return {"Authorization": f"Bearer {credentials.token}"}
