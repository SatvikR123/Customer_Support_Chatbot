#!/usr/bin/env python3
"""
Test script for Task 3: ChromaDB and Data Ingestion

This script tests the ChromaDB setup, data ingestion, and basic retrieval functionality
for the boAt Customer Support Chatbot.
"""

import os
import json
import logging
import dotenv
from typing import Dict, List, Any, Optional, Tuple

# Import our modules
from src.utils.data_pipeline import DataPipeline
from src.database.vector_store import VectorStore

# Load environment variables
dotenv.load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_data_pipeline():
    """Test the data processing and ingestion pipeline."""
    logger.info("=== Testing Data Pipeline ===")
    
    # Initialize the pipeline
    pipeline = DataPipeline(data_dir="data")
    
    # Test if we need to process data
    processed_path = os.path.join("data", "gemini_processed.json")
    if not os.path.exists(processed_path):
        logger.info("Processing scraped content...")
        if not pipeline.process_scraped_data():
            logger.error("Failed to process scraped content")
            return False
    else:
        logger.info(f"Processed data already exists at {processed_path}")
    
    # Validate the data
    logger.info("Validating data...")
    valid, report = pipeline.validate_data(verbose=True)
    if not valid:
        logger.warning("Data validation raised issues, but continuing for testing purposes")
    
    # Load data to vector database
    logger.info("Loading data to vector database...")
    if not pipeline.load_to_vector_db():
        logger.error("Failed to load data to vector database")
        return False
    
    logger.info("Data pipeline test completed successfully")
    return True

def test_vector_store():
    """Test the vector store retrieval functionality."""
    logger.info("=== Testing Vector Store Retrieval ===")
    
    try:
        # Initialize the vector store
        vector_store = VectorStore()
        logger.info("Vector store initialized successfully")
        
        # Test querying return policy
        return_queries = [
            "What is boAt's return policy for damaged items?",
            "How many days do I have to return a product?",
            "Can I get a refund for my headphones?"
        ]
        
        logger.info("Testing return policy queries:")
        for query in return_queries:
            logger.info(f"\nQuery: {query}")
            results = vector_store.query_return_policy(query, n_results=2)
            logger.info(f"Found {len(results)} results")
            
            for i, result in enumerate(results):
                logger.info(f"Result {i+1}:")
                metadata = result.get("metadata", {})
                logger.info(f"  Title: {metadata.get('title', 'N/A')}")
                logger.info(f"  Score: {result.get('score', 'N/A')}")
                content = result.get("content", "")
                logger.info(f"  Content: {content[:100]}..." if len(content) > 100 else f"  Content: {content}")
        
        # Test querying service centers
        service_queries = [
            "Where can I find a service center in Maharashtra?",
            "Is there a boAt service center in Delhi?",
            "What are the service center locations near me?"
        ]
        
        logger.info("\nTesting service center queries:")
        for query in service_queries:
            logger.info(f"\nQuery: {query}")
            results = vector_store.query_service_centers(query, n_results=2)
            logger.info(f"Found {len(results)} results")
            
            for i, result in enumerate(results):
                logger.info(f"Result {i+1}:")
                metadata = result.get("metadata", {})
                logger.info(f"  State: {metadata.get('state', 'N/A')}")
                logger.info(f"  Address: {metadata.get('address', 'N/A')}")
                logger.info(f"  Contact: {metadata.get('contact', 'N/A')}")
                logger.info(f"  Score: {result.get('score', 'N/A')}")
        
        logger.info("Vector store test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error testing vector store: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    logger.info("Starting ChromaDB and Data Ingestion tests")
    
    # Test data pipeline
    pipeline_result = test_data_pipeline()
    if not pipeline_result:
        logger.error("Data pipeline test failed")
    
    # Test vector store
    vector_store_result = test_vector_store()
    if not vector_store_result:
        logger.error("Vector store test failed")
    
    # Overall result
    if pipeline_result and vector_store_result:
        logger.info("All tests passed successfully! ✅")
        return 0
    else:
        logger.error("Some tests failed! ❌")
        return 1

if __name__ == "__main__":
    exit(main()) 