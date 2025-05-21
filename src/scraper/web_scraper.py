#!/usr/bin/env python3
"""
Web scraper for extracting content from boAt's return policy and service center pages.
This scraper actually fetches and parses the real content from the specified URLs.
"""
import requests
from bs4 import BeautifulSoup
import os
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def scrape_url(url, category):
    """
    Scrape content from a URL.
    
    Args:
        url: The URL to scrape
        category: The category of the content (e.g., 'return_policy')
        
    Returns:
        Dictionary containing scraped data
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    logger.info(f"Scraping {url}...")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract the main content
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
            
        # Get text
        text = soup.get_text(separator='\n')
        
        # Break into lines and remove leading/trailing space
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Remove blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # For more structured data, also try to extract specific elements
        main_content = soup.find("div", class_="page-width")
        structured_content = {}
        
        if main_content:
            # Try to extract headings and their content
            sections = []
            headings = main_content.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
            
            for heading in headings:
                heading_text = heading.get_text().strip()
                if heading_text:
                    # Get the content following this heading
                    content_parts = []
                    for sibling in heading.find_next_siblings():
                        if sibling.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                            break
                        if sibling.name in ["p", "div", "ul", "ol"]:
                            content_parts.append(sibling.get_text().strip())
                    
                    if content_parts:
                        sections.append({
                            "title": heading_text,
                            "content": "\n".join(content_parts)
                        })
            
            if sections:
                structured_content["sections"] = sections
            
            # If this is the service center page, try to extract location information
            if "service-center" in url.lower():
                states = []
                current_state = None
                
                # This is a simplistic approach - actual implementation might need
                # to be tailored to the specific structure of the service center page
                for element in main_content.find_all(["h2", "h3", "p", "div"]):
                    text = element.get_text().strip()
                    if not text:
                        continue
                    
                    # Check if this is a state heading (usually shorter text in a heading element)
                    if element.name in ["h2", "h3"] or (len(text) < 50 and text.isupper()):
                        current_state = text
                        states.append({
                            "state": current_state,
                            "locations": []
                        })
                    
                    # If we have a current state and this looks like an address (longer text in a paragraph)
                    elif current_state and element.name == "p" and len(text) > 20:
                        if states:
                            locations = states[-1]["locations"]
                            lines = text.split("\n")
                            
                            if len(lines) >= 1:
                                location = {
                                    "name": lines[0].strip() if len(lines) > 0 else "Unknown",
                                    "address": lines[1].strip() if len(lines) > 1 else text.strip(),
                                    "contact": lines[2].strip() if len(lines) > 2 else ""
                                }
                                locations.append(location)
                
                if states:
                    structured_content["service_centers"] = states
        
        result = {
            "url": url,
            "category": category,
            "raw_content": text,
            "structured_content": structured_content
        }
        
        logger.info(f"Successfully scraped {url}")
        return result
        
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return {
            "url": url,
            "category": category,
            "raw_content": f"Error: {str(e)}",
            "structured_content": {}
        }

def categorize_url(url):
    """Determine the category of a URL based on its path."""
    if "return-policy" in url.lower():
        return "return_policy"
    elif "service-center" in url.lower():
        return "service_center"
    else:
        return "unknown"

def read_links_file(file_path):
    """
    Read and parse the links from the links.txt file.
    
    Args:
        file_path: Path to the links.txt file
        
    Returns:
        List of tuples (url, category)
    """
    urls = []
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
            
        category = None
        for line in lines:
            line = line.strip()
            if line.startswith("##"):
                category = line[2:].strip()
            elif line.startswith("http"):
                # Clean up URL (remove spaces, etc.)
                url = line.replace(" ", "")
                
                # If category is not specified via ##, determine from URL
                if not category:
                    category = categorize_url(url)
                    
                urls.append((url, category))
                
        logger.info(f"Read {len(urls)} URLs from {file_path}")
        return urls
        
    except Exception as e:
        logger.error(f"Error reading links file {file_path}: {e}")
        return []

def process_raw_content(scraped_data):
    """
    Process the raw scraped content into more usable formats.
    
    Args:
        scraped_data: List of dictionaries containing scraped data
        
    Returns:
        Dictionary with processed data by category
    """
    processed_data = {}
    
    for item in scraped_data:
        category = item["category"]
        url = item["url"]
        
        if "structured_content" in item and item["structured_content"]:
            # We have structured content
            if category == "return_policy" and "sections" in item["structured_content"]:
                processed_data["return_policy"] = item["structured_content"]["sections"]
                
            elif category == "service_center" and "service_centers" in item["structured_content"]:
                processed_data["service_centers"] = item["structured_content"]["service_centers"]
                
        else:
            # Fall back to raw content if no structured content was extracted
            logger.warning(f"No structured content for {url}, using raw content")
            
            if category == "return_policy":
                processed_data["return_policy"] = [{
                    "title": "Return Policy",
                    "content": item["raw_content"]
                }]
                
            elif category == "service_center":
                processed_data["service_centers"] = [{
                    "state": "Unknown",
                    "locations": [{
                        "name": "Service Center",
                        "address": "Contact customer service for details",
                        "contact": "Please visit the website for current contact information"
                    }]
                }]
    
    return processed_data

def main():
    """Run the scraper."""
    print("Running Web Scraper for boAt Customer Support")
    print("=" * 50)
    
    # Get the project root directory
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Create data directory if it doesn't exist
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Read URLs from links.txt
    links_file = os.path.join(project_root, "links.txt")
    urls = read_links_file(links_file)
    
    if not urls:
        logger.error("No URLs found in links.txt. Aborting.")
        return
    
    # Scrape each URL
    scraped_data = []
    for url, category in urls:
        data = scrape_url(url, category)
        scraped_data.append(data)
    
    # Save raw scraped data
    raw_output_file = os.path.join(data_dir, "scraped_content.json")
    with open(raw_output_file, "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, indent=2)
    
    logger.info(f"Saved raw scraped data to {raw_output_file}")
    
    # Process the raw content into more usable formats
    processed_data = process_raw_content(scraped_data)
    
    # Save return policy data if available
    if "return_policy" in processed_data:
        return_policy_file = os.path.join(data_dir, "return_policy.json")
        with open(return_policy_file, "w", encoding="utf-8") as f:
            json.dump(processed_data["return_policy"], f, indent=2)
        logger.info(f"Saved return policy data to {return_policy_file}")
    
    # Save service center data if available
    if "service_centers" in processed_data:
        service_centers_file = os.path.join(data_dir, "service_centers.json")
        with open(service_centers_file, "w", encoding="utf-8") as f:
            json.dump(processed_data["service_centers"], f, indent=2)
        logger.info(f"Saved service centers data to {service_centers_file}")
    
    print(f"\nScraped {len(scraped_data)} URLs")
    print("\nData files generated:")
    print(f"- {raw_output_file}")
    
    if "return_policy" in processed_data:
        print(f"- {os.path.join(data_dir, 'return_policy.json')}")
    
    if "service_centers" in processed_data:
        print(f"- {os.path.join(data_dir, 'service_centers.json')}")

if __name__ == "__main__":
    main() 