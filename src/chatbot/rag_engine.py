#!/usr/bin/env python3
"""
RAG Engine module for boAt Customer Support Chatbot.

This module implements Retrieval-Augmented Generation using ChromaDB for retrieval
and a Gemini/LLM for generation.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
import dotenv
from enum import Enum
import google.generativeai as genai

# Import our database module
from src.database.vector_store import VectorStore

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
dotenv.load_dotenv()

# Configure Gemini API
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
except Exception as e:
    logger.error(f"Error configuring Gemini API: {e}")


class QueryType(Enum):
    """Types of queries that can be handled by the RAG engine."""
    RETURN_POLICY = "return_policy"
    SERVICE_CENTER = "service_center"
    GENERAL = "general"


class RAGEngine:
    """
    RAG Engine for answering customer support queries using vector database retrieval
    and LLM generation.
    """
    
    def __init__(self, 
                 model_name: str = "gemini-2.0-flash",
                 temperature: float = 0.2,
                 top_k_results: int = 3):
        """
        Initialize the RAG Engine.
        
        Args:
            model_name: Name of the generative model to use
            temperature: Temperature for text generation (higher = more creative)
            top_k_results: Number of relevant documents to retrieve
        """
        self.model_name = model_name
        self.temperature = temperature
        self.top_k_results = top_k_results
        
        # Initialize vector store
        try:
            self.vector_store = VectorStore()
            logger.info("Vector store initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing vector store: {e}")
            raise
        
        # Initialize Gemini model
        try:
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={
                    "temperature": self.temperature,
                    "top_p": 0.95,
                    "top_k": 0,
                    "max_output_tokens": 1024,
                }
            )
            logger.info(f"Gemini model '{model_name}' initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Gemini model: {e}")
            raise
    
    def detect_query_type(self, query: str) -> QueryType:
        """
        Detect the type of query based on the content.
        
        Args:
            query: The customer's query text
            
        Returns:
            The detected query type
        """
        query_lower = query.lower()
        
        # Return policy related keywords
        return_keywords = [
            "return", "refund", "replace", "replacement", "warranty", "damaged",
            "broken", "defective", "cancel", "order", "delivery", "shipping",
            "days", "policy", "money back", "exchange"
        ]
        
        # Service center related keywords
        service_keywords = [
            "service", "center", "repair", "fix", "location", "address",
            "contact", "store", "branch", "office", "nearest", "where", "hours"
        ]
        
        # Count matches for each category
        return_count = sum(1 for kw in return_keywords if kw in query_lower)
        service_count = sum(1 for kw in service_keywords if kw in query_lower)
        
        # Determine type based on keyword matches
        if return_count > service_count:
            return QueryType.RETURN_POLICY
        elif service_count > return_count:
            return QueryType.SERVICE_CENTER
        else:
            return QueryType.GENERAL
    
    def retrieve_relevant_docs(self, query: str, query_type: QueryType) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents from the vector store based on query type.
        
        Args:
            query: The customer's query text
            query_type: The type of query
            
        Returns:
            List of relevant documents with their content and metadata
        """
        if query_type == QueryType.RETURN_POLICY:
            return self.vector_store.query_return_policy(query, n_results=self.top_k_results)
        elif query_type == QueryType.SERVICE_CENTER:
            return self.vector_store.query_service_centers(query, n_results=self.top_k_results)
        else:
            # For general queries, try both collections and merge results
            policy_docs = self.vector_store.query_return_policy(query, n_results=2)
            service_docs = self.vector_store.query_service_centers(query, n_results=2)
            
            # Combine results
            combined_docs = []
            combined_docs.extend(policy_docs)
            combined_docs.extend(service_docs)
            
            # Sort by relevance (score)
            combined_docs.sort(key=lambda x: x.get("score", 1.0))
            
            # Limit to top_k_results
            return combined_docs[:self.top_k_results]
    
    def generate_response(self, query: str, relevant_docs: List[Dict[str, Any]]) -> str:
        """
        Generate a response using LLM with the relevant context.
        
        Args:
            query: The customer's query text
            relevant_docs: List of relevant documents retrieved from vector store
            
        Returns:
            Generated response text
        """
        # Prepare context from relevant documents
        context = ""
        for i, doc in enumerate(relevant_docs):
            doc_content = doc.get("content", "")
            doc_metadata = doc.get("metadata", {})
            
            if doc_metadata.get("doc_type") == "policy":
                context += f"Return Policy Information:\n{doc_content}\n\n"
            elif doc_metadata.get("doc_type") == "location":
                state = doc_metadata.get("state", "")
                address = doc_metadata.get("address", "")
                contact = doc_metadata.get("contact", "")
                context += f"Service Center in {state}:\n{address}\nContact: {contact}\n\n"
            else:
                context += f"Document {i+1}:\n{doc_content}\n\n"
        
        # Create prompt with context
        prompt = f"""
        You are a helpful customer support chatbot for boAt, a consumer electronics brand.
        
        CONTEXT INFORMATION:
        {context}
        
        USER QUESTION:
        {query}
        
        Please provide a helpful, friendly, and accurate response based on the information above.
        If the information is not in the context, politely explain that you don't have that specific information
        and suggest contacting boAt's customer support directly.
        
        Format your response in a conversational, easy to read manner.
        """
        
        try:
            # Generate response using Gemini
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm sorry, I'm having trouble generating a response right now. Please try again later or contact boAt customer support directly for assistance."
    
    def answer_query(self, query: str) -> str:
        """
        Process a customer query and generate a response using RAG.
        
        Args:
            query: The customer's query text
            
        Returns:
            Response text answering the query
        """
        # Detect query type
        query_type = self.detect_query_type(query)
        logger.info(f"Query type detected: {query_type.value}")
        
        # Retrieve relevant documents
        relevant_docs = self.retrieve_relevant_docs(query, query_type)
        logger.info(f"Retrieved {len(relevant_docs)} relevant documents")
        
        # Generate response
        response = self.generate_response(query, relevant_docs)
        
        return response


# Test function for direct module execution
def test_rag_engine():
    """
    Test the RAG engine with a sample query.
    """
    engine = RAGEngine()
    
    # Test queries
    test_queries = [
        "What is boAt's return policy for damaged items?",
        "Where can I find a service center in Maharashtra?",
        "How many days do I have to return a boAt headphone?"
    ]
    
    for query in test_queries:
        print(f"\n\n=== Testing Query: '{query}' ===")
        response = engine.answer_query(query)
        print(f"\nResponse: {response}")


# Run test if module is executed directly
if __name__ == "__main__":
    test_rag_engine() 