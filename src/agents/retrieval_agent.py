#!/usr/bin/env python3
"""
Retrieval Agent for boAt Customer Support Chatbot.

This module implements a specialized agent for retrieving relevant information
from the vector database based on the query type and parameters.
"""

import os
import logging
import json
from typing import Dict, List, Any, Optional, Tuple

# Import our database module
from src.database.vector_store import VectorStore

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RetrievalAgent:
    """
    Specialized agent for retrieving and filtering information from vector database.
    
    This class handles:
    - Retrieving relevant documents based on query type
    - Filtering results by relevance
    - Providing organized context for response generation
    """
    
    def __init__(self, vector_store: Optional[VectorStore] = None):
        """
        Initialize the retrieval agent with a vector store instance.
        
        Args:
            vector_store: Instance of the VectorStore class
        """
        # Initialize vector store
        self.vector_store = vector_store or VectorStore()
        logger.info("Retrieval agent initialized")
    
    def retrieve_information(self, 
                            query_analysis: Dict[str, Any], 
                            n_results: int = 3) -> Dict[str, Any]:
        """
        Retrieve relevant information based on query analysis.
        
        Args:
            query_analysis: Output from the query analyzer
            n_results: Number of results to retrieve per category
            
        Returns:
            Dictionary containing retrieved documents and metadata
        """
        # Extract query information
        query_text = query_analysis.get("refined_query") or query_analysis.get("query_text", "")
        query_type = query_analysis.get("query_type", "general")
        parameters = query_analysis.get("parameters", {})
        has_secondary_intents = query_analysis.get("has_secondary_intents", False)
        secondary_intents = query_analysis.get("secondary_intents", [])
        
        logger.info(f"Retrieving information for query: '{query_text}' of type: {query_type}")
        
        # Retrieve primary information based on query type
        primary_results = self._retrieve_by_type(query_text, query_type, parameters, n_results)
        
        # Retrieve secondary information if needed
        secondary_results = {}
        if has_secondary_intents:
            for intent in secondary_intents:
                secondary_results[intent] = self._retrieve_by_type(
                    query_text, intent, parameters, n_results=1
                )
        
        # Compile response
        response = {
            "query_text": query_text,
            "query_type": query_type,
            "primary_results": primary_results,
            "has_secondary_results": has_secondary_intents and bool(secondary_results),
            "secondary_results": secondary_results,
            "retrieved_at": self._get_timestamp()
        }
        
        # Log retrieval summary
        primary_count = len(primary_results.get("documents", []))
        logger.info(f"Retrieved {primary_count} primary documents for query type: {query_type}")
        
        if has_secondary_intents:
            for intent, results in secondary_results.items():
                secondary_count = len(results.get("documents", []))
                logger.info(f"Retrieved {secondary_count} secondary documents for intent: {intent}")
        
        return response
    
    def _retrieve_by_type(self, 
                         query: str, 
                         query_type: str, 
                         parameters: Dict[str, Any],
                         n_results: int) -> Dict[str, Any]:
        """
        Retrieve information based on query type.
        
        Args:
            query: Query text
            query_type: Type of query (return_policy, service_center, etc.)
            parameters: Extracted parameters from the query
            n_results: Number of results to retrieve
            
        Returns:
            Dictionary with retrieved documents and metadata
        """
        results = {
            "documents": [],
            "metadata": {"retrieved": 0}
        }
        
        try:
            # Modify query based on parameters
            enhanced_query = self._enhance_query(query, query_type, parameters)
            
            # Retrieve from appropriate collection based on query type
            if query_type == "return_policy" or query_type == "warranty":
                raw_results = self.vector_store.query_return_policy(enhanced_query, n_results=n_results)
                results["documents"] = raw_results
                results["metadata"]["source"] = "return_policy_collection"
                
            elif query_type == "service_center":
                # Apply location filter if available
                locations = parameters.get("locations", [])
                if locations:
                    # If we have specific locations, adjust query
                    location_query = f"boAt service center in {' '.join(locations)}"
                    raw_results = self.vector_store.query_service_centers(location_query, n_results=n_results)
                else:
                    raw_results = self.vector_store.query_service_centers(enhanced_query, n_results=n_results)
                
                results["documents"] = raw_results
                results["metadata"]["source"] = "service_centers_collection"
                
            elif query_type == "product_issue":
                # For product issues, check both collections
                policy_results = self.vector_store.query_return_policy(enhanced_query, n_results=1)
                service_results = self.vector_store.query_service_centers(enhanced_query, n_results=1)
                
                combined_results = []
                combined_results.extend(policy_results)
                combined_results.extend(service_results)
                
                # Sort by relevance and limit results
                combined_results.sort(key=lambda x: x.get("score", 1.0))
                results["documents"] = combined_results[:n_results]
                results["metadata"]["source"] = "combined_collections"
                
            else:  # General or unknown query type
                # Try both collections and merge results
                policy_results = self.vector_store.query_return_policy(enhanced_query, n_results=n_results//2 or 1)
                service_results = self.vector_store.query_service_centers(enhanced_query, n_results=n_results//2 or 1)
                
                combined_results = []
                combined_results.extend(policy_results)
                combined_results.extend(service_results)
                
                # Sort by relevance and limit results
                combined_results.sort(key=lambda x: x.get("score", 1.0))
                results["documents"] = combined_results[:n_results]
                results["metadata"]["source"] = "combined_collections"
            
            # Update metadata
            results["metadata"]["retrieved"] = len(results["documents"])
            results["metadata"]["enhanced_query"] = enhanced_query
            
        except Exception as e:
            logger.error(f"Error retrieving information for {query_type}: {e}")
            results["metadata"]["error"] = str(e)
        
        return results
    
    def _enhance_query(self, 
                      query: str, 
                      query_type: str, 
                      parameters: Dict[str, Any]) -> str:
        """
        Enhance the query with parameters for better retrieval.
        
        Args:
            query: Original query text
            query_type: Type of query
            parameters: Extracted parameters
            
        Returns:
            Enhanced query with parameters
        """
        # Start with the original query
        enhanced_query = query
        
        # Add product information if available
        products = parameters.get("products", [])
        if products and not any(product.lower() in query.lower() for product in products):
            product_str = products[0]  # Just use the first product to avoid overcomplicating
            enhanced_query = f"{product_str} {enhanced_query}"
        
        # Add time period for return policy queries
        if query_type == "return_policy" and "time_period" in parameters:
            time_period = parameters["time_period"]
            if time_period and "how many days" not in query.lower() and "how long" not in query.lower():
                enhanced_query = f"how many {time_period['unit']} {enhanced_query}"
        
        # Add location for service center queries
        if query_type == "service_center" and "locations" in parameters:
            locations = parameters["locations"]
            if locations and not any(loc.lower() in query.lower() for loc in locations):
                location_str = locations[0]  # Just use the first location
                if "where" in enhanced_query.lower():
                    enhanced_query = f"where in {location_str} {enhanced_query}"
                else:
                    enhanced_query = f"{enhanced_query} in {location_str}"
        
        logger.debug(f"Enhanced query from '{query}' to '{enhanced_query}'")
        return enhanced_query
    
    def _get_timestamp(self) -> str:
        """Get the current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


# Test function for direct module execution
def test_retrieval_agent():
    """
    Test the retrieval agent with sample queries.
    """
    # Initialize the vector store
    vector_store = VectorStore()
    
    # Ensure data is loaded
    if vector_store.return_policy_collection.count() == 0 or vector_store.service_centers_collection.count() == 0:
        print("Loading data into vector store...")
        vector_store.load_and_add_data()
    
    # Initialize the retrieval agent
    agent = RetrievalAgent(vector_store)
    
    # Test query analyses
    test_analyses = [
        {
            "query_text": "What is boAt's return policy for damaged items?",
            "refined_query": "What is boAt's return policy for damaged items?",
            "query_type": "return_policy",
            "parameters": {"products": ["boat"]},
            "has_secondary_intents": False
        },
        {
            "query_text": "Where can I find a service center in Maharashtra?",
            "refined_query": "Where can I find a service center in Maharashtra?",
            "query_type": "service_center",
            "parameters": {"locations": ["Maharashtra"]},
            "has_secondary_intents": False
        },
        {
            "query_text": "My headphones are not charging, can I return them?",
            "refined_query": "My headphones are not charging, can I return them?",
            "query_type": "product_issue",
            "parameters": {"products": ["headphones"]},
            "has_secondary_intents": True,
            "secondary_intents": ["return_policy"]
        }
    ]
    
    for analysis in test_analyses:
        print(f"\n=== Testing Retrieval for Query: '{analysis['query_text']}' ===")
        results = agent.retrieve_information(analysis, n_results=2)
        
        print(f"Query Type: {results['query_type']}")
        print(f"Primary Results Count: {len(results['primary_results']['documents'])}")
        
        for i, doc in enumerate(results['primary_results']['documents']):
            print(f"\nDocument {i+1}:")
            metadata = doc.get("metadata", {})
            for key, value in metadata.items():
                print(f"  {key}: {value}")
            
            content = doc.get("content", "")
            if len(content) > 100:
                print(f"  Content: {content[:100]}...")
            else:
                print(f"  Content: {content}")
        
        if results["has_secondary_results"]:
            print("\nSecondary Results:")
            for intent, sec_results in results["secondary_results"].items():
                print(f"  Intent: {intent}, Count: {len(sec_results['documents'])}")


# Run test if module is executed directly
if __name__ == "__main__":
    test_retrieval_agent() 