#!/usr/bin/env python3
"""
Test script for the direct loader functionality.

This script tests the DirectLoader implementation to verify it can
correctly process scraped content and add it to the vector database.
"""
import os
import sys
import json
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# Import our modules
from src.utils.direct_loader import DirectLoader
from src.database.vector_store import VectorStore

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_direct_loader():
    """Test the direct loader functionality."""
    logger.info("=== Testing Direct Loader ===")
    
    # Initialize the loader
    loader = DirectLoader(data_dir="data")
    
    # Test loading scraped content
    logger.info("Testing loading of scraped content...")
    if not os.path.exists("data/scraped_content.json"):
        logger.error("Scraped content file not found. Please run the scraper first.")
        return False
    
    # Test processing content
    logger.info("Testing processing of scraped content...")
    if not loader.load_scraped_content():
        logger.error("Failed to process scraped content")
        return False
    
    # Verify processed content was saved
    if not os.path.exists(loader.return_policy_path) and not os.path.exists(loader.service_centers_path):
        logger.error("No processed content files were generated")
        return False
    
    # Check return policy content
    if os.path.exists(loader.return_policy_path):
        with open(loader.return_policy_path, 'r', encoding='utf-8') as f:
            return_policy_data = json.load(f)
        logger.info(f"Processed {len(return_policy_data)} return policy documents")
        
        # Check document format
        if return_policy_data:
            first_doc = return_policy_data[0]
            logger.info(f"First document title: {first_doc.get('title', 'N/A')}")
            logger.info(f"First document content length: {len(first_doc.get('content', ''))}")
    
    # Check service centers content
    if os.path.exists(loader.service_centers_path):
        with open(loader.service_centers_path, 'r', encoding='utf-8') as f:
            service_centers_data = json.load(f)
        
        num_states = len(service_centers_data)
        num_locations = sum(len(state.get("locations", [])) for state in service_centers_data)
        logger.info(f"Processed service center information: {num_states} states, {num_locations} locations")
        
        # Check data format
        if service_centers_data:
            first_state = service_centers_data[0]
            logger.info(f"First state: {first_state.get('state', 'N/A')}")
            if first_state.get("locations"):
                first_location = first_state["locations"][0]
                logger.info(f"First location name: {first_location.get('name', 'N/A')}")
                logger.info(f"First location address: {first_location.get('address', 'N/A')}")
    
    # Test loading to vector database
    logger.info("Testing loading to vector database...")
    counts = loader.load_to_vector_db()
    
    logger.info(f"Added {counts['return_policy']} return policy documents to vector store")
    logger.info(f"Added {counts['service_centers']} service center locations to vector store")
    
    if counts['return_policy'] == 0 and counts['service_centers'] == 0:
        logger.error("No documents were added to the vector database")
        return False
    
    logger.info("Direct loader test completed successfully")
    return True

def test_vector_store_query():
    """Test querying the vector store after loading."""
    logger.info("=== Testing Vector Store Queries ===")
    
    try:
        # Initialize the vector store
        vector_store = VectorStore()
        
        # Test querying return policy
        return_queries = [
            "What is boAt's return policy?",
            "How many days do I have for replacement?",
            "When can I get a refund?"
        ]
        
        logger.info("Testing return policy queries:")
        for query in return_queries:
            logger.info(f"\nQuery: {query}")
            results = vector_store.query_return_policy(query, n_results=1)
            
            if results:
                logger.info(f"Found {len(results)} results")
                for i, result in enumerate(results):
                    content = result.get("content", "")
                    logger.info(f"Result {i+1} (first 100 chars): {content[:100]}..." if len(content) > 100 else f"Result {i+1}: {content}")
            else:
                logger.warning(f"No results found for query: {query}")
        
        # Test querying service centers
        service_queries = [
            "Where are boAt service centers in Delhi?",
            "Is there a service center in Mumbai?",
            "boAt service center in Gujarat"
        ]
        
        logger.info("\nTesting service center queries:")
        for query in service_queries:
            logger.info(f"\nQuery: {query}")
            results = vector_store.query_service_centers(query, n_results=1)
            
            if results:
                logger.info(f"Found {len(results)} results")
                for i, result in enumerate(results):
                    metadata = result.get("metadata", {})
                    state = metadata.get("state", "N/A")
                    address = metadata.get("address", "N/A")
                    logger.info(f"Result {i+1}: Service center in {state} at {address}")
            else:
                logger.warning(f"No results found for query: {query}")
        
        logger.info("Vector store query test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error testing vector store queries: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    logger.info("Starting Direct Loader and Vector Store tests")
    
    # Test direct loader
    loader_result = test_direct_loader()
    if not loader_result:
        logger.error("Direct loader test failed")
    
    # Test vector store queries
    query_result = test_vector_store_query()
    if not query_result:
        logger.error("Vector store query test failed")
    
    # Overall result
    if loader_result and query_result:
        logger.info("All tests passed successfully! ✅")
        return 0
    else:
        logger.error("Some tests failed! ❌")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 