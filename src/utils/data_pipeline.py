#!/usr/bin/env python3
"""
Data pipeline module for integrating text preprocessing, data validation, and vector database.

This module handles the complete flow from raw scraped content to processed and validated
data ready for vector database insertion.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Import our custom modules
from src.utils.gemini_processor import GeminiProcessor
from src.utils.data_validator import validate_processed_data_file, validate_vector_docs_file
from src.database.vector_store import VectorStore

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataPipeline:
    """
    End-to-end data pipeline integrating text preprocessing, validation, and database operations.
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the data pipeline.
        
        Args:
            data_dir: Directory for storing data files
        """
        self.data_dir = data_dir
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Set up paths
        self.scraped_content_path = os.path.join(self.data_dir, "scraped_content.json")
        self.processed_data_path = os.path.join(self.data_dir, "gemini_processed.json")
        self.vector_docs_path = os.path.join(self.data_dir, "gemini_vector_docs.json")
        
        # Initialize components
        self.gemini_processor = GeminiProcessor()
        self.vector_store = None  # Initialized on demand
        
        logger.info("Data pipeline initialized")
    
    def process_scraped_data(self) -> bool:
        """
        Process scraped content using Gemini.
        
        Returns:
            True if processing was successful, False otherwise
        """
        if not os.path.exists(self.scraped_content_path):
            logger.error(f"Scraped content file not found: {self.scraped_content_path}")
            return False
        
        try:
            logger.info(f"Processing scraped content from: {self.scraped_content_path}")
            processed_data = self.gemini_processor.process_scraped_json(
                self.scraped_content_path, 
                self.processed_data_path
            )
            
            # Prepare documents for vector database
            logger.info("Preparing documents for vector database")
            vector_docs = self.gemini_processor.prepare_for_vectordb(processed_data)
            
            # Save vector docs
            with open(self.vector_docs_path, 'w', encoding='utf-8') as f:
                json.dump(vector_docs, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Vector database documents saved to: {self.vector_docs_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing scraped data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def validate_data(self, verbose: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate processed data and vector docs.
        
        Args:
            verbose: Show detailed validation report
            
        Returns:
            Tuple of (all_valid, combined_report)
        """
        combined_report = {
            "processed_data": None,
            "vector_docs": None,
            "all_valid": False
        }
        
        # Validate processed data
        logger.info(f"Validating processed data: {self.processed_data_path}")
        processed_valid, processed_report = validate_processed_data_file(self.processed_data_path)
        combined_report["processed_data"] = processed_report
        
        if processed_valid:
            logger.info(f"✅ Processed data validation passed: {processed_report['valid_items']}/{processed_report['total_items']} items valid")
        else:
            logger.error(f"❌ Processed data validation failed: {processed_report['valid_items']}/{processed_report['total_items']} items valid")
            if verbose:
                for item_idx, issues in processed_report["issues_by_item"].items():
                    logger.info(f"  Item {item_idx}:")
                    for issue in issues:
                        logger.info(f"    - {issue}")
                
                if processed_report["overall_issues"]:
                    logger.info("Overall issues:")
                    for issue in processed_report["overall_issues"]:
                        logger.info(f"  - {issue}")
        
        # Validate vector docs
        logger.info(f"Validating vector documents: {self.vector_docs_path}")
        vector_valid, vector_report = validate_vector_docs_file(self.vector_docs_path)
        combined_report["vector_docs"] = vector_report
        
        if vector_valid:
            logger.info(f"✅ Vector documents validation passed: {vector_report['valid_docs']}/{vector_report['total_docs']} documents valid")
        else:
            logger.error(f"❌ Vector documents validation failed: {vector_report['valid_docs']}/{vector_report['total_docs']} documents valid")
            if verbose:
                for doc_idx, issues in vector_report["issues_by_doc"].items():
                    logger.info(f"  Document {doc_idx}:")
                    for issue in issues:
                        logger.info(f"    - {issue}")
                
                if vector_report["overall_issues"]:
                    logger.info("Overall issues:")
                    for issue in vector_report["overall_issues"]:
                        logger.info(f"  - {issue}")
        
        # Check if all validations passed
        all_valid = processed_valid and vector_valid
        combined_report["all_valid"] = all_valid
        
        if all_valid:
            logger.info("🎉 All validations passed!")
        else:
            logger.warning("❌ Some validations failed. Fix issues before proceeding.")
        
        return all_valid, combined_report
    
    def load_to_vector_db(self) -> bool:
        """
        Load validated vector documents into the vector database.
        
        Returns:
            True if loading was successful, False otherwise
        """
        try:
            # Initialize vector store if not already done
            if self.vector_store is None:
                self.vector_store = VectorStore()
            
            # Load vector documents
            with open(self.vector_docs_path, 'r', encoding='utf-8') as f:
                vector_docs = json.load(f)
            
            # Process documents by category
            return_policy_docs = []
            service_center_docs = []
            
            for doc in vector_docs:
                if not doc.get('metadata'):
                    logger.warning(f"Document missing metadata: {doc.get('id')}")
                    continue
                
                category = doc['metadata'].get('category')
                
                if category == 'Return Policy':
                    return_policy_docs.append({
                        "title": doc['id'],
                        "content": doc['text']
                    })
                elif category == 'Service Centers':
                    # Extract states and split into separate documents
                    text = doc['text']
                    
                    # Basic structure for service centers
                    service_centers = []
                    
                    # Extract state names from text (very simplified approach)
                    states_section = ""
                    if "boAt has service centers in the following states:" in text:
                        states_section = text.split("boAt has service centers in the following states:")[1].split("\n\n")[0]
                    
                    # Process each state
                    for line in states_section.strip().split("\n"):
                        if line.startswith("- "):
                            state = line[2:].strip()
                            service_centers.append({
                                "state": state,
                                "locations": [{
                                    "name": f"boAt Service Center in {state}",
                                    "address": f"Please contact customer support for exact address in {state}",
                                    "contact": doc['metadata'].get('contact_details', "")
                                }]
                            })
                    
                    service_center_docs.extend(service_centers)
            
            # Add documents to vector store
            if return_policy_docs:
                logger.info(f"Adding {len(return_policy_docs)} return policy documents to vector store")
                self.vector_store.add_return_policy_docs(return_policy_docs)
            
            if service_center_docs:
                logger.info(f"Adding {len(service_center_docs)} service center locations to vector store")
                self.vector_store.add_service_center_docs(service_center_docs)
            
            logger.info("Successfully loaded documents into vector database")
            return True
            
        except Exception as e:
            logger.error(f"Error loading to vector database: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_pipeline(self, validate: bool = True, verbose: bool = False) -> bool:
        """
        Run the complete data pipeline.
        
        Args:
            validate: Whether to validate the data
            verbose: Show detailed validation report
            
        Returns:
            True if the pipeline completed successfully, False otherwise
        """
        # Step 1: Process scraped data
        process_success = self.process_scraped_data()
        if not process_success:
            logger.error("Failed to process scraped data. Pipeline stopped.")
            return False
        
        # Step 2: Validate data (optional)
        if validate:
            validation_success, _ = self.validate_data(verbose=verbose)
            if not validation_success:
                logger.warning("Data validation failed. Proceeding with caution...")
        
        # Step 3: Load to vector database
        db_success = self.load_to_vector_db()
        if not db_success:
            logger.error("Failed to load data to vector database. Pipeline stopped.")
            return False
        
        logger.info("🎉 Data pipeline completed successfully!")
        return True

def main():
    """Main function for running the data pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the boAt chatbot data pipeline")
    parser.add_argument("--data-dir", default="data", help="Directory for data files")
    parser.add_argument("--skip-validation", action="store_true", help="Skip data validation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    
    args = parser.parse_args()
    
    pipeline = DataPipeline(data_dir=args.data_dir)
    success = pipeline.run_pipeline(
        validate=not args.skip_validation,
        verbose=args.verbose
    )
    
    if not success:
        logger.error("Pipeline failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main()) 