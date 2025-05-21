#!/usr/bin/env python3
"""
FastAPI Server with WebSocket Support for boAt Customer Support Chatbot

This module implements a FastAPI server with WebSocket support for real-time
communication with the boAt customer support chatbot, which uses AutoGen agents
and RAG to provide helpful responses about return policies and service centers.
"""

import json
import uuid
import logging
import os
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import our existing agent system and orchestrator
from src.agents.autogen_wrapper import AutoGenAgentSystem
from src.agents.orchestrator import Orchestrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="boAt Customer Support Chatbot API",
    description="API for interacting with the boAt customer support chatbot powered by AutoGen and RAG",
    version="1.0.0"
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Get the directory of this file
current_dir = os.path.dirname(os.path.abspath(__file__))

# Mount static files directory
static_dir = os.path.join(current_dir, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    logger.warning(f"Static directory not found: {static_dir}")

# Store active connections and conversation history
active_connections: Dict[str, WebSocket] = {}
conversation_history: Dict[str, List[Dict[str, Any]]] = {}

# Models for API requests and responses
class ChatRequest(BaseModel):
    """Request model for starting a new chat session"""
    user_id: Optional[str] = None

class MessageRequest(BaseModel):
    """Request model for sending a message via the REST API"""
    conversation_id: str
    message: str

class MessageResponse(BaseModel):
    """Response model for chat messages"""
    conversation_id: str
    message: str
    sender: str

# Create a single orchestrator instance for the application
orchestrator = Orchestrator()

# Application startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize resources when the application starts"""
    logger.info("Starting up the boAt Customer Support Chatbot API")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources when the application shuts down"""
    logger.info("Shutting down the boAt Customer Support Chatbot API")
    # Close all active WebSocket connections
    for connection in active_connections.values():
        await connection.close()

# Serve the chat client HTML page
@app.get("/")
async def get_chat_client():
    """Serve the chat client HTML page"""
    html_path = os.path.join(static_dir, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    else:
        logger.error(f"Chat client HTML file not found: {html_path}")
        return {"error": "Chat client HTML file not found"}

# REST API endpoints
@app.post("/api/chat/start", response_model=dict)
async def start_chat(request: ChatRequest):
    """
    Start a new chat session and return a conversation_id
    
    Args:
        request: The chat request with optional user_id
        
    Returns:
        A dictionary with the conversation_id
    """
    # Generate a unique conversation ID if not provided
    user_id = request.user_id or str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    
    # Initialize conversation history
    conversation_history[conversation_id] = []
    
    logger.info(f"Started new chat session with conversation_id: {conversation_id}")
    
    return {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "message": "Chat session started successfully"
    }

@app.post("/api/chat/message", response_model=MessageResponse)
async def send_message(request: MessageRequest):
    """
    Send a message to the chatbot using the REST API
    
    Args:
        request: The message request with conversation_id and message
        
    Returns:
        The response from the chatbot
    """
    conversation_id = request.conversation_id
    
    # Check if conversation exists
    if conversation_id not in conversation_history:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Store user message in conversation history
    conversation_history[conversation_id].append({
        "sender": "user",
        "message": request.message
    })
    
    # Process message with Orchestrator
    try:
        # Use the async version for better FastAPI integration
        response = await orchestrator.process_query_async(request.message)
        
        # Extract just the response text if the response is a complex object
        processed_response = response
        if isinstance(response, dict) and "response_text" in response:
            processed_response = response["response_text"]
        elif isinstance(response, str):
            processed_response = response
        
        # Store bot response in conversation history
        conversation_history[conversation_id].append({
            "sender": "bot",
            "message": processed_response
        })
        
        return MessageResponse(
            conversation_id=conversation_id,
            message=processed_response,
            sender="bot"
        )
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.get("/api/chat/history/{conversation_id}")
async def get_chat_history(conversation_id: str):
    """
    Get the chat history for a conversation
    
    Args:
        conversation_id: The ID of the conversation
        
    Returns:
        The chat history
    """
    if conversation_id not in conversation_history:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "conversation_id": conversation_id,
        "history": conversation_history[conversation_id]
    }

# WebSocket endpoint for real-time chat
@app.websocket("/ws/chat/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    """
    WebSocket endpoint for real-time chat
    
    Args:
        websocket: The WebSocket connection
        conversation_id: The ID of the conversation
    """
    await websocket.accept()
    
    # Initialize conversation if it doesn't exist
    if conversation_id not in conversation_history:
        conversation_history[conversation_id] = []
    
    # Store the connection
    active_connections[conversation_id] = websocket
    
    try:
        # Send welcome message
        welcome_message = {
            "sender": "bot",
            "message": "Hello! I'm the boAt customer support assistant. I can help you with information about return policies, warranty, and service center locations. How can I assist you today?",
            "conversation_id": conversation_id
        }
        await websocket.send_text(json.dumps(welcome_message))
        conversation_history[conversation_id].append({
            "sender": "bot",
            "message": welcome_message["message"]
        })
        
        # Handle messages
        while True:
            # Receive message from WebSocket
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            # Store user message in conversation history
            conversation_history[conversation_id].append({
                "sender": "user",
                "message": user_message
            })
            
            # Process message with Orchestrator
            response = await orchestrator.process_query_async(user_message)
            
            # Extract just the response text if the response is a complex object
            processed_response = response
            if isinstance(response, dict) and "response_text" in response:
                processed_response = response["response_text"]
            elif isinstance(response, str):
                processed_response = response
            
            # Store bot response in conversation history
            conversation_history[conversation_id].append({
                "sender": "bot",
                "message": processed_response
            })
            
            # Send response back to WebSocket
            await websocket.send_text(json.dumps({
                "sender": "bot",
                "message": processed_response,
                "conversation_id": conversation_id
            }))
            
    except WebSocketDisconnect:
        # Clean up when client disconnects
        if conversation_id in active_connections:
            del active_connections[conversation_id]
        logger.info(f"WebSocket client disconnected: {conversation_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {str(e)}")
        await websocket.close(code=1011, reason=f"Error: {str(e)}")
        if conversation_id in active_connections:
            del active_connections[conversation_id]

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

# Run the server directly when the script is executed
if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True) 