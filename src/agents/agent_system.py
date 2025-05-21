#!/usr/bin/env python3
"""
AutoGen Multi-Agent System for boAt Customer Support Chatbot.

This module implements a multi-agent system using AutoGen for handling
customer support queries about boAt's products, return policies, and service centers.
"""

import os
import logging
import json
import autogen
import dotenv
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

# Load environment variables
dotenv.load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AgentRole(Enum):
    """Roles of agents in the system."""
    ORCHESTRATOR = "orchestrator"
    QUERY_ANALYZER = "query_analyzer"
    RETRIEVAL = "retrieval"
    RESPONSE_GENERATOR = "response_generator"
    USER = "user"

class AgentSystem:
    """
    Multi-agent system for boat customer support using AutoGen.
    
    This system uses multiple agents to:
    1. Analyze customer queries
    2. Retrieve relevant information
    3. Generate appropriate responses
    4. Coordinate the overall workflow
    """
    
    def __init__(self, 
                config_list: Optional[List[Dict[str, Any]]] = None,
                verbose: bool = False):
        """
        Initialize the agent system.
        
        Args:
            config_list: LLM configuration for AutoGen
            verbose: Whether to show detailed agent conversations
        """
        self.verbose = verbose
        
        # Set up LLM config
        if config_list is None:
            # Default to Gemini if available
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                self.config_list = [
                    {
                        "model": "gemini-2.0-flash",
                        "api_key": api_key,
                        "api_type": "google",
                    }
                ]
            else:
                # Fallback to OpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self.config_list = [
                        {
                            "model": "gpt-3.5-turbo",
                            "api_key": api_key,
                        }
                    ]
                else:
                    raise ValueError("No API keys found for LLM services (Google or OpenAI)")
        else:
            self.config_list = config_list
            
        # Initialize the agents
        self._setup_agents()
        logger.info("Agent system initialized")
    
    def _setup_agents(self):
        """Set up the agents and their relationships."""
        # Create orchestrator agent
        self.orchestrator = autogen.AssistantAgent(
            name="Orchestrator",
            system_message="""You are the orchestrator agent for a boAt customer support system.
            Your role is to:
            1. Receive customer queries
            2. Direct the query to the appropriate specialist agent
            3. Ensure the customer receives a complete and accurate response
            4. Maintain the conversation flow
            
            Work with the QueryAnalyzer, RetrievalSpecialist, and ResponseGenerator agents to fulfill customer requests.
            """,
            llm_config={"config_list": self.config_list},
        )
        
        # Create query analyzer agent
        self.query_analyzer = autogen.AssistantAgent(
            name="QueryAnalyzer",
            system_message="""You are the query analyzer for a boAt customer support system.
            Your role is to:
            1. Analyze customer queries to identify their intent and type
            2. Classify queries into categories (return policy, service center location, etc.)
            3. Extract key parameters needed for information retrieval
            4. Rewrite ambiguous queries to be more specific
            
            Process the query and report your analysis to the Orchestrator.
            """,
            llm_config={"config_list": self.config_list},
        )
        
        # Create retrieval specialist agent
        self.retrieval_specialist = autogen.AssistantAgent(
            name="RetrievalSpecialist",
            system_message="""You are the retrieval specialist for a boAt customer support system.
            Your role is to:
            1. Receive query analysis from the QueryAnalyzer
            2. Use the vector database to retrieve relevant information
            3. Filter and rank the retrieved information by relevance
            4. Provide the most accurate and helpful information to the ResponseGenerator
            
            Always cite the source of your information when reporting to the Orchestrator.
            """,
            llm_config={"config_list": self.config_list},
        )
        
        # Create response generator agent
        self.response_generator = autogen.AssistantAgent(
            name="ResponseGenerator",
            system_message="""You are the response generator for a boAt customer support system.
            Your role is to:
            1. Receive relevant information from the RetrievalSpecialist
            2. Craft a clear, helpful, and accurate response for the customer
            3. Ensure the response directly addresses the customer's query
            4. Maintain a friendly, professional tone consistent with boAt's brand voice
            
            Generate the response and send it to the Orchestrator to deliver to the customer.
            """,
            llm_config={"config_list": self.config_list},
        )
        
        # Create user proxy agent
        self.user_proxy = autogen.UserProxyAgent(
            name="Customer",
            human_input_mode="ALWAYS" if self.verbose else "TERMINATE",
            code_execution_config=False,  # No code execution needed
        )
        
        # Register agent functions will be implemented in separate methods
        
    def start_conversation(self, initial_message: Optional[str] = None):
        """
        Start a conversation with the agent system.
        
        Args:
            initial_message: The initial customer query
        """
        if initial_message:
            # Start with a specific message
            self.user_proxy.initiate_chat(
                self.orchestrator,
                message=initial_message
            )
        else:
            # Default welcome message
            welcome_message = (
                "Hello! I'm the boAt customer support assistant. "
                "I can help you with information about return policies, warranty, "
                "and service center locations. How can I assist you today?"
            )
            self.orchestrator.send(welcome_message, self.user_proxy)
            
            # Continue the conversation
            self.user_proxy.human_input()
    
    def query_without_interaction(self, query: str) -> str:
        """
        Process a query without interactive conversation for API mode.
        
        Args:
            query: The customer query
            
        Returns:
            The generated response
        """
        # To be implemented
        pass


# For testing purposes
if __name__ == "__main__":
    agent_system = AgentSystem(verbose=True)
    agent_system.start_conversation() 