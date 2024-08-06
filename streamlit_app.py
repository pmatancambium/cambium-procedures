# streamlit_app.py
import hmac
import streamlit as st
from dotenv import load_dotenv
from data_source import FileDataSource
from data_parser import ServiceCallParser, ProcedureParser
from embedder import GCPVertexAIEmbedder
from vectordb import MongoVectorDB
from search_service import SearchService
import chardet
import os
import re
from pymongo.errors import DuplicateKeyError
import streamlit.components.v1 as components
from google.oauth2 import service_account

load_dotenv()

credentials = service_account.Credentials.from_service_account_info(st.secrets["gcs_connections"])

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False

if not check_password():
    st.stop()  # Do not continue if check_password is not True.

# Main Streamlit app starts here
logo_path = "logo.png"
st.set_page_config(page_title="Service Call Search Engine", layout="wide")

uploaded_file = st.sidebar.file_uploader("Choose a file", type=["txt", "docx"])
skip_existing = st.sidebar.checkbox("Skip existing documents", value=True)

gcp_project = os.getenv("GCP_PROJECT_ID")
gcp_region = os.getenv("GCP_REGION")
gcp_model = os.getenv("GCP_MODEL")
mongo_connection_string = os.getenv("MONGO_CONNECTION_STRING")
mongo_db_name = "cambium-procedures"
mongo_collection_name = "procedures"

if uploaded_file:
    st.info("File uploaded successfully!")
    if st.button("Load and Process Data"):
        with st.spinner("Processing data..."):
            file_path = uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            if file_path.endswith('.txt'):
                raw_data = uploaded_file.read()
                result = chardet.detect(raw_data)
                encoding = result["encoding"]
                text_input = raw_data.decode(encoding)
                parser = ServiceCallParser()
            else:
                parser = ProcedureParser()

            embedder = GCPVertexAIEmbedder()
            vector_db = MongoVectorDB(
                connection_string=mongo_connection_string,
                db_name=mongo_db_name,
                collection_name=mongo_collection_name,
            )

            parsed_data = parser.parse(file_path)

            for chunk in parsed_data:
                text = chunk['text']
                filename = chunk['filename']
                unique_chunk_identifier = f"{filename}-{chunk.get('heading', '')}-{len(text)}"

                if skip_existing and vector_db.document_exists(unique_chunk_identifier):
                    st.warning(f"Chunk from {filename} already exists. Skipping.")
                    continue

                embeddings = embedder.embed_batch([text])
                for embedding in embeddings:
                    try:
                        chunk['unique_chunk_identifier'] = unique_chunk_identifier
                        vector_db.store_embedding(embedding, chunk)
                    except DuplicateKeyError:
                        st.warning(f"Chunk from {filename} already exists. Skipping.")

            st.success("Data Loaded and Processed Successfully")

query = st.text_input(
    "Enter search query",
    help="You can type your search query here. E.g., 'Network issue on 12th May'",
)

if st.button("Search"):
    st.info("Searching for documents similar to: " + query)
    embedder = GCPVertexAIEmbedder()
    vector_db = MongoVectorDB(
        connection_string=mongo_connection_string,
        db_name=mongo_db_name,
        collection_name=mongo_collection_name,
    )
    search_service = SearchService(embedder, vector_db)
    threshold = 0.8  # Set your threshold here
    results = search_service.search(query, threshold=threshold)

    if results:
        st.write(f"Found {len(results)} documents:")

        for index, result in enumerate(results, start=1):
            st.write("---")
            st.write(f"Document {index} of {len(results)}")
            st.write(f"# {result['filename']}")

            # Use custom CSS to style the scrollable text area
            st.markdown(
                f"""
                <style>
                    .scrollable-text {{
                        max-height: 400px;
                        overflow-y: auto;
                        border: 1px solid #ccc;
                        padding: 10px;
                        background-color: #f9f9f9;
                    }}
                    .highlight {{
                        background-color: yellow;
                    }}
                </style>
                """,
                unsafe_allow_html=True
            )
            
            # Use components.html to render the HTML content
            components.html(
                f"""
                <div class="scrollable-text">
                    {result['text']}
                </div>
                """,
                height=400,
                scrolling=True
            )
    else:
        st.warning("No results found for your query.")
