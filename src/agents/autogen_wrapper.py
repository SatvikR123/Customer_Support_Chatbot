#!/usr/bin/env python3
"""
AutoGen Wrapper for boAt Customer Support Chatbot.

This module implements the integration between our specialized agents
and the AutoGen multi-agent framework.
"""

import os
import logging
import json
import autogen
from typing import Dict, List, Any, Optional, Tuple, Callable
import dotenv

# Import our orchestrator and agents
from src.agents.orchestrator import Orchestrator
from src.agents.query_analyzer import QueryAnalyzer
from src.agents.retrieval_agent import RetrievalAgent
from src.agents.response_generator import ResponseGenerator

# Load environment variables
dotenv.load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutoGenAgentSystem:
    """
    Integration of our specialized agents with the AutoGen multi-agent framework.
    
    This class:
    - Creates and configures AutoGen agents
    - Registers our custom agent functions with AutoGen
    - Manages conversations between agents
    - Provides a unified interface for the chatbot
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the AutoGen agent system.
        
        Args:
            verbose: Whether to show detailed agent conversations
        """
        self.verbose = verbose
        
        # Set up LLM config
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            self.config_list = [
                {
                    "model": "gemini-1.5-flash",
                    "api_key": api_key,
                }
            ]
        else:
            raise ValueError("No API keys found for LLM services (Google)")
        
        # Our specialized agent system
        self.orchestrator = Orchestrator()
        
        # Initialize AutoGen agents
        self._setup_agents()
        logger.info("AutoGen agent system initialized")
    
    def _setup_agents(self):
        """Set up all AutoGen agents and register custom functions."""
        # Create the user proxy agent
        self.user_proxy = autogen.UserProxyAgent(
            name="Customer",
            human_input_mode="ALWAYS",  # Always require human input regardless of verbose setting
            code_execution_config=False,  # No code execution needed
        )
        
        # Set up the function map for the retrieval agent
        retrieval_functions = {
            "analyze_query": self._analyze_query,
            "retrieve_information": self._retrieve_information,
            "generate_response": self._generate_response,
            "process_complete_query": self._process_complete_query,
        }
        
        # Create the assistant agent with custom functions
        self.assistant = autogen.AssistantAgent(
            name="boAt_Support",
            system_message="""You are a helpful customer support assistant for boAt Lifestyle, a popular audio electronics company.
            
            Your job is to help customers with questions about:
            - Return policies and procedures
            - Warranty information
            - Service center locations and contacts
            - Basic product troubleshooting
            
            You have access to specialized functions to analyze customer queries, retrieve relevant information, and generate accurate responses.
            
            Always be friendly, professional, and accurate in your responses. If you don't have an answer, be honest about it and suggest alternative ways for the customer to get help.
            
            Use the provided functions whenever appropriate to ensure you give the most accurate and helpful information.
            """,
            llm_config={
                "config_list": self.config_list,
                "functions": [
                    {
                        "name": "analyze_query",
                        "description": "Analyze a customer query to determine its type and extract relevant parameters",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The customer's question or message"
                                }
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "retrieve_information",
                        "description": "Retrieve relevant information based on query analysis results",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query_analysis": {
                                    "type": "object",
                                    "description": "The analysis results from analyze_query function"
                                },
                                "n_results": {
                                    "type": "integer",
                                    "description": "Number of results to retrieve"
                                }
                            },
                            "required": ["query_analysis"]
                        }
                    },
                    {
                        "name": "generate_response",
                        "description": "Generate a human-friendly response based on retrieved information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The original customer query"
                                },
                                "retrieval_results": {
                                    "type": "object",
                                    "description": "Results from the retrieve_information function"
                                }
                            },
                            "required": ["query", "retrieval_results"]
                        }
                    },
                    {
                        "name": "process_complete_query",
                        "description": "Process a complete customer query through all stages at once",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The customer's question or message"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                ]
            }
        )
        
        # Register the functions with the user proxy
        self.user_proxy.register_function(
            function_map=retrieval_functions
        )
    
    def start_conversation(self, initial_message: Optional[str] = None):
        """
        Start a conversation with the AutoGen agent system.
        
        Args:
            initial_message: Optional initial query from the customer
        """
        if initial_message:
            # Start with a specific message
            self.user_proxy.initiate_chat(
                self.assistant,
                message=initial_message
            )
        else:
            # Default welcome message
            welcome_message = (
                "Hello! I'm the boAt customer support assistant. "
                "I can help you with information about return policies, warranty, "
                "and service center locations. How can I assist you today?"
            )
            
            # Initiate chat with welcome message
            self.user_proxy.initiate_chat(
                self.assistant,
                message=f"HELP: {welcome_message}"
            )
    
    def process_query(self, query: str, callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Process a single query through the orchestrator without starting a conversation.
        
        Args:
            query: The customer query to process
            callback: Optional callback function to receive the response
            
        Returns:
            The generated response
        """
        try:
            logger.info(f"Processing query through orchestrator: {query}")
            response = self.orchestrator.process_query(query)
            
            # If a callback is provided, call it with the response
            if callback:
                callback(response)
                
            return response
        except Exception as e:
            error_message = f"Error processing query: {str(e)}"
            logger.error(error_message)
            
            # Call callback with error message if provided
            if callback:
                callback(f"I'm sorry, I encountered an error: {str(e)}. Please try again later.")
                
            return f"I'm sorry, I encountered an error: {str(e)}. Please try again later."
    
    # Function implementations for AutoGen integration
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze a customer query using the query analyzer.
        
        Args:
            query: The customer's question
            
        Returns:
            Dictionary with query analysis results
        """
        return self.orchestrator.query_analyzer.classify_query(query)
    
    def _retrieve_information(self, 
                            query_analysis: Dict[str, Any], 
                            n_results: int = 3) -> Dict[str, Any]:
        """
        Retrieve information based on query analysis.
        
        Args:
            query_analysis: Query analysis results
            n_results: Number of results to retrieve
            
        Returns:
            Dictionary with retrieval results
        """
        return self.orchestrator.retrieval_agent.retrieve_information(query_analysis, n_results)
    
    def _generate_response(self, 
                         query: str, 
                         retrieval_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a response based on retrieved information.
        
        Args:
            query: The original customer query
            retrieval_results: Results from information retrieval
            
        Returns:
            Dictionary with the generated response
        """
        return self.orchestrator.response_generator.generate_response(query, retrieval_results)
    
    def _process_complete_query(self, query: str) -> Dict[str, Any]:
        """
        Process a complete query through all stages.
        
        Args:
            query: The customer's question
            
        Returns:
            Dictionary with complete processing results
        """
        return self.orchestrator.process_query(query)


# Usage example function
def run_autogen_conversation():
    """Run an example conversation with the AutoGen agent system."""
    # Initialize agent system
    agent_system = AutoGenAgentSystem(verbose=True)
    
    # Start conversation
    agent_system.start_conversation(
        "I need help with returning my boAt Airdopes that aren't working properly"
    )


# Direct script execution
if __name__ == "__main__":
    run_autogen_conversation() 