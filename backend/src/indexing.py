import logging
import os
import re

import streamlit as st
from dotenv import load_dotenv
from fastembed import SparseTextEmbedding, TextEmbedding
from fastembed.late_interaction import LateInteractionTextEmbedding
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core.schema import Document
from llama_index.embeddings.openai import OpenAIEmbedding
from openai import OpenAI
from qdrant_client import QdrantClient, models

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_HOST = os.getenv("QDRANT_HOST")
COLLECTION_NAME = "genezio"
BATCH_SIZE = 4


class CustomTransformation:
    def __call__(self, documents):
        transformed_documents = []
        for doc in documents:
            transformed_content = doc.get_content().lower()
            transformed_content = re.sub(r"\s+", " ", transformed_content)
            transformed_content = re.sub(r"[^\w\s]", "", transformed_content)
            transformed_documents.append(
                Document(text=transformed_content, metadata=doc.metadata)
            )
        return transformed_documents


class DocumentProcessor:
    def __init__(self):
        self.embed_model = OpenAIEmbedding()
        self.splitter = SemanticSplitterNodeParser(
            buffer_size=1,
            breakpoint_percentile_threshold=95,
            embed_model=self.embed_model,
        )

    def process_documents(self, temp_dir):
        try:
            # Load documents from temporary directory
            documents = SimpleDirectoryReader(input_dir=temp_dir).load_data()

            if not documents:
                return None, "No documents found to process."

            # Apply transformations
            custom_transform = CustomTransformation()
            documents = custom_transform(documents)

            # Split into nodes
            nodes = self.splitter.get_nodes_from_documents(documents)

            return nodes, None
        except Exception as e:
            return None, f"Error processing documents: {str(e)}"


class QdrantIndexer:
    def __init__(self):
        self.openai_client = OpenAI()
        self.embedding_model = TextEmbedding(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.sparse_embedding_model = SparseTextEmbedding(
            model_name="Qdrant/bm42-all-minilm-l6-v2-attentions"
        )
        self.late_interaction_embedding_model = LateInteractionTextEmbedding(
            model_name="colbert-ir/colbertv2.0"
        )

        self.qdrant_client = QdrantClient(
            url=QDRANT_HOST,
            api_key=QDRANT_API_KEY,
            timeout=600,
        )

    def small_embedding(self, text, model="text-embedding-3-small"):
        text = text.replace("\n", " ")
        return (
            self.openai_client.embeddings.create(
                input=[text], model=model, dimensions=128
            )
            .data[0]
            .embedding
        )

    def large_embedding(self, text, model="text-embedding-3-large"):
        text = text.replace("\n", " ")
        return (
            self.openai_client.embeddings.create(
                input=[text], model=model, dimensions=1024
            )
            .data[0]
            .embedding
        )

    def create_sparse_vector(self, text):
        embeddings = list(self.sparse_embedding_model.embed([text]))[0]
        return models.SparseVector(
            indices=embeddings.indices.tolist(), values=embeddings.values.tolist()
        )

    def setup_collection(self, sample_text):
        if not self.qdrant_client.collection_exists(collection_name=COLLECTION_NAME):
            dense_embedding = list(self.embedding_model.embed([sample_text]))[0]
            late_interaction_embedding = list(
                self.late_interaction_embedding_model.embed([sample_text])
            )[0]

            self.qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config={
                    "dense": models.VectorParams(
                        size=len(dense_embedding),
                        distance=models.Distance.COSINE,
                    ),
                    "colbert": models.VectorParams(
                        size=len(late_interaction_embedding[0]),
                        distance=models.Distance.COSINE,
                        multivector_config=models.MultiVectorConfig(
                            comparator=models.MultiVectorComparator.MAX_SIM
                        ),
                    ),
                    "small-embedding": models.VectorParams(
                        size=128,
                        distance=models.Distance.COSINE,
                        datatype=models.Datatype.FLOAT16,
                    ),
                    "large-embedding": models.VectorParams(
                        size=1024,
                        distance=models.Distance.COSINE,
                        datatype=models.Datatype.FLOAT16,
                    ),
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(
                        index=models.SparseIndexParams(
                            on_disk=False,
                        ),
                    )
                },
            )

    def index_documents(self, nodes):
        documents = [node.text for node in nodes]
        metadata = [node.metadata for node in nodes]

        total_docs = len(documents)
        processed = 0
        failed_batches = []

        progress_bar = st.progress(0)
        status_text = st.empty()

        while processed < total_docs:
            end_idx = min(processed + BATCH_SIZE, total_docs)
            batch_docs = documents[processed:end_idx]
            batch_metadata = metadata[processed:end_idx]

            try:
                dense_embeddings = list(self.embedding_model.embed(batch_docs))
                sparse_vectors = [self.create_sparse_vector(doc) for doc in batch_docs]
                late_interaction_embeddings = list(
                    self.late_interaction_embedding_model.embed(batch_docs)
                )
                small_embeddings = [self.small_embedding(text) for text in batch_docs]
                large_embeddings = [self.large_embedding(text) for text in batch_docs]

                points = [
                    models.PointStruct(
                        id=processed + i,
                        vector={
                            "dense": dense_emb.tolist(),
                            "sparse": sparse_vec,
                            "colbert": late_emb.tolist(),
                            "small-embedding": small_emb,
                            "large-embedding": large_emb,
                        },
                        payload={
                            "text": doc,
                            **metadata,
                        },
                    )
                    for i, (
                        doc,
                        metadata,
                        dense_emb,
                        sparse_vec,
                        late_emb,
                        small_emb,
                        large_emb,
                    ) in enumerate(
                        zip(
                            batch_docs,
                            batch_metadata,
                            dense_embeddings,
                            sparse_vectors,
                            late_interaction_embeddings,
                            small_embeddings,
                            large_embeddings,
                        )
                    )
                ]

                self.qdrant_client.upload_points(
                    collection_name=COLLECTION_NAME,
                    points=points,
                    batch_size=BATCH_SIZE,
                )

                # Update progress
                progress = (processed + BATCH_SIZE) / total_docs
                progress_bar.progress(min(progress, 1.0))
                status_text.text(
                    f"Processing documents: {processed + BATCH_SIZE}/{total_docs}"
                )

            except Exception as e:
                failed_batches.append((processed, end_idx))
                logger.error(f"Error processing batch {processed}-{end_idx}: {str(e)}")

            processed = end_idx

        return len(failed_batches) == 0
