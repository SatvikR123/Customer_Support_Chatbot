"""
Vector store implementation using ChromaDB for the boAt Customer Support Chatbot.
"""
import chromadb
import os
import logging
import dotenv
import json
from typing import List, Dict, Any, Optional
import numpy as np

# Load environment variables
dotenv.load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CustomEmbeddingFunction:
    """
    A custom embedding function class to avoid compatibility issues with newer NumPy.
    This is a simplified version that uses sentence-transformers directly.
    """
    
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        """Initialize with a specific model name."""
        self.model_name = model_name
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded sentence transformer model: {model_name}")
        except ImportError:
            logger.error("sentence-transformers package not found. Please install it with pip.")
            self.model = None
    
    def __call__(self, input):
        """
        Generate embeddings for a list of texts.
        Changed parameter name from 'texts' to 'input' to match ChromaDB interface.
        """
        if self.model is None:
            logger.error("No model available for generating embeddings")
            # Return empty vectors of the right size as a fallback
            return [[0.0] * 384 for _ in input]  # 384 is the dimension for all-MiniLM-L6-v2
        
        try:
            embeddings = self.model.encode(input)
            # Convert to native Python list for better compatibility
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            # Return empty vectors of the right size as a fallback
            return [[0.0] * 384 for _ in input]

class VectorStore:
    """
    A class to manage vector database operations using ChromaDB.
    """
    
    def __init__(self):
        """Initialize the vector store with ChromaDB."""
        persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")
        try:
            self.client = chromadb.PersistentClient(path=persist_directory)
            logger.info("ChromaDB client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing ChromaDB client: {e}")
            raise
        
        # Use custom embedding function to avoid compatibility issues
        self.embedding_function = CustomEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        
        # Create collections if they don't exist
        try:
            self.return_policy_collection = self.client.get_or_create_collection(
                name="return_policy", 
                embedding_function=self.embedding_function,
                metadata={"description": "Return policy information from boAt's website"}
            )
            
            self.service_centers_collection = self.client.get_or_create_collection(
                name="service_centers",
                embedding_function=self.embedding_function,
                metadata={"description": "Service center locations from boAt's website"}
            )
            logger.info("Vector store collections initialized with ChromaDB")
        except Exception as e:
            logger.error(f"Error creating ChromaDB collections: {e}")
            raise
    
    def add_return_policy_docs(self, documents: List[Dict[str, str]]) -> None:
        """
        Add return policy documents to the vector store.
        
        Args:
            documents: A list of policy documents with title and content.
        """
        if not documents:
            logger.warning("No return policy documents to add")
            return
            
        ids = []
        texts = []
        metadatas = []
        
        for i, doc in enumerate(documents):
            doc_id = f"policy_{i}"
            ids.append(doc_id)
            texts.append(doc["content"])
            metadatas.append({
                "title": doc["title"],
                "source": "return_policy",
                "doc_type": "policy"
            })
        
        try:
            self.return_policy_collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
            logger.info(f"Added {len(documents)} return policy documents to vector store")
        except Exception as e:
            logger.error(f"Error adding return policy documents to vector store: {e}")
    
    def add_service_center_docs(self, service_centers: List[Dict[str, Any]]) -> None:
        """
        Add service center documents to the vector store.
        
        Args:
            service_centers: A list of service center information by state.
        """
        if not service_centers:
            logger.warning("No service center documents to add")
            return
            
        ids = []
        texts = []
        metadatas = []
        
        doc_id_counter = 0
        for state_info in service_centers:
            state = state_info["state"]
            for location in state_info["locations"]:
                doc_id = f"sc_{doc_id_counter}"
                doc_id_counter += 1
                
                # Create a searchable text representation of the location
                text = f"boAt service center in {state}. {location['name']}. {location['address']}. {location.get('contact', '')}"
                
                ids.append(doc_id)
                texts.append(text)
                metadatas.append({
                    "state": state,
                    "name": location["name"],
                    "address": location["address"],
                    "contact": location.get("contact", ""),
                    "source": "service_centers",
                    "doc_type": "location"
                })
        
        try:
            self.service_centers_collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
            logger.info(f"Added {doc_id_counter} service center documents to vector store")
        except Exception as e:
            logger.error(f"Error adding service center documents to vector store: {e}")
    
    def query_return_policy(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Query the return policy collection.
        
        Args:
            query: The search query.
            n_results: Number of results to return.
            
        Returns:
            A list of matching documents with their metadata.
        """
        try:
            results = self.return_policy_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if not results["documents"]:
                return []
                
            documents = []
            for i, doc in enumerate(results["documents"][0]):
                documents.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if i < len(results["metadatas"][0]) else {},
                    "score": results["distances"][0][i] if i < len(results["distances"][0]) else None
                })
                
            return documents
        except Exception as e:
            logger.error(f"Error querying return policy: {e}")
            return []
    
    def query_service_centers(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Query the service centers collection.
        
        Args:
            query: The search query, typically including a location.
            n_results: Number of results to return.
            
        Returns:
            A list of matching service center locations with their metadata.
        """
        try:
            results = self.service_centers_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if not results["documents"]:
                return []
                
            locations = []
            for i, doc in enumerate(results["documents"][0]):
                locations.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if i < len(results["metadatas"][0]) else {},
                    "score": results["distances"][0][i] if i < len(results["distances"][0]) else None
                })
                
            return locations
        except Exception as e:
            logger.error(f"Error querying service centers: {e}")
            return []
    
    def load_and_add_data(self) -> Dict[str, int]:
        """
        Load data from JSON files and add it to the vector store.
        
        Returns:
            A dictionary with counts of documents added.
        """
        counts = {"return_policy": 0, "service_centers": 0}
        
        # Load and add return policy data
        try:
            with open("data/return_policy.json", "r", encoding="utf-8") as f:
                return_policy_data = json.load(f)
                self.add_return_policy_docs(return_policy_data)
                counts["return_policy"] = len(return_policy_data)
        except Exception as e:
            logger.error(f"Error loading return policy data: {e}")
        
        # Load and add service center data
        try:
            with open("data/service_centers.json", "r", encoding="utf-8") as f:
                service_centers_data = json.load(f)
                self.add_service_center_docs(service_centers_data)
                counts["service_centers"] = sum(len(state["locations"]) for state in service_centers_data)
        except Exception as e:
            logger.error(f"Error loading service center data: {e}")
        
        return counts

# Main function for running the vector store directly
if __name__ == "__main__":
    vector_store = VectorStore()
    counts = vector_store.load_and_add_data()
    print(f"Added {counts['return_policy']} return policy documents and {counts['service_centers']} service center locations to the vector store.") 