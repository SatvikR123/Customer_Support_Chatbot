"""
Main entry point to run the boAt Customer Support Chatbot application.
"""
import os
import sys
import argparse
import logging
import uvicorn
import dotenv
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
dotenv.load_dotenv()

def run_server():
    """Run the FastAPI server"""
    from src.backend.app import app as backend_app
    
    # Mount the frontend files
    backend_app.mount("/", StaticFiles(directory="src/frontend", html=True), name="frontend")
    
    # Run the server
    port = int(os.getenv("SERVER_PORT", 8000))
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    
    logger.info(f"Starting server at http://{host}:{port}")
    uvicorn.run(backend_app, host=host, port=port)

def scrape_data():
    """Run the web scraper to fetch data"""
    from src.scraper.scraper import BoatScraper
    
    logger.info("Starting web scraper")
    scraper = BoatScraper()
    results = scraper.run()
    logger.info(f"Scraping completed: {results}")
    return results

def build_vector_db():
    """Build the vector database from scraped data"""
    from src.database.vector_store import VectorStore
    
    logger.info("Building vector database")
    vector_store = VectorStore()
    counts = vector_store.load_and_add_data()
    logger.info(f"Vector database built: {counts}")
    return counts

def main():
    """Main entry point with command line arguments"""
    parser = argparse.ArgumentParser(description="boAt Customer Support Chatbot")
    parser.add_argument("--scrape", action="store_true", help="Run the web scraper to fetch data")
    parser.add_argument("--build-db", action="store_true", help="Build the vector database from scraped data")
    parser.add_argument("--serve", action="store_true", help="Start the FastAPI server")
    parser.add_argument("--all", action="store_true", help="Run everything: scrape, build DB, and start server")
    
    args = parser.parse_args()
    
    # If no arguments are provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    # Run all steps if --all is specified
    if args.all:
        scrape_data()
        build_vector_db()
        run_server()
        return
    
    # Otherwise run specific steps as requested
    if args.scrape:
        scrape_data()
    
    if args.build_db:
        build_vector_db()
    
    if args.serve:
        run_server()

if __name__ == "__main__":
    main() 