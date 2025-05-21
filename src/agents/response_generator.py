#!/usr/bin/env python3
"""
Response Generator Agent for boAt Customer Support Chatbot.

This module implements a specialized agent for generating human-friendly responses
based on retrieved information from the vector database.
"""

import os
import logging
import json
import google.generativeai as genai
from typing import Dict, List, Any, Optional, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Google Generative AI
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    logger.warning("No Google API key found. Response generation may be limited.")

class ResponseGenerator:
    """
    Specialized agent for generating human-friendly responses from retrieved information.
    
    This class handles:
    - Crafting conversational responses from retrieved documents
    - Formatting responses to match boAt's tone and style
    - Ensuring responses address the original query
    - Handling different query types appropriately
    """
    
    def __init__(self):
        """Initialize the response generator."""
        self.model = None
        try:
            # Initialize Gemini model
            if api_key:
                model_name = "gemini-1.5-flash"  # Use a faster model for production
                self.model = genai.GenerativeModel(model_name)
                logger.info(f"Response generator initialized with {model_name}")
            else:
                logger.warning("No API key available. Response generation will be limited.")
        except Exception as e:
            logger.error(f"Error initializing Gemini model: {e}")
    
    def generate_response(self, 
                         query_text: str,
                         retrieval_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a human-friendly response based on retrieved information.
        
        Args:
            query_text: The original customer query
            retrieval_results: Results from the retrieval agent
            
        Returns:
            Dictionary containing the generated response and metadata
        """
        # Extract information from retrieval results
        query_type = retrieval_results.get("query_type", "general")
        primary_results = retrieval_results.get("primary_results", {})
        has_secondary_results = retrieval_results.get("has_secondary_results", False)
        secondary_results = retrieval_results.get("secondary_results", {})
        
        # Check if we have documents
        primary_documents = primary_results.get("documents", [])
        if not primary_documents:
            return self._generate_fallback_response(query_text, query_type)
        
        # Generate a context string from the retrieved documents
        context = self._prepare_context(query_type, primary_documents, secondary_results if has_secondary_results else {})
        
        # Generate response using Gemini
        response_text = self._generate_with_llm(query_text, query_type, context)
        
        # Create response object
        response = {
            "response_text": response_text,
            "query_text": query_text,
            "query_type": query_type,
            "sources_used": len(primary_documents),
            "generated_at": self._get_timestamp()
        }
        
        logger.info(f"Generated response for query type: {query_type}")
        return response
    
    def _prepare_context(self, 
                        query_type: str, 
                        primary_documents: List[Dict[str, Any]],
                        secondary_results: Dict[str, Any]) -> str:
        """
        Prepare a context string from retrieved documents for the LLM.
        
        Args:
            query_type: Type of the query
            primary_documents: Main retrieved documents
            secondary_results: Secondary retrieved documents
            
        Returns:
            Context string for the LLM
        """
        context_parts = ["### Retrieved Information:"]
        
        # Process primary documents
        context_parts.append(f"\n## Primary Information ({query_type}):")
        
        for i, doc in enumerate(primary_documents):
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            
            if query_type == "service_center":
                # Format service center information
                state = metadata.get("state", "N/A")
                address = metadata.get("address", "N/A")
                contact = metadata.get("contact", "N/A")
                
                context_parts.append(f"\nService Center {i+1}:")
                context_parts.append(f"State: {state}")
                context_parts.append(f"Address: {address}")
                context_parts.append(f"Contact: {contact}")
                context_parts.append(f"Additional Info: {content}")
                
            elif query_type == "return_policy" or query_type == "warranty":
                # Format return policy information
                title = metadata.get("title", "Policy Information")
                context_parts.append(f"\nPolicy {i+1}: {title}")
                context_parts.append(f"{content}")
                
            else:
                # General format for other document types
                context_parts.append(f"\nDocument {i+1}:")
                # Add metadata if available
                for key, value in metadata.items():
                    if key not in ["embedding"]:  # Skip embedding vectors
                        context_parts.append(f"{key}: {value}")
                context_parts.append(f"Content: {content}")
        
        # Process secondary results if available
        if secondary_results:
            context_parts.append("\n## Secondary Information:")
            
            for intent, results in secondary_results.items():
                context_parts.append(f"\nRelated Information ({intent}):")
                secondary_docs = results.get("documents", [])
                
                for i, doc in enumerate(secondary_docs):
                    content = doc.get("content", "")
                    metadata = doc.get("metadata", {})
                    
                    # Add a summary line from this secondary document
                    if content:
                        # Just take the first sentence or first 100 chars
                        summary = content.split('.')[0] + '.' if '.' in content else content[:100] + '...'
                        context_parts.append(f"{summary}")
        
        return "\n".join(context_parts)
    
    def _generate_with_llm(self, 
                          query: str, 
                          query_type: str, 
                          context: str) -> str:
        """
        Generate a response using Gemini.
        
        Args:
            query: The customer query
            query_type: Type of the query
            context: Context information from retrieved documents
            
        Returns:
            Generated response text
        """
        if not self.model:
            return self._fallback_response_template(query, query_type)
        
        try:
            # Create the prompt for Gemini
            prompt = self._create_generation_prompt(query, query_type, context)
            
            # Generate response
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # If no response was generated, use fallback
            if not response_text:
                return self._fallback_response_template(query, query_type)
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating response with Gemini: {e}")
            return self._fallback_response_template(query, query_type)
    
    def _create_generation_prompt(self, 
                                query: str, 
                                query_type: str, 
                                context: str) -> str:
        """
        Create a prompt for the Gemini model.
        
        Args:
            query: The customer query
            query_type: Type of the query
            context: Context information from retrieved documents
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a helpful boAt customer support assistant. Generate a friendly, concise, and accurate response to the customer query below, based on the provided information.

Customer Query: {query}

{context}

Guidelines:
1. Respond in a friendly and professional tone that matches boAt's brand voice
2. Be concise but thorough - address the specific question asked
3. Only use facts from the provided information
4. If talking about service centers, provide complete address and contact details
5. For return policy questions, be specific about time periods and conditions
6. If the information is incomplete, acknowledge limitations without making up details

Response:"""

        return prompt
    
    def _generate_fallback_response(self, 
                                   query: str, 
                                   query_type: str) -> Dict[str, Any]:
        """
        Generate a fallback response when no documents are retrieved.
        
        Args:
            query: The customer query
            query_type: Type of the query
            
        Returns:
            Response dictionary
        """
        response_text = self._fallback_response_template(query, query_type)
        
        response = {
            "response_text": response_text,
            "query_text": query,
            "query_type": query_type,
            "sources_used": 0,
            "is_fallback": True,
            "generated_at": self._get_timestamp()
        }
        
        logger.warning(f"Used fallback response for query type: {query_type}")
        return response
    
    def _fallback_response_template(self, 
                                   query: str, 
                                   query_type: str) -> str:
        """
        Create a fallback response based on query type.
        
        Args:
            query: The customer query
            query_type: Type of the query
            
        Returns:
            Fallback response text
        """
        if query_type == "return_policy":
            return """I'd be happy to help with your question about boAt's return policy. However, I don't have all the specific details at the moment.

For the most accurate and up-to-date information about returns, replacements, or refunds, I recommend:

1. Visiting boAt's official website at www.boat-lifestyle.com
2. Checking the 'Return Policy' section under customer support
3. Contacting boAt customer service directly at +912249461882 or info@imaginemarketingindia.com

They'll be able to provide you with the exact information for your situation."""

        elif query_type == "service_center":
            return """I'd like to help you locate a boAt service center. While I don't have the complete list of service centers right now, here's how you can find this information:

1. Visit boAt's official website at www.boat-lifestyle.com
2. Go to the 'Support' or 'Service Centers' section
3. Enter your location to find the nearest service center
4. Alternatively, contact boAt customer service at +912249461882 for immediate assistance

They'll be able to provide you with the address and contact information for the service center nearest to you."""

        else:
            return """Thank you for your question about boAt products. I'd like to help, but I don't have all the specific information needed to answer your query completely at the moment.

For the most accurate and current information, I recommend:

1. Visiting the official boAt website at www.boat-lifestyle.com
2. Contacting boAt customer service directly at +912249461882 or info@imaginemarketingindia.com

They'll be able to assist you with your specific question and provide the most up-to-date information."""
    
    def _get_timestamp(self) -> str:
        """Get the current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


# Test function for direct module execution
def test_response_generator():
    """
    Test the response generator with sample retrieval results.
    """
    generator = ResponseGenerator()
    
    # Sample retrieval results
    sample_retrieval = {
        "query_text": "What is boAt's return policy for damaged items?",
        "query_type": "return_policy",
        "primary_results": {
            "documents": [
                {
                    "content": "boAt offers a 7-day return policy for damaged or defective items. The item must be returned in its original packaging with all accessories. Shipping costs for returns are covered by boAt for defective items.",
                    "metadata": {
                        "title": "Return Policy - Damaged Items",
                        "score": 0.85
                    }
                },
                {
                    "content": "For items damaged during shipping, customers must report the damage within 24 hours of receiving the product. Photo evidence of the damage may be required.",
                    "metadata": {
                        "title": "Shipping Damage Policy",
                        "score": 0.76
                    }
                }
            ],
            "metadata": {
                "retrieved": 2,
                "source": "return_policy_collection"
            }
        },
        "has_secondary_results": False,
        "secondary_results": {}
    }
    
    # Generate response
    print("Testing Response Generator...")
    response = generator.generate_response(
        sample_retrieval["query_text"],
        sample_retrieval
    )
    
    # Print results
    print(f"\nQuery: {response['query_text']}")
    print(f"Query Type: {response['query_type']}")
    print(f"Sources Used: {response['sources_used']}")
    print(f"Generated At: {response['generated_at']}")
    print("\nResponse:")
    print(response['response_text'])


# Run test if module is executed directly
if __name__ == "__main__":
    test_response_generator() 