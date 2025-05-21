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
import re
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
    
    # Use Playwright for dynamic scraping of both pages
    try:
        import asyncio
        try:
            # Try direct import first (if in same directory)
            from playwright_scraper import scrape_service_centers
        except ImportError:
            try:
                # Try package import (from project structure)
                from src.scraper.playwright_scraper import scrape_service_centers
            except ImportError:
                # If still not found, try installing and importing playwright
                logger.info("Playwright not found. Attempting to install...")
                import subprocess
                import sys
                
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
                    subprocess.check_call([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"])
                    
                    # Now try to import again
                    try:
                        from playwright_scraper import scrape_service_centers
                    except ImportError:
                        try:
                            from src.scraper.playwright_scraper import scrape_service_centers
                        except ImportError:
                            raise ImportError("Could not import playwright_scraper even after installation")
                except Exception as e:
                    logger.error(f"Failed to install Playwright: {e}")
                    raise ImportError("Failed to install Playwright")
        
        logger.info("Using Playwright for scraping...")
        
        if "service-center" in url.lower():
            # Use the existing service center scraping function
            try:
                result = asyncio.run(scrape_service_centers(url))
                # Verify we got actual data
                if (result and "structured_content" in result and 
                    "service_centers" in result["structured_content"] and
                    len(result["structured_content"]["service_centers"]) > 0):
                    
                    # Clean up any "ref: <Node>" entries
                    if "structured_content" in result and "service_centers" in result["structured_content"]:
                        for state in result["structured_content"]["service_centers"]:
                            # Filter out any problematic locations
                            state["locations"] = [loc for loc in state.get("locations", []) 
                                               if loc.get("name") != "ref: <Node>"]
                    
                    logger.info("Successfully scraped service centers with Playwright")
                    return result
                else:
                    logger.warning("Playwright scraper did not return valid data for service centers. Falling back to static scraping.")
                    return scrape_url_static(url, category)
            except Exception as e:
                logger.error(f"Error using Playwright for service centers: {e}")
                logger.info("Falling back to static scraping...")
                return scrape_url_static(url, category)
        elif "return-policy" in url.lower():
            # Create a generic page scraping function for the return policy page
            try:
                # Import or create a function to scrape generic pages
                try:
                    from playwright_generic_scraper import scrape_generic_page
                except ImportError:
                    # Define a simple generic page scraper using playwright if not imported
                    async def scrape_generic_page(page_url):
                        import asyncio
                        from playwright.async_api import async_playwright
                        
                        result = {
                            "url": page_url,
                            "category": "return_policy",
                            "raw_content": "",
                            "structured_content": {}
                        }
                        
                        async with async_playwright() as p:
                            browser = await p.chromium.launch(headless=True)
                            page = await browser.new_page()
                            
                            try:
                                await page.goto(page_url, wait_until="networkidle")
                                
                                # Extract text content
                                text_content = await page.evaluate("""
                                    () => {
                                        // Remove scripts, styles, and hidden elements
                                        const elements = document.querySelectorAll('script, style, [style*="display:none"]');
                                        for (const element of elements) {
                                            element.remove();
                                        }
                                        return document.body.innerText;
                                    }
                                """)
                                
                                # Update raw_content with processed text instead of HTML
                                result["raw_content"] = text_content
                                
                                # Get structured content - try multiple strategies
                                # Strategy 1: Extract headings and their content
                                sections = await page.evaluate("""
                                    () => {
                                        const sections = [];
                                        const headings = document.querySelectorAll('.page-width h1, .page-width h2, .page-width h3, .page-width h4, .page-width h5, .page-width h6');
                                        
                                        for (const heading of headings) {
                                            const title = heading.innerText.trim();
                                            if (!title) continue;
                                            
                                            // Get content elements after this heading until the next heading
                                            let contentHtml = '';
                                            let contentText = '';
                                            let currentElement = heading.nextElementSibling;
                                            
                                            while (currentElement && !currentElement.matches('h1, h2, h3, h4, h5, h6')) {
                                                contentHtml += currentElement.outerHTML;
                                                contentText += currentElement.innerText.trim() + '\\n';
                                                currentElement = currentElement.nextElementSibling;
                                            }
                                            
                                            if (contentText) {
                                                sections.push({
                                                    title: title,
                                                    content: contentText.trim()
                                                });
                                            }
                                        }
                                        
                                        return sections;
                                    }
                                """)
                                
                                # Add structured content
                                if sections and len(sections) > 0:
                                    result["structured_content"]["sections"] = sections
                                    
                                # Strategy 2: If no sections were found, try to extract by paragraphs
                                if not sections or len(sections) == 0:
                                    sections = await page.evaluate("""
                                        () => {
                                            const mainContent = document.querySelector('.page-width');
                                            if (!mainContent) return [];
                                            
                                            const paragraphs = mainContent.querySelectorAll('p');
                                            if (paragraphs.length === 0) return [];
                                            
                                            // Group paragraphs into sections
                                            let currentTitle = "Return Policy";
                                            let currentContent = [];
                                            const sections = [];
                                            
                                            for (const p of paragraphs) {
                                                const text = p.innerText.trim();
                                                if (!text) continue;
                                                
                                                // Check if this paragraph looks like a heading
                                                const isHeading = text.length < 100 && 
                                                                (text.endsWith(':') || 
                                                                 text.toUpperCase() === text ||
                                                                 p.classList.contains('bold') ||
                                                                 window.getComputedStyle(p).fontWeight > 500);
                                                
                                                if (isHeading) {
                                                    // Save the previous section if it exists
                                                    if (currentContent.length > 0) {
                                                        sections.push({
                                                            title: currentTitle,
                                                            content: currentContent.join('\\n')
                                                        });
                                                    }
                                                    
                                                    // Start a new section
                                                    currentTitle = text;
                                                    currentContent = [];
                                                } else {
                                                    currentContent.push(text);
                                                }
                                            }
                                            
                                            // Add the last section
                                            if (currentContent.length > 0) {
                                                sections.push({
                                                    title: currentTitle,
                                                    content: currentContent.join('\\n')
                                                });
                                            }
                                            
                                            return sections;
                                        }
                                    """)
                                    
                                    if sections and len(sections) > 0:
                                        result["structured_content"]["sections"] = sections
                                
                                # Strategy 3: Simple extraction
                                if not result["structured_content"].get("sections") or len(result["structured_content"].get("sections", [])) == 0:
                                    page_content_div = await page.query_selector('.page-width')
                                    if page_content_div:
                                        content_text = await page_content_div.inner_text()
                                        if content_text:
                                            result["structured_content"]["sections"] = [{
                                                "title": "Return Policy",
                                                "content": content_text.strip()
                                            }]
                                
                                return result
                            finally:
                                await browser.close()
                
                # Scrape the return policy page using Playwright
                logger.info("Scraping return policy with Playwright...")
                result = asyncio.run(scrape_generic_page(url))
                
                # Verify the result
                if (result and "structured_content" in result and 
                    "sections" in result["structured_content"] and 
                    len(result["structured_content"]["sections"]) > 0):
                    
                    logger.info("Successfully scraped return policy with Playwright")
                    return result
                else:
                    logger.warning("Playwright didn't extract structured content for return policy. Falling back to static scraping.")
                    return scrape_url_static(url, category)
            except Exception as e:
                logger.error(f"Error using Playwright for return policy: {e}")
                logger.info("Falling back to static scraping...")
                return scrape_url_static(url, category)
        else:
            # For other URLs, use static scraping
            return scrape_url_static(url, category)
                
    except ImportError as e:
        logger.warning(f"Playwright not available: {e}")
        logger.info("Using static scraping instead")
        return scrape_url_static(url, category)

def scrape_url_static(url, category):
    """Static scraping method using requests and BeautifulSoup."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
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
                
            # For service center pages, try to extract state and location information
            if category == "service_center":
                # Look for state headings and accordion buttons
                state_elements = main_content.find_all("button", class_="accordion") or main_content.find_all("h2") or main_content.find_all("h3")
                states = []
                
                if not state_elements:
                    # If no accordion buttons found, try to find states by matching common state names
                    common_states = ["Delhi", "Mumbai", "Chennai", "Kolkata", "Punjab", "Uttar Pradesh", 
                                   "West Bengal", "Haryana", "Bihar", "Gujarat", "Rajasthan", 
                                   "Maharashtra", "Karnataka", "Tamil Nadu", "Kerala", "Telangana"]
                    
                    for state_name in common_states:
                        # Look for elements containing state names
                        elements = soup.find_all(string=re.compile(f"\\b{state_name}\\b"))
                        if elements:
                            state_elements.extend(elements)
                
                for state_elem in state_elements:
                    if hasattr(state_elem, 'get_text'):
                        state_name = state_elem.get_text().strip()
                    else:
                        state_name = str(state_elem).strip()
                        
                    if not state_name:
                        continue
                    
                    # Try to find the panel that follows this accordion button
                    locations = []
                    
                    if hasattr(state_elem, 'find_next'):
                        panel = state_elem.find_next("div", class_="panel")
                        
                        if panel:
                            # Find all entries inside the panel
                            entries = panel.find_all("div", class_="service-center-entry") or panel.find_all("p")
                            
                            for entry in entries:
                                entry_text = entry.get_text().strip()
                                if not entry_text:
                                    continue
                                
                                lines = entry_text.split('\n')
                                name = lines[0].strip() if len(lines) > 0 else "Unknown"
                                address = '\n'.join(lines[1:-1]) if len(lines) > 2 else (lines[1] if len(lines) > 1 else "")
                                contact = lines[-1] if len(lines) > 1 else ""
                                
                                locations.append({
                                    "name": name,
                                    "address": address,
                                    "contact": contact
                                })
                    
                    states.append({
                        "state": state_name,
                        "locations": locations
                    })
                
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
        logger.error(f"Error static scraping {url}: {e}")
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
    
    # If links.txt doesn't exist, create it with default URLs
    if not os.path.exists(links_file):
        logger.info(f"Creating links.txt with default URLs")
        with open(links_file, "w") as f:
            f.write("## return_policy\n")
            f.write("https://www.boat-lifestyle.com/pages/return-policy\n")
            f.write("## service_center\n")
            f.write("https://www.boat-lifestyle.com/pages/service-center-list\n")
            
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
    
    # Check if we already have playwright_service_centers.json and use that data if it exists
    playwright_file = os.path.join(data_dir, "playwright_service_centers.json")
    if os.path.exists(playwright_file):
        try:
            logger.info(f"Found existing Playwright service center data at {playwright_file}")
            with open(playwright_file, "r", encoding="utf-8") as f:
                playwright_data = json.load(f)
                
            # Check if the data is valid
            if (playwright_data and "structured_content" in playwright_data and 
                "service_centers" in playwright_data["structured_content"]):
                # Check if we have any service center entries with actual locations
                has_valid_entries = False
                for state in playwright_data["structured_content"]["service_centers"]:
                    if state.get("locations") and len(state.get("locations", [])) > 0:
                        has_valid_entries = True
                        break
                        
                if has_valid_entries:
                    logger.info("Using existing Playwright service center data")
                    # Add this to scraped_data for consistency
                    for i, item in enumerate(scraped_data):
                        if item["category"] == "service_center":
                            scraped_data[i] = playwright_data
                            break
                    
                    # Save the updated scraped_data
                    with open(raw_output_file, "w", encoding="utf-8") as f:
                        json.dump(scraped_data, f, indent=2)
                    logger.info(f"Updated {raw_output_file} with Playwright service center data")
                    
                    # Update processed_data too
                    if "service_centers" in processed_data:
                        processed_data["service_centers"] = playwright_data["structured_content"]["service_centers"]
                        
                        # Save the updated service centers data
                        with open(service_centers_file, "w", encoding="utf-8") as f:
                            json.dump(processed_data["service_centers"], f, indent=2)
                        logger.info(f"Updated {service_centers_file} with Playwright service center data")
        except Exception as e:
            logger.error(f"Error processing Playwright service center data: {e}")
    
    print(f"\nScraped {len(scraped_data)} URLs")
    print("\nData files generated:")
    print(f"- {raw_output_file}")
    
    if "return_policy" in processed_data:
        print(f"- {os.path.join(data_dir, 'return_policy.json')}")
    
    if "service_centers" in processed_data:
        print(f"- {os.path.join(data_dir, 'service_centers.json')}")

if __name__ == "__main__":
    main() 