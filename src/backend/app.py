"""
Main FastAPI application for the boAt Customer Support Chatbot.
This file will contain the FastAPI server with WebSocket support.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Path
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
import os
import dotenv
import uuid
from typing import Dict, Any

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

# Store active connections
active_connections: Dict[str, WebSocket] = {}

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
@app.websocket("/ws/chat/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    conversation_id: str = Path(..., description="Unique ID for the conversation")
):
    await websocket.accept()
    active_connections[conversation_id] = websocket
    logger.info(f"WebSocket connection established for conversation: {conversation_id}")
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "info",
            "message": "Connected to boAt Customer Support Chatbot. How can I help you today?"
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info(f"Received message from {conversation_id}: {data}")
            
            try:
                # Parse the message
                message_data = json.loads(data)
                user_message = message_data.get("message", "")
                
                if not user_message:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Please provide a message."
                    })
                    continue
                
                # In a real implementation, this would call the RAG system
                # For now, we'll use a simple placeholder response
                if "return" in user_message.lower() or "refund" in user_message.lower():
                    response = "For returns and refunds, boAt offers a 7-day replacement policy. You can initiate a return through our website or app by going to My Orders and selecting the item you wish to return."
                elif "service" in user_message.lower() or "center" in user_message.lower():
                    response = "We have service centers across India. You can find the nearest one by visiting our website's support section and entering your city or PIN code."
                else:
                    response = f"Thank you for your question about '{user_message}'. Our customer support team is processing your request. How else can I assist you today?"
                
                # Send response back to client
                await websocket.send_json({
                    "type": "response",
                    "message": response
                })
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {data}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid message format. Please send a valid JSON object."
                })
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "An error occurred while processing your request."
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for conversation: {conversation_id}")
        if conversation_id in active_connections:
            del active_connections[conversation_id]
    except Exception as e:
        logger.error(f"WebSocket error for conversation {conversation_id}: {e}")
        if conversation_id in active_connections:
            del active_connections[conversation_id]

# This will be replaced with actual agent integration later
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVER_PORT", 8000))
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    uvicorn.run("app:app", host=host, port=port, reload=True) 