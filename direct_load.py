#!/usr/bin/env python3
"""
Script to directly load scraped content into the vector database.

This script bypasses the Gemini API processing step and loads the scraped
content directly into the vector database using local text processing.
"""
import os
import sys
import json
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# Import the direct loader
from src.utils.direct_loader import DirectLoader

def print_separator():
    print("=" * 80)

def print_section(title):
    print_separator()
    print(f"  {title.upper()}")
    print_separator()

def main():
    print_section("boAt Chatbot Direct Data Loader")
    
    print("\nThis script will load scraped content directly into the vector database.")
    print("It bypasses the Gemini API processing and uses local text processing instead.")
    print("The results will be saved in the 'data' directory and loaded into ChromaDB.\n")
    
    # Check if the scraped content exists
    scraped_content_path = Path("data/scraped_content.json")
    if not scraped_content_path.exists():
        print(f"❌ Scraped content file not found: {scraped_content_path}")
        print("Please run the scraper first using run_scraper.py.")
        return 1
    
    # Count items in scraped content
    try:
        with open(scraped_content_path, 'r', encoding='utf-8') as f:
            scraped_data = json.load(f)
        
        return_policy_count = sum(1 for item in scraped_data 
                                if 'return-policy' in item.get('url', '') 
                                or item.get('category', '').lower() == 'return_policy')
        
        service_center_count = sum(1 for item in scraped_data 
                                  if 'service-center' in item.get('url', '') 
                                  or item.get('category', '').lower() == 'service_center')
        
        print(f"Found {len(scraped_data)} items in scraped content:")
        print(f"  - Return policy items: {return_policy_count}")
        print(f"  - Service center items: {service_center_count}")
        print()
    except Exception as e:
        print(f"❌ Error reading scraped content: {e}")
        return 1
    
    # Confirm with user
    choice = input("Do you want to proceed with loading this content into the vector database? (y/n) [Default: y]: ").strip().lower() or "y"
    
    if choice != "y":
        print("\nOperation cancelled by user.")
        return 0
    
    print("\nProceeding with direct loading...\n")
    
    # Create and run the direct loader
    try:
        print_section("Processing Scraped Content")
        loader = DirectLoader()
        success = loader.run_pipeline()
        
        if success:
            print_section("Results")
            print("\n✅ Successfully loaded content into vector database!")
            
            # Check if the processed files exist
            return_policy_path = Path("data/direct_return_policy.json")
            service_centers_path = Path("data/direct_service_centers.json")
            
            if return_policy_path.exists():
                with open(return_policy_path, 'r', encoding='utf-8') as f:
                    return_policy_data = json.load(f)
                print(f"Return policy documents: {len(return_policy_data)}")
            
            if service_centers_path.exists():
                with open(service_centers_path, 'r', encoding='utf-8') as f:
                    service_centers_data = json.load(f)
                locations_count = sum(len(state.get("locations", [])) for state in service_centers_data)
                print(f"Service center locations: {locations_count} across {len(service_centers_data)} states")
            
            print("\nYou can now use these embeddings in your chatbot!")
            print("The vector database has been updated with the processed content.")
            
            return 0
        else:
            print_section("Error")
            print("\n❌ Failed to load content into vector database.")
            print("Check the logs for details on what went wrong.")
            return 1
        
    except Exception as e:
        print_section("Error")
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 