"""
Main entry point to run the boAt Customer Support Chatbot application.

This script provides commands to:
1. Run the web scraper to fetch information from boAt's website
2. Process scraped content directly into the vector database
3. Run the FastAPI server for the chatbot interface

The application uses ChromaDB as its vector database with embeddings 
generated directly from scraped content without requiring the Gemini API.
This direct loading approach processes raw scraped content into structured
information suitable for vector storage and retrieval.
"""
import os
import sys
import argparse
import logging
import json
import dotenv
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import WebSocketRoute, Route, Mount
from starlette.responses import FileResponse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
dotenv.load_dotenv()

# Try to import uvicorn, handle case when it's not installed
try:
    import uvicorn
except ImportError:
    logger.error("uvicorn package is not installed. Please install it with 'pip install uvicorn'")
    uvicorn = None

def create_app():
    """Create and configure the FastAPI app with our frontend"""
    # Create a new FastAPI app
    app = FastAPI()
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Import the API server app and get its WebSocket handler
    from src.api.server import app as server_app
    from src.api.server import websocket_endpoint
    
    # Get the frontend directory path
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src/frontend")
    logger.info(f"Using frontend directory: {frontend_dir}")
    
    # Serve index.html at the root
    @app.get("/")
    async def get_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))
    
    # Mount static files directory for all frontend assets
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
    
    # Add WebSocket endpoint directly to our app
    @app.websocket("/ws/chat/{conversation_id}")
    async def ws_endpoint(websocket: WebSocket, conversation_id: str):
        await websocket_endpoint(websocket, conversation_id)
    
    # Add API routes from the server app
    for route in server_app.routes:
        if isinstance(route, WebSocketRoute):
            # Skip WebSocket routes as we've already added our own
            continue
        elif isinstance(route, Route) and not route.path.startswith("/ws"):
            # Add HTTP routes with /api prefix
            path = f"/api{route.path}" if route.path != "/" else "/api"
            app.routes.append(Route(path, route.endpoint, methods=route.methods))
    
    return app

def run_server():
    """Run the FastAPI server"""
    # Check if uvicorn is installed
    if uvicorn is None:
        logger.error("Cannot run server: uvicorn is not installed. Please install it with 'pip install uvicorn'")
        return {"error": "uvicorn not installed"}
    
    # Create the app with our frontend mounted
    app = create_app()
    
    # Run the server
    port = int(os.getenv("SERVER_PORT", 8000))
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    
    logger.info(f"Starting server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)

def scrape_data():
    """Run the web scraper to fetch data"""
    import subprocess
    import sys
    from pathlib import Path
    
    logger.info("Starting web scraper")
    
    # Run the web_scraper.py directly
    web_scraper_path = Path(__file__).parent / "src" / "scraper" / "web_scraper.py"
    
    # Check if the file exists
    if not web_scraper_path.exists():
        logger.error(f"Web scraper script not found at {web_scraper_path}")
        return {"error": f"Web scraper script not found at {web_scraper_path}"}
    
    # Run the web scraper script as a subprocess
    try:
        logger.info(f"Executing {web_scraper_path}")
        result = subprocess.run(
            [sys.executable, str(web_scraper_path)],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"Web scraper output:\n{result.stdout}")
        return {"status": "success", "message": "Scraping completed successfully"}
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running web scraper: {e}")
        logger.error(f"Stderr: {e.stderr}")
        return {"error": f"Error running web scraper: {e.stderr}"}

def build_vector_db():
    """Build the vector database from scraped data using the direct loader"""
    # Import the DirectLoader
    from src.utils.direct_loader import DirectLoader
    
    logger.info("Building vector database using direct loader")
    
    # Create a DirectLoader instance
    loader = DirectLoader()
    
    # Run the direct loading pipeline
    success = loader.run_pipeline()
    
    if success:
        logger.info("Vector database built successfully using direct loader")
        return {"status": "success", "message": "Vector database built successfully"}
    else:
        logger.error("Failed to build vector database")
        return {"status": "error", "message": "Failed to build vector database"}

def main():
    """Main entry point with command line arguments"""
    parser = argparse.ArgumentParser(description="boAt Customer Support Chatbot")
    parser.add_argument("--scrape", action="store_true", help="Run the web scraper to fetch data")
    parser.add_argument("--build-db", action="store_true", help="Build the vector database from scraped data")
    parser.add_argument("--direct-load", action="store_true", help="Directly load scraped content to vector database without Gemini processing")
    parser.add_argument("--serve", action="store_true", help="Start the FastAPI server")
    parser.add_argument("--all", action="store_true", help="Run everything: scrape, build DB, and start server")
    # Add arguments from task6_runner.py for server configuration
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code changes")
    
    args = parser.parse_args()
    
    # If no arguments are provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    # Run all steps if --all is specified
    if args.all:
        scrape_data()
        build_vector_db()
        # Use args for server configuration
        if uvicorn is None:
            logger.error("Cannot run server: uvicorn is not installed. Please install it with 'pip install uvicorn'")
            return
        run_server()
        return
    
    # Otherwise run specific steps as requested
    if args.scrape:
        scrape_data()
    
    if args.build_db or args.direct_load:
        build_vector_db()
    
    if args.serve:
        # Check if uvicorn is installed
        if uvicorn is None:
            logger.error("Cannot run server: uvicorn is not installed. Please install it with 'pip install uvicorn'")
            return
        
        # Pass server configuration from args
        app = create_app()
        
        # Get port from args.port or env variable
        port = args.port or int(os.getenv("SERVER_PORT", 8000))
        host = args.host or os.getenv("SERVER_HOST", "0.0.0.0")
        
        logger.info(f"Starting server at http://{host}:{port}")
        uvicorn.run(
            app, 
            host=host, 
            port=port,
            reload=args.reload
        )

if __name__ == "__main__":
    main() 