"""
Main FastAPI application for the boAt Customer Support Chatbot.
This file will contain the FastAPI server with WebSocket support.
"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
import os
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="boAt Customer Support Chatbot",
    description="AI-powered virtual assistant for boAt customer support",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "boAt Customer Support Chatbot API",
        "status": "online",
        "version": "0.1.0",
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# WebSocket endpoint for chat
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        # Placeholder for actual chat functionality
        await websocket.send_json({
            "type": "info",
            "message": "Connected to boAt Customer Support Chatbot. This is a placeholder."
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info(f"Received message: {data}")
            
            # Echo the message back as a placeholder
            await websocket.send_json({
                "type": "response",
                "message": f"Placeholder response to: {data}"
            })
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info("WebSocket connection closed")

# This will be replaced with actual agent integration later
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVER_PORT", 8000))
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    uvicorn.run("app:app", host=host, port=port, reload=True) 