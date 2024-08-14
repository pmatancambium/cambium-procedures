# streamlit_app.py
import hmac
import streamlit as st
from dotenv import load_dotenv
from data_source import FileDataSource
from data_parser import ProcedureParser
from embedder import GCPVertexAIEmbedder
from vectordb import MongoVectorDB
from search_service import SearchService
import chardet
import os
import re
from pymongo.errors import DuplicateKeyError
import streamlit.components.v1 as components
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession

load_dotenv()


def check_password():
    def password_entered():
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


if not check_password():
    st.stop()

# Main Streamlit app starts here
logo_path = "logo.png"
st.set_page_config(page_title="Service Call Search Engine", layout="wide")

uploaded_file = st.sidebar.file_uploader("Choose a file", type=["txt", "docx", "pdf"])
skip_existing = st.sidebar.checkbox("Skip existing documents", value=True)

mongo_connection_string = st.secrets["MONGO_CONNECTION_STRING"]
mongo_db_name = "cambium-procedures"
mongo_collection_name = "procedures"

# Initialize Vertex AI
vertexai.init(project=st.secrets["GCP_PROJECT_ID"], location=st.secrets["GCP_REGION"])


def generate_answer(question: str, context: str):
    model = GenerativeModel("gemini-1.0-pro")
    chat = model.start_chat()
    # prompt = f"""Based on the following context, answer the question. If the answer is not in the context, say so.
    prompt = f"""בהתבסס על ההקשר הבא, ענה על השאלה. אם התשובה אינה בהקשר, תגיד זאת. נסה לתת תשובה מפורטת

Context:
{context}

Question: {question}

Answer:"""
    response = chat.send_message(prompt, stream=True)
    return response


def is_rtl(text):
    hebrew_pattern = re.compile(r"[\u0590-\u05FF\uFB1D-\uFB4F]")
    return bool(hebrew_pattern.search(text))


def display_text_with_direction(text):
    if is_rtl(text):
        st.markdown(f'<div dir="rtl" lang="he">{text}</div>', unsafe_allow_html=True)
    else:
        st.write(text)


# Adding tabs for different sections of the app
tab1, tab2 = st.tabs(["Search", "View All Documents"])

with tab1:
    if uploaded_file:
        st.info("File uploaded successfully!")
        if st.button("Load and Process Data"):
            with st.spinner("Processing data..."):
                file_path = uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                if file_path.endswith(".txt"):
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
                    plain_text = chunk["plain_text"]
                    formatted_text = chunk["formatted_text"]
                    filename = chunk["filename"]
                    unique_chunk_identifier = (
                        f"{filename}-{chunk.get('heading', '')}-{len(plain_text)}"
                    )

                    if skip_existing and vector_db.document_exists(
                        unique_chunk_identifier
                    ):
                        st.warning(f"Chunk from {filename} already exists. Skipping.")
                        continue

                    embeddings = embedder.embed_batch([plain_text])
                    for embedding in embeddings:
                        try:
                            chunk["unique_chunk_identifier"] = unique_chunk_identifier
                            chunk["text"] = (
                                formatted_text  # Store formatted text in the database
                            )
                            vector_db.store_embedding(embedding, chunk)
                        except DuplicateKeyError:
                            st.warning(
                                f"Chunk from {filename} already exists. Skipping."
                            )

                st.success("Data Loaded and Processed Successfully")

    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    messages = st.session_state["messages"]

    # Chat input for search query
    chat_message = st.chat_input("Enter search query")

    if chat_message:
        embedder = GCPVertexAIEmbedder()
        vector_db = MongoVectorDB(
            connection_string=mongo_connection_string,
            db_name=mongo_db_name,
            collection_name=mongo_collection_name,
        )
        search_service = SearchService(embedder, vector_db)
        threshold = 0.83  # Set your threshold here
        results = search_service.search(chat_message, threshold=threshold)

        if results:
            context = "\n\n".join([result["text"] for result in results])

            # Add user message
            messages.append({"role": "user", "parts": [chat_message]})
            user_msg_area = st.chat_message("user")
            if is_rtl(chat_message):
                user_msg_area.markdown(
                    f'<div dir="rtl" lang="he">{chat_message}</div>',
                    unsafe_allow_html=True,
                )
            else:
                user_msg_area.markdown(chat_message)

            res_area = st.chat_message("assistant").empty()

            # Generate answer using Gemini API
            response = generate_answer(chat_message, context)

            res_text = ""
            for chunk in response:
                res_text += chunk.text
                res_area.markdown(res_text)

            messages.append({"role": "model", "parts": [res_text]})

            st.write("---")
            st.header("Here are the relevant documents:")

            for index, result in enumerate(results, start=1):
                st.write("---")
                st.write(f"Document {index} of {len(results)}")
                st.write(f"# {result['filename']}")

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
                    unsafe_allow_html=True,
                )
                dir_attr = "rtl" if is_rtl(result["text"]) else "ltr"
                lang_attr = "he" if is_rtl(result["text"]) else "en"
                components.html(
                    f"""
                    <div class="scrollable-text" dir="{dir_attr}" lang="{lang_attr}">
                        {result['text']}
                    </div>
                    """,
                    # height=400,
                    scrolling=True,
                )
        else:
            st.warning("No results found for your query.")

with tab2:
    st.header("Available Documents")
    vector_db = MongoVectorDB(
        connection_string=mongo_connection_string,
        db_name=mongo_db_name,
        collection_name=mongo_collection_name,
    )
    documents = vector_db.collection.distinct("filename")

    if documents:
        for doc in documents:
            with st.expander(f"{doc}"):
                chunks = vector_db.fetch_all_chunks(doc)
                for chunk in chunks:
                    dir_attr = "rtl" if is_rtl(chunk["text"]) else "ltr"
                    lang_attr = "he" if is_rtl(chunk["text"]) else "en"
                    components.html(
                        f"""
                        <div class="scrollable-text" dir="{dir_attr}" lang="{lang_attr}">
                            {chunk['text']}
                        </div>
                        """,
                        # height=200,
                        scrolling=True,
                    )
                    st.write("---")
    else:
        st.info("No documents available.")
