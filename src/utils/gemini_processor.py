#!/usr/bin/env python3
"""
Gemini-based processor for scraped content.

This module uses Google's Gemini model to extract structured information
from boAt's return policy and service center pages.
"""

import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import Google's Gemini API
try:
    import google.generativeai as genai
except ImportError:
    print("Google Generative AI package not found. Installing...")
    import subprocess
    subprocess.check_call(["pip", "install", "google-generativeai"])
    import google.generativeai as genai

class GeminiProcessor:
    """Process scraped content using Google's Gemini model."""
    
    def __init__(self):
        """
        Initialize the Gemini processor.
        Loads API key from environment variables.
        """
        # Get API key from environment
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        
        if not self.api_key:
            # Try alternative env variable
            self.api_key = os.environ.get("GEMINI_API_KEY")
            
        if not self.api_key:
            raise ValueError(
                "No API key found in environment variables. "
                "Please set GOOGLE_API_KEY in your .env file."
            )
        
        # Configure the Gemini API
        genai.configure(api_key=self.api_key)
        
        # Get the model (using Gemini Pro as default)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    def process_return_policy(self, content: str) -> Dict[str, Any]:
        """
        Process return policy content using Gemini.
        
        Args:
            content: Raw scraped content from return policy page
            
        Returns:
            Dictionary with structured return policy information
        """
        prompt = f"""
        Extract structured information from this boAt Return Policy page content. 
        Focus on the following aspects:
        1. Replacement policy details (timeframe, conditions)
        2. Non-replacement conditions
        3. Cancellation policy details
        4. Return/refund policy summary
        
        Format the response as a JSON object with these keys:
        - replacement_timeframe: Number of days for replacement
        - replacement_conditions: List of conditions when replacement is allowed
        - non_replacement_conditions: List of conditions when replacement is not allowed
        - cancellation_conditions: List of conditions related to cancellation
        - return_policy_summary: A concise summary of the overall policy
        
        Here's the content:
        {content}
        
        Return ONLY the JSON object, nothing else.
        """
        
        response = self.model.generate_content(prompt)
        
        # Extract JSON from response
        try:
            # Try to parse the response text as JSON
            result = json.loads(response.text)
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from the text
            try:
                # Look for JSON-like content between triple backticks
                json_text = response.text.split("```json")[1].split("```")[0].strip()
                result = json.loads(json_text)
            except (IndexError, json.JSONDecodeError):
                # If that fails too, create a basic structure with the raw response
                result = {
                    "error": "Could not parse JSON from response",
                    "raw_response": response.text,
                    "replacement_timeframe": None,
                    "replacement_conditions": [],
                    "non_replacement_conditions": [],
                    "cancellation_conditions": [],
                    "return_policy_summary": "Policy could not be structured automatically."
                }
        
        return result
    
    def process_service_centers(self, content: str) -> Dict[str, Any]:
        """
        Process service center content using Gemini.
        
        Args:
            content: Raw scraped content from service centers page
            
        Returns:
            Dictionary with structured service center information
        """
        prompt = f"""
        Extract structured information from this boAt Service Centers page content.
        Focus on the following aspects:
        1. List of states where service centers are available
        2. Service center hours/timing information
        3. Holiday information (when centers are closed)
        4. Contact details for customer support
        
        Format the response as a JSON object with these keys:
        - states_with_centers: List of state names where centers are available
        - service_hours: Information about operating hours
        - holiday_info: Information about holidays/closures
        - contact_details: Contact information for customer support
        
        Here's the content:
        {content}
        
        Return ONLY the JSON object, nothing else.
        """
        
        response = self.model.generate_content(prompt)
        
        # Extract JSON from response
        try:
            # Try to parse the response text as JSON
            result = json.loads(response.text)
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from the text
            try:
                # Look for JSON-like content between triple backticks
                json_text = response.text.split("```json")[1].split("```")[0].strip()
                result = json.loads(json_text)
            except (IndexError, json.JSONDecodeError):
                # If that fails too, create a basic structure with the raw response
                result = {
                    "error": "Could not parse JSON from response",
                    "raw_response": response.text,
                    "states_with_centers": [],
                    "service_hours": None,
                    "holiday_info": None,
                    "contact_details": None
                }
        
        return result
    
    def process_scraped_json(self, input_file: str, output_file: Optional[str] = None) -> Dict:
        """
        Process the scraped JSON content file into structured data.
        
        Args:
            input_file: Path to input JSON file
            output_file: Optional path to save processed output
            
        Returns:
            Processed and structured content dictionary
        """
        with open(input_file, 'r', encoding='utf-8') as f:
            scraped_data = json.load(f)
        
        processed_data = []
        
        for item in scraped_data:
            processed_item = {
                'url': item['url'],
                'category': item['category'],
                'raw_content': item['raw_content'],
                'structured_content': {}
            }
            
            # Process the content based on category
            if item['category'] == 'Return Policy':
                structured_content = self.process_return_policy(item['raw_content'])
                processed_item['structured_content'] = structured_content
                
            elif item['category'] == 'Service Centers':
                structured_content = self.process_service_centers(item['raw_content'])
                processed_item['structured_content'] = structured_content
            
            processed_data.append(processed_item)
        
        # Save to output file if specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, indent=2, ensure_ascii=False)
        
        return processed_data
    
    def prepare_for_vectordb(self, processed_data: List[Dict]) -> List[Dict[str, Any]]:
        """
        Prepare processed data for insertion into a vector database.
        
        Args:
            processed_data: List of processed data items
            
        Returns:
            List of documents ready for vector database insertion
        """
        vector_docs = []
        
        for item in processed_data:
            category = item['category']
            url = item['url']
            
            if category == 'Return Policy':
                structured = item.get('structured_content', {})
                
                # Create a document for return policy
                text_content = "boAt Return and Replacement Policy:\n\n"
                
                if structured.get('replacement_timeframe'):
                    text_content += f"boAt offers product replacement within {structured['replacement_timeframe']} days of delivery.\n\n"
                
                if structured.get('replacement_conditions'):
                    text_content += "Products can be replaced under these conditions:\n"
                    for i, condition in enumerate(structured['replacement_conditions'], 1):
                        text_content += f"{i}. {condition}\n"
                    text_content += "\n"
                
                if structured.get('non_replacement_conditions'):
                    text_content += "Products will NOT be replaced under these conditions:\n"
                    for i, condition in enumerate(structured['non_replacement_conditions'], 1):
                        text_content += f"{i}. {condition}\n"
                    text_content += "\n"
                
                if structured.get('cancellation_conditions'):
                    text_content += "Order cancellation policy:\n"
                    for i, condition in enumerate(structured['cancellation_conditions'], 1):
                        text_content += f"{i}. {condition}\n"
                    text_content += "\n"
                
                if structured.get('return_policy_summary'):
                    text_content += f"Summary: {structured['return_policy_summary']}"
                
                vector_docs.append({
                    'id': 'boat_return_replacement_policy',
                    'text': text_content,
                    'metadata': {
                        'category': category,
                        'source_url': url,
                        'contains_refund_info': 'refund' in text_content.lower(),
                        'contains_cancellation_info': 'cancellation' in text_content.lower()
                    }
                })
            
            elif category == 'Service Centers':
                structured = item.get('structured_content', {})
                
                # Create a document for service centers
                text_content = "boAt Service Center Information:\n\n"
                
                if structured.get('states_with_centers'):
                    text_content += "boAt has service centers in the following states:\n"
                    for state in structured['states_with_centers']:
                        text_content += f"- {state}\n"
                    text_content += "\n"
                
                if structured.get('service_hours'):
                    text_content += f"Service Hours: {structured['service_hours']}\n\n"
                
                if structured.get('holiday_info'):
                    text_content += f"Holiday Information: {structured['holiday_info']}\n\n"
                
                if structured.get('contact_details'):
                    text_content += f"Customer Support Contact:\n{structured['contact_details']}"
                
                vector_docs.append({
                    'id': 'boat_service_center_locations',
                    'text': text_content,
                    'metadata': {
                        'category': category,
                        'source_url': url,
                        'state_count': len(structured.get('states_with_centers', [])),
                        'has_contact_info': bool(structured.get('contact_details'))
                    }
                })
        
        return vector_docs

def main():
    """Process scraped content with Gemini."""
    parser = argparse.ArgumentParser(description="Process scraped content using Gemini")
    parser.add_argument("--input", "-i", default="../../data/scraped_content.json", 
                        help="Path to input scraped content JSON file")
    parser.add_argument("--output", "-o", default="../../data/gemini_processed.json",
                        help="Path to output processed content JSON file")
    parser.add_argument("--vector-output", "-v", default="../../data/gemini_vector_docs.json",
                        help="Path to output vector docs JSON file")
    
    args = parser.parse_args()
    
    # Resolve relative paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, args.input)
    output_path = os.path.join(script_dir, args.output)
    vector_output_path = os.path.join(script_dir, args.vector_output)
    
    # Make sure output directories exist
    Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
    Path(os.path.dirname(vector_output_path)).mkdir(parents=True, exist_ok=True)
    
    print(f"Processing scraped content from: {input_path}")
    
    try:
        # Initialize processor (without API key argument)
        processor = GeminiProcessor()
        
        # Process the scraped content
        processed_data = processor.process_scraped_json(input_path, output_path)
        
        print(f"Structured content saved to: {output_path}")
        
        # Prepare documents for vector database
        vector_docs = processor.prepare_for_vectordb(processed_data)
        
        # Save vector docs
        with open(vector_output_path, 'w', encoding='utf-8') as f:
            json.dump(vector_docs, f, indent=2, ensure_ascii=False)
        
        print(f"Vector database documents saved to: {vector_output_path}")
        
    except Exception as e:
        print(f"Error processing content: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 