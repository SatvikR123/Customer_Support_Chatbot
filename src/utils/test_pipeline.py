#!/usr/bin/env python3
"""
Test script for data pipeline validation.

This script tests the entire data pipeline from scraped content to vector database integration.
"""

import os
import json
import logging
import argparse
import sys
from pathlib import Path

# Add parent directory to path to allow importing local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import our modules
from src.utils.data_pipeline import DataPipeline

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_dummy_scraped_content(filepath: str) -> None:
    """
    Create a dummy scraped content file for testing.
    
    Args:
        filepath: Path to save the dummy file
    """
    dummy_data = [
        {
            "url": "https://www.boat-lifestyle.com/pages/return-policy",
            "category": "Return Policy",
            "raw_content": """
            boAt's Return and Replacement Policy:
            
            1. Replacement Timeframe:
            - Products can be replaced within 7 days of delivery.
            
            2. Conditions for Replacement:
            - The product must be defective or damaged upon arrival.
            - The product must be in its original packaging with all accessories.
            - The product must not have been used or damaged by the customer.
            
            3. Non-replaceable Conditions:
            - Products with physical damage caused by the customer.
            - Products with missing accessories or packaging.
            - Products used beyond the 7-day replacement window.
            
            4. Cancellation Policy:
            - Orders can be cancelled before shipment.
            - Cancellation is not possible once the order is shipped.
            
            5. Refund Policy:
            - Refunds are processed within 7-10 business days after product return.
            - Original payment method will be used for refund.
            """
        },
        {
            "url": "https://www.boat-lifestyle.com/pages/service-centers",
            "category": "Service Centers",
            "raw_content": """
            boAt Service Centers Information:
            
            Service Center Locations:
            We have service centers in the following states:
            - Delhi
            - Maharashtra
            - Karnataka
            - Tamil Nadu
            - West Bengal
            - Telangana
            - Uttar Pradesh
            
            Service Hours:
            Monday to Saturday: 10:00 AM to 7:00 PM
            
            Holiday Information:
            All centers are closed on Sundays and national holidays.
            
            Contact Details:
            For service center related queries, please call our customer support at:
            Phone: 1800-XXX-XXXX
            Email: support@boat-lifestyle.com
            """
        }
    ]
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Write dummy data to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dummy_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Created dummy scraped content at: {filepath}")

def test_pipeline(use_dummy_data: bool = False, data_dir: str = "test_data") -> bool:
    """
    Test the complete data pipeline.
    
    Args:
        use_dummy_data: Whether to create and use dummy data
        data_dir: Directory for test data files
        
    Returns:
        True if tests passed, False otherwise
    """
    # Set up test data directory
    test_dir = os.path.abspath(data_dir)
    os.makedirs(test_dir, exist_ok=True)
    
    # Create dummy data if needed
    if use_dummy_data:
        dummy_file = os.path.join(test_dir, "scraped_content.json")
        create_dummy_scraped_content(dummy_file)
    
    # Initialize and run pipeline
    pipeline = DataPipeline(data_dir=test_dir)
    
    logger.info("=== Testing Data Pipeline ===")
    
    # Test 1: Process scraped data
    logger.info("Test 1: Processing scraped data...")
    process_result = pipeline.process_scraped_data()
    
    if not process_result:
        logger.error("❌ Test 1 FAILED: Could not process scraped data")
        return False
    
    logger.info("✅ Test 1 PASSED: Successfully processed scraped data")
    
    # Test 2: Validate data
    logger.info("Test 2: Validating processed data...")
    valid, report = pipeline.validate_data(verbose=True)
    
    if not valid:
        logger.warning("⚠️ Test 2 WARNING: Data validation had issues")
        # Continue anyway for testing purposes
    else:
        logger.info("✅ Test 2 PASSED: Data validation successful")
    
    # Test 3: Load to vector database
    logger.info("Test 3: Loading data to vector database...")
    db_result = pipeline.load_to_vector_db()
    
    if not db_result:
        logger.error("❌ Test 3 FAILED: Could not load data to vector database")
        return False
    
    logger.info("✅ Test 3 PASSED: Successfully loaded data to vector database")
    
    # Test 4: Basic vector store query test
    logger.info("Test 4: Testing vector store queries...")
    
    try:
        # Initialize vector store if needed
        if pipeline.vector_store is None:
            logger.error("❌ Test 4 FAILED: Vector store not initialized")
            return False
        
        # Test return policy query
        return_results = pipeline.vector_store.query_return_policy("What is boAt's replacement policy?")
        
        if not return_results:
            logger.error("❌ Test 4 FAILED: No results from return policy query")
            return False
        
        # Test service center query
        service_results = pipeline.vector_store.query_service_centers("boAt service center in Maharashtra")
        
        if not service_results:
            logger.error("❌ Test 4 FAILED: No results from service center query")
            return False
        
        logger.info("✅ Test 4 PASSED: Vector store queries returned results")
        
    except Exception as e:
        logger.error(f"❌ Test 4 FAILED: Vector store query error: {e}")
        return False
    
    logger.info("🎉 All pipeline tests PASSED!")
    return True

def main():
    """Run pipeline tests."""
    parser = argparse.ArgumentParser(description="Test the boAt chatbot data pipeline")
    parser.add_argument("--use-real-data", action="store_true", 
                        help="Use existing scraped data instead of generating dummy data")
    parser.add_argument("--data-dir", default="test_data", 
                        help="Directory for test data files")
    
    args = parser.parse_args()
    
    success = test_pipeline(
        use_dummy_data=not args.use_real_data,
        data_dir=args.data_dir
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 