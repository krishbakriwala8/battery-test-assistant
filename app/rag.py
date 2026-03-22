"""
# embedding with openai
import os
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

class RequirementRAG:
    def __init__(self, persist_directory="./chroma_db", api_key=None):
        self.persist_directory = persist_directory
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required.")
        self.embeddings = OpenAIEmbeddings(api_key=self.api_key)
        self.vectorstore = None
        self.retriever = None

    def load_document(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.txt':
            loader = TextLoader(file_path, encoding='utf-8')
        elif ext == '.pdf':
            loader = PyPDFLoader(file_path)
        else:
            raise ValueError("Unsupported file type. Use PDF or TXT.")

        documents = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = splitter.split_documents(documents)

        self.vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=self.embeddings,
            persist_directory=self.persist_directory
        )
        self.vectorstore.persist()
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})

    def answer_question(self, question):
        if not self.retriever:
            return "No document loaded. Please upload a requirement file first."

        docs = self.retriever.get_relevant_documents(question)
        if not docs:
            return "No relevant information found."

        context = "\n\n".join([doc.page_content for doc in docs])
        return f"Based on the requirement document:\n{context}\n\nQuestion: {question}"
"""
# embedding with huggingface
import os
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

class RequirementRAG:
    def __init__(self, persist_directory="./chroma_db", api_token=None):
        self.persist_directory = persist_directory
        self.api_token = api_token  # optional

        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.vectorstore = None
        self.retriever = None
        

    def load_document(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.txt':
            loader = TextLoader(file_path, encoding='utf-8')
        elif ext == '.pdf':
            loader = PyPDFLoader(file_path)
        else:
            raise ValueError("Unsupported file type. Use PDF or TXT.")

        documents = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = splitter.split_documents(documents)

        self.vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=self.embeddings,
            persist_directory=self.persist_directory
        )
        self.vectorstore.persist()
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})

    def answer_question(self, question):
        if not self.retriever:
            return "No document loaded. Please upload a requirement file first."

        docs = self.retriever.get_relevant_documents(question)
        if not docs:
            return "No relevant information found."

        context = "\n\n".join([doc.page_content for doc in docs])
        return f"Based on the requirement document:\n{context}\n\nQuestion: {question}"