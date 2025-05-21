#!/usr/bin/env python3
"""
Orchestrator for boAt Customer Support Chatbot

This module implements the orchestrator that coordinates the flow of information
between specialized agents for analyzing queries, retrieving relevant information,
and generating responses.
"""

import os
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
import time
import asyncio

# Import our specialized agents
from src.agents.query_analyzer import QueryAnalyzer
from src.agents.retrieval_agent import RetrievalAgent
from src.agents.response_generator import ResponseGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Orchestrator for coordinating the flow between specialized agents.
    
    This class is responsible for:
    1. Receiving user queries
    2. Coordinating the query analysis to determine query type and parameters
    3. Retrieving relevant information from the vector database
    4. Generating a human-friendly response
    """
    
    def __init__(self):
        """Initialize the orchestrator with specialized agents."""
        self.query_analyzer = QueryAnalyzer()
        self.retrieval_agent = RetrievalAgent()
        self.response_generator = ResponseGenerator()
        logger.info("Orchestrator initialized with specialized agents")
    
    def process_query(self, query: str) -> str:
        """
        Process a complete query through the orchestration pipeline.
        
        Args:
            query: The user query to process
            
        Returns:
            A string containing the generated response
        """
        logger.info(f"Processing query: '{query}'")
        
        # Step 1: Query analysis
        logger.info("Step 1: Query analysis")
        analysis_result = self.analyze_query(query)
        query_type = analysis_result.get("query_type", "unknown")
        parameters = analysis_result.get("parameters", {})
        
        # Step 2: Information retrieval
        logger.info(f"Step 2: Information retrieval for query type: {query_type}")
        retrieved_info = self.retrieve_information(query_type, parameters)
        
        # Step 3: Response generation
        logger.info("Step 3: Response generation")
        response = self.generate_response(query, retrieved_info)
        
        return response
    
    async def process_query_async(self, query: str) -> str:
        """
        Process a query asynchronously (for FastAPI integration).
        
        This is a wrapper around the synchronous process_query method to make it 
        compatible with FastAPI's async handlers.
        
        Args:
            query: The user query to process
            
        Returns:
            A string containing the generated response
        """
        # In a production system, you'd run process_query in a thread pool executor
        # For simplicity, we'll just call the synchronous method directly
        response = self.process_query(query)
        
        # Ensure we return a string
        if isinstance(response, dict) and "response_text" in response:
            return response["response_text"]
        elif isinstance(response, str):
            return response
        else:
            # If we get something unexpected, convert to string
            try:
                return str(response)
            except:
                return "I'm sorry, I encountered an error processing your request."
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze the query to determine its type and extract parameters.
        
        Args:
            query: The user query to analyze
            
        Returns:
            A dictionary with the query type and extracted parameters
        """
        return self.query_analyzer.classify_query(query)
    
    def retrieve_information(self, query_type: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve relevant information based on the query type and parameters.
        
        Args:
            query_type: The type of query (e.g., 'return_policy', 'service_center')
            parameters: The parameters extracted from the query
            
        Returns:
            A list of relevant information items
        """
        # Create a query analysis dict from query_type and parameters
        query_analysis = {
            "query_type": query_type,
            "parameters": parameters
        }
        return self.retrieval_agent.retrieve_information(query_analysis)
    
    def generate_response(self, query: str, retrieved_info: List[Dict[str, Any]]) -> str:
        """
        Generate a human-friendly response based on the retrieved information.
        
        Args:
            query: The original user query
            retrieved_info: The information retrieved from the vector database
            
        Returns:
            A human-friendly response
        """
        return self.response_generator.generate_response(query, retrieved_info)


# Test function for direct module execution
def test_orchestrator():
    """
    Test the orchestrator with sample queries.
    """
    # Initialize the orchestrator
    orchestrator = Orchestrator()
    
    # Test queries
    test_queries = [
        "What is boAt's return policy for damaged items?",
        "Where can I find a service center in Maharashtra?",
        "How many days do I have to return my Airdopes?",
        "My headphones are not charging, what should I do?",
        "Does the warranty cover water damage?",
    ]
    
    # Process each query
    for query in test_queries:
        print(f"\n=== Testing Query: '{query}' ===")
        result = orchestrator.process_query(query)
        
        print("\nResponse:")
        print(result)


# Run test if module is executed directly
if __name__ == "__main__":
    test_orchestrator() 