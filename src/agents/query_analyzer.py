#!/usr/bin/env python3
"""
Query Analyzer Agent for boAt Customer Support Chatbot.

This module implements a specialized agent for analyzing customer queries,
classifying them by type, and extracting key parameters for information retrieval.
"""

import os
import logging
import json
import re
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Types of queries that can be handled by the system."""
    RETURN_POLICY = "return_policy"
    SERVICE_CENTER = "service_center"
    WARRANTY = "warranty"
    PRODUCT_ISSUE = "product_issue"
    GENERAL = "general"
    UNKNOWN = "unknown"

class QueryAnalyzer:
    """
    Specialized agent for analyzing customer queries about boAt products and services.
    
    This class handles:
    - Query classification (return policy, service center location, etc.)
    - Entity and parameter extraction
    - Query refinement for ambiguous questions
    """
    
    def __init__(self):
        """Initialize the query analyzer."""
        # Keywords for different query types
        self.return_keywords = [
            "return", "refund", "replacement", "exchange", "cancel", "ship back",
            "money back", "change my mind", "don't want", "send back", 
            "return policy", "return period", "return window", "days to return"
        ]
        
        self.service_keywords = [
            "service center", "repair center", "service shop", "repair shop", 
            "fix", "repair", "broken", "damage", "not working", "service location",
            "nearest center", "closest center", "repair facility", "where can I get it fixed"
        ]
        
        self.warranty_keywords = [
            "warranty", "guarantee", "covered", "warranty policy", "warranty period",
            "warranty claim", "warranty coverage", "extend warranty", "warranty card",
            "warranty registration", "one year warranty", "warranty details"
        ]
        
        self.product_issue_keywords = [
            "not charging", "won't turn on", "no sound", "low volume", "battery",
            "not connecting", "bluetooth issue", "not pairing", "stops working",
            "problem with", "issue with", "doesn't work", "defective", "faulty"
        ]
        
        self.states = [
            "Maharashtra", "Delhi", "Karnataka", "Tamil Nadu", "Telangana", 
            "West Bengal", "Gujarat", "Rajasthan", "Uttar Pradesh", "Madhya Pradesh",
            "Punjab", "Haryana", "Kerala", "Andhra Pradesh", "Bihar", "Odisha",
            "Jharkhand", "Assam", "Chhattisgarh", "Uttarakhand", "Himachal Pradesh",
            "Goa", "Chandigarh", "Mumbai", "Bangalore", "Chennai", "Hyderabad", "Kolkata"
        ]
        
        self.products = [
            "headphones", "earphones", "earbuds", "neckband", "speakers", "smartwatch",
            "smart watch", "airdopes", "rockerz", "bassheads", "stone", "aavante", "boat"
        ]
        
        logger.info("Query analyzer initialized")
    
    def classify_query(self, query: str) -> Dict[str, Any]:
        """
        Classify a customer query and extract relevant parameters.
        
        Args:
            query: The customer's question or message
            
        Returns:
            A dictionary with query classification and extracted parameters
        """
        query_lower = query.lower()
        
        # Count matches for each category
        return_count = sum(1 for kw in self.return_keywords if kw.lower() in query_lower)
        service_count = sum(1 for kw in self.service_keywords if kw.lower() in query_lower)
        warranty_count = sum(1 for kw in self.warranty_keywords if kw.lower() in query_lower)
        product_issue_count = sum(1 for kw in self.product_issue_keywords if kw.lower() in query_lower)
        
        # Get the primary query type based on keyword matches
        counts = {
            QueryType.RETURN_POLICY: return_count,
            QueryType.SERVICE_CENTER: service_count,
            QueryType.WARRANTY: warranty_count,
            QueryType.PRODUCT_ISSUE: product_issue_count
        }
        
        max_count = max(counts.values())
        if max_count == 0:
            query_type = QueryType.GENERAL
        else:
            # Get the query type with the highest count
            query_type = max(counts.keys(), key=lambda k: counts[k])
        
        # Extract parameters from query
        params = self._extract_parameters(query, query_type)
        
        # Check for multi-intent queries
        secondary_intents = []
        for qtype, count in counts.items():
            if count > 0 and qtype != query_type:
                secondary_intents.append(qtype.value)
        
        # Refine query if needed
        refined_query = self._refine_query(query, query_type)
        
        result = {
            "query_text": query,
            "refined_query": refined_query,
            "query_type": query_type.value,
            "parameters": params,
            "confidence_scores": {k.value: v/max(max_count, 1) for k, v in counts.items()},
            "has_secondary_intents": len(secondary_intents) > 0,
            "secondary_intents": secondary_intents
        }
        
        logger.info(f"Classified query: {query_type.value} with parameters: {params}")
        return result
    
    def _extract_parameters(self, query: str, query_type: QueryType) -> Dict[str, Any]:
        """
        Extract relevant parameters from the query based on its type.
        
        Args:
            query: The customer's question
            query_type: The classified query type
            
        Returns:
            Dictionary of extracted parameters
        """
        query_lower = query.lower()
        params = {}
        
        # Extract location parameters for service center queries
        if query_type == QueryType.SERVICE_CENTER:
            # Look for state/city mentions
            found_locations = []
            for location in self.states:
                if location.lower() in query_lower:
                    found_locations.append(location)
            
            if found_locations:
                params["locations"] = found_locations
        
        # Extract product information
        found_products = []
        for product in self.products:
            if product.lower() in query_lower:
                found_products.append(product)
        
        if found_products:
            params["products"] = found_products
        
        # Extract time parameters for return policy queries
        if query_type == QueryType.RETURN_POLICY:
            # Look for time periods
            time_patterns = [
                r'(\d+)\s*(day|days)',
                r'(\d+)\s*(week|weeks)',
                r'(\d+)\s*(month|months)'
            ]
            
            for pattern in time_patterns:
                matches = re.findall(pattern, query_lower)
                if matches:
                    number, unit = matches[0]
                    params["time_period"] = {
                        "value": int(number),
                        "unit": unit
                    }
                    break
        
        return params
    
    def _refine_query(self, query: str, query_type: QueryType) -> str:
        """
        Refine ambiguous queries to be more specific.
        
        Args:
            query: The original query
            query_type: The classified query type
            
        Returns:
            A refined query that's more specific
        """
        query_lower = query.lower()
        
        # For service center queries without location, make it more general
        if query_type == QueryType.SERVICE_CENTER and "where" in query_lower:
            has_location = any(state.lower() in query_lower for state in self.states)
            if not has_location:
                return "What are the service center locations for boAt products?"
        
        # For return policy queries that are too general
        if query_type == QueryType.RETURN_POLICY and "policy" in query_lower:
            if all(term not in query_lower for term in ["how many days", "how long", "time period"]):
                return "What is the return policy for boAt products, including the return time period?"
        
        # For general product issues, make it more specific if possible
        if query_type == QueryType.PRODUCT_ISSUE:
            if not any(product in query_lower for product in self.products):
                # Try to make it more specific
                if "not charging" in query_lower:
                    return "What should I do if my boAt product is not charging?"
                if "not connecting" in query_lower or "pairing" in query_lower:
                    return "How to fix boAt Bluetooth device that's not connecting or pairing?"
        
        # If no refinement needed, return the original query
        return query


# Test function for direct module execution
def test_query_analyzer():
    """
    Test the query analyzer with sample queries.
    """
    analyzer = QueryAnalyzer()
    
    # Test queries
    test_queries = [
        "What is boAt's return policy for damaged items?",
        "Where can I find a service center in Maharashtra?",
        "How many days do I have to return my Airdopes?",
        "My headphones are not charging, what should I do?",
        "Does the warranty cover water damage?",
        "I want to return my earbuds",
        "Where can I get my smartwatch fixed?",
        "What is the warranty period for Rockerz?",
        "Help me with my boAt speaker",
        "I need service center information",
    ]
    
    for query in test_queries:
        print(f"\n=== Testing Query: '{query}' ===")
        result = analyzer.classify_query(query)
        print(f"Query Type: {result['query_type']}")
        print(f"Parameters: {json.dumps(result['parameters'], indent=2)}")
        if result['refined_query'] != query:
            print(f"Refined Query: {result['refined_query']}")
        print(f"Confidence Scores: {json.dumps(result['confidence_scores'], indent=2)}")
        if result['has_secondary_intents']:
            print(f"Secondary Intents: {result['secondary_intents']}")


# Run test if module is executed directly
if __name__ == "__main__":
    test_query_analyzer()