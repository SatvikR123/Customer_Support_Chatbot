#!/usr/bin/env python3
"""
Direct loader for scraped content to vector database.

This module directly processes scraped content into a format suitable
for storage in the vector database, bypassing the Gemini API processing.
"""

import os
import json
import logging
import sys
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to Python path for relative imports if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import vector store
from src.database.vector_store import VectorStore

class DirectLoader:
    """
    Process scraped content directly into the vector database without using Gemini API.
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the direct loader.
        
        Args:
            data_dir: Directory containing data files
        """
        self.data_dir = data_dir
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Set up paths
        self.scraped_content_path = os.path.join(self.data_dir, "scraped_content.json")
        self.return_policy_path = os.path.join(self.data_dir, "direct_return_policy.json")
        self.service_centers_path = os.path.join(self.data_dir, "direct_service_centers.json")
        
        # Initialize vector store
        self.vector_store = VectorStore()
        
        logger.info("Direct loader initialized")
    
    def process_return_policy(self, content: str) -> List[Dict[str, str]]:
        """
        Process return policy content into documents for the vector database.
        
        Args:
            content: Raw content from the return policy page
            
        Returns:
            List of documents ready for the vector database
        """
        # Split the content into sections for better retrieval
        docs = []
        
        # Clean up the content - remove common navigation elements and headers
        cleaned_content = content
        for term in ["Categories", "Navigation", "boAt Lifestyle", "Newsletter", "Search", "Most Searched & Bought"]:
            cleaned_content = cleaned_content.replace(term, "")
        
        # Simple section detection in the return policy content
        sections = [
            "Return Policy",
            "Replacement Policy",
            "Cancellation Policy",
            "Product Pricing",
            "Security",
            "Out of Stock situations",
            "Delivery of products",
            "Delivery Charges"
        ]
        
        section_texts = {}
        current_section = None
        
        for line in cleaned_content.split("\n"):
            line = line.strip()
            if not line:
                continue
                
            # Check if this line is a section header
            if line in sections:
                current_section = line
                section_texts[current_section] = []
            elif current_section:
                section_texts[current_section].append(line)
        
        # Create documents for each section
        for section, lines in section_texts.items():
            if lines:
                docs.append({
                    "title": f"boAt {section}",
                    "content": f"boAt {section}:\n\n" + "\n".join(lines)
                })
        
        # If no sections were found, create a single document with the cleaned content
        if not docs:
            docs.append({
                "title": "boAt Return Policy",
                "content": cleaned_content
            })
        
        return docs
    
    def process_service_centers(self, raw_content: str, structured_content: Dict) -> List[Dict[str, Any]]:
        """
        Process service center information into documents for the vector database.
        
        Args:
            raw_content: Raw content from the service centers page
            structured_content: Structured content from the scraper
            
        Returns:
            List of service center information by state
        """
        service_centers = []
        
        # Use structured content if available
        if structured_content and "service_centers" in structured_content:
            return structured_content["service_centers"]
        
        # Extract state names from the raw content
        # This is a fallback in case structured content is not available
        lines = raw_content.split("\n")
        states = []
        
        for line in lines:
            line = line.strip()
            # Look for state names in the content
            if line and len(line) < 50 and line not in ["Categories", "Navigation", "Search"]:
                # Some basic filtering to find state names
                if "boAt" not in line.lower() and "shop" not in line.lower():
                    states.append(line)
        
        # Create a document for each state
        for state in states[:30]:  # Limit to likely states
            service_centers.append({
                "state": state,
                "locations": [{
                    "name": f"boAt Service Center in {state}",
                    "address": f"Please visit boAt website for detailed address information in {state}",
                    "contact": "customer.service@imaginemarketingindia.com"
                }]
            })
        
        return service_centers
    
    def load_scraped_content(self) -> bool:
        """
        Load scraped content and prepare it for the vector database.
        
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(self.scraped_content_path):
            logger.error(f"Scraped content file not found: {self.scraped_content_path}")
            return False
        
        try:
            # Load scraped content
            with open(self.scraped_content_path, 'r', encoding='utf-8') as f:
                scraped_data = json.load(f)
            
            logger.info(f"Loaded scraped content from: {self.scraped_content_path}")
            
            # Process return policy and service centers
            return_policy_docs = []
            service_centers = []
            
            for item in scraped_data:
                url = item.get('url', '')
                category = item.get('category', '')
                raw_content = item.get('raw_content', '')
                structured_content = item.get('structured_content', {})
                
                if 'return-policy' in url or category.lower() == 'return_policy':
                    # Process return policy
                    docs = self.process_return_policy(raw_content)
                    return_policy_docs.extend(docs)
                    
                elif 'service-center' in url or category.lower() == 'service_center':
                    # Process service centers
                    centers = self.process_service_centers(raw_content, structured_content)
                    service_centers.extend(centers)
            
            # Save processed documents
            if return_policy_docs:
                with open(self.return_policy_path, 'w', encoding='utf-8') as f:
                    json.dump(return_policy_docs, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved {len(return_policy_docs)} return policy documents to: {self.return_policy_path}")
            
            if service_centers:
                with open(self.service_centers_path, 'w', encoding='utf-8') as f:
                    json.dump(service_centers, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved service center information for {len(service_centers)} states to: {self.service_centers_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing scraped content: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_to_vector_db(self) -> Dict[str, int]:
        """
        Load processed documents into the vector database.
        
        Returns:
            Dictionary with counts of documents added
        """
        counts = {"return_policy": 0, "service_centers": 0}
        
        try:
            # Load and add return policy data
            if os.path.exists(self.return_policy_path):
                with open(self.return_policy_path, 'r', encoding='utf-8') as f:
                    return_policy_data = json.load(f)
                
                self.vector_store.add_return_policy_docs(return_policy_data)
                counts["return_policy"] = len(return_policy_data)
                logger.info(f"Added {len(return_policy_data)} return policy documents to vector store")
            
            # Load and add service center data
            if os.path.exists(self.service_centers_path):
                with open(self.service_centers_path, 'r', encoding='utf-8') as f:
                    service_centers_data = json.load(f)
                
                self.vector_store.add_service_center_docs(service_centers_data)
                counts["service_centers"] = sum(len(state.get("locations", [])) for state in service_centers_data)
                logger.info(f"Added {counts['service_centers']} service center locations to vector store")
            
            return counts
            
        except Exception as e:
            logger.error(f"Error loading to vector database: {e}")
            import traceback
            traceback.print_exc()
            return {"return_policy": 0, "service_centers": 0}
    
    def run_pipeline(self) -> bool:
        """
        Run the complete direct loading pipeline.
        
        Returns:
            True if successful, False otherwise
        """
        # Load and process scraped content
        if not self.load_scraped_content():
            logger.error("Failed to load and process scraped content")
            return False
        
        # Load to vector database
        counts = self.load_to_vector_db()
        
        success = counts["return_policy"] > 0 or counts["service_centers"] > 0
        if success:
            logger.info(f"Successfully loaded {counts['return_policy']} return policy documents and {counts['service_centers']} service center locations to vector database")
        else:
            logger.error("Failed to load any documents to vector database")
        
        return success

def main():
    """
    Run the direct loader as a standalone script.
    """
    logger.info("Starting direct loading of scraped content to vector database")
    
    loader = DirectLoader()
    success = loader.run_pipeline()
    
    if success:
        logger.info("✅ Direct loading pipeline completed successfully!")
        return 0
    else:
        logger.error("❌ Direct loading pipeline failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 